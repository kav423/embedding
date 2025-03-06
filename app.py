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

@app.post("/process-document/")
async def process_document(file: UploadFile = File(...)):
    try:
        # Создаем временную директорию для обработки
        temp_dir = Path("temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем загруженный файл
        input_doc_path = temp_dir / file.filename
        with open(input_doc_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Вызываем основную логику обработки
        result = main(input_doc_path)

        # Возвращаем результат
        return JSONResponse(content=result)

    except Exception as e:
        _log.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path("temp") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

@app.get("/")
async def root():
    return {"message": "Service is running!"}