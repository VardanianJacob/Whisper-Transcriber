from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from api.whisper import transcribe_audio
from utils.save import save_transcript_to_file
import os

app = FastAPI(title="Whisper Transcription API")

@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
    <html>
        <head><title>Upload Audio</title></head>
        <body>
            <h1>Upload an audio file</h1>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept="audio/*">
                <input type="submit">
            </form>
        </body>
    </html>
    '''

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        result = transcribe_audio(temp_path)
        save_transcript_to_file(result, temp_path, "verbose_json")
        os.remove(temp_path)
        return {"message": "✅ Transcription complete", "filename": file.filename}
    except Exception as e:
        return {"error": str(e)}

