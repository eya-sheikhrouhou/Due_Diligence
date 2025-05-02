import streamlit as st
from streamlit_webrtc import webrtc_streamer, RTCConfiguration, WebRtcMode
from config.settings import initialize_session_state, setup_page_config, get_gpu_status
from utils.misc_utils import is_valid_url
from utils.image_utils import save_image, process_uploaded_images, process_webcam_image, process_ip_camera
from processors.face_processor import FaceDetectionProcessor
from processors.face_recognizer import FaceRecognizer
from processors.video_processor import VideoFileProcessor
from detectors.dlib_detector import load_dlib_models
import os
import logging
from PIL import Image
import numpy as np
import io
import uuid

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
class SuppressScriptRunContextFilter(logging.Filter):
    def filter(self, record):
        return "missing ScriptRunContext" not in record.getMessage()
logger.addFilter(SuppressScriptRunContextFilter())

# --- Initialize Session State ---
initialize_session_state()
if "cropped_faces" not in st.session_state:
    st.session_state.cropped_faces = []

# --- Streamlit Page Config ---
setup_page_config()

# --- Display GPU Status ---
gpu_available, device = get_gpu_status()
st.write(f"GPU Available: {gpu_available} (Using {'GPU' if gpu_available else 'CPU'})")

# --- Title ---
st.title("📷 Enhanced Face Detection with MTCNN or DLib")

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
    ["Use IP Camera", "Use Local Webcam", "Upload Images", "Upload Video", "Real-Time Detection (Webcam)", "Face Recognition"],
    key="input_method_radio"
)

# --- Sidebar Controls ---
st.sidebar.header("Settings")
debug_mode = st.sidebar.checkbox("Enable debug mode", value=False)
model_choice = st.sidebar.radio("Choose Face Detection Model:", ["MTCNN", "DLib"])
dlib_model_type = st.sidebar.radio("DLib Model Type:", ["HOG (faster)", "CNN (more accurate)"]) if model_choice == "DLib" else None
confidence_threshold = st.sidebar.slider("Minimum confidence (MTCNN only):", 0.0, 1.0, 0.8, 0.01) if model_choice == "MTCNN" else None
similarity_threshold = st.sidebar.slider("Face Recognition Similarity Threshold:", 0.0, 1.0, 0.6, 0.01) if (model_choice == "MTCNN") and (input_method == "Face Recognition") else 0.6
dlib_upsample = st.sidebar.slider("DLib Upsampling (higher = better detection, slower):", 0, 3, 1, 1) if model_choice == "DLib" else 1
if input_method == "Use IP Camera":
    ip_timeout = st.sidebar.slider("IP Camera Timeout (seconds):", 1, 10, 5, 1)
    max_retries = st.sidebar.slider("IP Camera Retry Attempts:", 1, 5, 3, 1)
else:
    ip_timeout = None
    max_retries = None 
show_landmarks = st.sidebar.checkbox("Show Facial Landmarks", value=True)
box_color = st.sidebar.color_picker("Bounding Box Color:", "#800000")  # Default: dark red
landmark_color = st.sidebar.color_picker("Landmark Color:", "#FF0000")  # Default: bright red
playback_speed = st.sidebar.slider("Video Playback Speed:", 0.5, 2.0, 1.0, 0.1) if input_method == "Upload Video" else None
max_file_size_mb = 5  # Limit uploaded file size

# --- WebRTC Configuration ---
RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]}
    ]
})

