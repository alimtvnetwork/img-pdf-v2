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
    "HKCU:\Software\Classes\Jpg2Pdf.FolderMenu.UI",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu.PDF",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu.Image",
    "HKCU:\Software\Classes\Jpg2Pdf.FilesMenu.UI"
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
Remove-Item -LiteralPath (Join-Path $binDir "jpg2pdf-selected-runner.cmd") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $binDir "jpg2pdf-selected-launcher.vbs") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $binDir "jpg2pdf-gui-launch.vbs") -Force -ErrorAction SilentlyContinue

foreach ($p in $paths) {
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Recurse -Force
        Write-Host "Removed: $p" -ForegroundColor Yellow
    }
}

function Broadcast-ShellChange {
    try {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class ShellNotify {
    [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
}
"@ -ErrorAction SilentlyContinue
        [ShellNotify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    } catch { }
}
Broadcast-ShellChange

Write-Host "Unregister complete." -ForegroundColor Green
