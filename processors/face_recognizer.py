import cv2
import numpy as np
import streamlit as st
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from config.settings import get_gpu_status
import logging

logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self, similarity_threshold=0.6):
        _, device = get_gpu_status()
        try:
            self.mtcnn = MTCNN(
                keep_all=False,
                device=device,
                min_face_size=20,
                thresholds=[0.4, 0.5, 0.5],
                factor=0.709
            )
            self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)
            self.similarity_threshold = similarity_threshold
            self.reference_embedding = None
            self.match_color_rgb = (0, 255, 0)  # Green for match
            self.no_match_color_rgb = (255, 0, 0)  # Red for no match
            st.info("InceptionResnetV1 initialized successfully.")
            logger.info("FaceRecognizer initialized with MTCNN and InceptionResnetV1.")
        except Exception as e:
            st.error(f"❌ Failed to initialize FaceRecognizer: {e}")
            logger.error(f"FaceRecognizer Initialization Error: {e}")
            raise

    def preprocess_image(self, image):
        """Normalize and resize the input image for consistent processing."""
        try:
            # Resize to ensure consistent input size
            max_size = 512
            h, w = image.shape[:2]
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            # Apply CLAHE for better contrast
            img_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_lab[:, :, 0] = clahe.apply(img_lab[:, :, 0])
            img_normalized = cv2.cvtColor(img_lab, cv2.COLOR_LAB2BGR)
            return img_normalized
        except Exception as e:
            logger.error(f"Image Preprocessing Error: {e}")
            return image

    def set_reference_embedding(self, reference_image):
        """Compute and store the reference embedding from an image, and save the cropped face."""
        try:
            # Preprocess the image
            reference_bgr = self.preprocess_image(reference_image)
            reference_rgb = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2RGB)
            logger.info(f"Processing reference image: size={reference_rgb.shape}")
            # Detect and crop face
            reference_tensor = self.mtcnn(reference_rgb)
            if reference_tensor is not None:
                logger.info(f"Reference face tensor shape: {reference_tensor.shape}")
                # Convert tensor to NumPy for display and store in session state
                try:
                    face_np = reference_tensor.cpu().permute(1, 2, 0).numpy()
                    face_np = (face_np * 255).astype(np.uint8)  # Assume [0, 1] range
                    face_np = cv2.cvtColor(face_np, cv2.COLOR_RGB2BGR)
                    st.session_state.cropped_faces = [{
                        'image': face_np,
                        'caption': "Detected Face from Reference Image"
                    }]
                    logger.info("Cropped face from reference image stored in session state")
                except Exception as e:
                    logger.error(f"Error converting reference face tensor: {e}")
                    st.session_state.cropped_faces = []
                # Compute embedding
                reference_tensor = reference_tensor.to(self.resnet.device)
                with torch.no_grad():
                    self.reference_embedding = self.resnet(reference_tensor.unsqueeze(0)).squeeze().cpu().numpy()
                    norm = np.linalg.norm(self.reference_embedding)
                    if norm == 0:
                        st.error("❌ Invalid embedding generated (zero norm).")
                        logger.error("Invalid embedding: zero norm")
                        self.reference_embedding = None
                        return
                    self.reference_embedding /= norm
                st.info(f"Reference embedding computed: shape={self.reference_embedding.shape}, norm=1.00")
                logger.info(f"Reference embedding computed: shape={self.reference_embedding.shape}")
            else:
                st.error("❌ Could not detect a face in the reference image.")
                logger.error("No face detected in reference image")
                self.reference_embedding = None
                st.session_state.cropped_faces = []
        except Exception as e:
            st.error(f"❌ Error processing reference image: {e}")
            logger.error(f"Reference Image Processing Error: {e}")
            self.reference_embedding = None
            st.session_state.cropped_faces = []

    def recognize_face(self, face_tensor):
        """Compare a face tensor to the reference embedding."""
        if self.reference_embedding is None:
            logger.debug("No reference embedding for recognition")
            return False, 0.0
        try:
            if face_tensor is None or face_tensor.shape != (3, 160, 160):
                logger.error(f"Invalid face tensor shape: {face_tensor.shape if face_tensor is not None else 'None'}")
                return False, 0.0
            with torch.no_grad():
                embedding = self.resnet(face_tensor.unsqueeze(0)).squeeze().cpu().numpy()
                norm = np.linalg.norm(embedding)
                if norm == 0:
                    logger.error("Invalid embedding: zero norm")
                    return False, 0.0
                embedding /= norm
                similarity = np.dot(embedding, self.reference_embedding)
            logger.debug(f"Similarity computed: {similarity:.2f}")
            return similarity > self.similarity_threshold, similarity
        except Exception as e:
            logger.error(f"Face Recognition Error: {e}")
            return False, 0.0