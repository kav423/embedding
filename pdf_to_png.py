import logging
from pathlib import Path
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

_log = logging.getLogger(__name__)

def render_pdf_to_png(pdf_path, output_images_dir):
    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_page_images = True

        doc_converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend
                ),
            },
        )

        conv_res = doc_converter.convert(pdf_path)
        doc_filename = conv_res.input.file.stem

        for page_no, page in conv_res.document.pages.items():
            page_image_filename = output_images_dir / f"{doc_filename}-{page_no}.png"
            if page.image.pil_image:
                with page_image_filename.open("wb") as fp:
                    page.image.pil_image.save(fp, format="PNG")
                _log.info(f"Image saved: {page_image_filename}")
            else:
                _log.warning(f"No image found for page {page_no}")

        return True
    except Exception as e:
        _log.error(f"Error rendering PDF to PNG: {e}")
        return False