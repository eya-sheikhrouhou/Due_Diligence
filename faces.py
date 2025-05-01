import streamlit as st
import cv2
from PIL import Image
import datetime
import numpy as np
import io
import re
import time
import logging
from pathlib import Path
from mtcnn import MTCNN
import tensorflow as tf
import urllib.parse
import dlib
import os
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# --- Suppress TensorFlow Warnings ---
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Suppress oneDNN warnings
tf.get_logger().setLevel('ERROR')  # Suppress deprecated warnings

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Check GPU Availability ---
gpu_available = tf.config.list_physical_devices('GPU')

# --- Streamlit Page Config (Must be first Streamlit command) ---
st.set_page_config(page_title="Enhanced Face Detection with MTCNN or DLib", layout="wide")

# --- Display GPU Status ---
st.write(f"GPU Available: {bool(gpu_available)} (Using {'GPU' if gpu_available else 'CPU'})")

# --- Title ---
st.title("📷 Enhanced Face Detection with MTCNN or DLib")

# --- Sidebar Controls ---
st.sidebar.header("Settings")
debug_mode = st.sidebar.checkbox("Enable debug mode", value=False)
model_choice = st.sidebar.radio("Choose Face Detection Model:", ["MTCNN", "DLib"])
dlib_model_type = st.sidebar.radio("DLib Model Type:", ["HOG (faster)", "CNN (more accurate)"]) if model_choice == "DLib" else None
confidence_threshold = st.sidebar.slider("Minimum confidence (MTCNN only):", 0.0, 1.0, 0.9, 0.01)
dlib_upsample = st.sidebar.slider("DLib Upsampling (higher = better detection, slower):", 0, 3, 1, 1) if model_choice == "DLib" else 1
show_landmarks = st.sidebar.checkbox("Show Facial Landmarks", value=True)
box_color = st.sidebar.color_picker("Bounding Box Color:", "#800000")  # Default: dark red
landmark_color = st.sidebar.color_picker("Landmark Color:", "#FF0000")  # Default: bright red
ip_timeout = st.sidebar.slider("IP Camera Timeout (seconds):", 1, 10, 5, 1)
max_retries = st.sidebar.slider("IP Camera Retry Attempts:", 1, 5, 3, 1)
max_file_size_mb = 5  # Limit uploaded file size

# Convert hex colors to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

box_color_rgb = hex_to_rgb(box_color)
landmark_color_rgb = hex_to_rgb(landmark_color)

# --- Display Total Face Count in Sidebar ---
if "total_faces_detected" not in st.session_state:
    st.session_state.total_faces_detected = 0
st.sidebar.metric("Total Faces Detected", st.session_state.total_faces_detected)

# --- Input Method ---
input_method = st.radio("Input Method:", ["Use IP Camera", "Use Local Webcam", "Upload Images", "Upload Video", "Real-Time Detection (Webcam)"])

# --- Save Directory & Prefix ---
save_dir = st.text_input("Save Directory (leave blank for default):", value="saved_images")
filename_prefix = st.text_input("📄 Filename Prefix:", value="captured")

# --- Sanitize Input ---
def sanitize_input(text):
    return re.sub(r'[^\w\-]', '', text.replace('..', '').replace('/', '').replace('\\', ''))

save_dir = sanitize_input(save_dir) or "saved_images"
filename_prefix = sanitize_input(filename_prefix) or "captured"

# --- Save Image Function ---
def save_image(image, source_label):
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{source_label}_{timestamp}.jpg"
    full_path = save_path / filename
    try:
        image.save(full_path, format="JPEG", quality=95)
        st.success(f"✅ Image saved at `{full_path}`")
        return str(full_path)
    except OSError as e:
        st.error(f"❌ Error saving image: {e}")
        return None

