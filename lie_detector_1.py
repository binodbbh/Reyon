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

# Function to collect baseline data (2 minutes)
def collect_baseline_data(duration_sec=120):
    baseline_ecg_data = []
    start_time = time.time()

    print("Collecting baseline data for 2 minutes...")

    while time.time() - start_time < duration_sec:
        if ser.in_waiting > 0:
            # Read the data from Arduino and decode it
            ecg_value = ser.readline().decode('utf-8').strip()
            
            try:
                ecg_value = int(ecg_value)
                if 0 <= ecg_value <= 1023:
                    baseline_ecg_data.append(ecg_value)  # Collect baseline data
            except ValueError:
                pass  # If data is not a valid integer, skip it

    # After 2 minutes, return the baseline ECG data
    print("Baseline data collection complete.")
    return baseline_ecg_data

# Function to prompt the user for lie detection
def prompt_for_lie_detection():
    user_choice = input("Would you like to answer a question to test for stress (possible lie)? (yes/no): ").strip().lower()

    if user_choice == "yes":
        return True
    else:
        print("No more questions for lie detection. Exiting.")
        return False

# Function to monitor for stress (possible lie detection)
def monitor_for_stress(duration_sec=30):
    print("Monitoring for physiological stress...")

    # Start monitoring the heart rate and HRV after the user agrees to start lie detection
    rr_intervals.clear()  # Clear RR intervals for fresh monitoring

    while time.time() - question_response_start < duration_sec:  # Monitor for 30 seconds
        if ser.in_waiting > 0:
            # Read the data from Arduino and decode it
            ecg_value = ser.readline().decode('utf-8').strip()
            
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
                        if hrv < stress_threshold:
                            print(f"Stress detected! HRV: {hrv:.2f} (Potential Lie Detected)")
                            plt.title('Potential Lie Detected: Stress Level High')
                        else:
                            plt.title(f'Heart Rate: {heart_rate:.2f} bpm, HRV: {hrv:.2f}')
                    
                    update_plot()  # Update the plot with the new data

    # After monitoring, analyze HRV to determine if stress was detected
    if hrv < stress_threshold:
        print(f"Stress detected after monitoring: HRV is low ({hrv:.2f}) - Potential Lie!")
    else:
        print("HRV is normal, no signs of stress detected.")

# Read and visualize ECG data in real-time
try:
    # Step 1: Collect baseline data for 2 minutes
    baseline_data = collect_baseline_data(duration_sec=120)
    
    # Step 2: Analyze baseline data (e.g., calculate HRV and Heart Rate)
    baseline_peaks = detect_peaks(baseline_data)
    
    # Calculate RR intervals for the baseline data
    baseline_rr_intervals = np.diff(baseline_peaks)
    baseline_hrv = calculate_hrv(baseline_rr_intervals)
    baseline_heart_rate = 60 / (np.mean(baseline_rr_intervals) / 100)  # Heart rate in bpm

    print(f"Baseline HRV: {baseline_hrv:.2f}")
    print(f"Baseline Heart Rate: {baseline_heart_rate:.2f} bpm")

    # Step 3: Repeatedly prompt user for lie detection
    while True:
        if prompt_for_lie_detection():
            # Ask the user a question (you can replace this with a random or predefined question list)
            question = input("Please answer the following question: ")

            print(f"Question: {question}")
            print("Please answer honestly. Monitoring physiological response...")
            
            # Step 4: Start monitoring for stress (possible lie detection)
            monitor_for_stress(duration_sec=30)
        else:
            break

except KeyboardInterrupt:
    print("\nProgram interrupted.")

finally:
    ser.close()  # Close the serial connection when done
    plt.ioff()  # Turn off interactive mode for plotting
    plt.show()  # Show the final plot
