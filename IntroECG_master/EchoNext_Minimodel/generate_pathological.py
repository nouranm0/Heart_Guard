import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def generate_pathological_ecg(filename, hypertrophy=False, poor_r_wave=False):
    print(f"Generating {filename}...")
    t = np.linspace(0, 5, 2500)
    plt.figure(figsize=(15, 20))
    
    pulse_rate = 1.2 # Slightly fast
    
    for i in range(12):
        plt.subplot(12, 1, i + 1)
        
        signal = np.zeros_like(t)
        for beat_time in np.arange(0.2, 5, 1.0/pulse_rate):
            # P wave
            signal += 0.1 * np.exp(-((t - beat_time + 0.15)**2) / (2 * 0.02**2))
            
            # QRS complex
            qrs_amp = 1.0
            if hypertrophy:
                # Amplify V5/V6 (leads 10, 11) for hypertrophy simulation
                if i >= 9: qrs_amp = 6.0 # Even more extreme
                # Deep S in V1/V2 (leads 6, 7)
                if i == 6 or i == 7: qrs_amp = -5.0
            
            if poor_r_wave and i >= 6 and i <= 9: # V1-V4
                qrs_amp = 0.05 # Tiny R waves
            
            signal += qrs_amp * np.exp(-((t - beat_time)**2) / (2 * 0.005**2))
            
            # T wave (Inverted in hypertrophy leads)
            t_amp = 0.2
            if hypertrophy and i >= 9: t_amp = -0.5
            signal += t_amp * np.exp(-((t - beat_time - 0.25)**2) / (2 * 0.04**2))
            
        # Add baseline noise
        signal += np.random.normal(0, 0.05, len(t))
        
        plt.plot(t, signal, color='black', linewidth=1.2)
        plt.axis('off')
        
    plt.tight_layout()
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"Created {filename}")

if __name__ == "__main__":
    generate_pathological_ecg("test_hypertrophy.jpg", hypertrophy=True)
    generate_pathological_ecg("test_poor_r_wave.jpg", poor_r_wave=True)