# --- Preprocess Image ---
def preprocess_image(image_np, max_size=640):
    h, w = image_np.shape[:2]
    scale = min(max_size / w, max_size / h)
    if scale < 1:
        new_w, new_h = int(w * scale), int(h * scale)
        image_np = cv2.resize(image_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        scale = 1.0  # No scaling applied
    return image_np, scale

# --- Load DLib Models ---
try:
    if model_choice == "DLib" and dlib_model_type == "CNN (more accurate)":
        cnn_model_path = "mmod_human_face_detector.dat"
        if not os.path.exists(cnn_model_path):
            st.error(f"❌ CNN model file not found at {cnn_model_path}. Please download 'mmod_human_face_detector.dat' from http://dlib.net/files/mmod_human_face_detector.dat.bz2 and place it in the project directory.")
            dlib_detector = dlib.get_frontal_face_detector()  # Fallback to HOG
            dlib_model_type = "HOG (faster)"  # Update to reflect fallback
        else:
            dlib_detector = dlib.cnn_face_detection_model_v1(cnn_model_path)
    else:
        dlib_detector = dlib.get_frontal_face_detector()

    # Path to shape predictor file (download and place in project directory)
    shape_predictor_path = "shape_predictor_68_face_landmarks.dat"
    if not os.path.exists(shape_predictor_path):
        st.error(f"❌ Shape predictor file not found at {shape_predictor_path}. Please download 'shape_predictor_68_face_landmarks.dat' from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2 and place it in the project directory to enable facial landmarks with DLib.")
        dlib_predictor = None
    else:
        dlib_predictor = dlib.shape_predictor(shape_predictor_path)
except Exception as e:
    st.error(f"❌ Error loading DLib models: {e}")
    dlib_detector = None
    dlib_predictor = None

# --- Init Session State ---
if "captured_images" not in st.session_state:
    st.session_state.captured_images = []
if "source" not in st.session_state:
    st.session_state.source = ""
if "saved_path" not in st.session_state:
    st.session_state.saved_path = None
if "mtcnn_detector" not in st.session_state:
    st.session_state.mtcnn_detector = MTCNN(device="GPU:0" if gpu_available else "CPU:0")
if "dlib_detector" not in st.session_state:
    st.session_state.dlib_detector = dlib_detector

# --- Validate URL ---
def is_valid_url(url):
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

# --- Real-Time Face Detection (Webcam) ---
class FaceDetectionProcessor(VideoProcessorBase):
    def __init__(self):
        self.model_choice = model_choice
        self.dlib_model_type = dlib_model_type
        self.dlib_upsample = dlib_upsample
        self.confidence_threshold = confidence_threshold
        self.show_landmarks = show_landmarks
        self.box_color_rgb = box_color_rgb
        self.landmark_color_rgb = landmark_color_rgb

    def recv(self, frame):
        try:
            # Fix: Use "bgr24" instead of "bgr"
            img = frame.to_ndarray(format="bgr24")
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_processed, scale = preprocess_image(img_rgb, max_size=640)

            if self.model_choice == "MTCNN":
                detector = st.session_state.mtcnn_detector
                faces = detector.detect_faces(img_processed)
            else:  # DLib
                if st.session_state.dlib_detector is None:
                    st.error("❌ DLib detector not initialized.")
                    return frame
                gray = cv2.cvtColor(img_processed, cv2.COLOR_RGB2GRAY)
                faces_dlib = st.session_state.dlib_detector(gray, self.dlib_upsample)
                faces = []
                for face in faces_dlib:
                    if self.dlib_model_type == "CNN (more accurate)":
                        rect = face.rect  # mmod_rectangle has .rect
                        confidence = face.confidence
                    else:
                        rect = face  # HOG detector returns a rectangle directly
                        confidence = 1.0  # Placeholder for HOG
                    x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
                    x, y = max(0, x), max(0, y)
                    w, h = min(w, img_processed.shape[1] - x), min(h, img_processed.shape[0] - y)
                    keypoints = {}
                    if dlib_predictor and self.show_landmarks:
                        shape = dlib_predictor(gray, rect)
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
                cv2.rectangle(img_rgb, (x, y), (x + width, y + height), self.box_color_rgb, 2)
                cv2.putText(img_rgb, f"{confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.box_color_rgb, 1)
                if self.show_landmarks:
                    for key, (px, py) in face['keypoints'].items():
                        px, py = int(px / scale), int(py / scale)
                        cv2.circle(img_rgb, (px, py), 2, self.landmark_color_rgb, -1)
                count += 1

            st.session_state.total_faces_detected = count
            return frame.from_ndarray(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), format="bgr24")
        except Exception as e:
            logger.error(f"Real-time detection error: {e}")
            st.error(f"❌ Real-time detection error: {e}")
            return frame

if input_method == "Real-Time Detection (Webcam)":
    st.info("ℹ️ Ensure browser webcam access is enabled.")
    webrtc_streamer(
        key="face-detection",
        video_processor_factory=FaceDetectionProcessor,
        rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
        media_stream_constraints={"video": True, "audio": False}
    )

# --- IP Camera ---
elif input_method == "Use IP Camera":
    ip_default = "http://192.168.1.7:8080/video"
    IP_CAMERA_URL = st.text_input("IP Camera URL:", ip_default)

    if not is_valid_url(IP_CAMERA_URL):
        st.warning("❌ Invalid URL. Use 'http://' or 'https://'.")
    else:
        # Live Preview with Responsive Size
        st.markdown("### Live Camera Preview")
        st.markdown(
            f'<iframe src="{IP_CAMERA_URL}" style="width:90%; height:90vh;" frameborder="0"></iframe>',
            unsafe_allow_html=True
        )

        if st.button("📸 Capture Photo from IP Camera"):
            with st.spinner("Connecting to camera..."):
                for attempt in range(max_retries):
                    try:
                        cap = cv2.VideoCapture(IP_CAMERA_URL)
                        if not cap.isOpened():
                            st.error(f"❌ Failed to connect (Attempt {attempt + 1}/{max_retries}).")
                            st.markdown(f"[🔗 Test Stream]({IP_CAMERA_URL})")
                            continue
                        start_time = time.time()
                        while time.time() - start_time < ip_timeout:
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame_rgb)
                                img.thumbnail((1024, 768))
                                st.session_state.captured_images = [(img, "ip")]
                                st.session_state.source = "ip"
                                break
                        else:
                            st.error(f"❌ Timeout (Attempt {attempt + 1}/{max_retries}).")
                        cap.release()
                        if st.session_state.captured_images:
                            break
                    except Exception as e:
                        st.error(f"❌ Error (Attempt {attempt + 1}/{max_retries}): {e}")
                        logger.error(f"IP Camera Error: {e}")
                    time.sleep(1)
                else:
                    st.error("❌ Max retries reached. Check camera URL or network.")

