import serial
import time
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# ===== Settings =====
PORT_SENSOR = "COM3"
PORT_MOTOR = "COM9"
BAUD = 9600
SAMPLING_RATE = 100
BUFFER_SIZE = 512
SENSOR_POSITIONS = np.array([0.3, 0.6, 0.9])
structure_height = 85.2
start_norm = 0.5
CM_TO_DEG = 360.0 / 11.0  # cm to degree
ANALYSIS_INTERVAL = 0.5
last_analysis_time = 0

# Mode shape function
def mode_shape_beta(x, A, beta):
    eta = (np.cos(beta) + np.cosh(beta)) / (np.sin(beta) + np.sinh(beta))
    return A * (np.cos(beta * x) - np.cosh(beta * x) - eta * (np.sin(beta * x) - np.sinh(beta * x)))

# Serial connection for sensor
ser_sensor = serial.Serial(PORT_SENSOR, BAUD, timeout=1)
time.sleep(2)
print("[INFO] Sensor serial connected.")

# Live plotting
plt.ion()
fig, ax = plt.subplots()
x_space = np.linspace(0, 1, 1000)

buffer_z = []

try:
    while True:
        if ser_sensor.in_waiting:
            line = ser_sensor.readline().decode('utf-8', errors='ignore').strip()
            if line:
                parts = line.split(',')
                if len(parts) == 6:
                    try:
                        AcX_1 = int(parts[0])
                        AcZ_1 = int(parts[1])
                        AcX_2 = int(parts[2])
                        AcZ_2 = int(parts[3])
                        AcX_3 = int(parts[4])
                        AcZ_3 = int(parts[5])
                        buffer_z.append([AcZ_1, AcZ_2, AcZ_3])

                        if len(buffer_z) >= BUFFER_SIZE and time.time() - last_analysis_time >= ANALYSIS_INTERVAL:
                            last_analysis_time = time.time()
####################################여기까지 수정 완료 / 아래 FFT 부분은 내가 몰라서 너가 해줘야되 고라니율 ㅜㅜ####################################                           

                            data_z = np.array(buffer_z[-BUFFER_SIZE:])
                            sigs = [data_z[:, i] - np.mean(data_z[:, i]) for i in range(3)]

                            xf = fftfreq(BUFFER_SIZE, 1 / SAMPLING_RATE)[:BUFFER_SIZE // 2]
                            mags = [np.abs(fft(sig)[:BUFFER_SIZE // 2]) for sig in sigs]

                            peak_idx = np.argmax(np.sum(mags, axis=0))
                            amps = np.array([np.real(fft(sig)[peak_idx]) for sig in sigs])
                            max_amp = np.max(np.abs(amps))
                            norm_z = amps / max_amp if max_amp != 0 else amps

                            fft_avg_amplitude = np.mean([np.mean(mag) for mag in mags])
                            rms_amplitude = np.mean([np.sqrt(np.mean(sig**2)) for sig in sigs])
                            print(f"[INFO] FFT avg amplitude: {fft_avg_amplitude:.4f}, RMS amplitude: {rms_amplitude:.4f}")

                            try:
                                (A_fit, beta_fit), _ = curve_fit(
                                    mode_shape_beta,
                                    SENSOR_POSITIONS,
                                    norm_z,
                                    p0=[1, 4.6941],
                                    bounds=([0.5, 4.4], [5, 5.0])
                                )
                            except RuntimeError:
                                print("[WARN] curve_fit failed")
                                continue

                            y_fit_z = mode_shape_beta(x_space, A_fit, beta_fit)
                            limited_idx = (x_space >= 0.3) & (x_space <= 0.7)
                            x_limited = x_space[limited_idx]
                            y_limited = y_fit_z[limited_idx]
                            x_max = x_limited[np.argmax(np.abs(y_limited))]

                            # Plotting
                            ax.clear()
                            ax.plot(x_space, mode_shape_beta(x_space, 1, 4.6941), '--', label='Theoretical 2nd Mode')
                            ax.plot(x_space, y_fit_z, color='orange', label='Fitted Mode (Z-axis)')
                            ax.scatter(SENSOR_POSITIONS, norm_z, color='red', label='Sensor Amplitudes')
                            ax.set_ylim([-1.2, 1.2])
                            ax.set_title("Real-Time Mode Shape Fitting (Z-axis)")
                            ax.set_xlabel("Normalized Height")
                            ax.set_ylabel("Relative Amplitude")
                            ax.legend()
                            ax.grid(True)
                            plt.pause(0.01)

                            # Calculate delta and angle
                            delta_norm = x_max - start_norm
                            delta_cm = delta_norm * structure_height
                            delta_deg = delta_cm * CM_TO_DEG

                            print(f"[INFO] norm_z: {norm_z.round(3)}")
                            print(f"[FIT] A = {A_fit:.4f}, beta = {beta_fit:.4f}")
                            print(f"[INFO] Max amplitude at x = {x_max:.3f} → Δnorm = {delta_norm:.3f} → Move TMD by {delta_cm:.2f} cm")

                            # Send to motor
                            try:
                                ser_motor = serial.Serial(PORT_MOTOR, BAUD, timeout=1)
                                time.sleep(2)
                                ser_motor.write(f"{delta_deg:.2f}\n".encode())
                                print(f"[INFO] Sent to motor: {delta_deg:.2f} deg (from {delta_cm:.2f} cm)")
                                ser_motor.close()
                            except Exception as e:
                                print("[ERROR] Failed to send to motor:", e)

                            # Update start_norm
                            start_norm = x_max

                    except Exception as e:
                        print("[WARN] Analysis error:", e)

except KeyboardInterrupt:
    print("\n[EXIT] User interrupted.")
    ser_sensor.close()
