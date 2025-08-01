import serial                      # 시리얼 통신을 위한 모듈 (아두이노 데이터 수신)
import time                        # 시간 지연 및 타이밍 제어를 위한 모듈
import numpy as np                # 수치 연산을 위한 핵심 라이브러리
from scipy.fft import fft, fftfreq # 푸리에 변환 및 주파수 배열 생성 함수
from scipy.optimize import curve_fit # 비선형 곡선 피팅 함수 (최적화)
import matplotlib.pyplot as plt   # 데이터 시각화를 위한 그래프 라이브러리

# ===== 설정 =====
PORT = "COM3"                         # 센서 데이터가 연결된 아두이노의 시리얼 포트 이름
BAUD = 9600                           # 아두이노와의 통신 속도 (baud rate)
SAMPLING_RATE = 100                  # 센서 데이터 샘플링 주기 (초당 100번 샘플링)
BUFFER_SIZE = 512                    # FFT 수행을 위한 데이터 버퍼 크기
SENSOR_POSITIONS = np.array([0.3, 0.6, 0.9])  # 센서가 설치된 구조물의 상대 위치 (단위: m)

# ===== 2차 모드 형상 함수 =====
BETA = 4.6941  # 2차 모드 형상에서 사용되는 고유 상수 (보의 경계조건에 따라 결정됨)
ETA = 0.9825   # 경계조건을 만족시키는 모드 형상 상수 (BETA에 따라 계산됨)

def mode_shape(x, A):
    # 구조물의 모드 형상(2차 모드 기준)을 계산하는 함수
    term = np.cos(BETA * x) - np.cosh(BETA * x) - ETA * (np.sin(BETA * x) - np.sinh(BETA * x))
    return A * term  # 계산된 모드 형상 진폭 반환


# ===== 시리얼 연결 =====
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)
print("[INFO] Serial 연결됨")

buffer_x = []
buffer_z = []

try:
    while True:
        if ser.in_waiting:  # 시리얼 버퍼에 수신된 데이터가 있는지 확인
            line = ser.readline().decode('utf-8', errors='ignore').strip()  # 한 줄씩 읽어서 디코딩
            if line:  # 읽은 줄이 비어있지 않으면 처리
                parts = line.split(',')  # 쉼표 기준으로 데이터 나누기
                if len(parts) == 6:  # 센서 값 6개가 모두 들어왔을 때만 처리
                    try:
                        # 각 센서의 X, Z축 가속도 값을 정수형으로 변환
                        AcX_1 = int(parts[0])
                        AcZ_1 = int(parts[1])
                        AcX_2 = int(parts[2])
                        AcZ_2 = int(parts[3])
                        AcX_3 = int(parts[4])
                        AcZ_3 = int(parts[5])

                        # X축 가속도 값 3개를 한 줄로 묶어서 버퍼에 추가
                        buffer_x.append([AcX_1, AcX_2, AcX_3])
                        # Z축 가속도 값 3개를 한 줄로 묶어서 버퍼에 추가
                        buffer_z.append([AcZ_1, AcZ_2, AcZ_3])

                        if len(buffer_x) >= BUFFER_SIZE:
                            data_x = np.array(buffer_x[-BUFFER_SIZE:])
                            data_z = np.array(buffer_z[-BUFFER_SIZE:])
                            buffer_x = buffer_x[-BUFFER_SIZE:]
                            buffer_z = buffer_z[-BUFFER_SIZE:]

                            # FFT
                            xf = fftfreq(BUFFER_SIZE, 1 / SAMPLING_RATE)[:BUFFER_SIZE // 2]
                            mags_x, mags_z = [], []

                            for i in range(3):
                                sig_x = data_x[:, i] - np.mean(data_x[:, i])
                                sig_z = data_z[:, i] - np.mean(data_z[:, i])
                                fx = np.abs(fft(sig_x)[:BUFFER_SIZE // 2])
                                fz = np.abs(fft(sig_z)[:BUFFER_SIZE // 2])
                                mags_x.append(fx)
                                mags_z.append(fz)

                           
                            avg_mag = np.sum(mags_x, axis=0) + np.sum(mags_z, axis=0)
                            first_idx = np.argmax(avg_mag)

                            avg_mag_temp = avg_mag.copy()
                            avg_mag_temp[max(0, first_idx - 1):first_idx + 2] = 0  

                            second_idx = np.argmax(avg_mag_temp)

                            freq_gap = np.abs(xf[second_idx] - xf[first_idx])
                            if freq_gap > 1.0:
                                peak_idx = second_idx
                            else:
                                peak_idx = first_idx

                            dom_freq = xf[peak_idx]
                            print(f"[INFO] 지배 진동수 (보정): {dom_freq:.2f} Hz")

                            # 진폭 정규화
                            amps_x = [fx[peak_idx] for fx in mags_x]
                            amps_z = [fz[peak_idx] for fz in mags_z]
                            norm_x = np.array(amps_x) / np.max(np.abs(amps_x))
                            norm_z = np.array(amps_z) / np.max(np.abs(amps_z))

                            # 피팅
                            A_x, _ = curve_fit(mode_shape, SENSOR_POSITIONS, norm_x)
                            A_z, _ = curve_fit(mode_shape, SENSOR_POSITIONS, norm_z)
                            print(f"[INFO] 피팅 계수: A_x = {A_x[0]:.3f}, A_z = {A_z[0]:.3f}")

                            # 시각화
                            x_range = np.linspace(0.2, 1.0, 500)
                            y_fit_x = mode_shape(x_range, A_x[0])
                            y_fit_z = mode_shape(x_range, A_z[0])
                            plt.clf()
                            plt.plot(x_range, y_fit_x, label="X축 피팅", color='blue')
                            plt.plot(x_range, y_fit_z, label="Z축 피팅", color='orange')
                            plt.scatter(SENSOR_POSITIONS, norm_x, color='blue', marker='o', label="X축 센서")
                            plt.scatter(SENSOR_POSITIONS, norm_z, color='orange', marker='s', label="Z축 센서")
                            plt.title(f"X/Z 축 모드 형상 피팅 (2차 모드 중심, f = {dom_freq:.2f} Hz)")
                            plt.xlabel("높이 위치 (m)")
                            plt.ylabel("정규화 진폭")
                            plt.legend()
                            plt.grid(True)
                            plt.pause(0.01)

                    except Exception as e:
                        print("[WARN] 파싱/피팅 오류:", e)

except KeyboardInterrupt:
    print("\n[종료] 사용자 중단")
    ser.close()
