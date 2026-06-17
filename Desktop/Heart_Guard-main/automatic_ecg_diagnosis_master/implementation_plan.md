# Implementation Plan - Custom ECG Validator Training

## Goal
Enable the user to train a custom AI model to distinguish "Valid ECG" from "Invalid/Anomaly" using their own dataset of images and PDFs.

## User Review Required
> [!IMPORTANT]
> This requires the user to provide a training dataset organized in folders: `data/train/valid` (ECGs) and `data/train/invalid` (Random/Bad images). Without this data, the script cannot run.

## Proposed Changes

### [New Script] train_validator.py
Create a standalone training script that:
1.  **Data Loading:** Uses `ImageDataGenerator` to load images from `data/train`.
2.  **Model**: Uses **MobileNetV2** (pre-trained on ImageNet) as the base.
3.  **Head**: Adds a GlobalAveragePooling and Dense layer for binary classification.
4.  **Training**: Fine-tunes the model for a few epochs.
5.  **Saving**: Saves the trained model to `model/custom_validator.h5`.

### [Modify] ai_validator.py
Update the existing validator to support custom models.

#### [MODIFY] ai_validator.py
- Add logic to check for `model/custom_validator.h5`.
- If found:
    - Load the custom model.
    - Predict: `Valid` if score > 0.5 (or user threshold).
- If not found:
    - Fallback to the existing "Generic MobileNetV2" check (Document vs Image logic).

## Verification Plan

### Manual Verification
1.  **Run Training (Dry Run):**
    - Create dummy data folders `data/train/valid` and `data/train/invalid`.
    - Put `test_tachy_135bpm.jpg` in `valid`.
    - Put `cat.jpg` (if I had it, or just a noise image) in `invalid`.
    - Run `python train_validator.py`.
    - Verify `model/custom_validator.h5` is created.
2.  **Test Integration:**
    - Run `api_server.py`.
    - Upload an image.
    - Verify logs show "Using Custom Validator Model".
