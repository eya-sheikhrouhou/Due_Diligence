# Face Detection and Recognition

A Streamlit-based application for real-time face detection and recognition using MTCNN, DLib, and InceptionResnetV1. The application supports webcam-based face detection and recognition, with modular components for detection, recognition, and video processing.

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

1. Upload a reference image for face recognition via the Streamlit interface.
2. The webcam feed will display detected faces with bounding boxes and similarity scores for recognized faces.
3. Detected images can be saved to the `saved_images/` directory.

## Dependencies

Key dependencies are listed in `requirements.txt`. Ensure you have the required DLib model files (`mmod_human_face_detector.dat` and `shape_predictor_68_face_landmarks.dat`) in the root directory if using DLib-based detection.