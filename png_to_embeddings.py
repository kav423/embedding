import torch
import torchvision.transforms as transforms
from transformers import SwinModel
from PIL import Image
import numpy as np
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

try:
    swin_model = SwinModel.from_pretrained("microsoft/swin-base-patch4-window7-224")
    swin_model.eval()
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
except Exception as e:
    logging.error("Error loading the Swin model: " + str(e))

def get_image_embedding(page_image_filename):
    try:
        img = Image.open(page_image_filename).convert('RGB')
        img_tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            embedding = swin_model(img_tensor).last_hidden_state
        return embedding.cpu().numpy()
    except Exception as e:
        logging.error(f"Error when receiving embedding: {e}")
        return None

def process_images_for_embeddings(output_images_dir, output_embeddings_dir):
    output_embeddings_dir.mkdir(parents=True, exist_ok=True)
    for filename in output_images_dir.glob("*.png"):
        embedding = get_image_embedding(filename)
        if embedding is not None:
            embedding_path = output_embeddings_dir / f"{filename.stem}.npy"
            np.save(embedding_path, embedding)
            _log.info(f"Embedding saved: {embedding_path}")