from fastapi import FastAPI, File, UploadFile, HTTPException, Response, Request, Query
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import shutil
import logging
import uuid
import pyzipper
from document_to_md import convert_document_to_md
from md_to_html import convert_markdown_to_html
from html_to_pdf import generate_pdf
from pdf_to_png import render_pdf_to_png
from png_to_embeddings import process_images_for_embeddings
from utils.file_processing import process_directory_png

# Настройка логгера
_log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Создание FastAPI приложения
app = FastAPI()

# Словарь для хранения сессий
sessions = {}

def cleanup_temp_files(temp_dir: Path):
    """
    Удаляет временную директорию и все её содержимое.
    """
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            _log.info(f"Temporary files in {temp_dir} deleted.")
    except Exception as e:
        _log.error(f"Error deleting temporary files: {e}")

@app.post("/upload-document/")
async def upload_document(
    file: UploadFile = File(...),
    response: Response = None,
    include_images: bool = Query(default=True, description="Include images in Markdown")
):
    """
    Загружает документ и выполняет все этапы преобразования.
    """
    try:
        # Генерируем уникальный идентификатор сессии
        session_id = str(uuid.uuid4())

        # Создаем временную директорию для сессии
        temp_dir = Path("temp") / session_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем загруженный файл
        input_doc_path = temp_dir / file.filename
        with open(input_doc_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Конвертация документа в Markdown
        _log.info("Starting document to Markdown conversion...")
        md_file = convert_document_to_md(input_doc_path, temp_dir, image_resolution_scale=2.0, include_images=include_images)
        if not md_file:
            raise Exception("Failed to convert document to Markdown.")
        _log.info(f"Markdown file created: {md_file}")

        # 2. Конвертация Markdown в HTML
        _log.info("Starting Markdown to HTML conversion...")
        html_file = temp_dir / f"{input_doc_path.stem}-with-image-refs.html"
        if not convert_markdown_to_html(md_file, html_file):
            raise Exception("Failed to convert Markdown to HTML.")
        _log.info(f"HTML file created: {html_file}")

        # 3. Конвертация HTML в PDF
        _log.info("Starting HTML to PDF conversion...")
        pdf_file = temp_dir / "output.pdf"
        if not generate_pdf(html_file, pdf_file, wkhtmltopdf_path="D:\\wkhtmltox-0.12.6-1.mxe-cross-win64\\wkhtmltox\\bin\\wkhtmltopdf.exe"):
            raise Exception("Failed to convert HTML to PDF.")
        _log.info(f"PDF file created: {pdf_file}")

        # 4. Рендеринг PDF в PNG
        _log.info("Starting PDF to PNG rendering...")
        output_images_dir = temp_dir / "images"
        output_images_dir.mkdir(parents=True, exist_ok=True)
        if not render_pdf_to_png(pdf_file, output_images_dir):
            raise Exception("Failed to render PDF to PNG.")
        _log.info(f"PNG images saved to: {output_images_dir}")

        # 5. Получение эмбеддингов из PNG
        _log.info("Starting PNG to embeddings conversion...")
        output_embeddings_dir = temp_dir / "embeddings"
        output_embeddings_dir.mkdir(parents=True, exist_ok=True)
        process_images_for_embeddings(output_images_dir, output_embeddings_dir)
        _log.info(f"Embeddings saved to: {output_embeddings_dir}")

        # 6. Перемещение .npy файлов
        _log.info("Moving .npy files...")
        process_directory_png(output_images_dir, output_embeddings_dir)
        _log.info(f".npy files moved to: {output_embeddings_dir}")

        # Сохраняем результаты в сессии
        sessions[session_id] = {
            "md_file": md_file,
            "html_file": html_file,
            "pdf_file": pdf_file,
            "images_dir": output_images_dir,
            "embeddings_dir": output_embeddings_dir,
            "include_images": include_images
        }

        # Устанавливаем session_id в куки
        response.set_cookie(key="session_id", value=session_id)
        _log.info(f"Session ID set in cookies: {session_id}")

        return {"status": "success", "message": "Document processed.", "session_id": session_id}
    except Exception as e:
        _log.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-md/")
async def get_md(request: Request):
    """
    Возвращает Markdown-файл.
    """
    try:
        # Извлекаем session_id из куки
        session_id = request.cookies.get("session_id")
        _log.info(f"Session ID from cookies: {session_id}")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID not found in cookies.")

        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        md_file = session.get("md_file")
        if not md_file:
            raise HTTPException(status_code=404, detail="Markdown file not found.")

        return FileResponse(md_file, media_type="text/markdown", filename=md_file.name)
    except Exception as e:
        _log.error(f"Error retrieving Markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-html/")
async def get_html(request: Request):
    """
    Возвращает HTML-файл.
    """
    try:
        # Извлекаем session_id из куки
        session_id = request.cookies.get("session_id")
        _log.info(f"Session ID from cookies: {session_id}")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID not found in cookies.")

        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        html_file = session.get("html_file")
        if not html_file:
            raise HTTPException(status_code=404, detail="HTML file not found.")

        return FileResponse(html_file, media_type="text/html", filename=html_file.name)
    except Exception as e:
        _log.error(f"Error retrieving HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-pdf/")
async def get_pdf(request: Request):
    """
    Возвращает PDF-файл.
    """
    try:
        # Извлекаем session_id из куки
        session_id = request.cookies.get("session_id")
        _log.info(f"Session ID from cookies: {session_id}")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID not found in cookies.")

        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        pdf_file = session.get("pdf_file")
        if not pdf_file:
            raise HTTPException(status_code=404, detail="PDF file not found.")

        return FileResponse(pdf_file, media_type="application/pdf", filename=pdf_file.name)
    except Exception as e:
        _log.error(f"Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-png/")
async def get_png(request: Request):
    """
    Возвращает ZIP-архив с PNG-изображениями.
    """
    try:
        # Извлекаем session_id из куки
        session_id = request.cookies.get("session_id")
        _log.info(f"Session ID from cookies: {session_id}")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID not found in cookies.")

        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        images_dir = session.get("images_dir")
        if not images_dir:
            raise HTTPException(status_code=404, detail="PNG images not found.")

        # Создаем ZIP-архив с PNG-изображениями
        zip_path = images_dir.parent / "images.zip"
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, allowZip64=True) as zipf:
            for file in images_dir.glob("*.png"):
                zipf.write(file, file.name)

        return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)
    except Exception as e:
        _log.error(f"Error retrieving PNG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-embeddings/")
async def get_embeddings(request: Request):
    """
    Возвращает ZIP-архив с эмбеддингами.
    """
    try:
        # Извлекаем session_id из куки
        session_id = request.cookies.get("session_id")
        _log.info(f"Session ID from cookies: {session_id}")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID not found in cookies.")

        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        embeddings_dir = session.get("embeddings_dir")
        if not embeddings_dir:
            raise HTTPException(status_code=404, detail="Embeddings not found.")

        # Создаем ZIP-архив с эмбеддингами
        zip_path = embeddings_dir.parent / "embeddings.zip"
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, allowZip64=True) as zipf:
            for file in embeddings_dir.glob("*.npy"):
                zipf.write(file, file.name)

        return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)
    except Exception as e:
        _log.error(f"Error retrieving embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Service is running!"}