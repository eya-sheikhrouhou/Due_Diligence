import streamlit as st
import cv2
import dlib
import os
import logging

logger = logging.getLogger(__name__)

def load_dlib_models(model_choice, dlib_model_type):
    """Load DLib models and update session state."""
    try:
        if model_choice == "DLib" and dlib_model_type == "CNN (more accurate)":
            cnn_model_path = "mmod_human_face_detector.dat"
            if not os.path.exists(cnn_model_path):
                st.warning(f"❌ CNN model file not found at {cnn_model_path}. Falling back to HOG detector.")
                st.markdown("Please download 'mmod_human_face_detector.dat' from [dlib.net](http://dlib.net/files/mmod_human_face_detector.dat.bz2) and place it in the project directory.")
                st.session_state.dlib_detector = dlib.get_frontal_face_detector()
            else:
                st.session_state.dlib_detector = dlib.cnn_face_detection_model_v1(cnn_model_path)
        else:
            st.session_state.dlib_detector = dlib.get_frontal_face_detector()

        shape_predictor_path = "shape_predictor_68_face_landmarks.dat"
        if not os.path.exists(shape_predictor_path):
            st.warning(f"❌ Shape predictor file not found at {shape_predictor_path}. Facial landmarks disabled for DLib.")
            st.markdown("Please download 'shape_predictor_68_face_landmarks.dat' from [dlib.net](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2) and place it in the project directory.")
            st.session_state.dlib_predictor = None
        else:
            st.session_state.dlib_predictor = dlib.shape_predictor(shape_predictor_path)
    except Exception as e:
        st.error(f"❌ Error loading DLib models: {e}")
        st.session_state.dlib_detector = None
        st.session_state.dlib_predictor = None

def detect_faces_dlib(image, dlib_model_type, dlib_upsample, show_landmarks):
    """Detect faces using DLib."""
    faces = []
    if st.session_state.dlib_detector is None:
        st.error("❌ DLib detector not initialized.")
        return faces
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    faces_dlib = st.session_state.dlib_detector(gray, dlib_upsample)
    for face in faces_dlib:
        if dlib_model_type == "CNN (more accurate)" and hasattr(face, 'rect'):
            rect = face.rect
            confidence = face.confidence
        else:
            rect = face
            confidence = 1.0
        x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
        x, y = max(0, x), max(0, y)
        w, h = min(w, image.shape[1] - x), min(h, image.shape[0] - y)
        keypoints = {}
        if st.session_state.dlib_predictor and show_landmarks:
            shape = st.session_state.dlib_predictor(gray, rect)
            keypoints = {
                'left_eye': (shape.part(36).x, shape.part(36).y),
                'right_eye': (shape.part(45).x, shape.part(45).y),
                'nose': (shape.part(30).x, shape.part(30).y),
                'mouth_left': (shape.part(48).x, shape.part(48).y),
                'mouth_right': (shape.part(54).x, shape.part(54).y)
            }
        faces.append({
            'box': [x, y, w, h],
            'confidence': confidence,
            'keypoints': keypoints
        })
    return faces