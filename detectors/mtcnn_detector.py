import streamlit as st
from facenet_pytorch import MTCNN

def detect_faces_mtcnn(image, show_landmarks, confidence_threshold):
    """Detect faces using MTCNN."""
    faces = []
    if st.session_state.mtcnn_detector is None:
        st.error("❌ MTCNN detector not initialized.")
        return faces
    boxes, probs, landmarks = st.session_state.mtcnn_detector.detect(image, landmarks=True)
    if boxes is not None:
        for i, box in enumerate(boxes):
            x, y, x2, y2 = box
            w, h = x2 - x, y2 - y
            confidence = probs[i] if probs is not None else 1.0
            if confidence < confidence_threshold:
                continue
            keypoints = {}
            if show_landmarks and landmarks is not None:
                lm = landmarks[i]
                keypoints = {
                    'left_eye': (lm[0][0], lm[0][1]),
                    'right_eye': (lm[1][0], lm[1][1]),
                    'nose': (lm[2][0], lm[2][1]),
                    'mouth_left': (lm[3][0], lm[3][1]),
                    'mouth_right': (lm[4][0], lm[4][1])
                }
            faces.append({
                'box': [x, y, w, h],
                'confidence': confidence,
                'keypoints': keypoints
            })
    return faces