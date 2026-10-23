// YouTube thumbnail helpers for the web app.
// Ported from the desktop engine (tools/jpg2pdf/src/jpg2pdf_app/youtube.py)
// so the web and desktop tools accept the same URL forms.

const VIDEO_ID_RE = /^[A-Za-z0-9_-]{11}$/;

export function extractVideoId(input: string): string | null {
  const value = input.trim();
  if (VIDEO_ID_RE.test(value)) return value;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  const host = url.hostname.replace(/^www\.|^m\./, "");
  if (host === "youtu.be") {
    const id = url.pathname.split("/").filter(Boolean)[0] ?? "";
    return VIDEO_ID_RE.test(id) ? id : null;
  }
  if (host === "youtube.com" || host === "music.youtube.com") {
    const fromQuery = url.searchParams.get("v");
    if (fromQuery && VIDEO_ID_RE.test(fromQuery)) return fromQuery;
    const parts = url.pathname.split("/").filter(Boolean);
    if (
      parts.length >= 2 &&
      ["shorts", "embed", "live", "v"].includes(parts[0]) &&
      VIDEO_ID_RE.test(parts[1])
    ) {
      return parts[1];
    }
  }
  return null;
}

export function slugifyTitle(title: string, fallback: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
  return slug || fallback;
}

export async function fetchVideoTitle(videoId: string): Promise<string | null> {
  try {
    const res = await fetch(
      `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`,
    );
    if (!res.ok) return null;
    const data = (await res.json()) as { title?: string };
    return data.title ?? null;
  } catch {
    return null;
  }
}

const THUMBNAIL_SIZES = ["maxresdefault", "sddefault", "hqdefault", "default"];

/**
 * Download the best available thumbnail for a video.
 * YouTube serves a tiny placeholder image for missing sizes, so
 * candidates under 2 KB are treated as missing (same rule as desktop).
 */
export async function downloadThumbnail(
  videoId: string,
): Promise<{ blob: Blob; sizeName: string } | null> {
  for (const sizeName of THUMBNAIL_SIZES) {
    try {
      const res = await fetch(
        `https://i.ytimg.com/vi/${videoId}/${sizeName}.jpg`,
      );
      if (!res.ok) continue;
      const blob = await res.blob();
      if (blob.size < 2000) continue;
      return { blob, sizeName };
    } catch {
      // CORS or network failure for this size; try the next one.
    }
  }
  return null;
}
