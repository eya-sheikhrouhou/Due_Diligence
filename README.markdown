# Face Detection and Recognition

A Streamlit-based application for real-time face detection and recognition using MTCNN, DLib, and InceptionResnetV1.

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

## Structure

- `faces.py`: Main Streamlit application.
- `detectors/`: Face detection logic (MTCNN and DLib).
- `processors/`: Face processing and recognition logic.
- `utils/`: Helper functions for image processing and logging.
- `config/`: Configuration settings.

## Usage

1. Upload a reference image for face recognition.
2. The webcam feed will display detected faces with bounding boxes and similarity scores.