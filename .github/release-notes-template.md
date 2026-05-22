# {{VERSION}}

[{{VERSION}}](https://github.com/{{REPO}}/tree/{{VERSION}}) · [`{{COMMIT_SHORT}}`](https://github.com/{{REPO}}/commit/{{COMMIT_FULL}})

{{CHANGELOG}}

---

## Release Info

| Field | Value |
| --- | --- |
| Version | `{{VERSION}}` |
| Commit | `{{COMMIT_SHORT}}` |
| Branch | `{{BRANCH}}` |
| Build Date | {{BUILD_DATE_UTC}} |
| Python Version | {{PYTHON_VERSION}} |

## Checksums (SHA256)

```
{{CHECKSUMS}}
```

## Install this exact version ({{VERSION}})

Windows (PowerShell):

```powershell
& { $env:JPG2PDF_REPO = "{{REPO}}"; $env:JPG2PDF_VERSION = "{{VERSION}}"; irm https://github.com/{{REPO}}/releases/download/{{VERSION}}/install.ps1 | iex }
```

Linux / macOS (bash):

```bash
curl -fsSL https://github.com/{{REPO}}/releases/download/{{VERSION}}/install.sh | JPG2PDF_REPO={{REPO}} JPG2PDF_VERSION={{VERSION}} bash
```

### Manual download

Download the appropriate binary from the assets below and place it on your `PATH`.

## Assets

| Platform | Architecture | File |
| --- | --- | --- |
| Windows | amd64 | `jpg2pdf-windows-x64.exe` |
| Linux   | amd64 | `jpg2pdf-linux-x64` |
| Linux   | arm64 | `jpg2pdf-linux-arm64` |
| macOS   | x64   | `jpg2pdf-macos-x64` |
| macOS   | arm64 | `jpg2pdf-macos-arm64` |

GUI binaries and macOS `.app` bundles are also attached.

## Full changelog

See [CHANGELOG.md](https://github.com/{{REPO}}/blob/{{VERSION}}/CHANGELOG.md) for the complete history.
