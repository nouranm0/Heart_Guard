import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def generate_ecg_image(filename, pulse_rate=1.0, noise_level=0.1, amplitude=1.0):
    """
    Generates a synthetic 12-lead ECG image.
    pulse_rate: 1.0 is normal, >1.0 is fast (tachycardia), <1.0 is slow (bradycardia)
    """
    print(f"Generating {filename}...")
    t = np.linspace(0, 5, 2500) # 5 seconds of data
    
    plt.figure(figsize=(15, 20))
    for i in range(12):
        plt.subplot(12, 1, i + 1)
        
        # Base heart beat (P-QRS-T approximation)
        # Simple QRS spike
        heart_beats = np.zeros_like(t)
        for beat_time in np.arange(0.1, 5, 1.0/pulse_rate):
            # QRS spike
            heart_beats += amplitude * np.exp(-((t - beat_time)**2) / (2 * 0.01**2))
            # T wave
            heart_beats += (amplitude * 0.2) * np.exp(-((t - beat_time - 0.2)**2) / (2 * 0.05**2))
            # P wave
            heart_beats += (amplitude * 0.1) * np.exp(-((t - beat_time + 0.1)**2) / (2 * 0.04**2))
            
        # Add some noise and lead variation
        signal = heart_beats + np.random.normal(0, noise_level, len(t)) + (i % 3) * 0.2
        
        plt.plot(t, signal, color='black', linewidth=1.5)
        plt.axis('off')
        
    plt.tight_layout()
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"Successfully created {filename}")

if __name__ == "__main__":
    # Case 1: Normal ECG
    generate_ecg_image("test_normal.jpg", pulse_rate=1.0)
    
    # Case 2: Tachycardia (Fast heart rate)
    generate_ecg_image("test_tachycardia.jpg", pulse_rate=2.0)
    
    # Case 3: Bradycardia (Slow heart rate)
    generate_ecg_image("test_bradycardia.jpg", pulse_rate=0.5)

    print("\n--- Test Cases Generated ---")
    print("You can now test the model using these commands:")
    print("1. python cradlenet/scripts/inference/predict_file.py --input_file test_normal.jpg --checkpoint models/echonext_multilabel_minimodel/weights.pt --num_classes 12")
    print("2. python cradlenet/scripts/inference/predict_file.py --input_file test_tachycardia.jpg --checkpoint models/echonext_multilabel_minimodel/weights.pt --num_classes 12")
