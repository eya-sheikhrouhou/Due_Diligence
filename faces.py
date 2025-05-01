import streamlit as st
from streamlit_webrtc import webrtc_streamer, RTCConfiguration, WebRtcMode
from config.settings import initialize_session_state, setup_page_config, get_gpu_status
from utils.misc_utils import is_valid_url
from utils.image_utils import save_image, process_uploaded_images, process_webcam_image, process_ip_camera
from processors.face_processor import FaceDetectionProcessor
from processors.video_processor import VideoFileProcessor
from detectors.dlib_detector import load_dlib_models
import os
import logging
from PIL import Image
import numpy as np
import io

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Initialize Session State ---
initialize_session_state()

# --- Streamlit Page Config ---
setup_page_config()

# --- Display GPU Status ---
gpu_available, device = get_gpu_status()
st.write(f"GPU Available: {gpu_available} (Using {'GPU' if gpu_available else 'CPU'})")

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
playback_speed = st.sidebar.slider("Video Playback Speed:", 0.5, 2.0, 1.0, 0.1)
max_file_size_mb = 5  # Limit uploaded file size

# --- Display Total Face Count in Sidebar ---
if "total_faces_detected" not in st.session_state:
    st.session_state.total_faces_detected = 0
st.sidebar.metric("Total Faces Detected", st.session_state.total_faces_detected)

# --- Save Directory & Prefix ---
save_dir = st.text_input("Save Directory (leave blank for default):", value="saved_images")
filename_prefix = st.text_input("📄 Filename Prefix:", value="captured")

# --- Input Method ---
input_method = st.radio(
    "Input Method:",
    ["Use IP Camera", "Use Local Webcam", "Upload Images", "Upload Video", "Real-Time Detection (Webcam)"],
    key="input_method_radio"
)

# --- Real-Time Detection (Webcam) ---
if input_method == "Real-Time Detection (Webcam)":
    st.info("ℹ️ Ensure browser webcam access is enabled.")
    webrtc_streamer(
        key="face-detection",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=lambda: FaceDetectionProcessor(
            model_choice, dlib_model_type, dlib_upsample, confidence_threshold,
            show_landmarks, box_color, landmark_color
        ),
        rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True
    )

# --- IP Camera ---
elif input_method == "Use IP Camera":
    ip_default = "http://192.168.1.7:8080/video"
    IP_CAMERA_URL = st.text_input("IP Camera URL:", ip_default)
    if not is_valid_url(IP_CAMERA_URL):
        st.warning("❌ Invalid URL. Use 'http://' or 'https://'.")
    else:
        st.markdown("### Live Camera Preview")
        st.markdown(
            f'<iframe src="{IP_CAMERA_URL}" style="width:90%; height:90vh;" frameborder="0"></iframe>',
            unsafe_allow_html=True
        )
        if st.button("📸 Capture Photo from IP Camera"):
            process_ip_camera(IP_CAMERA_URL, max_retries, ip_timeout)

# --- Local Webcam ---
elif input_method == "Use Local Webcam":
    st.info("ℹ️ Ensure browser webcam access is enabled.")
    camera_image = st.camera_input("📷 Take a Picture")
    if camera_image:
        process_webcam_image(camera_image, max_file_size_mb)

# --- Upload Images ---
elif input_method == "Upload Images":
    uploaded_files = st.file_uploader("Upload Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files:
        process_uploaded_images(uploaded_files, max_file_size_mb)

# --- Upload Video ---
elif input_method == "Upload Video":
    uploaded_video = st.file_uploader("Upload Video", type=["mp4", "avi", "mov"])
    if uploaded_video:
        with st.spinner("Processing video..."):
            temp_video_path = "temp_video.mp4"
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_video.read())
            st.session_state.video_processing = False
            save_video = st.checkbox("Save Annotated Video", value=False)
            start_button = st.button("Start Detection")
            stop_button = st.button("Stop Detection")
            frame_placeholder = st.empty()
            progress_bar = st.progress(0)
            if start_button:
                st.session_state.video_processing = True
                video_processor = VideoFileProcessor(
                    temp_video_path, model_choice, dlib_model_type, dlib_upsample,
                    confidence_threshold, show_landmarks, box_color, landmark_color, playback_speed
                )
                video_processor.process_video(frame_placeholder, progress_bar, save_video, save_dir, filename_prefix)
            if stop_button:
                st.session_state.video_processing = False
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

# --- Display and Process Images ---
if st.session_state.captured_images and input_method != "Real-Time Detection (Webcam)":
    for idx, (pil_image, source) in enumerate(st.session_state.captured_images):
        st.image(pil_image, caption=f"Captured Image {idx + 1} ({source})", use_container_width=True)
        if st.button(f"💾 Save Image {idx + 1}", key=f"save_{idx}"):
            saved_path = save_image(pil_image, source, save_dir, filename_prefix)
            st.session_state.saved_path = saved_path

    # --- Face Detection for Images ---
    if st.button("🧠 Detect Faces"):
        with st.spinner(f"Detecting faces with {model_choice}..."):
            # Load DLib models if needed
            if model_choice == "DLib":
                load_dlib_models(model_choice, dlib_model_type)
            from detectors.mtcnn_detector import detect_faces_mtcnn
            from detectors.dlib_detector import detect_faces_dlib
            all_faces = []
            scales = []
            for idx, (pil_image, _) in enumerate(st.session_state.captured_images):
                from utils.image_utils import preprocess_image
                image_np = np.array(pil_image.convert("RGB"), dtype=np.uint8)
                image_processed, scale = preprocess_image(image_np)
                scales.append(scale)
                faces = []
                if model_choice == "MTCNN":
                    faces = detect_faces_mtcnn(image_processed, show_landmarks, confidence_threshold)
                else:
                    faces = detect_faces_dlib(image_processed, dlib_model_type, dlib_upsample, show_landmarks)
                all_faces.append(faces)

            total_faces = 0
            for idx, (pil_image, source) in enumerate(st.session_state.captured_images):
                try:
                    image_np = np.array(pil_image.convert("RGB"), dtype=np.uint8)
                    scale = scales[idx]
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
                        from utils.image_utils import draw_rectangle, draw_text, draw_circle
                        draw_rectangle(annotated_np, (x, y), (x + width, y + height), box_color)
                        draw_text(annotated_np, f"{confidence:.2f}", (x, y - 10), box_color)
                        if show_landmarks:
                            for key, (px, py) in face['keypoints'].items():
                                px, py = int(px / scale), int(py / scale)
                                draw_circle(annotated_np, (px, py), landmark_color)
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