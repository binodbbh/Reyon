import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from scipy.signal import find_peaks

# Set the serial port and baud rate (change to match your system)
serial_port = 'COM3'  # Replace with your actual port (e.g., '/dev/ttyACM0' for Linux/Mac)
baud_rate = 9600

# Initialize the serial connection
ser = serial.Serial(serial_port, baud_rate)
time.sleep(2)  # Wait for Arduino to reset

# Number of samples to keep for visualization
buffer_size = 200

# Deque to store the ECG data for real-time plotting
ecg_data = deque(maxlen=buffer_size)

# HRV and Heart Rate Variables
rr_intervals = []  # List to store RR intervals (in samples)
heart_rate = 0  # Current heart rate
hrv = 0  # Current heart rate variability
stress_threshold = 50  # A threshold for HRV change indicating stress

# Set up the plot
plt.ion()  # Turn on interactive mode for real-time plotting
fig, ax = plt.subplots(figsize=(10, 4))
line, = ax.plot([], [], label="ECG Signal")
ax.set_xlim(0, buffer_size)  # x-axis limits (0 to buffer_size)
ax.set_ylim(0, 1023)  # y-axis limits (for 10-bit ADC values)
ax.set_title('Real-time ECG Data')
ax.set_xlabel('Samples')
ax.set_ylabel('ECG Value')
ax.legend()

# Function to update the plot with new data
def update_plot():
    line.set_ydata(ecg_data)
    line.set_xdata(np.arange(len(ecg_data)))
    plt.draw()
    plt.pause(0.01)  # Small pause to allow for plot update

# Function to detect peaks in the ECG signal (simulating R-peaks)
def detect_peaks(ecg_data):
    # Use scipy's find_peaks function to detect local maxima (R-peaks)
    peaks, _ = find_peaks(np.array(ecg_data), height=500, distance=20)  # Adjust parameters
    return peaks

# Function to calculate HRV from RR intervals
def calculate_hrv(rr_intervals):
    if len(rr_intervals) > 1:
        # Calculate the standard deviation of RR intervals (SDNN) as a simple measure of HRV
        return np.std(rr_intervals)
    return 0

# Read and visualize ECG data in real-time
try:
    while True:
        if ser.in_waiting > 0:
            # Read the data from Arduino and decode it
            ecg_value = ser.readline().decode('utf-8').strip()
            
            # Convert the received value to an integer (ECG data is typically in the range of 0-1023)
            try:
                ecg_value = int(ecg_value)
                if 0 <= ecg_value <= 1023:
                    ecg_data.append(ecg_value)  # Add the new value to the deque
                    
                    # Detect R-peaks (heartbeats)
                    peaks = detect_peaks(ecg_data)
                    
                    if len(peaks) >= 2:
                        # Calculate RR intervals (time difference between successive R-peaks)
                        rr_interval = peaks[-1] - peaks[-2]
                        rr_intervals.append(rr_interval)
                        
                        # Calculate HRV (Heart Rate Variability)
                        hrv = calculate_hrv(rr_intervals)
                        
                        # Calculate heart rate (in beats per minute)
                        heart_rate = 60 / (np.mean(rr_intervals) / 100)  # Convert RR interval to heart rate
                        
                        # Check for stress based on HRV
                        if len(rr_intervals) > 5 and hrv > stress_threshold:
                            print("Stress detected! HRV: ", hrv)
                            # Mark as potential lie detection
                            plt.title('Potential Lie Detected: Stress Level High')
                        else:
                            plt.title(f'Heart Rate: {heart_rate:.2f} bpm, HRV: {hrv:.2f}')
                    
                    update_plot()  # Update the plot with the new data
            except ValueError:
                pass  # If data is not a valid integer, skip it

except KeyboardInterrupt:
    print("\nProgram interrupted.")

finally:
    ser.close()  # Close the serial connection when done
    plt.ioff()  # Turn off interactive mode for plotting
    plt.show()  # Show the final plot
