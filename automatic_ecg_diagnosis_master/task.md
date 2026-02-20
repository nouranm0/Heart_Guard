# Task List for ECG Validation Training

- [ ] Create `train_validator.py` script <!-- id: 0 -->
    - [ ] Implement data loading from `data/train/valid` and `data/train/invalid` <!-- id: 1 -->
    - [ ] Implement transfer learning using MobileNetV2 <!-- id: 2 -->
    - [ ] Save model to `model/custom_validator.h5` <!-- id: 3 -->
- [ ] Update `ai_validator.py` <!-- id: 4 -->
    - [ ] Add logic to load `custom_validator.h5` if it exists <!-- id: 5 -->
    - [ ] Fallback to generic ImageNet check if custom model is missing <!-- id: 6 -->
- [ ] Verify with test data <!-- id: 7 -->
- [ ] Document usage in README <!-- id: 8 -->
