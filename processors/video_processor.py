import streamlit as st
import cv2
import numpy as np
import time
import datetime
from pathlib import Path
import logging
from facenet_pytorch import MTCNN
import dlib
import os
from utils.image_utils import preprocess_image
from utils.misc_utils import hex_to_rgb
from processors.face_processor import FaceDetectionProcessor

logger = logging.getLogger(__name__)

class VideoFileProcessor:
    def __init__(self, video_path, model_choice, dlib_model_type, dlib_upsample, confidence_threshold, show_landmarks, box_color, landmark_color, playback_speed, recognizer=None):
        self.video_path = video_path
        self.model_choice = model_choice
        self.dlib_model_type = dlib_model_type
        self.dlib_upsample = dlib_upsample
        self.confidence_threshold = confidence_threshold
        self.show_landmarks = show_landmarks
        self.box_color_rgb = hex_to_rgb(box_color)
        self.landmark_color_rgb = hex_to_rgb(landmark_color)
        self.playback_speed = playback_speed
        # Initialize MTCNN
        if "mtcnn_detector" not in st.session_state or st.session_state.mtcnn_detector is None:
            from config.settings import get_gpu_status
            try:
                _, device = get_gpu_status()
                st.session_state.mtcnn_detector = MTCNN(
                    keep_all=True, device=device, min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7], factor=0.709
                )
                logger.info("MTCNN detector initialized in VideoFileProcessor.")
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
        self.face_processor = FaceDetectionProcessor(
            model_choice, dlib_model_type, dlib_upsample, confidence_threshold,
            show_landmarks, box_color, landmark_color, recognizer=recognizer
        )

    def process_video(self, frame_placeholder, progress_bar, save_video, save_dir, filename_prefix):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            st.error("❌ Failed to open video file.")
            return
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if total_frames <= 0:
            total_frames = float('inf')
        if save_video:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = save_path / f"{filename_prefix}_annotated_{timestamp}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        st.session_state.total_faces_detected = 0
        current_frame = 0
        try:
            while cap.isOpened() and st.session_state.video_processing:
                ret, frame = cap.read()
                if not ret:
                    break
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_processed, scale = preprocess_image(img_rgb)
                faces = self.face_processor.process_frame(img_processed, scale)
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
                    box_color = self.face_processor.match_color_rgb if 'is_match' in face and face['is_match'] else self.face_processor.no_match_color_rgb if 'is_match' in face else self.box_color_rgb
                    text = f"{'Match' if 'is_match' in face and face['is_match'] else 'No Match'} ({face['similarity']:.2f})" if 'is_match' in face else f"{confidence:.2f}"
                    draw_rectangle(img_rgb, (x, y), (x + width, y + height), box_color)
                    draw_text(img_rgb, text, (x, y - 10), box_color)
                    if self.show_landmarks:
                        for key, (px, py) in face['keypoints'].items():
                            px, py = int(px / scale), int(py / scale)
                            draw_circle(img_rgb, (px, py), self.landmark_color_rgb)
                    count += 1
                st.session_state.total_faces_detected = count
                frame_placeholder.image(img_rgb, caption=f"Processed Video Frame: {count} face(s) detected", use_container_width=True)
                if save_video:
                    out.write(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
                current_frame += 1
                if total_frames != float('inf'):
                    progress = min(current_frame / total_frames, 1.0)
                    progress_bar.progress(progress)
                time.sleep(1 / (fps * self.playback_speed)) if fps > 0 else time.sleep(1 / 30)
            if save_video:
                out.release()
                st.success(f"✅ Annotated video saved at `{output_path}`")
        except Exception as e:
            st.error(f"❌ Video processing error: {e}")
            logger.error(f"Video Processing Error: {e}")
        finally:
            cap.release()
            if save_video:
                out.release()