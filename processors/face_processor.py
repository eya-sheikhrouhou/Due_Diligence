from streamlit_webrtc import VideoProcessorBase
import streamlit as st
import cv2
import numpy as np
import av
from facenet_pytorch import MTCNN, InceptionResnetV1
import dlib
import os
import logging
import torch
from utils.image_utils import preprocess_image
from utils.misc_utils import hex_to_rgb

logger = logging.getLogger(__name__)

class FaceDetectionProcessor(VideoProcessorBase):
    def __init__(self, model_choice, dlib_model_type, dlib_upsample, confidence_threshold, show_landmarks, box_color, landmark_color, recognition_mode=False, similarity_threshold=0.8, debug_placeholder=None):
        self.model_choice = model_choice
        self.dlib_model_type = dlib_model_type
        self.dlib_upsample = dlib_upsample
        self.confidence_threshold = confidence_threshold
        self.show_landmarks = show_landmarks
        self.box_color_rgb = hex_to_rgb(box_color)
        self.landmark_color_rgb = hex_to_rgb(landmark_color)
        self.recognition_mode = recognition_mode
        self.similarity_threshold = similarity_threshold
        self.match_color_rgb = (0, 255, 0)  # Green for matches
        self.no_match_color_rgb = (255, 0, 0)  # Red for non-matches
        self.debug_placeholder = debug_placeholder
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
        # Initialize InceptionResnetV1 for recognition
        if self.recognition_mode and ("resnet" not in st.session_state or st.session_state.resnet is None):
            from config.settings import get_gpu_status
            try:
                _, device = get_gpu_status()
                st.session_state.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
                logger.info("InceptionResnetV1 initialized in FaceDetectionProcessor.")
            except Exception as e:
                st.error(f"❌ Failed to initialize InceptionResnetV1: {e}")
                st.session_state.resnet = None
        self.resnet = st.session_state.resnet if self.recognition_mode else None
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

    def compute_embedding(self, img_rgb):
        """Compute facial embedding for a single face using InceptionResnetV1."""
        if self.resnet is None or self.mtcnn is None:
            logger.error("MTCNN or Resnet not initialized.")
            return None
        try:
            # Detect faces and get aligned face crops
            faces_cropped = self.mtcnn(img_rgb, save_path=None)
            if faces_cropped is None or len(faces_cropped) == 0:
                logger.warning("No faces detected in frame for embedding.")
                return None
            # Compute embedding for the first detected face
            face_tensor = faces_cropped[0].unsqueeze(0)  # Add batch dimension
            if torch.cuda.is_available():
                face_tensor = face_tensor.cuda()
            with torch.no_grad():
                embedding = self.resnet(face_tensor).cpu().numpy().flatten()
            logger.debug(f"Computed frame embedding shape: {embedding.shape}, norm={np.linalg.norm(embedding):.2f}")
            return embedding
        except Exception as e:
            logger.error(f"Embedding computation error: {e}")
            return None

    def cosine_similarity(self, emb1, emb2):
        """Compute cosine similarity between two embeddings."""
        if emb1 is None or emb2 is None:
            logger.warning("One or both embeddings are None.")
            return 0.0
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero norm detected in embeddings.")
                return 0.0
            emb1_norm = emb1 / norm1
            emb2_norm = emb2 / norm2
            similarity = np.dot(emb1_norm, emb2_norm)
            # Clamp to [-1, 1] to avoid floating-point errors
            similarity = np.clip(similarity, -1.0, 1.0)
            logger.debug(f"Cosine similarity: {similarity:.2f}")
            return similarity
        except Exception as e:
            logger.error(f"Cosine similarity error: {e}")
            return 0.0

    def process_frame(self, img_rgb, scale):
        from detectors.mtcnn_detector import detect_faces_mtcnn
        from detectors.dlib_detector import detect_faces_dlib
        if self.model_choice == "MTCNN":
            faces = detect_faces_mtcnn(img_rgb, self.show_landmarks, self.confidence_threshold)
        else:
            faces = detect_faces_dlib(img_rgb, self.dlib_model_type, self.dlib_upsample, self.show_landmarks)
        if self.recognition_mode and faces and "reference_embedding" in st.session_state and st.session_state.reference_embedding is not None:
            current_embedding = self.compute_embedding(img_rgb)
            if current_embedding is not None:
                similarity = self.cosine_similarity(st.session_state.reference_embedding, current_embedding)
                for face in faces:
                    face['similarity'] = similarity
                    face['is_match'] = similarity >= self.similarity_threshold
                    logger.info(f"Face detected: similarity={similarity:.2f}, is_match={face['is_match']}")
                    # Update debug UI if enabled
                    if self.debug_placeholder is not None:
                        self.debug_placeholder.write(f"Similarity: {similarity:.2f}, Match: {face['is_match']}")
        else:
            logger.debug("No faces or reference embedding for recognition.")
        return faces

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
                # Choose color and text based on recognition mode
                if self.recognition_mode and 'is_match' in face and face['similarity'] is not None:
                    box_color = self.match_color_rgb if face['is_match'] else self.no_match_color_rgb
                    text = f"{'Match' if face['is_match'] else 'No Match'} ({face['similarity']:.2f})"
                else:
                    box_color = self.box_color_rgb
                    text = f"{confidence:.2f}"
                draw_rectangle(img_rgb, (x, y), (x + width, y + height), box_color)
                draw_text(img_rgb, text, (x, y - 10), box_color)
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