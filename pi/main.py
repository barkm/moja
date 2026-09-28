from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic_settings import BaseSettings

from hardware import detect_hardware
from stream import Stream
from sensor import read_sensor_data
from system import read_system_info


class Settings(BaseSettings):
    name: str = "birdhouse"
    test_stream: bool = False
    test_sensor: bool = False


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stream = Stream(settings.test_stream)
    app.state.hardware = detect_hardware(settings.test_stream, settings.test_sensor)
    yield
    app.state.stream.stop()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def root():
    return {"status": "ok", "name": settings.name}


@app.get("/hls/{filename:path}")
async def serve_hls_files(request: Request, filename: str):
    if not _is_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    stream: Stream = request.app.state.stream
    try:
        stream_path = stream.get_file(filename)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail="Stream not available") from e
    if not stream_path:
        raise HTTPException(status_code=404, detail="File not found")
    headers = (
        {"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"}
        if "m3u8" in filename
        else {}
    )
    return FileResponse(stream_path, headers=headers)


@app.get("/start")
def start_stream(request: Request, bitrate: int = 500000, framerate: int = 24):
    stream: Stream = request.app.state.stream
    try:
        playlist_filename = stream.start(bitrate, framerate)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail="Stream not available") from e
    return {"playlist": f"/hls/{playlist_filename}"}


def _is_filename(filename: str) -> bool:
    path = Path(filename)
    return (
        len(path.parts) == 1 and not path.is_absolute() and filename not in {"..", "."}
    )


@app.get("/sensor")
def get_sensor_data():
    try:
        return read_sensor_data(settings.test_sensor)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail="Sensor not available") from e


@app.get("/hardware")
def get_hardware(request: Request):
    return request.app.state.hardware


@app.get("/system")
def get_system_info():
    return read_system_info()
