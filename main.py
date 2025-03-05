import logging
from pathlib import Path
from document_to_md import convert_document_to_md
from md_to_html import convert_markdown_to_html
from html_to_pdf import generate_pdf
from pdf_to_png import render_pdf_to_png
from png_to_embeddings import process_images_for_embeddings
from utils.file_processing import process_directory_png

_log = logging.getLogger(__name__)

# Константы
IMAGE_RESOLUTION_SCALE = 2.0
output_embeddings_dir = Path("output/embeddings/")
output_images_dir = Path("output/images/")
WKHTMLTOPDF_PATH = "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"

def main():
    logging.basicConfig(level=logging.INFO)
    input_doc_path = Path("input/ImageSource indelivered Issues - 2025-02-26 (1).xlsx")
    output_dir = Path("scratch")

    # 1. Конвертация документа в Markdown
    md_file = convert_document_to_md(input_doc_path, output_dir, IMAGE_RESOLUTION_SCALE)
    if not md_file:
        _log.error("Failed to convert document to Markdown.")
        return

    # 2. Конвертация Markdown в HTML
    html_file = output_dir / f"{input_doc_path.stem}-with-image-refs.html"
    if not convert_markdown_to_html(md_file, html_file):
        _log.error("Failed to convert Markdown to HTML.")
        return

    # 3. Конвертация HTML в PDF
    pdf_file = output_dir / "output.pdf"
    if not generate_pdf(html_file, pdf_file, WKHTMLTOPDF_PATH):
        _log.error("Failed to convert HTML to PDF.")
        return

    # 4. Рендеринг PDF в PNG
    if not render_pdf_to_png(pdf_file, output_images_dir):
        _log.error("Failed to render PDF to PNG.")
        return

    # 5. Получение эмбеддингов из PNG
    process_images_for_embeddings(output_images_dir, output_embeddings_dir)

    # 6. Перемещение .npy файлов
    process_directory_png(output_images_dir, output_embeddings_dir)

if __name__ == "__main__":
    main()