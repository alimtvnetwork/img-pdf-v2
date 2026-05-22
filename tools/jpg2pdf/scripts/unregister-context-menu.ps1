<#
.SYNOPSIS
  Remove jpg2pdf Explorer context-menu entries (HKCU only).
#>
$ErrorActionPreference = "SilentlyContinue"

$paths = @(
    "HKCU:\Software\Classes\*\shell\Jpg2PdfMenu",
    "HKCU:\Software\Classes\AllFilesystemObjects\shell\Jpg2PdfMenu",
    "HKCU:\Software\Classes\Directory\shell\Jpg2PdfMenu",
    "HKCU:\Software\Classes\Directory\Background\shell\Jpg2PdfMenu",
    "HKCU:\Software\Classes\Jpg2Pdf.FolderMenu",
    "HKCU:\Software\Classes\Jpg2Pdf.FolderMenu.PDF",
    "HKCU:\Software\Classes\Jpg2Pdf.FolderMenu.Image",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu.PDF",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu.Image"
)

$exts = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf", ".html", ".htm", ".docx", ".doc")
foreach ($ext in $exts) {
    $paths += "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\Jpg2PdfMenu"
    $progId = (Get-ItemProperty -Path "HKCU:\Software\Classes\$ext" -ErrorAction SilentlyContinue)."(default)"
    if (-not $progId) {
        $progId = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\$ext" -ErrorAction SilentlyContinue)."(default)"
    }
    if ($progId) {
        $paths += "HKCU:\Software\Classes\$progId\shell\Jpg2PdfMenu"
    }
}

$binDir = Join-Path $HOME "Tools\bin"
Remove-Item -Path (Join-Path $binDir "jpg2pdf-files-*.cmd") -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path $binDir "jpg2pdf-selected-runner.cmd") -Force -ErrorAction SilentlyContinue

foreach ($p in $paths) {
    if (Test-Path $p) {
        Remove-Item $p -Recurse -Force
        Write-Host "Removed: $p" -ForegroundColor Yellow
    }
}
Write-Host "Unregister complete." -ForegroundColor Green
