            from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import uuid
import os
from pathlib import Path
import logging

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Abdulalam Universal Downloader",
    description="يدعم جميع المنصات: YouTube, TikTok, Douyin, Snapchat, Instagram, Twitter, +1800 موقع",
    version="3.0-Ultimate"
)

# السماح بكل شيء
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

# إعدادات yt-dlp القوية جداً
def get_ydl_opts(download=False, audio_only=False, quality="best"):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'socket_timeout': 60,
        'retries': 3,
        'fragment_retries': 3,
        # محاكاة متصفح حقيقي
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        # دعم جميع الصيغ        'format_sort': ['res', 'fps', 'hdr', 'lang', 'proto'],
    }
    
    if download:
        filename = f"video_{uuid.uuid4().hex}"
        opts['outtmpl'] = str(DOWNLOAD_DIR / filename) + '.%(ext)s'
        
        if audio_only:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        else:
            if quality == 'best':
                opts['format'] = 'bestvideo+bestaudio/best'
            else:
                max_height = quality.replace('p', '')
                opts['format'] = f'bestvideo[height<={max_height}]+bestaudio/best'
    
    return opts

@app.get("/")
def root():
    return {
        "status": "✅ Online",
        "service": "Abdulalam Universal Downloader",
        "version": "3.0",
        "supported_platforms": "YouTube, TikTok (Global + Douyin), Snapchat, Instagram, Twitter/X, Facebook, Reddit, Pinterest, LinkedIn, Twitch, +1800 sites",
        "endpoints": {
            "get_info": "POST /api/get-info",
            "download": "POST /api/download",
            "health": "GET /api/healthz"
        }
    }

@app.get("/api/healthz")
def health_check():
    return {"status": "healthy", "service": "abdulalam-downloader"}

@app.post("/api/get-info")
async def get_info(request: VideoRequest):
    """
    جلب معلومات الفيديو من ANY موقع - 1800+ منصة
    """
    try:
        logger.info(f"Fetching info for: {request.url}")
        
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                raise HTTPException(status_code=404, detail="لم يتم العثور على الفيديو")
            
            # استخراج الجودات
            formats = []
            seen = set()
            
            for f in info.get('formats', []):
                height = f.get('height')
                if height and height not in seen:
                    seen.add(height)
                    formats.append({
                        'format_id': f.get('format_id', ''),
                        'resolution': f"{height}p",
                        'ext': f.get('ext', 'mp4').upper(),
                        'filesize': f.get('filesize', 0),
                        'fps': f.get('fps', 0),
                    })
            
            # ترتيب من الأعلى للأدنى
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')) if x['resolution'].replace('p', '').isdigit() else 0, reverse=True)
            
            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration_string', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'platform': info.get('extractor', 'unknown'),
                'formats': formats[:15],
                'url': request.url,
                'description': info.get('description', '')[:200] if info.get('description') else ''
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error fetching info: {error_msg}")
        raise HTTPException(status_code=400, detail=f"❌ {error_msg}")

@app.post("/api/download")
async def download_video(request: VideoRequest):
    """
    تحميل الفيديو من ANY موقع
    """
    try:
        logger.info(f"Downloading: {request.url} | Quality: {request.quality} | Audio: {request.audio_only}")
        
        opts = get_ydl_opts(download=True, audio_only=request.audio_only, quality=request.quality)        
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([request.url])
        
        # البحث عن الملف
        files = list(DOWNLOAD_DIR.glob(f"video_{uuid.uuid4().hex[:8]}*"))
        if not files:
            # محاولة أخرى للبحث
            files = list(DOWNLOAD_DIR.glob("video_*"))
        
        if files:
            file_path = files[0]
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type='application/octet-stream'
            )
        
        raise HTTPException(status_code=500, detail="لم يتم العثور على الملف بعد التحميل")
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"❌ خطأ في التحميل: {str(e)}")

@app.get("/api/supported-sites")
async def supported_sites():
    """
    قائمة بجميع المواقع المدعومة
    """
    return {
        "message": "✅ يدعم 1800+ موقع ومنصة",
        "major_platforms": [
            "YouTube (بما في ذلك Shorts)",
            "TikTok (العالمي + Douyin الصيني)",
            "Snapchat",
            "Instagram (Reels, Stories, Posts, IGTV)",
            "Twitter/X",
            "Facebook",
            "Reddit",
            "Pinterest",
            "LinkedIn",
            "Twitch",
            "Vimeo",
            "Dailymotion",
            "SoundCloud",
            "Spotify",
            "Apple Music",
            "Deezer"
        ],
        "ai_platforms": [            "Runway ML",
            "Midjourney (فيديوهات)",
            "Stable Diffusion videos",
            "Pika Labs",
            "Kaiber"
        ],
        "total_sites": "1800+",
        "documentation": "https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md"
    }

# تنظيف تلقائي
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
                    logger.info(f"Deleted old file: {file_path}")
                except:
                    pass

@app.on_event("startup")
async def startup_event():
    cleanup_old_files()
    logger.info("✅ Server started - Supports 1800+ platforms")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
