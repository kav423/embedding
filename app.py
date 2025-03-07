from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import shutil
import logging
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

        # Получаем путь к Markdown-файлу
        md_file = temp_dir / f"{input_doc_path.stem}-with-image-refs.md"
        if not md_file.exists():
            raise HTTPException(status_code=500, detail="Markdown file not found.")

        # Возвращаем Markdown-файл для скачивания
        return FileResponse(
            md_file,
            media_type="text/markdown",
            filename=md_file.name
        )

    except Exception as e:
        _log.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Service is running!"}