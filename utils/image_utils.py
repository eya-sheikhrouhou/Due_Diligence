import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
from pathlib import Path
import datetime
import logging
import torch
from utils.misc_utils import sanitize_input, hex_to_rgb

logger = logging.getLogger(__name__)

def preprocess_image(image_np, max_size=640):
    """Preprocess image by resizing if necessary."""
    h, w = image_np.shape[:2]
    scale = min(max_size / w, max_size / h)
    if scale < 1:
        new_w, new_h = int(w * scale), int(h * scale)
        image_np = cv2.resize(image_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        scale = 1.0
    return image_np, scale

def save_image(image, source_label, save_dir, filename_prefix):
    """Save image to specified directory."""
    save_dir = sanitize_input(save_dir) or "saved_images"
    filename_prefix = sanitize_input(filename_prefix) or "captured"
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

def draw_rectangle(image, top_left, bottom_right, color):
    """Draw a rectangle on the image."""
    color_rgb = hex_to_rgb(color) if isinstance(color, str) else color
    cv2.rectangle(image, top_left, bottom_right, color_rgb, 2)

def draw_text(image, text, position, color):
    """Draw text on the image."""
    color_rgb = hex_to_rgb(color) if isinstance(color, str) else color
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_rgb, 1)

def draw_circle(image, center, color):
    """Draw a circle on the image."""
    color_rgb = hex_to_rgb(color) if isinstance(color, str) else color
    cv2.circle(image, center, 2, color_rgb, -1)

def process_uploaded_images(uploaded_files, max_file_size_mb):
    """Process uploaded image files."""
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

def process_webcam_image(camera_image, max_file_size_mb):
    """Process image from local webcam."""
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

def process_ip_camera(url, max_retries, ip_timeout):
    """Capture and process image from IP camera."""
    import time
    for attempt in range(max_retries):
        try:
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                st.error(f"❌ Failed to connect (Attempt {attempt + 1}/{max_retries}).")
                st.markdown(f"[🔗 Test Stream]({url})")
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

def extract_reference_embedding(pil_image):
    """Extract facial embedding from a reference image."""
    if "mtcnn_detector" not in st.session_state or st.session_state.mtcnn_detector is None:
        st.error("❌ MTCNN detector not initialized.")
        logger.error("MTCNN detector not initialized.")
        return None
    if "resnet" not in st.session_state or st.session_state.resnet is None:
        st.error("❌ InceptionResnetV1 not initialized.")
        logger.error("InceptionResnetV1 not initialized.")
        return None
    try:
        img_rgb = np.array(pil_image.convert("RGB"))
        logger.debug(f"Reference image shape: {img_rgb.shape}")
        faces_cropped = st.session_state.mtcnn_detector(img_rgb, save_path=None)
        if faces_cropped is None or len(faces_cropped) == 0:
            logger.warning("No faces detected in reference image.")
            return None
        face_tensor = faces_cropped[0].unsqueeze(0)  # Add batch dimension
        logger.debug(f"Face tensor shape: {face_tensor.shape}")
        if torch.cuda.is_available():
            face_tensor = face_tensor.cuda()
        with torch.no_grad():
            embedding = st.session_state.resnet(face_tensor).cpu().numpy().flatten()
        logger.info(f"Reference embedding computed: shape={embedding.shape}, norm={np.linalg.norm(embedding):.2f}")
        return embedding
    except Exception as e:
        st.error(f"❌ Error extracting embedding: {e}")
        logger.error(f"Embedding Extraction Error: {e}")
        return None