# --- Local Webcam ---
elif input_method == "Use Local Webcam":
    st.info("ℹ️ Ensure browser webcam access is enabled.")
    camera_image = st.camera_input("📷 Take a Picture")
    if camera_image:
        with st.spinner("Processing image..."):
            try:
                image_bytes = camera_image.read()
                if len(image_bytes) > max_file_size_mb * 1024 * 1024:
                    st.error(f"❌ Image exceeds {max_file_size_mb}MB limit.")
                    st.session_state.captured_images = []
                    st.session_state.source = ""
                else:
                    try:
                        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    except Exception as e:
                        logger.warning(f"PIL failed to decode image: {e}. Falling back to OpenCV.")
                        image_np = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                        if image_np is None:
                            raise ValueError("Failed to decode image with OpenCV.")
                        image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(image_np)

                    pil_image.thumbnail((1024, 768))
                    st.session_state.captured_images = [(pil_image, "webcam")]
                    st.session_state.source = "webcam"
            except Exception as e:
                st.error(f"❌ Error processing webcam image: {e}")
                logger.error(f"Webcam Error: {e}")

# --- Upload Images ---
elif input_method == "Upload Images":
    uploaded_files = st.file_uploader("Upload Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        with st.spinner("Processing uploaded images..."):
            st.session_state.captured_images = []
            for uploaded_file in uploaded_files:
                try:
                    if uploaded_file.size > max_file_size_mb * 1024 * 1024:
                        st.error(f"❌ {uploaded_file.name} exceeds {max_file_size_mb}MB limit.")
                        continue
                    pil_image = Image.open(uploaded_file).convert("RGB")
                    pil_image.thumbnail((1024, 768))
                    st.session_state.captured_images.append((pil_image, "upload"))
                    st.session_state.source = "upload"
                except Exception as e:
                    st.error(f"❌ Error processing {uploaded_file.name}: {e}")
                    logger.error(f"Upload Error: {e}")

# --- Upload Video ---
elif input_method == "Upload Video":
    uploaded_video = st.file_uploader("Upload Video", type=["mp4", "avi", "mov"])
    if uploaded_video:
        with st.spinner("Processing video..."):
            # Save the video temporarily
            temp_video_path = "temp_video.mp4"
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_video.read())
            
            cap = cv2.VideoCapture(temp_video_path)
            st.session_state.captured_images = []
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                pil_image.thumbnail((1024, 768))
                st.session_state.captured_images.append((pil_image, f"video_frame_{frame_count}"))
                st.session_state.source = "video"
                frame_count += 1
                if frame_count >= 10:  # Limit to 10 frames for demo
                    break
            cap.release()
            os.remove(temp_video_path)

