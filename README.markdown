# Face Detection and Recognition

A Streamlit-based application for real-time face detection and single-face recognition using MTCNN, DLib, and InceptionResnetV1. The application supports webcam-based face detection and recognition, with modular components for detection, recognition, and video processing.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv face_detection_env
   source face_detection_env/bin/activate  # On Windows: face_detection_env\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run faces.py
   ```

## File Structure

```
Due_Diligence/
├── face_detection_env/  # Virtual environment
├── saved_images/        # Directory for saved images
├── faces.py             # Main Streamlit app (minimal, orchestrates other modules)
├── config/
│   └── settings.py      # Configuration and session state initialization
├── detectors/
│   ├── __init__.py      # Make detectors a package
│   ├── mtcnn_detector.py # MTCNN detector logic
│   └── dlib_detector.py  # DLib detector logic
├── processors/
│   ├── __init__.py      # Make processors a package
│   ├── face_processor.py # Face detection processor for webcam
│   ├── face_recognizer.py # Face recognition logic
│   └── video_processor.py # Video file processor
├── utils/
│   ├── __init__.py      # Make utils a package
│   ├── image_utils.py   # Image preprocessing and saving
│   └── misc_utils.py    # URL validation, hex-to-RGB conversion, etc.
├── mmod_human_face_detector.dat          # DLib CNN model (if used)
└── shape_predictor_68_face_landmarks.dat # DLib landmark model (if used)
```

## Usage

1. **Select an Input Method**: Use the sidebar to choose an input method:
   - **Real-Time Detection (Webcam)**: Detects faces in real-time using your webcam with either MTCNN or DLib. Displays bounding boxes and confidence scores around detected faces.
   - **Face Recognition**: Upload a reference image to perform single-face recognition using MTCNN and InceptionResnetV1. The webcam feed will show similarity scores comparing detected faces to the reference face.
   - **Use Local Webcam**: Capture a single image from your webcam for face detection.
   - **Use IP Camera**: Stream and capture images from an IP camera for face detection.
   - **Upload Images**: Upload images for face detection.
   - **Upload Video**: Upload a video file to process and annotate faces.

2. **Adjust Settings**: Use the sidebar to configure:
   - Detection model (MTCNN or DLib).
   - DLib model type (HOG or CNN) and upsampling.
   - Confidence threshold (for MTCNN).
   - Display of facial landmarks.
   - Colors for bounding boxes and landmarks.
   - Similarity threshold for face recognition.
   - Save directory and filename prefix for captured images.

3. **Save Detected Images**: Detected images can be saved to the `saved_images/` directory using the save button provided after detection.

## Dependencies

Key dependencies are listed in `requirements.txt`. Ensure you have the required DLib model files (`mmod_human_face_detector.dat` and `shape_predictor_68_face_landmarks.dat`) in the root directory if using DLib-based detection. These files can be downloaded from [dlib.net](http://dlib.net/files/) if not already present.

## Notes

- The application currently supports single-face recognition in the "Face Recognition" mode. Multi-face recognition is not implemented.
- Ensure your webcam is accessible by the browser for real-time detection and recognition modes.
- For DLib detection, the CNN model (`mmod_human_face_detector.dat`) is more accurate but slower than the HOG model and requires the model file to be present.