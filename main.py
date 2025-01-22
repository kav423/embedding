import os
import logging
import time
from pathlib import Path
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
import torch
import torchvision.transforms as transforms
from transformers import SwinModel
from PIL import Image
import numpy as np
import shutil

_log = logging.getLogger(__name__)
IMAGE_RESOLUTION_SCALE = 2.0
output_embeddings_dir = Path("output/embeddings/")
output_images_dir = Path("output/images/")

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
    print("Install transformers and make sure that the Swin model is available.")

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

def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path("input/2411.02807v3.pdf")

    output_dir = Path("scratch")

    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    start_time = time.time()

    conv_res = doc_converter.convert(input_doc_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = conv_res.input.file.stem

    # Save page images
    for page_no, page in conv_res.document.pages.items():
        page_no = page.page_no
        page_image_filename = output_images_dir / f"{doc_filename}-{page_no}.png"
        with page_image_filename.open("wb") as fp:
            page.image.pil_image.save(fp, format="PNG")

    # Save images of figures and tables
    table_counter = 0
    picture_counter = 0
    for element, _level in conv_res.document.iterate_items():
        if isinstance(element, TableItem):
            table_counter += 1
            element_image_filename = (
                output_dir / f"{doc_filename}-table-{table_counter}.png"
            )
            with element_image_filename.open("wb") as fp:
                element.get_image(conv_res.document).save(fp, "PNG")

        if isinstance(element, PictureItem):
            picture_counter += 1
            element_image_filename = (
                output_dir / f"{doc_filename}-picture-{picture_counter}.png"
            )
            with element_image_filename.open("wb") as fp:
                element.get_image(conv_res.document).save(fp, "PNG")

    # Save markdown with embedded pictures
    md_filename = output_dir / f"{doc_filename}-with-images.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)

    # Save markdown with externally referenced pictures
    md_filename = output_dir / f"{doc_filename}-with-image-refs.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)

    # Save HTML with externally referenced pictures
    html_filename = output_dir / f"{doc_filename}-with-image-refs.html"
    conv_res.document.save_as_html(html_filename, image_mode=ImageRefMode.REFERENCED)


    for filename in os.listdir(output_images_dir):
        if os.path.isfile(os.path.join(output_images_dir, filename)):
            page_image_filename = os.path.join(output_images_dir, filename)
            embedding = get_image_embedding(page_image_filename)
            if embedding is not None:
                embedding_path = os.path.splitext(page_image_filename)[0] + ".npy"
                np.save(embedding_path, embedding)
                logging.info(f"Embedding saved in '{embedding_path}'")

    end_time = time.time() - start_time

    _log.info(f"Document converted and figures exported in {end_time:.2f} seconds.")


def process_directory_png(output_images_dir, output_embeddings_dir):

    if not os.path.exists(output_embeddings_dir):
        os.makedirs(output_embeddings_dir)

    for filename in os.listdir(output_images_dir):
        file_path = os.path.join(output_images_dir, filename)
        if os.path.isfile(file_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == ".npy":
                try:
                    file_to_move = file_path
                    shutil.move(file_to_move, output_embeddings_dir)
                    print(f"The file '{filename}' now in '{output_embeddings_dir}'")
                except Exception as e:
                    print(f"Movement error '{filename}': {e}")
            else:
                print(f"The file '{filename}' is not .npy, skipped")


if __name__ == "__main__":
    main()
    process_directory_png(output_images_dir, output_embeddings_dir)