# --- Display and Process Images ---
if st.session_state.captured_images and input_method != "Real-Time Detection (Webcam)":
    for idx, (pil_image, source) in enumerate(st.session_state.captured_images):
        st.image(pil_image, caption=f"Captured Image {idx + 1} ({source})", use_container_width=True)
        if st.button(f"💾 Save Image {idx + 1}", key=f"save_{idx}"):
            saved_path = save_image(pil_image, source)
            st.session_state.saved_path = saved_path

    # --- Face Detection ---
    if st.button("🧠 Detect Faces"):
        with st.spinner(f"Detecting faces with {model_choice}..."):
            # Batch processing for MTCNN
            if model_choice == "MTCNN":
                images_np = [np.array(pil_image.convert("RGB"), dtype=np.uint8) for pil_image, _ in st.session_state.captured_images]
                images_processed = []
                scales = []
                for img_np in images_np:
                    img_processed, scale = preprocess_image(img_np, max_size=640)
                    images_processed.append(img_processed)
                    scales.append(scale)
                try:
                    detector = st.session_state.mtcnn_detector
                    all_faces = detector.detect_faces(images_processed)  # Batch detection
                except Exception as e:
                    st.error(f"❌ Batch detection failed with MTCNN: {e}. Falling back to sequential processing.")
                    all_faces = []
                    for img_processed in images_processed:
                        faces = detector.detect_faces(img_processed)
                        all_faces.append(faces)
            else:
                all_faces = []
                for idx, (pil_image, _) in enumerate(st.session_state.captured_images):
                    image_np = np.array(pil_image.convert("RGB"), dtype=np.uint8)
                    image_np_processed, scale = preprocess_image(image_np, max_size=640)
                    gray = cv2.cvtColor(image_np_processed, cv2.COLOR_RGB2GRAY)
                    faces_dlib = st.session_state.dlib_detector(gray, dlib_upsample)
                    faces = []
                    for face in faces_dlib:
                        if dlib_model_type == "CNN (more accurate)":
                            rect = face.rect  # mmod_rectangle has .rect
                            confidence = face.confidence
                        else:
                            rect = face  # HOG detector returns a rectangle directly
                            confidence = 1.0  # Placeholder for HOG
                        x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
                        x, y = max(0, x), max(0, y)
                        w, h = min(w, image_np_processed.shape[1] - x), min(h, image_np_processed.shape[0] - y)
                        keypoints = {}
                        if dlib_predictor and show_landmarks:
                            shape = dlib_predictor(gray, rect)
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
                    all_faces.append(faces)

            total_faces = 0
            for idx, (pil_image, source) in enumerate(st.session_state.captured_images):
                try:
                    image_np = np.array(pil_image.convert("RGB"), dtype=np.uint8)
                    scale = scales[idx] if model_choice == "MTCNN" else preprocess_image(image_np, max_size=640)[1]
                    if debug_mode:
                        st.write(f"Image {idx + 1}: mode={pil_image.mode}, size={pil_image.size}, preprocessed shape={image_np.shape}, scale={scale}")

                    faces = all_faces[idx]
                    if not faces:
                        st.warning(f"😕 No faces detected in Image {idx + 1}.")
                        continue

                    annotated_np = image_np.copy()
                    count = 0
                    for face in faces:
                        x, y, width, height = face['box']
                        confidence = face['confidence']
                        if model_choice == "MTCNN" and confidence < confidence_threshold:
                            continue
                        x, y = max(0, int(x / scale)), max(0, int(y / scale))
                        width, height = int(width / scale), int(height / scale)
                        x_end, y_end = min(x + width, image_np.shape[1]), min(y + height, image_np.shape[0])
                        x, y = max(0, x), max(0, y)
                        width, height = x_end - x, y_end - y
                        if width <= 0 or height <= 0:
                            continue
                        cv2.rectangle(annotated_np, (x, y), (x + width, y + height), box_color_rgb, 2)
                        cv2.putText(annotated_np, f"{confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color_rgb, 1)
                        if show_landmarks:
                            for key, (px, py) in face['keypoints'].items():
                                px, py = int(px / scale), int(py / scale)
                                cv2.circle(annotated_np, (px, py), 2, landmark_color_rgb, -1)
                        count += 1

                    total_faces += count
                    st.image(annotated_np, caption=f"Image {idx + 1}: Detected {count} face(s) using {model_choice}", use_container_width=True)
                    if model_choice == "MTCNN":
                        st.success(f"✅ Image {idx + 1}: Detected {count} face(s) with confidence >= {confidence_threshold}")
                    else:
                        st.success(f"✅ Image {idx + 1}: Detected {count} face(s) with confidence = {1.00 if dlib_model_type != 'CNN (more accurate)' else 'variable'} (DLib {dlib_model_type})")

                    annotated_pil = Image.fromarray(annotated_np)
                    buf = io.BytesIO()
                    annotated_pil.save(buf, format="JPEG")
                    st.download_button(
                        f"⬇️ Download Annotated Image {idx + 1}",
                        data=buf.getvalue(),
                        file_name=f"detected_faces_{idx + 1}.jpg",
                        mime="image/jpeg",
                        key=f"download_{idx}"
                    )

                except Exception as e:
                    st.error(f"❌ Face detection error for Image {idx + 1}: {e}")
                    logger.error(f"Detection Error: {e}")

            st.session_state.total_faces_detected = total_faces

# --- Clear Session ---
if st.button("Clear"):
    st.session_state.clear()
    st.rerun()