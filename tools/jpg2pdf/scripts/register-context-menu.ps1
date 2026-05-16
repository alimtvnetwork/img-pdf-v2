<#
.SYNOPSIS
  Register Windows Explorer context-menu entries for jpg2pdf.

.PARAMETER ExePath
  Full path to jpg2pdf.exe (or jpg2pdf.cmd shim) used by all menu entries.

.NOTES
  HKCU only - no admin required.
  Selected-files verbs use shipped per-verb .cmd launchers (next to the exe)
  for maximum reliability:
    * No nested registry quoting fragility.
    * MultiSelectModel=Player on each leaf so Explorer invokes ONCE with
      all selected files appended as %1..%N.
    * Each launcher logs to %LOCALAPPDATA%\jpg2pdf\context.log and PAUSES on
      non-zero exit so users can read errors instead of seeing a flashed
      console.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)] [string]$ExePath
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ExePath)) { Write-Error "Not found: $ExePath"; exit 1 }
$exe    = (Resolve-Path $ExePath).Path
$binDir = Split-Path -Parent $exe

# ---------------------------------------------------------------
# Per-verb launcher specs. Each entry: id, label, jpg2pdf args (without --files).
# ---------------------------------------------------------------
$verbs = @(
    @{ Id = "a4";          Label = "Combine into PDF (A4)";                       Args = "--size a4" },
    @{ Id = "letter";      Label = "Combine into PDF (Letter)";                   Args = "--size letter" },
    @{ Id = "legal";       Label = "Combine into PDF (Legal)";                    Args = "--size legal" },
    @{ Id = "a4-cw";       Label = "Combine into PDF (A4, rotate 90 CW)";         Args = "--size a4 --rotate 270" },
    @{ Id = "a4-ccw";      Label = "Combine into PDF (A4, rotate 90 CCW)";        Args = "--size a4 --rotate 90" },
    @{ Id = "a4-180";      Label = "Combine into PDF (A4, rotate 180)";           Args = "--size a4 --rotate 180" },
    @{ Id = "a4-noar";     Label = "Combine into PDF (A4, no auto-rotate)";       Args = "--size a4 --no-auto-rotate" },
    @{ Id = "a4-pencil";   Label = "Combine into PDF (A4, pencil / paper look)";  Args = "--size a4 --style pencil --ask-strength" }
)

# ---------------------------------------------------------------
# Write a launcher .cmd per verb into the install dir.
# Logs invocation + exit code to %LOCALAPPDATA%\jpg2pdf\context.log
# Pauses on non-zero exit so the user can actually read what went wrong.
# ---------------------------------------------------------------
function Write-VerbLauncher {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$ExePath,
        [Parameter(Mandatory=$true)][string]$VerbArgs,
        [Parameter(Mandatory=$true)][string]$Label
    )

    # Quote exe path for cmd.exe.
    $quotedExe = '"' + $ExePath + '"'

    $lines = @(
        '@echo off',
        'setlocal EnableExtensions',
        'title jpg2pdf - ' + $Label,
        'set "JPG2PDF_LOGDIR=%LOCALAPPDATA%\jpg2pdf"',
        'if not exist "%JPG2PDF_LOGDIR%" mkdir "%JPG2PDF_LOGDIR%" >nul 2>nul',
        'set "JPG2PDF_LOG=%JPG2PDF_LOGDIR%\context.log"',
        'echo. >> "%JPG2PDF_LOG%"',
        'echo [%DATE% %TIME%] verb=' + $Label + ' args=' + $VerbArgs + ' files=%* >> "%JPG2PDF_LOG%"',
        'echo [jpg2pdf] ' + $Label,
        'echo [jpg2pdf] Files: %*',
        'echo.',
        $quotedExe + ' ' + $VerbArgs + ' --files %*',
        'set "JPG2PDF_CODE=%ERRORLEVEL%"',
        'echo [%DATE% %TIME%] exit=%JPG2PDF_CODE% >> "%JPG2PDF_LOG%"',
        'if not "%JPG2PDF_CODE%"=="0" (',
        '  echo.',
        '  echo [jpg2pdf] FAILED with exit code %JPG2PDF_CODE%.',
        '  echo [jpg2pdf] Log: %JPG2PDF_LOG%',
        '  pause',
        ')',
        'endlocal & exit /b %JPG2PDF_CODE%'
    )

    # ASCII to keep PS 5.1 / Win cmd happy regardless of code page.
    Set-Content -LiteralPath $Path -Value $lines -Encoding ASCII
}

function New-Key($path) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
}

