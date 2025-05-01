from streamlit_webrtc import VideoProcessorBase
import streamlit as st
import cv2
import numpy as np
import av
from facenet_pytorch import MTCNN
import dlib
import os
import logging
from utils.image_utils import preprocess_image
from utils.misc_utils import hex_to_rgb

logger = logging.getLogger(__name__)

class FaceDetectionProcessor(VideoProcessorBase):
    def __init__(self, model_choice, dlib_model_type, dlib_upsample, confidence_threshold, show_landmarks, box_color, landmark_color):
        self.model_choice = model_choice
        self.dlib_model_type = dlib_model_type
        self.dlib_upsample = dlib_upsample
        self.confidence_threshold = confidence_threshold
        self.show_landmarks = show_landmarks
        self.box_color_rgb = hex_to_rgb(box_color)
        self.landmark_color_rgb = hex_to_rgb(landmark_color)
        # Initialize MTCNN
        if "mtcnn_detector" not in st.session_state or st.session_state.mtcnn_detector is None:
            from config.settings import get_gpu_status
            try:
                _, device = get_gpu_status()
                st.session_state.mtcnn_detector = MTCNN(
                    keep_all=True, device=device, min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7], factor=0.709
                )
                logger.info("MTCNN detector initialized in FaceDetectionProcessor.")
            except Exception as e:
                st.error(f"❌ Failed to initialize MTCNN detector: {e}")
                st.session_state.mtcnn_detector = None
        self.mtcnn = st.session_state.mtcnn_detector
        # Initialize DLib
        if "dlib_detector" not in st.session_state or st.session_state.dlib_detector is None:
            try:
                if self.model_choice == "DLib" and self.dlib_model_type == "CNN (more accurate)":
                    cnn_model_path = "mmod_human_face_detector.dat"
                    if not os.path.exists(cnn_model_path):
                        logger.warning(f"CNN model file not found at {cnn_model_path}. Falling back to HOG detector.")
                        st.session_state.dlib_detector = dlib.get_frontal_face_detector()
                    else:
                        st.session_state.dlib_detector = dlib.cnn_face_detection_model_v1(cnn_model_path)
                else:
                    st.session_state.dlib_detector = dlib.get_frontal_face_detector()
            except Exception as e:
                st.error(f"❌ Failed to initialize DLib detector: {e}")
                st.session_state.dlib_detector = None
        if "dlib_predictor" not in st.session_state or st.session_state.dlib_predictor is None:
            try:
                shape_predictor_path = "shape_predictor_68_face_landmarks.dat"
                if not os.path.exists(shape_predictor_path):
                    logger.warning(f"Shape predictor file not found at {shape_predictor_path}. Facial landmarks disabled.")
                    st.session_state.dlib_predictor = None
                else:
                    st.session_state.dlib_predictor = dlib.shape_predictor(shape_predictor_path)
            except Exception as e:
                st.error(f"❌ Failed to initialize DLib predictor: {e}")
                st.session_state.dlib_predictor = None
        self.dlib_detector = st.session_state.dlib_detector
        self.dlib_predictor = st.session_state.dlib_predictor

    def process_frame(self, img_rgb, scale):
        from detectors.mtcnn_detector import detect_faces_mtcnn
        from detectors.dlib_detector import detect_faces_dlib
        if self.model_choice == "MTCNN":
            return detect_faces_mtcnn(img_rgb, self.show_landmarks, self.confidence_threshold)
        return detect_faces_dlib(img_rgb, self.dlib_model_type, self.dlib_upsample, self.show_landmarks)

    def recv(self, frame):
        try:
            img = frame.to_ndarray(format="bgr24")
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_processed, scale = preprocess_image(img_rgb)
            faces = self.process_frame(img_processed, scale)
            count = 0
            for face in faces:
                x, y, width, height = face['box']
                confidence = face['confidence']
                if self.model_choice == "MTCNN" and confidence < self.confidence_threshold:
                    continue
                x, y = max(0, int(x / scale)), max(0, int(y / scale))
                width, height = int(width / scale), int(height / scale)
                x_end, y_end = min(x + width, img_rgb.shape[1]), min(y + height, img_rgb.shape[0])
                x, y = max(0, x), max(0, y)
                width, height = x_end - x, y_end - y
                if width <= 0 or height <= 0:
                    continue
                from utils.image_utils import draw_rectangle, draw_text, draw_circle
                draw_rectangle(img_rgb, (x, y), (x + width, y + height), self.box_color_rgb)
                draw_text(img_rgb, f"{confidence:.2f}", (x, y - 10), self.box_color_rgb)
                if self.show_landmarks:
                    for key, (px, py) in face['keypoints'].items():
                        px, py = int(px / scale), int(py / scale)
                        draw_circle(img_rgb, (px, py), self.landmark_color_rgb)
                count += 1
            st.session_state.total_faces_detected = count
            return av.VideoFrame.from_ndarray(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), format="bgr24")
        except Exception as e:
            logger.error(f"Real-time detection error: {e}")
            st.error(f"❌ Real-time detection error: {e}")
            return frame