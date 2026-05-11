from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import uuid
import os
from pathlib import Path
import re

app = FastAPI(title="Abdulalam Universal Downloader")

# السماح لجميع المواقع
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
    return {
        "status": "ok", 
        "message": "✅ Universal Video Downloader - يدعم جميع المنصات بدون استثناء!",
        "supported_sites": "YouTube, TikTok, Instagram, Snapchat, Twitter, Facebook, Reddit, +1000 موقع آخر"
    }

@app.get("/api/healthz")
def health_check():
    return {"status": "healthy", "service": "abdulalam-downloader"}

@app.post("/api/get-info")
async def get_info(request: VideoRequest):
    """
    جلب معلومات الفيديو من ANY موقع - بدون قيود!
    """
    try:
        # إعدادات yt-dlp الشاملة
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,            'extract_flat': False,
            'ignoreerrors': False,
            'socket_timeout': 30,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                raise HTTPException(status_code=400, detail="لم يتم العثور على معلومات عن الفيديو")
            
            # استخراج جميع الجودات المتاحة
            formats = []
            seen_resolutions = set()
            
            for fmt in info.get('formats', []):
                height = fmt.get('height')
                if height and height not in seen_resolutions:
                    seen_resolutions.add(height)
                    formats.append({
                        'format_id': fmt.get('format_id', ''),
                        'resolution': f"{height}p",
                        'ext': fmt.get('ext', 'mp4').upper(),
                        'filesize': fmt.get('filesize', 0),
                        'format_note': fmt.get('format_note', ''),
                    })
            
            # ترتيب الجودات من الأعلى للأدنى
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')) if x['resolution'].replace('p', '').isdigit() else 0, reverse=True)
            
            return {
                'success': True,
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration_string', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'formats': formats[:15],  # أفضل 15 جودة
                'platform': info.get('extractor', 'unknown'),
                'url': request.url
            }
            
    except Exception as e:
        error_msg = str(e)
        if 'Unsupported URL' in error_msg:
            raise HTTPException(status_code=400, detail=f"❌ الرابط غير مدعوم: {request.url}")
        raise HTTPException(status_code=400, detail=f"خطأ في جلب المعلومات: {error_msg}")

@app.post("/api/download")
async def download_video(request: VideoRequest):    """
    تحميل الفيديو من ANY موقع - بدون قيود!
    """
    try:
        filename = f"video_{uuid.uuid4().hex}"
        output_path = DOWNLOAD_DIR / filename
        
        # إعدادات التحميل
        ydl_opts = {
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 60,
        }
        
        if request.audio_only:
            # تحميل صوت فقط
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # تحميل فيديو
            if request.quality == 'best':
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            else:
                max_height = request.quality.replace('p', '')
                ydl_opts['format'] = f'bestvideo[height<={max_height}]+bestaudio/best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([request.url])
        
        # البحث عن الملف المحمّل
        downloaded_files = list(DOWNLOAD_DIR.glob(f"{filename}*"))
        
        if downloaded_files:
            file_path = downloaded_files[0]
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type='application/octet-stream'
            )
        else:
            raise HTTPException(status_code=500, detail="لم يتم العثور على الملف بعد التحميل")
            
    except Exception as e:        raise HTTPException(status_code=500, detail=f"خطأ في التحميل: {str(e)}")

@app.get("/api/supported-sites")
async def supported_sites():
    """
    إرجاع قائمة بجميع المواقع المدعومة
    """
    return {
        "message": "✅ يدعم جميع المواقع التي يدعمها yt-dlp",
        "popular_sites": [
            "YouTube", "TikTok", "Instagram", "Snapchat", "Twitter/X",
            "Facebook", "Reddit", "Pinterest", "LinkedIn", "Vimeo",
            "Dailymotion", "Twitch", "SoundCloud", "Spotify", "Apple Music",
            "و +1000 موقع آخر!"
        ],
        "total_sites": "1000+",
        "no_restrictions": True
    }

# تنظيف الملفات القديمة
import shutil
import time

def cleanup_old_files():
    """حذف الملفات الأقدم من ساعة"""
    if DOWNLOAD_DIR.exists():
        now = time.time()
        for file_path in DOWNLOAD_DIR.iterdir():
            if file_path.is_file() and (now - file_path.stat().st_mtime) > 3600:
                try:
                    file_path.unlink()
                except:
                    pass

@app.on_event("startup")
async def startup_event():
    cleanup_old_files()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
