import os
import logging
import subprocess
import time
import pypandoc
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.pipeline.simple_pipeline import SimplePipeline
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
import torch
import torchvision.transforms as transforms
from transformers import SwinModel
from PIL import Image
import numpy as np
import shutil
from pathlib import Path
from bs4 import BeautifulSoup


_log = logging.getLogger(__name__)
IMAGE_RESOLUTION_SCALE = 2.0
output_embeddings_dir = Path("output/embeddings/")
output_images_dir = Path("output/images/")
WKHTMLTOPDF_PATH = "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"

def convert_markdown_to_html(markdown_file, html_file, css_file=None):

    if not os.path.exists(markdown_file):
        print(f"Error: Markdown file not found: {markdown_file}")
        return False

    extra_args = ['-s']
    if css_file:
        if not os.path.exists(css_file):
            print(f"Error: CSS file not found: {css_file}")
            return False
        extra_args.extend(['--css', css_file])

    try:
        # Используем pypandoc.convert_file для создания HTML файла
        pypandoc.convert_file(
            markdown_file,
            'html',
            outputfile=html_file,
            extra_args=extra_args
        )

        # Читаем HTML контент из созданного файла
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        if save_html_to_file(html_content, html_file):
            print(f"Successfully converted and saved {markdown_file} to {html_file}")
            return True
        else:
            return False


    except Exception as e:
        print(f"Error converting {markdown_file} to {html_file}: {e}")
        return False


def save_html_to_file(html_content, html_file):
    """
    Сохраняет HTML контент в файл.
    """
    try:
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Successfully saved HTML to {html_file}")
        return True
    except Exception as e:
        print(f"Error saving HTML to {html_file}: {e}")
        return False

def generate_pdf(html_file_to_pdf, output_file_pdf, disable_javascript=False):
    try:
        command = [WKHTMLTOPDF_PATH, '--enable-local-file-access', html_file_to_pdf, output_file_pdf]

        if disable_javascript:
            command.append("--disable-javascript")

        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        print(f"PDF successfully created: {output_file_pdf}")
    except subprocess.CalledProcessError as e:
        print(f"Error during execution wkhtmltopdf: {e}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
    except FileNotFoundError:
        print(f"error: wkhtmltopdf not found at path {WKHTMLTOPDF_PATH}")

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


def replace_char_in_links_bs4(html_file_path: Path, old_char: str, new_char: str, output_file_path: Path):

    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    for img_tag in soup.find_all('img'):
        for attribute in ['src', 'srcset']:
            if attribute in img_tag.attrs:
                attr_value = img_tag[attribute]
                if old_char in attr_value:
                    img_tag[attribute] = attr_value.replace(old_char, new_char)

    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path("input/Confirmation PAR Completed Scrubbed.pdf")

    output_dir = Path("scratch")

    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = (
        DocumentConverter(  # all of the below is optional, has internal defaults.
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
            ],  # whitelist formats, non-matching files are ignored.
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,  # pipeline options go here.
                    backend=PyPdfiumDocumentBackend  # optional: pick an alternative backend
                ),
                InputFormat.DOCX: WordFormatOption(
                    pipeline_cls=SimplePipeline  # default for office formats and HTML
                ),
            },
        )
    )

    start_time = time.time()

    conv_res = doc_converter.convert(input_doc_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = conv_res.input.file.stem

    # Save images of figures and tables
    table_counter = 0
    picture_counter = 0

    for element, _level in conv_res.document.iterate_items():
        _log.debug(f"Element type: {type(element)}")  # Логируем тип element
        if isinstance(element, TableItem):
            table_counter += 1
            element_image_filename = (
                    output_dir / f"{doc_filename}-table-{table_counter}.png"
            )
            image = element.get_image(conv_res.document)
            if image:
                try:
                    with element_image_filename.open("wb") as fp:
                        image.save(fp, "PNG")
                except Exception as e:
                    print(f"Error saving image for table {table_counter}: {e}")
            else:
                print(f"Warning: No image found for table {table_counter}")

        if isinstance(element, PictureItem):
            picture_counter += 1
            element_image_filename = (
                    output_dir / f"{doc_filename}-picture-{picture_counter}.png"
            )
            image = element.get_image(conv_res.document)
            if image:
                try:
                    with element_image_filename.open("wb") as fp:
                        image.save(fp, "PNG")
                except Exception as e:
                    print(f"Error saving image for picture {picture_counter}: {e}")
            else:
                print(f"Warning: No image found for picture {picture_counter}")
    # Save markdown with embedded pictures
    md_filename = output_dir / f"{doc_filename}-with-images.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)

    # Save markdown with externally referenced pictures
    md_filename = output_dir / f"{doc_filename}-with-image-refs.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)

    markdown_file = f"scratch/{doc_filename}-with-image-refs.md"
    html_file = str(output_dir / f"{doc_filename}-with-image-refs.html")
    css_file = None

    # Convert Markdown to HTML
    if convert_markdown_to_html(markdown_file, html_file, css_file):
        print("Conversion and saving successful!")
    else:
        print("Conversion and saving failed!")
        return  # Exit if conversion fails

    htmlFile = Path(f"scratch/{doc_filename}-with-image-refs.html")
    outputFile = Path(f"scratch/{doc_filename}-with-image-refs_new.html")
    old_char = "%5C"
    new_char = "/"

    replace_char_in_links_bs4(htmlFile, old_char, new_char, outputFile)

    html_file_to_pdf = "scratch/Confirmation PAR Completed Scrubbed-with-image-refs_new.html"
    output_file_pdf = ("scratch/output.pdf")

    generate_pdf(
        html_file_to_pdf,
        output_file_pdf,
        disable_javascript=False,
    )

    conv_res_new_pdf = doc_converter.convert(output_file_pdf)
    doc_filename_new_pdf = conv_res.input.file.stem

    for page_no, page in conv_res_new_pdf.document.pages.items():
        page_no = page.page_no
        page_image_filename = output_images_dir / f"{doc_filename_new_pdf}-{page_no}.png"
        with page_image_filename.open("wb") as fp:
            page.image.pil_image.save(fp, format="PNG")

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
