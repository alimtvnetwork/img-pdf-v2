// Browser-side merge engine for the web app.
//
// Mirrors the desktop engine's contract (tools/jpg2pdf/src/jpg2pdf.py):
// images, PDFs, HTML pages and Word documents merge into ONE pdf, in
// the order given. Everything runs client-side with pdf-lib; nothing
// is uploaded anywhere.
//
// Fidelity notes (web vs desktop):
// - Images and PDFs are embedded losslessly, like the desktop tool.
// - HTML and DOCX are rendered as text pages in the browser (the
//   desktop tool uses xhtml2pdf / Word / LibreOffice for full layout).
// - Legacy .doc files cannot be converted in a browser; they are
//   reported as skipped with that reason instead of failing silently.

import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

export type MergeKind = "image" | "pdf" | "html" | "word" | "unknown";

export interface MergeItem {
  id: string;
  name: string;
  kind: MergeKind;
  file: File;
  previewUrl?: string;
}

export interface SkippedItem {
  name: string;
  reason: string;
}

export interface MergeResult {
  bytes: Uint8Array;
  merged: string[];
  skipped: SkippedItem[];
  pageCount: number;
}

const IMAGE_EXTS = new Set(["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"]);
const HTML_EXTS = new Set(["html", "htm"]);
const WORD_EXTS = new Set(["docx", "doc"]);

export function kindOfFile(name: string): MergeKind {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (IMAGE_EXTS.has(ext)) return "image";
  if (ext === "pdf") return "pdf";
  if (HTML_EXTS.has(ext)) return "html";
  if (WORD_EXTS.has(ext)) return "word";
  return "unknown";
}

export const PAGE_SIZES = {
  a4: { width: 595.28, height: 841.89, label: "A4" },
  letter: { width: 612, height: 792, label: "Letter" },
  legal: { width: 612, height: 1008, label: "Legal" },
} as const;

export type PageSizeKey = keyof typeof PAGE_SIZES;

export type Orientation = "portrait" | "landscape";

/** Page dimensions in points. PDF pages are copied as-is and never
 * resized -- only image and text pages are laid out on this size,
 * mirroring the desktop tool's --size / --orientation. */
export function pageDims(
  pageSize: PageSizeKey,
  orientation: Orientation = "portrait",
): { width: number; height: number } {
  const { width, height } = PAGE_SIZES[pageSize];
  return orientation === "landscape"
    ? { width: height, height: width }
    : { width, height };
}

function wrapText(text: string, width: number): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    const words = paragraph.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      lines.push("");
      continue;
    }
    let current = "";
    for (const word of words) {
      if ((current + " " + word).trim().length > width) {
        if (current) lines.push(current);
        current = word;
      } else {
        current = (current + " " + word).trim();
      }
    }
    if (current) lines.push(current);
  }
  return lines;
}

/** Strip HTML to plain text, keeping paragraph breaks. */
export function htmlToText(html: string): string {
  const withBreaks = html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|h[1-6]|li|tr|section|article)>/gi, "\n");
  const doc = new DOMParser().parseFromString(withBreaks, "text/html");
  return (doc.body.textContent ?? "").replace(/[ \t]+\n/g, "\n").trim();
}

async function appendTextPages(
  out: PDFDocument,
  text: string,
  pageSize: PageSizeKey,
  orientation: Orientation = "portrait",
): Promise<void> {
  const { width, height } = pageDims(pageSize, orientation);
  const font = await out.embedFont(StandardFonts.Helvetica);
  const fontSize = 11;
  const lineHeight = 15;
  const margin = 50;
  const lines = wrapText(text, 88);
  const perPage = Math.max(1, Math.floor((height - margin * 2) / lineHeight));
  for (let i = 0; i < lines.length; i += perPage) {
    const page = out.addPage([width, height]);
    let y = height - margin;
    for (const line of lines.slice(i, i + perPage)) {
      page.drawText(line, {
        x: margin,
        y,
        size: fontSize,
        font,
        color: rgb(0.1, 0.1, 0.1),
      });
      y -= lineHeight;
    }
  }
}

async function imageToPngBytes(file: File): Promise<Uint8Array> {
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas is not available in this browser.");
  ctx.drawImage(bitmap, 0, 0);
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/png"),
  );
  if (!blob) throw new Error("Could not decode this image.");
  return new Uint8Array(await blob.arrayBuffer());
}

async function appendImage(
  out: PDFDocument,
  item: MergeItem,
  pageSize: PageSizeKey,
  orientation: Orientation = "portrait",
): Promise<void> {
  const bytes = new Uint8Array(await item.file.arrayBuffer());
  const lower = item.name.toLowerCase();
  let image;
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
    image = await out.embedJpg(bytes);
  } else if (lower.endsWith(".png")) {
    image = await out.embedPng(bytes);
  } else {
    image = await out.embedPng(await imageToPngBytes(item.file));
  }
  const { width, height } = pageDims(pageSize, orientation);
  const page = out.addPage([width, height]);
  const scale = Math.min(width / image.width, height / image.height);
  const drawWidth = image.width * scale;
  const drawHeight = image.height * scale;
  page.drawImage(image, {
    x: (width - drawWidth) / 2,
    y: (height - drawHeight) / 2,
    width: drawWidth,
    height: drawHeight,
  });
}

async function docxToText(file: File): Promise<string> {
  const mammoth = await import("mammoth");
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.convertToHtml({ arrayBuffer });
  return htmlToText(result.value);
}

export async function mergeFilesToPdf(
  items: MergeItem[],
  pageSize: PageSizeKey,
  orientation: Orientation = "portrait",
): Promise<MergeResult> {
  // Order is exactly the list order the caller passes in: the
  // visualizer's Up/Down/Top/Bottom and sort-by-name controls are
  // the only thing that changes it. Nothing here re-sorts.
  const out = await PDFDocument.create();
  const merged: string[] = [];
  const skipped: SkippedItem[] = [];

  for (const item of items) {
    try {
      if (item.kind === "image") {
        await appendImage(out, item, pageSize, orientation);
        merged.push(item.name);
      } else if (item.kind === "pdf") {
        const src = await PDFDocument.load(
          await item.file.arrayBuffer(),
        );
        const pages = await out.copyPages(src, src.getPageIndices());
        for (const page of pages) out.addPage(page);
        merged.push(item.name);
      } else if (item.kind === "html") {
        await appendTextPages(out, htmlToText(await item.file.text()), pageSize, orientation);
        merged.push(item.name);
      } else if (item.kind === "word") {
        if (item.name.toLowerCase().endsWith(".doc")) {
          throw new Error(
            "Legacy .doc cannot be converted in a browser. " +
              "Use the desktop app, or save it as .docx first.",
          );
        }
        await appendTextPages(out, await docxToText(item.file), pageSize, orientation);
        merged.push(item.name);
      } else {
        throw new Error("Unsupported file type.");
      }
    } catch (err) {
      skipped.push({
        name: item.name,
        reason: err instanceof Error ? err.message : String(err),
      });
    }
  }

  const bytes = await out.save();
  return { bytes, merged, skipped, pageCount: out.getPageCount() };
}
