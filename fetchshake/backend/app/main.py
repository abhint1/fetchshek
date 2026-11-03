
from __future__ import annotations

import asyncio
import ipaddress
import mimetypes
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yt_dlp

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from starlette.background import BackgroundTask


APP_VERSION = "1.1.0"
MAX_REDIRECTS = 8
TIMEOUT = 30
MAX_DOWNLOAD_MB = int(os.getenv("MAX_DOWNLOAD_MB", "500"))

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "fetchshek"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Fetchshek API", version=APP_VERSION)

origins = [
    x.strip()
    for x in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",")
    if x.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    media_type: str = Field(
        "auto", pattern="^(auto|video|image)$"
    )


class DownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str | None = None
    media_type: str = Field(
        "auto", pattern="^(auto|video|image)$"
    )


QUALITY_PRESETS = {
    "best": "bestvideo*+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "audio": "bestaudio/best",
}


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only valid HTTP/HTTPS URLs are supported.")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")

    host = parsed.hostname.lower()

    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("Local network URLs are not allowed.")

    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            records = socket.getaddrinfo(
                host, None, type=socket.SOCK_STREAM
            )
            addresses = {
                ipaddress.ip_address(record[4][0])
                for record in records
            }
        except socket.gaierror as exc:
            raise ValueError("Could not resolve URL hostname.") from exc

    for ip in addresses:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(
                "Private or reserved network destinations are blocked."
            )

    return url


async def resolve_url(url: str) -> str:
    current = validate_public_url(url)

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=TIMEOUT,
        headers={"User-Agent": "Fetchshek/1.1"},
    ) as client:

        for _ in range(MAX_REDIRECTS + 1):
            current = validate_public_url(current)

            try:
                async with client.stream(
                    "GET",
                    current,
                    headers={"Range": "bytes=0-0"},
                ) as response:

                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")

                        if not location:
                            return current

                        current = str(response.url.join(location))
                        continue

                    return str(response.url)

            except httpx.HTTPError:
                return current

    raise ValueError("Too many redirects.")


def identify_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()

    if host.endswith(("youtube.com", "youtu.be")):
        return "YouTube"
    if host.endswith(("twitter.com", "x.com", "t.co")):
        return "X"
    if host.endswith("instagram.com"):
        return "Instagram"
    if host.endswith(("facebook.com", "fb.watch")):
        return "Facebook"
    if host.endswith(("reddit.com", "redd.it")):
        return "Reddit"
    if host.endswith("tiktok.com"):
        return "TikTok"
    if host.endswith(("pinterest.com", "pin.it")):
        return "Pinterest"
    if host.endswith("vimeo.com"):
        return "Vimeo"

    return "Website / direct link"


def extract_info(url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": TIMEOUT,
        "retries": 1,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("No media was found at this URL.")

    raw_formats = info.get("formats") or []

    video_formats = [
        f for f in raw_formats
        if f.get("url")
        and f.get("vcodec") not in (None, "none")
    ]

    audio_formats = [
        f for f in raw_formats
        if f.get("url")
        and f.get("acodec") not in (None, "none")
    ]

    max_height = max(
        (f.get("height") or 0 for f in video_formats),
        default=0,
    )

    has_video = bool(video_formats)
    has_audio = bool(audio_formats)

    if not has_video and not has_audio:
        raise ValueError("No downloadable media formats found.")

    media_type = "video" if has_video else "audio"

    presets = []

    if has_video:
        presets.append({
            "format_id": "best",
            "label": "Best quality",
            "description": "Maximum available video quality",
            "available": True,
        })

        for height in (1080, 720, 480, 360):
            presets.append({
                "format_id": f"{height}p",
                "label": f"{height}p",
                "description": f"Up to {height}p",
                "available": max_height >= height,
            })

    if has_audio:
        presets.append({
            "format_id": "audio",
            "label": "Audio only",
            "description": "Best available audio",
            "available": True,
        })

    return {
        "title": info.get("title") or "Media download",
        "media_type": media_type,
        "thumbnail": info.get("thumbnail"),
        "duration_seconds": info.get("duration"),
        "formats": presets,
        "extractor": info.get("extractor_key") or "yt-dlp",
    }


def direct_media_info(url: str) -> dict | None:
    try:
        with httpx.Client(
            follow_redirects=False,
            timeout=TIMEOUT,
        ) as client:

            current = url

            for _ in range(MAX_REDIRECTS + 1):
                validate_public_url(current)

                response = client.head(
                    current,
                    headers={"User-Agent": "Fetchshek/1.1"},
                )

                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")

                    if not location:
                        return None

                    current = str(response.url.join(location))
                    continue

                content_type = (
                    response.headers.get("content-type", "")
                    .split(";")[0].lower()
                )

                if not (
                    content_type.startswith("image/")
                    or content_type.startswith("video/")
                ):
                    return None

                kind = (
                    "image"
                    if content_type.startswith("image/")
                    else "video"
                )

                return {
                    "title": Path(urlparse(current).path).name
                    or "Media download",
                    "media_type": kind,
                    "thumbnail": current if kind == "image" else None,
                    "duration_seconds": None,
                    "formats": [{
                        "format_id": "original",
                        "label": "Original quality",
                        "description": "Original media file",
                        "available": True,
                    }],
                    "extractor": "direct-url",
                }

    except httpx.HTTPError:
        return None

    return None


def download_direct(url: str) -> Path:
    validate_public_url(url)

    with httpx.stream(
        "GET",
        url,
        timeout=TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": "Fetchshek/1.1"},
    ) as response:

        if response.status_code in (301, 302, 303, 307, 308):
            raise ValueError(
                "Direct media redirected. Please try the original media URL."
            )

        response.raise_for_status()

        content_type = (
            response.headers.get("content-type", "")
            .split(";")[0].lower()
        )

        if not (
            content_type.startswith("image/")
            or content_type.startswith("video/")
        ):
            raise ValueError("URL does not point to an image or video.")

        suffix = mimetypes.guess_extension(content_type) or ".bin"
        path = DOWNLOAD_DIR / f"direct-{next(tempfile._get_candidate_names())}{suffix}"

        total = 0

        with path.open("wb") as output:
            for chunk in response.iter_bytes(1024 * 1024):
                total += len(chunk)

                if total > MAX_DOWNLOAD_MB * 1024 * 1024:
                    output.close()
                    path.unlink(missing_ok=True)
                    raise ValueError(
                        f"File exceeds the {MAX_DOWNLOAD_MB} MB limit."
                    )

                output.write(chunk)

    return path


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "fetchshek-api",
        "version": APP_VERSION,
    }


