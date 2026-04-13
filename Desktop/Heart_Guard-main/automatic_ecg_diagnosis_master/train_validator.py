import os
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Configuration
IMG_SIZE = (224, 224)
BATCH_SIZE = 8
EPOCHS = 10
LEARNING_RATE = 0.0001
DATA_DIR = 'data/train'
MODEL_DIR = 'model'
MODEL_PATH = os.path.join(MODEL_DIR, 'custom_validator.h5')

def train_custom_validator():
    """
    Trains a MobileNetV2 on user-provided data to detect valid ECGs.
    Architecture: MobileNetV2 (frozen base) -> GlobalAvgPool -> Dense(1, sigmoid)
    Classes: 0 = Invalid (Background/Noise/Cat), 1 = Valid (ECG)
    """
    
    # 1. Setup Data Generators
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory '{DATA_DIR}' not found!")
        print("Please create: data/train/valid and data/train/invalid")
        return

    print("Found data directory, initializing generators...")
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        validation_split=0.2
    )

    try:
        train_generator = train_datagen.flow_from_directory(
            DATA_DIR,
            target_size=IMG_SIZE,
            batch_size=BATCH_SIZE,
            class_mode='binary',
            subset='training'
        )

        validation_generator = train_datagen.flow_from_directory(
            DATA_DIR,
            target_size=IMG_SIZE,
            batch_size=BATCH_SIZE,
            class_mode='binary',
            subset='validation'
        )
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    if train_generator.samples == 0:
        print("No images found! Add images to data/train/valid and data/train/invalid")
        return

    print(f"Training on {train_generator.samples} images, Validating on {validation_generator.samples} images")
    print(f"Classes: {train_generator.class_indices}")

    # 2. Build Model
    base_model = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights='imagenet')
    base_model.trainable = False  # Freeze base model

    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(128, activation='relu')(x)
    predictions = Dense(1, activation='sigmoid')(x)

    model = Model(inputs=base_model.input, outputs=predictions)

    model.compile(optimizer=Adam(learning_rate=LEARNING_RATE), 
                  loss='binary_crossentropy', 
                  metrics=['accuracy'])
    
    model.summary()

    # 3. Train
    print("Starting training...")
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=validation_generator
    )

    # 4. Save
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

    model.save(MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    print("You can now restart the API server to use this custom model.")

if __name__ == '__main__':
    train_custom_validator()
