import os
import logging
import time
from pathlib import Path
from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.pipeline.simple_pipeline import SimplePipeline
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption, \
    ExcelFormatOption, PowerpointFormatOption, HTMLFormatOption, ImageFormatOption

_log = logging.getLogger(__name__)

def convert_document_to_md(input_doc_path, output_dir, image_resolution_scale):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = image_resolution_scale
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.PPTX,
            InputFormat.XLSX,
            InputFormat.IMAGE,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline
            ),
            InputFormat.XLSX: ExcelFormatOption(
                pipeline_cls=SimplePipeline,
            ),
            InputFormat.PPTX: PowerpointFormatOption(
                pipeline_cls=SimplePipeline,
                backend=MsPowerpointDocumentBackend
            ),
            InputFormat.HTML: HTMLFormatOption(
                pipeline_cls=SimplePipeline,
            ),
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
            ),
        },
    )

    start_time = time.time()
    conv_res = doc_converter.convert(input_doc_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = conv_res.input.file.stem

    table_counter = 0
    picture_counter = 0

    for element, _level in conv_res.document.iterate_items():
        _log.debug(f"Element type: {type(element)}")
        if isinstance(element, TableItem):
            table_counter += 1
            element_image_filename = output_dir / f"{doc_filename}-table-{table_counter}.png"
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
            element_image_filename = output_dir / f"{doc_filename}-picture-{picture_counter}.png"
            image = element.get_image(conv_res.document)
            if image:
                try:
                    with element_image_filename.open("wb") as fp:
                        image.save(fp, "PNG")
                except Exception as e:
                    print(f"Error saving image for picture {picture_counter}: {e}")
            else:
                print(f"Warning: No image found for picture {picture_counter}")

    md_filename = output_dir / f"{doc_filename}-with-images.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)

    md_filename = output_dir / f"{doc_filename}-with-image-refs.md"
    conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)

    end_time = time.time() - start_time
    _log.info(f"Document converted and figures exported in {end_time:.2f} seconds.")
    return md_filename