from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import uuid
import os
from pathlib import Path

app = FastAPI()

# السماح لجميع المواقع بالدخول
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    quality: str = "best"
    audio_only: bool = False

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
def root():
    return {"status": "ok", "message": "Server is running successfully"}

@app.post("/api/get-info")
async def get_info(request: VideoRequest):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(request.url, download=False)
            formats = []
            seen = set()
            for f in info.get('formats', []):
                h = f.get('height')
                if h and h not in seen:
                    seen.add(h)
                    formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f"{h}p",
                        'ext': f.get('ext', 'mp4').upper()
                    })
            return {'success': True, 'title': info.get('title'), 'formats': formats[:10]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
async def download(request: VideoRequest):
    try:
        filename = f"video_{uuid.uuid4().hex}"
        output = DOWNLOAD_DIR / filename
        
        ydl_opts = {'outtmpl': str(output), 'quiet': True}
        
        if request.audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio/best' if request.quality == 'best' else f'bestvideo[height<={request.quality.replace("p","")}]+bestaudio/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([request.url])

        files = list(DOWNLOAD_DIR.glob(f"{filename}*"))
        if files:
            return FileResponse(path=files[0], filename=files[0].name)
        return JSONResponse(content={"error": "File not found"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