# ---------------------------------------------------------------
# Build the submenu trees.
# ---------------------------------------------------------------
function Build-Submenu {
    param([string]$ClassName, [string]$Mode)  # 'Folder' or 'Files'

    $base = "HKCU:\Software\Classes\$ClassName\shell"
    if (Test-Path "HKCU:\Software\Classes\$ClassName") {
        Remove-Item "HKCU:\Software\Classes\$ClassName" -Recurse -Force
    }
    New-Key $base

    function _add($Id, $Label, $Command, [switch]$MultiSelect) {
        $k = "$base\$Id"
        New-Key $k
        Set-ItemProperty -Path $k -Name "(default)" -Value $Label
        New-ItemProperty -Path $k -Name "MUIVerb" -Value $Label -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $k -Name "Icon"    -Value $exe   -PropertyType String -Force | Out-Null
        if ($MultiSelect) {
            # CRITICAL: must live on each LEAF when using ExtendedSubCommandsKey
            New-ItemProperty -Path $k -Name "MultiSelectModel" -Value "Player" -PropertyType String -Force | Out-Null
        }
        New-Key "$k\command"
        Set-ItemProperty -Path "$k\command" -Name "(default)" -Value $Command
    }

    if ($Mode -eq 'Folder') {
        $q = '"' + $exe + '"'
        _add "01_A4"        "Convert All to A4"                       ($q + ' --size a4 "%V"')
        _add "02_Letter"    "Convert All to Letter"                   ($q + ' --size letter "%V"')
        _add "03_Legal"     "Convert All to Legal"                    ($q + ' --size legal "%V"')
        _add "04_A4_R"      "Convert All to A4 (recursive)"           ($q + ' --size a4 --recursive "%V"')
        _add "05_A4_CW"     "Convert All to A4 (rotate 90 CW)"        ($q + ' --size a4 --rotate 270 "%V"')
        _add "06_A4_CCW"    "Convert All to A4 (rotate 90 CCW)"       ($q + ' --size a4 --rotate 90 "%V"')
        _add "07_A4_180"    "Convert All to A4 (rotate 180)"          ($q + ' --size a4 --rotate 180 "%V"')
        _add "08_A4_NOAR"   "Convert All to A4 (no auto-rotate)"      ($q + ' --size a4 --no-auto-rotate "%V"')
        _add "09_A4_PENCIL" "Convert All to A4 (pencil / paper look)" ($q + ' --size a4 --style pencil --ask-strength "%V"')
    } else {
        # Files: each leaf invokes its shipped launcher .cmd, passing all
        # selected paths via %*. Using cmd.exe /c with a single quoted target
        # (the launcher path) plus %* afterwards keeps quoting trivial:
        #   cmd.exe /c ""C:\...\jpg2pdf-files-a4.cmd" %*"
        $i = 10
        foreach ($v in $verbs) {
            $launcher = Join-Path $binDir ("jpg2pdf-files-" + $v.Id + ".cmd")
            Write-VerbLauncher -Path $launcher -ExePath $exe -VerbArgs $v.Args -Label $v.Label
            $cmd = 'cmd.exe /c ""' + $launcher + '" %*"'
            _add ("{0:D2}_{1}" -f $i, $v.Id) $v.Label $cmd -MultiSelect
            $i++
        }
    }
}

function Register-Parent {
    param([string]$Root, [string]$ClassName)
    $parent = "$Root\Jpg2PdfMenu"
    if (Test-Path $parent) { Remove-Item $parent -Recurse -Force }
    New-Key $parent
    Set-ItemProperty -Path $parent -Name "(default)" -Value "Combine into PDF"
    New-ItemProperty -Path $parent -Name "MUIVerb"  -Value "Combine into PDF" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "Icon"     -Value $exe               -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "SubCommands" -Value "" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "ExtendedSubCommandsKey" -Value $ClassName -PropertyType String -Force | Out-Null
}

Write-Host "[ctx] Registering context menu (HKCU)..." -ForegroundColor Cyan

# Clean up obsolete VBS / PS1 launchers from older installs.
foreach ($stale in @("jpg2pdf-selected-launcher.ps1", "jpg2pdf-selected-launcher.vbs")) {
    $p = Join-Path $binDir $stale
    if (Test-Path $p) { Remove-Item $p -Force -ErrorAction SilentlyContinue }
}

Build-Submenu -ClassName "Jpg2Pdf.FolderMenu" -Mode 'Folder'
Build-Submenu -ClassName "Jpg2Pdf.FilesMenu"  -Mode 'Files'

# Hook into Explorer surfaces.
Register-Parent "HKCU:\Software\Classes\Directory\shell"            "Jpg2Pdf.FolderMenu"
Register-Parent "HKCU:\Software\Classes\Directory\Background\shell" "Jpg2Pdf.FolderMenu"

$exts = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
          ".pdf", ".html", ".htm", ".docx", ".doc")
foreach ($ext in $exts) {
    # Strip legacy file-class entries.
    $legacyRoots = @("HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\Jpg2PdfMenu")
    $oldProgId = (Get-ItemProperty -Path "HKCU:\Software\Classes\$ext" -ErrorAction SilentlyContinue)."(default)"
    if (-not $oldProgId) {
        $oldProgId = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\$ext" -ErrorAction SilentlyContinue)."(default)"
    }
    if ($oldProgId) { $legacyRoots += "HKCU:\Software\Classes\$oldProgId\shell\Jpg2PdfMenu" }
    foreach ($legacyRoot in $legacyRoots) {
        if (Test-Path $legacyRoot) { Remove-Item $legacyRoot -Recurse -Force }
    }

    $progId = (Get-ItemProperty -Path "HKCU:\Software\Classes\$ext" -ErrorAction SilentlyContinue)."(default)"
    if (-not $progId) {
        $progId = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\$ext" -ErrorAction SilentlyContinue)."(default)"
    }
    $targets = @("HKCU:\Software\Classes\SystemFileAssociations\$ext\shell")
    if ($progId) { $targets += "HKCU:\Software\Classes\$progId\shell" }

    foreach ($root in $targets) {
        Register-Parent $root "Jpg2Pdf.FilesMenu"
    }
}

Write-Host "[ctx] Done. Right-click any folder, folder background, or image file." -ForegroundColor Green
Write-Host "[ctx] Selected-file verbs log to %LOCALAPPDATA%\jpg2pdf\context.log and PAUSE on errors." -ForegroundColor Green
Write-Host "[ctx] If entries don't appear immediately, restart Explorer:" -ForegroundColor Yellow
Write-Host "      Stop-Process -Name explorer -Force; Start-Process explorer" -ForegroundColor Yellow