# --- Face Recognition ---
if input_method == "Face Recognition":
    if model_choice != "MTCNN":
        st.warning("⚠️ Face Recognition requires MTCNN. Please select MTCNN as the model.")
    else:
        st.info("ℹ️ Upload a reference image and ensure browser webcam access is enabled.")
        # Restart Stream Button
        if st.button("🔄 Restart Stream"):
            st.session_state.stream_key = str(uuid.uuid4())
            st.session_state.reference_embedding = None
            st.session_state.cropped_faces = []
            st.rerun()
        reference_image = st.file_uploader("Upload Reference Image", type=["jpg", "jpeg", "png"], accept_multiple_files=False)
        if reference_image:
            try:
                # Display reference image
                logger.info("Loading reference image")
                pil_image = Image.open(reference_image).convert("RGB")
                st.image(pil_image, caption="Reference Image", use_container_width=True)
                # Initialize FaceRecognizer
                logger.info("Initializing FaceRecognizer")
                recognizer = FaceRecognizer(similarity_threshold=similarity_threshold)
                image_np = np.array(pil_image)
                logger.info(f"Processing reference image: size={image_np.shape}")
                recognizer.set_reference_embedding(image_np)
                if recognizer.reference_embedding is not None:
                    st.session_state.reference_embedding = recognizer.reference_embedding
                    st.success("✅ Reference image processed successfully.")
                    # Display cropped face from reference image
                    cropped_faces_container = st.container()
                    with cropped_faces_container:
                        st.markdown("### Recognized Faces")
                        if st.session_state.cropped_faces:
                            cols = st.columns(min(len(st.session_state.cropped_faces), 3))
                            for idx, cropped_face in enumerate(st.session_state.cropped_faces):
                                with cols[idx % 3]:
                                    st.image(cropped_face['image'], caption=cropped_face['caption'], use_container_width=True)
                        else:
                            st.write("No faces detected in the reference image.")
                    # Debug info
                    debug_placeholder = st.container() if debug_mode else None
                    if debug_mode:
                        with debug_placeholder:
                            st.write("Debug Info: Check terminal logs for embedding, similarity, and cropped face details.")
                            st.write(f"Cropped Faces Container Status: {len(st.session_state.cropped_faces)} faces displayed (from reference image).")
                    # Webcam stream for face recognition
                    logger.info("Starting webrtc_streamer for face recognition")
                    stream_key = st.session_state.get("stream_key", "face-recognition")
                    stream = webrtc_streamer(
                        key=stream_key,
                        mode=WebRtcMode.SENDRECV,
                        video_processor_factory=lambda: FaceDetectionProcessor(
                            model_choice, dlib_model_type, dlib_upsample, confidence_threshold,
                            show_landmarks, box_color, landmark_color, recognizer=recognizer,
                            similarity_threshold=similarity_threshold, debug_placeholder=None  # Not used for webcam faces here
                        ),
                        rtc_configuration=RTC_CONFIG,
                        media_stream_constraints={
                            "video": {
                                "width": {"ideal": 640},
                                "height": {"ideal": 480},
                                "frameRate": {"ideal": 30}
                            },
                            "audio": False
                        },
                        async_processing=True
                    )
                    if stream.state.playing is False:
                        st.warning("⚠️ Webcam stream failed to start. Check browser permissions, webcam compatibility, or click 'Restart Stream'.")
                        logger.warning("Webcam stream failed to start")
                else:
                    st.error("❌ No face detected in the reference image.")
                    logger.error("Reference image processing failed: no face detected")
            except Exception as e:
                st.error(f"❌ Error processing reference image: {e}")
                logger.error(f"Reference Image Error: {e}")

# --- Real-Time Detection (Webcam) ---
elif input_method == "Real-Time Detection (Webcam)":
    st.info("ℹ️ Ensure browser webcam access is enabled.")
    logger.info("Starting webrtc_streamer for real-time detection")
    stream = webrtc_streamer(
        key=st.session_state.get("stream_key", "face-detection"),
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=lambda: FaceDetectionProcessor(
            model_choice, dlib_model_type, dlib_upsample, confidence_threshold,
            show_landmarks, box_color, landmark_color, recognizer=None
        ),
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={
            "video": {
                "width": {"ideal": 640},
                "height": {"ideal": 480},
                "frameRate": {"ideal": 30}
            },
            "audio": False
        },
        async_processing=True
    )
    if stream.state.playing is False:
        st.warning("⚠️ Webcam stream failed to start. Check browser permissions or webcam compatibility.")
        logger.warning("Webcam stream failed to start")

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
if st.session_state.captured_images and input_method not in ["Real-Time Detection (Webcam)", "Face Recognition"]:
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
    current_input_method = st.session_state.get("input_method_radio", "Use IP Camera")
    st.session_state.clear()
    st.session_state.input_method_radio = current_input_method
    st.rerun()