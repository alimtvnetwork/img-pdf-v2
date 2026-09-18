# Mixed-Input Merge

## Capability

`jpg2pdf` accepts images, existing PDFs, HTML pages, and Word docs in one call and merges them into a single PDF, **preserving the order given**.

## Supported extensions

| Kind  | Extensions                              | Renderer |
|-------|------------------------------------------|----------|
| Image | `.jpg .jpeg .png .webp .bmp .tif .tiff` | Pillow (honours `--size/--fit/--style/...`) |
| PDF   | `.pdf`                                   | `pypdf` — embedded as-is, geometry preserved |
| HTML  | `.html .htm`                             | `xhtml2pdf` (pure Python) |
| Word  | `.docx .doc`                             | `docx2pdf` — needs MS Word (Win) or LibreOffice (mac) |

## Invocation

```
jpg2pdf <folder>                       # folder mode (natural sort)
jpg2pdf --files f1 f2 f3 --out out.pdf # selection mode (selection order)
jpg2pdf --files-from list.txt          # one path per line, UTF-8
```

## Behavior rules

- Folder input → naturally sorted (`img2.jpg` before `img10.jpg`).
- Selection mode → preserved exactly as given.
- Consecutive images are batched into one image-PDF chunk for efficiency.
- `--size/--fit/--orientation/--dpi/--rotate/--auto-rotate/--style pencil` apply ONLY to image inputs. PDFs/HTML/Word keep their own page geometry.

## Windows context menu

Registered under HKCU. `MultiSelectModel=Player` ensures Windows passes ALL selected files in one invocation, in selection order. Entries exist for folders, images, `.pdf`, `.html`, and `.docx`.
