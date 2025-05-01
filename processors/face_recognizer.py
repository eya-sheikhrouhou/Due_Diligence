import cv2
import numpy as np
import streamlit as st
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from config.settings import DEVICE, SIMILARITY_THRESHOLD

class FaceRecognizer:
    def __init__(self):
        self.mtcnn = MTCNN(keep_all=False, device=DEVICE)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(DEVICE)
        self.similarity_threshold = SIMILARITY_THRESHOLD
        self.reference_embedding = None
        st.info("InceptionResnetV1 initialized successfully.")

    def set_reference_embedding(self, reference_image):
        """Compute and store the reference embedding from an image."""
        reference_rgb = cv2.cvtColor(reference_image, cv2.COLOR_BGR2RGB)
        reference_tensor = self.mtcnn(reference_rgb)
        if reference_tensor is not None:
            reference_tensor = reference_tensor.to(DEVICE)
            with torch.no_grad():
                self.reference_embedding = self.resnet(reference_tensor.unsqueeze(0)).squeeze().cpu().numpy()
                norm = np.linalg.norm(self.reference_embedding)
                self.reference_embedding /= norm
            st.info(f"Reference embedding computed: shape={self.reference_embedding.shape}, norm=1.00")
        else:
            st.error("Could not detect a face in the reference image.")

    def recognize_face(self, face_tensor):
        """Compare a face tensor to the reference embedding."""
        if self.reference_embedding is None:
            return False, 0.0
        with torch.no_grad():
            embedding = self.resnet(face_tensor.unsqueeze(0)).squeeze().cpu().numpy()
            norm = np.linalg.norm(embedding)
            if norm == 0:
                return False, 0.0
            embedding /= norm
            similarity = np.dot(embedding, self.reference_embedding)
        return similarity > self.similarity_threshold, similarity