import logging
from pathlib import Path
from document_to_md import convert_document_to_md
from md_to_html import convert_markdown_to_html
from html_to_pdf import generate_pdf, replace_char_in_links_bs4
from pdf_to_png import render_pdf_to_png
from png_to_embeddings import process_images_for_embeddings
from utils.file_processing import process_directory_png

_log = logging.getLogger(__name__)

# Константы
IMAGE_RESOLUTION_SCALE = 2.0
output_embeddings_dir = Path("output/embeddings/")
output_images_dir = Path("output/images/")
WKHTMLTOPDF_PATH = "C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"

def main(input_doc_path: Path):
    try:
        # Результаты обработки
        result = {
            "status": "success",
            "message": "Document processing started.",
            "steps": [],
            "download_link": None
        }

        # 1. Конвертация документа в Markdown
        md_file = convert_document_to_md(input_doc_path, Path("temp"), IMAGE_RESOLUTION_SCALE)
        if not md_file:
            raise Exception("Failed to convert document to Markdown.")
        result["steps"].append({"step": "Convert to Markdown", "status": "success", "message": f"Markdown saved to {md_file}"})

        # 2. Конвертация Markdown в HTML
        html_file = Path("temp") / f"{input_doc_path.stem}-with-image-refs.html"
        if not convert_markdown_to_html(md_file, html_file):
            raise Exception("Failed to convert Markdown to HTML.")
        result["steps"].append({"step": "Convert to HTML", "status": "success", "message": f"HTML saved to {html_file}"})

        # 3. Замена символов в ссылках HTML
        html_file_new = Path("temp") / f"{input_doc_path.stem}-with-image-refs_new.html"
        if not replace_char_in_links_bs4(html_file, "%5C", "/", html_file_new):
            raise Exception("Failed to replace characters in HTML links.")
        result["steps"].append({"step": "Fix HTML links", "status": "success", "message": f"Fixed links in {html_file_new}"})

        # 4. Конвертация HTML в PDF
        pdf_file = Path("temp") / "output.pdf"
        if not generate_pdf(html_file_new, pdf_file, WKHTMLTOPDF_PATH):
            raise Exception("Failed to convert HTML to PDF.")
        result["steps"].append({"step": "Convert to PDF", "status": "success", "message": f"PDF saved to {pdf_file}"})

        # 5. Рендеринг PDF в PNG
        if not render_pdf_to_png(pdf_file, output_images_dir):
            raise Exception("Failed to render PDF to PNG.")
        result["steps"].append({"step": "Render PDF to PNG", "status": "success", "message": f"PNG images saved to {output_images_dir}"})

        # 6. Получение эмбеддингов из PNG
        process_images_for_embeddings(output_images_dir, output_embeddings_dir)
        result["steps"].append({"step": "Generate embeddings", "status": "success", "message": f"Embeddings saved to {output_embeddings_dir}"})

        # 7. Перемещение .npy файлов
        process_directory_png(output_images_dir, output_embeddings_dir)
        result["steps"].append({"step": "Move .npy files", "status": "success", "message": f".npy files moved to {output_embeddings_dir}"})

        # Ссылка на скачивание PDF
        result["download_link"] = f"/download/{pdf_file.name}"

        return result

    except Exception as e:
        _log.error(f"Error processing document: {e}")
        raise