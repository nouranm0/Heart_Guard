import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.interpolate import interp1d
import os

def generate_test_image(path):
    print(f"Generating test image at {path}...")
    t = np.linspace(0, 1, 1000)
    plt.figure(figsize=(15, 20))
    for i in range(12):
        plt.subplot(12, 1, i + 1)
        # Oscillating signal
        signal = np.sin(2 * np.pi * 5 * t) + (i % 3) * 0.5
        plt.plot(t, signal, color='black')
        plt.axis('off')
    plt.tight_layout()
    plt.savefig(path, bbox_inches='tight', pad_inches=0)
    plt.close()

def parse_image_file(image_path):
    print(f"Opening image: {image_path}")
    img = Image.open(image_path).convert('L') # Grayscale
    img_data = np.array(img)
    
    h, w = img_data.shape
    section_h = h // 12
    ekg_array = np.zeros((2500, 12))
    
    for i in range(12):
        start_y = i * section_h
        end_y = (i+1) * section_h
        section = img_data[start_y:end_y, :]
        
        inverted = 255 - section
        threshold = np.max(inverted) * 0.5
        binary = (inverted > threshold).astype(float)
        
        coords = np.indices(binary.shape)
        y_coords = coords[0]
        
        weights = binary.sum(axis=0)
        weights[weights == 0] = 1
        
        y_centers = (binary * y_coords).sum(axis=0) / weights
        
        x_orig = np.linspace(0, 1, w)
        x_new = np.linspace(0, 1, 2500)
        f = interp1d(x_orig, y_centers, fill_value="extrapolate")
        ekg_array[:, i] = f(x_new)
        
    return ekg_array

if __name__ == "__main__":
    test_img = "test_verify.jpg"
    generate_test_image(test_img)
    try:
        data = parse_image_file(test_img)
        print(f"Extracted data shape: {data.shape}")
        if data.shape == (2500, 12):
            print("Verification SUCCESS: Signal extraction returned expected shape.")
        else:
            print(f"Verification FAILURE: Unexpected shape {data.shape}")
    except Exception as e:
        print(f"Verification FAILURE: Exception occurred: {e}")
    finally:
        if os.path.exists(test_img):
            os.remove(test_img)
