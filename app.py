from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import shutil
import logging
import pyzipper  # Используем pyzipper вместо zipfile
from main import main  # Импортируем основную логику

# Настройка логгера
_log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Создание FastAPI приложения
app = FastAPI()

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

def create_zip_from_directory(directory: Path, zip_path: Path):
    """
    Создает ZIP-архив с поддержкой ZIP64 с помощью pyzipper.
    """
    try:
        allowed_extensions = {".md", ".html", ".pdf", ".png", ".npy"}
        with pyzipper.AESZipFile(
            zip_path,
            'w',
            compression=pyzipper.ZIP_DEFLATED,
            allowZip64=True  # Включаем поддержку ZIP64
        ) as zipf:
            for file in directory.rglob("*"):
                if file.is_file() and file.suffix.lower() in allowed_extensions:
                    arcname = file.relative_to(directory)
                    zipf.write(file, arcname)
                    _log.info(f"Added {file} to ZIP archive.")
        _log.info(f"ZIP archive created: {zip_path}")
    except Exception as e:
        _log.error(f"Error creating ZIP archive: {e}")
        raise

@app.post("/process-document/")
async def process_document(file: UploadFile = File(...)):
    try:
        # Создаем временную директорию для обработки
        temp_dir = Path("temp")

        # Очищаем временные файлы перед началом обработки
        cleanup_temp_files(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем загруженный файл
        input_doc_path = temp_dir / file.filename
        with open(input_doc_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Вызываем основную логику обработки
        result = main(input_doc_path, temp_dir)

        # Создаем ZIP-архив с временными файлами
        zip_path = temp_dir / "output.zip"
        create_zip_from_directory(temp_dir, zip_path)

        # Проверяем, что ZIP-архив создан
        if not zip_path.exists():
            raise HTTPException(status_code=500, detail="Failed to create ZIP archive.")

        # Возвращаем ZIP-архив для скачивания
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_path.name
        )

    except Exception as e:
        _log.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Service is running!"}