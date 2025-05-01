import streamlit as st
import cv2
from PIL import Image
import datetime
import numpy as np
import io
import re
from pathlib import Path
from mtcnn import MTCNN
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

# Configure the Streamlit app
st.set_page_config(page_title="Camera Capture with MTCNN Face Detection", layout="centered")
st.title("📷 Capture Photo & Detect Faces with MTCNN")

# Debug mode toggle
debug_mode = st.checkbox("Enable debug mode", value=False)

# Input method: IP camera or local webcam
input_method = st.radio("Choose input method:", ["Use IP Camera", "Use local webcam"])

# Save location and filename prefix
save_dir = st.text_input("Enter save directory (leave blank for default):", value="saved_images")
if not save_dir.strip():
    save_dir = "saved_images"

filename_prefix = st.text_input("📄 Optional filename prefix:", value="captured")
if not filename_prefix.strip():
    filename_prefix = "captured"

# Sanitize inputs to prevent directory traversal and invalid filenames
def sanitize_input(text):
    return re.sub(r'[^\w\-]', '', text.replace('..', '').replace('/', '').replace('\\', ''))

save_dir = sanitize_input(save_dir)
filename_prefix = sanitize_input(filename_prefix)

# Function to save image
def save_image(image, source_label):
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{source_label}_{timestamp}.jpg"
    full_path = save_path / filename

    try:
        image.save(full_path, quality=95)
        st.success(f"✅ Image saved at `{full_path}`")
        return str(full_path)
    except OSError as e:
        st.error(f"❌ Error saving image: {e}. Check disk space or permissions.")
        return None

# Initialize session state
if "captured_image" not in st.session_state:
    st.session_state.captured_image = None
if "source" not in st.session_state:
    st.session_state.source = ""

# --- IP Camera Section ---
if input_method == "Use IP Camera":
    ip_default = "http://192.168.1.7:8080/video"
    IP_CAMERA_URL = st.text_input("Enter your IP Camera URL:", ip_default)

    if not IP_CAMERA_URL.startswith("http"):
        st.warning("❌ Please enter a valid URL starting with 'http'.")
    elif st.button("📸 Capture Photo from IP Camera"):
        with st.spinner("Connecting to camera and capturing image..."):
            try:
                cap = cv2.VideoCapture(IP_CAMERA_URL)
                if not cap.isOpened():
                    st.error("❌ Failed to connect to IP camera! Check the URL and ensure the camera is active.")
                else:
                    start_time = time.time()
                    while time.time() - start_time < 5:  # 5-second timeout
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            img = Image.fromarray(frame_rgb)
                            img.thumbnail((1024, 768))
                            st.session_state.captured_image = img
                            st.session_state.source = "ip"
                            break
                        time.sleep(0.1)
                    else:
                        st.error("❌ Failed to capture image within timeout period.")
                    cap.release()
            except Exception as e:
                st.error(f"❌ Error accessing IP camera: {e}")

# --- Local Webcam Section ---
elif input_method == "Use local webcam":
    st.info("ℹ️ Ensure your browser has webcam access enabled.")
    camera_image = st.camera_input("📷 Take a picture")
    if camera_image:
        with st.spinner("Processing your image..."):
            try:
                file_bytes = camera_image.read()
                pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                pil_image.thumbnail((1024, 768))
                st.session_state.captured_image = pil_image
                st.session_state.source = "webcam"
            except Exception as e:
                st.error(f"❌ Error processing webcam image: {e}")

# --- Show captured image and allow saving ---
if st.session_state.captured_image:
    st.image(st.session_state.captured_image, caption="Captured Image", use_container_width=True)
    if st.button("💾 Save Image"):
        saved_path = save_image(st.session_state.captured_image, st.session_state.source)
        st.session_state.saved_path = saved_path

# --- Face Detection Section ---
if st.session_state.get("captured_image") and st.button("🧠 Detect Faces"):
    with st.spinner("Detecting faces with MTCNN..."):
        try:
            # Initialize MTCNN detector
            detector = MTCNN(device="CPU:0")  # Use CPU; change to "GPU:0" if available
            pil_image = st.session_state.get("captured_image")

            if not isinstance(pil_image, Image.Image):
                st.error("❌ Captured image is not a valid PIL Image object.")
            else:
                # Convert PIL image to NumPy array (RGB)
                image_np = np.array(pil_image.convert("RGB"), dtype=np.uint8)
                if debug_mode:
                    st.write(f"Debug: Image mode={pil_image.mode}, size={pil_image.size}, array shape={image_np.shape}")

                # Detect faces
                faces = detector.detect_faces(image_np)
                if not faces:
                    st.warning("😕 No faces detected.")
                else:
                    # Create a figure for visualization
                    fig, ax = plt.subplots()
                    ax.imshow(image_np)
                    ax.axis("off")

                    for face in faces:
                        x, y, width, height = face['box']
                        confidence = face['confidence']
                        if confidence < 0.9:  # Filter low-confidence detections
                            continue

                        # Draw bounding box
                        rect = Rectangle((x, y), width, height, fill=False, color='maroon', linewidth=2)
                        ax.add_patch(rect)

                        # Draw facial landmarks
                        for key, value in face['keypoints'].items():
                            dot = Circle(value, radius=2, color='maroon')
                            ax.add_patch(dot)

                    # Display the result
                    st.pyplot(fig)
                    st.success(f"✅ Detected {len(faces)} face(s) with confidence >= 0.9")
                    plt.close(fig)

        except Exception as e:
            st.error(f"❌ Error during MTCNN face detection: {e}")

# --- Clear Button ---
if st.button("Clear"):
    st.session_state.clear()
    st.rerun()