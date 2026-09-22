"""YouTube thumbnail resolver and downloader for jpg2pdf.

Features:
- Video ID extraction from standard, short, embed, live, and share URLs.
- Video title extraction via public YouTube oEmbed endpoint (no API keys required).
- Title slugification to clean, lowercase, filesystem-safe slugs.
- Multi-resolution thumbnail cascading (maxresdefault -> sddefault -> hqdefault -> default).
- Automatic collision handling and OS explorer opening.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Match YouTube video ID (11 characters)
_YT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# Match YouTube URL patterns
_YT_URL_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.|m\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
]

# Resolution cascade for thumbnails
_THUMBNAIL_TEMPLATES = [
    "https://img.youtube.com/vi/{id}/maxresdefault.jpg",
    "https://img.youtube.com/vi/{id}/sddefault.jpg",
    "https://img.youtube.com/vi/{id}/hqdefault.jpg",
    "https://img.youtube.com/vi/{id}/mqdefault.jpg",
    "https://img.youtube.com/vi/{id}/default.jpg",
]

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def extract_video_id(url_or_id: str) -> str | None:
    """Extract an 11-character YouTube video ID from a URL or raw ID string."""
    candidate = url_or_id.strip()
    if not candidate:
        return None

    # Check if input is already a raw 11-character video ID
    if _YT_ID_REGEX.match(candidate):
        return candidate

    for pattern in _YT_URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group(1)

    return None


def slugify_title(title: str, max_len: int = 80) -> str:
    """Convert video title into a clean, lowercase, filesystem-safe slug."""
    if not title:
        return "youtube-video"

    # Lowercase
    slug = title.strip().lower()

    # Replace apostrophes with empty string (e.g. don't -> dont)
    slug = re.sub(r"['\u2018\u2019]", "", slug)

    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Collapse consecutive hyphens and strip edges
    slug = re.sub(r"-+", "-", slug).strip("-")

    if not slug:
        slug = "youtube-video"

    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")

    return slug


def fetch_video_title(video_id: str, timeout: float = 6.0) -> str:
    """Fetch video title using YouTube public oEmbed endpoint without API keys."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    req = urllib.request.Request(oembed_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                title = payload.get("title")
                if title:
                    return str(title).strip()
    except Exception:
        pass
    return f"youtube-{video_id}"


def get_default_thumbnail_dir() -> Path:
    """Return a standard persistent temporary directory for downloaded thumbnails."""
    temp_base = Path(tempfile.gettempdir()) / "jpg2pdf" / "thumbnails"
    temp_base.mkdir(parents=True, exist_ok=True)
    return temp_base


def download_thumbnail(url_or_id: str,
                       out_dir: Path | str | None = None,
                       custom_title: str | None = None) -> tuple[Path, str]:
    """Download highest resolution thumbnail for a video and save with slug title."""
    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL or video ID: {url_or_id}")

    target_dir = Path(out_dir) if out_dir else get_default_thumbnail_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    title = custom_title if custom_title else fetch_video_title(video_id)
    slug = slugify_title(title)

    # Determine unique output filename
    out_file = target_dir / f"{slug}.jpg"
    counter = 2
    while out_file.exists():
        out_file = target_dir / f"{slug}-{counter}.jpg"
        counter += 1

    # Cascade through thumbnail URLs from highest to lowest resolution
    image_bytes: bytes | None = None
    for tmpl in _THUMBNAIL_TEMPLATES:
        thumb_url = tmpl.format(id=video_id)
        req = urllib.request.Request(thumb_url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status == 200:
                    data = resp.read()
                    # YouTube returns a tiny ~1000 byte placeholder image for missing maxresdefault
                    if len(data) > 1200:
                        image_bytes = data
                        break
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue

    if not image_bytes:
        raise RuntimeError(f"Could not download any thumbnail for YouTube video ID '{video_id}'")

    out_file.write_bytes(image_bytes)
    return out_file, title


def resolve_youtube_thumbnails(inputs: list[str],
                               out_dir: Path | str | None = None) -> list[Path]:
    """Resolve and download thumbnails for a list of YouTube URLs or IDs."""
    results: list[Path] = []
    target_dir = Path(out_dir) if out_dir else get_default_thumbnail_dir()

    for item in inputs:
        # Handle comma or space separated lists within items
        parts = [p.strip() for p in re.split(r"[,\s]+", item) if p.strip()]
        for p in parts:
            vid = extract_video_id(p)
            if not vid:
                print(f"  [youtube] skip: not a recognized YouTube URL: {p}", file=sys.stderr)
                continue
            try:
                path, title = download_thumbnail(vid, out_dir=target_dir)
                print(f"  [youtube] downloaded: '{title}' -> {path.name}")
                results.append(path)
            except Exception as e:
                print(f"  [youtube] failed to download thumbnail for {p}: {e}", file=sys.stderr)

    return results


def open_directory_in_explorer(path: Path | str) -> bool:
    """Open a folder in the native OS file manager."""
    target = Path(path)
    if not target.is_dir():
        target = target.parent

    try:
        if sys.platform.startswith("win"):
            os.startfile(str(target))
            return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
            return True
        else:
            subprocess.Popen(["xdg-open", str(target)])
            return True
    except Exception as e:
        print(f"  (warning: could not open directory: {e})", file=sys.stderr)
        return False
