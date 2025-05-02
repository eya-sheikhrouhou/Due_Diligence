from streamlit_webrtc import VideoProcessorBase
import streamlit as st
import cv2
import numpy as np
import av
import dlib
import os
import logging
from utils.image_utils import preprocess_image
from utils.misc_utils import hex_to_rgb
from detectors.mtcnn_detector import detect_faces_mtcnn
from detectors.dlib_detector import detect_faces_dlib
from facenet_pytorch import MTCNN
import torch

logger = logging.getLogger(__name__)

class FaceDetectionProcessor(VideoProcessorBase):
    def __init__(self, model_choice, dlib_model_type, dlib_upsample, confidence_threshold, show_landmarks, box_color, landmark_color, recognizer=None, similarity_threshold=0.6, debug_placeholder=None):
        self.model_choice = model_choice
        self.dlib_model_type = dlib_model_type
        self.dlib_upsample = dlib_upsample
        self.confidence_threshold = confidence_threshold
        self.show_landmarks = show_landmarks
        self.box_color_rgb = hex_to_rgb(box_color)
        self.landmark_color_rgb = hex_to_rgb(landmark_color)
        self.recognizer = recognizer
        self.similarity_threshold = similarity_threshold
        self.match_color_rgb = (0, 255, 0)  # Green for matches
        self.no_match_color_rgb = (255, 0, 0)  # Red for non-matches
        self.debug_placeholder = debug_placeholder
        if "mtcnn_detector" not in st.session_state or st.session_state.mtcnn_detector is None:
            from config.settings import get_gpu_status
            try:
                _, device = get_gpu_status()
                st.session_state.mtcnn_detector = MTCNN(
                    keep_all=True, device=device, min_face_size=20,
                    thresholds=[0.4, 0.5, 0.5], factor=0.709
                )
                logger.info("MTCNN detector initialized in FaceDetectionProcessor.")
            except Exception as e:
                st.error(f"❌ Failed to initialize MTCNN detector: {e}")
                logger.error(f"MTCNN Initialization Error: {e}")
                st.session_state.mtcnn_detector = None
        self.mtcnn = st.session_state.mtcnn_detector
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
                logger.error(f"DLib Initialization Error: {e}")
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
                logger.error(f"DLib Predictor Initialization Error: {e}")
                st.session_state.dlib_predictor = None
        self.dlib_detector = st.session_state.dlib_detector
        self.dlib_predictor = st.session_state.dlib_predictor

    def preprocess_frame(self, image):
        """Normalize brightness and contrast of the input frame."""
        try:
            img_lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_lab[:, :, 0] = clahe.apply(img_lab[:, :, 0])
            img_normalized = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
            return img_normalized
        except Exception as e:
            logger.error(f"Frame Preprocessing Error: {e}")
            return image

    def process_frame(self, img_rgb, scale):
        # Perform face detection (for both modes)
        faces = []
        try:
            if self.model_choice == "MTCNN":
                faces = detect_faces_mtcnn(img_rgb, self.show_landmarks, self.confidence_threshold)
                logger.debug(f"MTCNN detected {len(faces)} faces")
            else:
                faces = detect_faces_dlib(img_rgb, self.dlib_model_type, self.dlib_upsample, self.show_landmarks)
                logger.debug(f"DLib detected {len(faces)} faces")
        except Exception as e:
            logger.error(f"Face Detection Error: {e}")
            return faces

        # Perform face recognition only if recognizer is provided (Face Recognition mode)
        if self.recognizer is not None and self.recognizer.reference_embedding is not None:
            try:
                logger.debug("Attempting to crop faces with MTCNN for recognition")
                faces_cropped = self.mtcnn(img_rgb, save_path=None)
                if faces_cropped is not None and len(faces_cropped) > 0:
                    logger.debug(f"Cropped {len(faces_cropped)} faces")
                    st.session_state.cropped_faces = []  # Reset cropped faces
                    for i, face_tensor in enumerate(faces_cropped):
                        if i >= len(faces):
                            logger.debug(f"Skipping extra cropped face {i+1}: detected {len(faces)} faces")
                            break
                        logger.debug(f"Processing cropped face {i+1}: shape={face_tensor.shape}")
                        if face_tensor.shape != (3, 160, 160):
                            logger.error(f"Invalid face tensor shape for face {i+1}: {face_tensor.shape}")
                            continue
                        if torch.cuda.is_available():
                            face_tensor = face_tensor.cuda()
                        is_match, similarity = self.recognizer.recognize_face(face_tensor)
                        faces[i]['similarity'] = similarity
                        faces[i]['is_match'] = is_match
                        logger.info(f"Face {i+1}: similarity={similarity:.2f}, is_match={is_match}")
                        # Convert tensor to NumPy for display
                        try:
                            face_np = face_tensor.cpu().permute(1, 2, 0).numpy()
                            face_np = (face_np * 255).astype(np.uint8)  # Assume [0, 1] range
                            face_np = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
                            st.session_state.cropped_faces.append({
                                'image': face_np,
                                'caption': f"Recognized Face {i+1}: {'Match' if is_match else 'No Match'} ({similarity:.2f})"
                            })
                            logger.debug(f"Added cropped face {i+1} to session state")
                        except Exception as e:
                            logger.error(f"Error converting cropped face {i+1}: {e}")
                            continue
                else:
                    logger.debug("No faces cropped for recognition")
                    st.session_state.cropped_faces = []
            except Exception as e:
                logger.error(f"Recognition Error: {e}")
                st.session_state.cropped_faces = []

        # Update debug UI if in Face Recognition mode
        if self.recognizer is not None and self.debug_placeholder is not None:
            with self.debug_placeholder.container():
                if not st.session_state.cropped_faces:
                    st.write("No faces recognized in this frame.")
                    logger.debug("No cropped faces to display")
                else:
                    logger.debug(f"Displaying {len(st.session_state.cropped_faces)} cropped faces")
                    cols = st.columns(min(len(st.session_state.cropped_faces), 3))
                    for idx, cropped_face in enumerate(st.session_state.cropped_faces):
                        with cols[idx % 3]:
                            st.image(cropped_face['image'], caption=cropped_face['caption'], use_container_width=True)

        return faces

    def recv(self, frame):
        try:
            img = frame.to_ndarray(format="bgr24")
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            # Preprocess frame
            img_rgb = self.preprocess_frame(img_rgb)
            img_processed, scale = preprocess_image(img_rgb)
            faces = self.process_frame(img_processed, scale)
            count = 0
            for face in faces:
                x, y, width, height = face['box']
                confidence = face['confidence']
                if self.model_choice == "MTCNN" and confidence < self.confidence_threshold:
                    logger.debug(f"Skipping face with low confidence: {confidence:.2f}")
                    continue
                x, y = max(0, int(x / scale)), max(0, int(y / scale))
                width, height = int(width / scale), int(height / scale)
                x_end, y_end = min(x + width, img_rgb.shape[1]), min(y + height, img_rgb.shape[0])
                x, y = max(0, x), max(0, y)
                width, height = x_end - x, y_end - y
                if width <= 0 or height <= 0:
                    logger.debug(f"Skipping invalid bounding box: x={x}, y={y}, width={width}, height={height}")
                    continue
                from utils.image_utils import draw_rectangle, draw_text, draw_circle
                # Use detection-only annotations if recognizer is None
                if self.recognizer is None:
                    box_color = self.box_color_rgb
                    text = f"{confidence:.2f}"
                else:
                    box_color = self.match_color_rgb if 'is_match' in face and face['is_match'] else self.no_match_color_rgb if 'is_match' in face else self.box_color_rgb
                    text = f"{'Match' if 'is_match' in face and face['is_match'] else 'No Match'} ({face['similarity']:.2f})" if 'is_match' in face else f"{confidence:.2f}"
                try:
                    draw_rectangle(img_rgb, (x, y), (x + width, y + height), box_color)
                    draw_text(img_rgb, text, (x, y - 10), box_color)
                    if self.show_landmarks:
                        for key, (px, py) in face['keypoints'].items():
                            px, py = int(px / scale), int(py / scale)
                            draw_circle(img_rgb, (px, py), self.landmark_color_rgb)
                    count += 1
                except Exception as e:
                    logger.error(f"Rendering Error for face {count+1}: {e}")
                    continue
            st.session_state.total_faces_detected = count
            logger.debug(f"Processed frame: detected {count} faces")
            # Trigger rerun only if in Face Recognition mode and new faces were added
            if self.recognizer is not None and st.session_state.get('_update_cropped_faces', False):
                st.session_state._update_cropped_faces = False
                st.rerun()
            return av.VideoFrame.from_ndarray(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), format="bgr24")
        except Exception as e:
            logger.error(f"Real-time detection error: {e}")
            st.error(f"❌ Real-time detection error: {e}")
            return frame