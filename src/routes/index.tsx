import { useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  ArrowDown,
  ArrowUp,
  FilePlus2,
  FileText,
  Image as ImageIcon,
  Merge,
  Trash2,
  Youtube,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Input } from "@/components/ui/input";
import {
  PAGE_SIZES,
  kindOfFile,
  mergeFilesToPdf,
  type MergeItem,
  type PageSizeKey,
  type SkippedItem,
} from "@/lib/merge";
import {
  downloadThumbnail,
  extractVideoId,
  fetchVideoTitle,
  slugifyTitle,
} from "@/lib/youtube";

export const Route = createFileRoute("/")({
  component: Index,
});

let nextId = 1;
function makeItem(file: File): MergeItem {
  return {
    id: `item-${nextId++}`,
    name: file.name,
    kind: kindOfFile(file.name),
    file,
  };
}

const ACCEPT =
  ".jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff,.pdf,.html,.htm,.docx,.doc";

function Index() {
  const [items, setItems] = useState<MergeItem[]>([]);
  const [pageSize, setPageSize] = useState<PageSizeKey>("a4");
  const [busy, setBusy] = useState(false);
  const [ytBusy, setYtBusy] = useState(false);
  const [ytUrl, setYtUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<SkippedItem[]>([]);
  const [result, setResult] = useState<{ url: string; pages: number } | null>(
    null,
  );
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = (files: FileList | File[]) => {
    const next = Array.from(files).map(makeItem);
    if (next.length > 0) {
      setItems((prev) => [...prev, ...next]);
      setResult(null);
    }
  };

  const move = (index: number, delta: number) => {
    setItems((prev) => {
      const target = index + delta;
      if (target < 0 || target >= prev.length) return prev;
      const copy = [...prev];
      const [entry] = copy.splice(index, 1);
      copy.splice(target, 0, entry);
      return copy;
    });
  };

  const removeAt = (index: number) =>
    setItems((prev) => prev.filter((_, i) => i !== index));

  const addYoutube = async () => {
    const videoId = extractVideoId(ytUrl);
    if (!videoId) {
      setError("That does not look like a YouTube URL or video ID.");
      return;
    }
    setYtBusy(true);
    setError(null);
    try {
      const title = await fetchVideoTitle(videoId);
      const thumb = await downloadThumbnail(videoId);
      if (!thumb) {
        setError(
          "Could not download the thumbnail (network or CORS blocked it). " +
            "Open the video on YouTube, save the thumbnail image, and add it as a file instead.",
        );
        return;
      }
      const name = `${slugifyTitle(title ?? "", videoId)}-thumbnail.jpg`;
      addFiles([new File([thumb.blob], name, { type: "image/jpeg" })]);
      setYtUrl("");
    } finally {
      setYtBusy(false);
    }
  };

  const merge = async () => {
    if (items.length === 0) return;
    setBusy(true);
    setError(null);
    setSkipped([]);
    try {
      const res = await mergeFilesToPdf(items, pageSize);
      setSkipped(res.skipped);
      if (res.merged.length === 0) {
        setError("Nothing could be merged. See the skipped files below.");
        setResult(null);
        return;
      }
      const blob = new Blob([res.bytes.buffer as ArrayBuffer], {
        type: "application/pdf",
      });
      setResult({ url: URL.createObjectURL(blob), pages: res.pageCount });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight">
            Combine into PDF
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Select images, PDFs, HTML and Word documents and merge them
            into a single PDF -- right here in your browser. Nothing is
            uploaded. Right-click the list or any file for quick actions.
          </p>
        </header>

        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                addFiles(e.dataTransfer.files);
              }}
              className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                dragOver
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/30 hover:border-primary/50"
              }`}
            >
              <FilePlus2 className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <p className="font-medium">
                Drop files here, or click to select
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Images, PDF, HTML, Word (.docx) -- merged in list order
              </p>
            </div>
          </ContextMenuTrigger>
          <ContextMenuContent>
            <ContextMenuItem onSelect={() => fileInputRef.current?.click()}>
              Add files...
            </ContextMenuItem>
            <ContextMenuItem
              onSelect={() => void merge()}
              disabled={busy || items.length === 0}
            >
              Merge into PDF
            </ContextMenuItem>
            <ContextMenuSeparator />
            <ContextMenuItem
              onSelect={() => {
                setItems([]);
                setResult(null);
                setSkipped([]);
              }}
              disabled={items.length === 0}
            >
              Clear list
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>

        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Youtube className="h-5 w-5" /> YouTube thumbnail
            </CardTitle>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Input
              value={ytUrl}
              onChange={(e) => setYtUrl(e.target.value)}
              placeholder="Paste a YouTube URL or video ID"
            />
            <Button onClick={() => void addYoutube()} disabled={ytBusy}>
              {ytBusy ? "Fetching..." : "Add thumbnail"}
            </Button>
          </CardContent>
        </Card>

        {items.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-base">
                Files to merge ({items.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {items.map((item, index) => (
                <ContextMenu key={item.id}>
                  <ContextMenuTrigger asChild>
                    <div className="flex items-center gap-3 rounded-lg border px-3 py-2">
                      {item.kind === "image" ? (
                        <ImageIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      )}
                      <span className="min-w-0 flex-1 truncate text-sm">
                        {item.name}
                      </span>
                      <span className="rounded bg-muted px-2 py-0.5 text-xs uppercase">
                        {item.kind}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => move(index, -1)}
                        disabled={index === 0}
                        aria-label="Move up"
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => move(index, 1)}
                        disabled={index === items.length - 1}
                        aria-label="Move down"
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeAt(index)}
                        aria-label="Remove"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem
                      onSelect={() => move(index, -1)}
                      disabled={index === 0}
                    >
                      Move up
                    </ContextMenuItem>
                    <ContextMenuItem
                      onSelect={() => move(index, 1)}
                      disabled={index === items.length - 1}
                    >
                      Move down
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onSelect={() => removeAt(index)}>
                      Remove from list
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}

              <div className="flex flex-wrap items-center gap-3 pt-3">
                <label className="text-sm text-muted-foreground">
                  Image page size
                </label>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(e.target.value as PageSizeKey)}
                  className="rounded-md border bg-background px-2 py-1.5 text-sm"
                >
                  {Object.entries(PAGE_SIZES).map(([key, value]) => (
                    <option key={key} value={key}>
                      {value.label}
                    </option>
                  ))}
                </select>
                <Button onClick={() => void merge()} disabled={busy}>
                  <Merge className="mr-2 h-4 w-4" />
                  {busy ? "Merging..." : "Merge into PDF"}
                </Button>
                {result && (
                  <a
                    href={result.url}
                    download="combined.pdf"
                    className="text-sm font-medium text-primary underline"
                  >
                    Download combined.pdf ({result.pages} pages)
                  </a>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {error && (
          <p className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm">
            {error}
          </p>
        )}
        {skipped.length > 0 && (
          <div className="mt-4 rounded-lg border px-4 py-3 text-sm">
            <p className="font-medium">Skipped files:</p>
            <ul className="mt-1 list-disc pl-5">
              {skipped.map((s) => (
                <li key={s.name}>
                  {s.name} -- {s.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        <footer className="mt-10 text-center text-xs text-muted-foreground">
          Prefer right-click in your file manager? Install the desktop
          tool and run <code>jpg2pdf --install-context-menu</code> -- it
          registers Combine into PDF in Windows Explorer, macOS Finder
          and Linux file managers.
        </footer>
      </div>
    </div>
  );
}
