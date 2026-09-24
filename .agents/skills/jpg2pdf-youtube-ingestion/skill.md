---
name: jpg2pdf-youtube-ingestion
description: Specialized engine skill for downloading, caching, slugifying, and ingesting YouTube thumbnails into PDF and image conversion pipelines.
---

# jpg2pdf YouTube Ingestion Skill

This skill governs the YouTube thumbnail downloading, resolution waterfall cascading, oEmbed title extraction, slugification, and conversion pipeline integration.

## Architectural Anchors
- Core Subsystem: `tools/jpg2pdf/src/jpg2pdf_app/youtube.py`
- CLI Integration: `tools/jpg2pdf/src/jpg2pdf.py` (`--youtube`, `--download-only`, `--open-dir`)
- Facade Exports: `tools/jpg2pdf/src/jpg2pdf_app/core.py`
- GUI Modal & Threading: `tools/jpg2pdf/src/jpg2pdf_app/gui.py` (`on_add_youtube`, `_start_youtube_worker`)

## Key Subsystems & Non-Negotiable Rules

### 1. Zero External Dependencies
The YouTube subsystem is built strictly on Python's standard library:
- `urllib.request` for HTTP GET requests
- `re` for regex parsing and slugification
- `json` for oEmbed payload deserialization
- `pathlib.Path` for cross-platform filesystem operations

Never introduce heavy third-party dependencies (like `pytube`, `yt-dlp`, or `requests`) into the default import graph.

### 2. URL and ID Pattern Matching (`extract_video_id`)
Supported formats evaluated via regular expressions:
1. **Raw Video ID:** Exact 11 characters `^[a-zA-Z0-9_-]{11}$`
2. **Watch URLs:** `youtube.com/watch?v={id}` (handles extra query parameters, `m.youtube.com`, `www.youtube.com`)
3. **Shorts URLs:** `youtube.com/shorts/{id}`
4. **Embed URLs:** `youtube.com/embed/{id}`
5. **Live Streams:** `youtube.com/live/{id}`
6. **Shortened URLs:** `youtu.be/{id}`
7. **Batch Token Splitting:** Space- and comma-delimited strings are parsed iteratively.

### 3. Five-Tier Resolution Waterfall & The 1200-Byte Guard
Thumbnails are retrieved by descending through `_THUMBNAIL_TEMPLATES`:
1. `maxresdefault.jpg` (1920x1080 / 1280x720)
2. `sddefault.jpg` (640x480)
3. `hqdefault.jpg` (480x360)
4. `mqdefault.jpg` (320x180)
5. `default.jpg` (120x90)

**CRITICAL: The 1200-Byte False-Positive Detection Rule:**
When `maxresdefault.jpg` is missing, YouTube's CDN returns HTTP 200 OK with a 1097-byte grey placeholder JPEG instead of HTTP 404.
The engine explicitly guards against this:
```python
if len(data) > 1200:
    image_bytes = data
    break
```
Any response payload <= 1200 bytes MUST be discarded as a placeholder, allowing the waterfall to continue down to `sddefault.jpg` or `hqdefault.jpg`.

### 4. Title Extraction & Slugification
- **oEmbed Endpoint:**
  `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={id}&format=json`
  Uses a 6.0-second timeout with a custom `User-Agent`.
  On timeout, network error, or missing title, cleanly falls back to `youtube-{video_id}` without raising unhandled exceptions.
- **Slugification (`slugify_title`):**
  1. Lowercase text.
  2. Strip apostrophes (`don't` -> `dont`) to prevent broken fragments.
  3. Replace non-alphanumeric characters with single hyphens (`-`).
  4. Truncate to a maximum of 80 characters without trailing hyphens.
- **Collision Deduplication:**
  If `{slug}.jpg` exists in target directory, test `{slug}-2.jpg`, `{slug}-3.jpg`, etc., avoiding overwriting previously fetched media.

### 5. CLI & Output Directory Conventions
- Target output directory resolution:
  1. Explicit `--out` directory or parent folder.
  2. Positional `folder` argument if it is a directory.
  3. Default persistent temp cache: `Path(tempfile.gettempdir()) / "jpg2pdf" / "thumbnails"`.
- `--download-only`: Downloads thumbnails to target directory and exits (returns code 0) without triggering PDF or stacked image generation.
- `--open-dir`: Opens output directory in native OS file manager (`os.startfile` on Windows, `open` on macOS, `xdg-open` on Linux).

### 6. Desktop GUI Integration
- `+ YouTube` button opens a modal text dialog allowing multiline entry of URLs/IDs.
- Automatic clipboard pre-fill if clipboard contains `youtube.com` or `youtu.be`.
- Downloads run in a background daemon thread (`threading.Thread`) and report results back to the main thread via `root.after(0, ...)`.
- Tagged with kind `yt` in the GUI listbox.

## Verification Checklist
- Test video ID extraction:
  ```bash
  python -c "from jpg2pdf_app.youtube import extract_video_id; assert extract_video_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'"
  ```
- Test CLI YouTube download-only:
  ```bash
  python tools/jpg2pdf/src/jpg2pdf.py --youtube dQw4w9WgXcQ --download-only
  ```
- Test resolution cascade: Ensure downloaded file is > 1200 bytes and a valid JPEG image.