@app.post("/api/v1/analyze")
async def analyze(req: AnalyzeRequest):
    submitted_url = str(req.url)

    try:
        resolved = await resolve_url(submitted_url)
        platform = identify_platform(resolved)

        try:
            info = await asyncio.to_thread(extract_info, resolved)

        except Exception:
            info = await asyncio.to_thread(
                direct_media_info, resolved
            )

            if not info:
                raise ValueError(
                    "Could not extract media. The post may be private, "
                    "unsupported, deleted, age-restricted, or require sign-in."
                )

        if (
            req.media_type != "auto"
            and info["media_type"] != req.media_type
        ):
            raise ValueError(
                f"This link contains {info['media_type']} media, "
                f"not {req.media_type}."
            )

        return {
            "success": True,
            "submitted_url": submitted_url,
            "resolved_url": resolved,
            "platform": platform,
            **info,
            "download_available": bool(info["formats"]),
        }

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Media analysis failed. Try another public link.",
        )


def download_with_ytdlp(
    url: str,
    format_id: str,
) -> Path:

    selected_format = QUALITY_PRESETS.get(format_id)

    if not selected_format:
        raise ValueError("Invalid download quality selected.")

    output_template = str(
        DOWNLOAD_DIR / "%(title).80s-%(id)s.%(ext)s"
    )

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": output_template,
        "socket_timeout": TIMEOUT,
        "retries": 1,
        "max_filesize": MAX_DOWNLOAD_MB * 1024 * 1024,
        "format": selected_format,
        "merge_output_format": "mp4",
    }

    before = set(DOWNLOAD_DIR.iterdir())

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    created = [
        path
        for path in DOWNLOAD_DIR.iterdir()
        if path.is_file() and path not in before
    ]

    if not created:
        raise ValueError("Download did not produce a file.")

    result = max(
        created,
        key=lambda path: path.stat().st_mtime,
    )

    if result.stat().st_size > MAX_DOWNLOAD_MB * 1024 * 1024:
        result.unlink(missing_ok=True)
        raise ValueError(
            f"File exceeds the {MAX_DOWNLOAD_MB} MB limit."
        )

    return result


@app.post("/api/v1/download")
async def download(req: DownloadRequest):
    submitted_url = str(req.url)

    try:
        resolved = await resolve_url(submitted_url)

        if req.format_id == "original":
            path = await asyncio.to_thread(
                download_direct, resolved
            )

        else:
            if req.format_id not in QUALITY_PRESETS:
                raise ValueError("Invalid quality selected.")

            info = await asyncio.to_thread(
                extract_info, resolved
            )

            if info["media_type"] == "audio" and req.format_id != "audio":
                raise ValueError("This URL only provides audio.")

            if req.media_type == "image":
                raise ValueError(
                    "For direct images, select Original quality."
                )

            if req.media_type == "video" and info["media_type"] != "video":
                raise ValueError("This link does not contain video.")

            available_ids = {
                item["format_id"]
                for item in info["formats"]
                if item.get("available")
            }

            selected = req.format_id or "best"

            if selected not in available_ids:
                raise ValueError(
                    "This quality is not available for this media."
                )

            path = await asyncio.to_thread(
                download_with_ytdlp,
                resolved,
                selected,
            )

        return FileResponse(
            path,
            filename=path.name,
            media_type="application/octet-stream",
            background=BackgroundTask(
                lambda: path.unlink(missing_ok=True)
            ),
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "Download failed. The media may be restricted, "
                "unsupported, or unavailable."
            ),
        )
