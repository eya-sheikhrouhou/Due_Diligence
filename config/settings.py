import streamlit as st
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
import logging
import os

# --- Suppress TensorFlow Warnings ---
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

logger = logging.getLogger(__name__)

def initialize_session_state():
    """Initialize Streamlit session state with default values."""
    if "captured_images" not in st.session_state:
        st.session_state.captured_images = []
    if "source" not in st.session_state:
        st.session_state.source = ""
    if "saved_path" not in st.session_state:
        st.session_state.saved_path = None
    if "mtcnn_detector" not in st.session_state:
        try:
            gpu_available, device = get_gpu_status()
            st.session_state.mtcnn_detector = MTCNN(
                keep_all=True, device=device, min_face_size=20,
                thresholds=[0.6, 0.7, 0.7], factor=0.709
            )
            logger.info("MTCNN detector initialized successfully.")
        except Exception as e:
            st.error(f"❌ Failed to initialize MTCNN detector: {e}")
            st.session_state.mtcnn_detector = None
    if "resnet" not in st.session_state:
        try:
            gpu_available, device = get_gpu_status()
            st.session_state.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
            logger.info("InceptionResnetV1 initialized successfully.")
        except Exception as e:
            st.error(f"❌ Failed to initialize InceptionResnetV1: {e}")
            st.session_state.resnet = None
    if "dlib_detector" not in st.session_state:
        st.session_state.dlib_detector = None
    if "dlib_predictor" not in st.session_state:
        st.session_state.dlib_predictor = None
    if "video_processing" not in st.session_state:
        st.session_state.video_processing = False
    if "reference_embedding" not in st.session_state:
        st.session_state.reference_embedding = None

def setup_page_config():
    """Set up Streamlit page configuration."""
    st.set_page_config(page_title="Enhanced Face Detection with MTCNN or DLib", layout="wide")

def get_gpu_status():
    """Check GPU availability and return device."""
    gpu_available = torch.cuda.is_available()
    device = "cuda" if gpu_available else "cpu"
    return gpu_available, device