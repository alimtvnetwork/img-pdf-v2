<#
.SYNOPSIS
  Register Windows Explorer context-menu entries for jpg2pdf.

.PARAMETER ExePath
  Full path to jpg2pdf.exe (or jpg2pdf.cmd shim) used by all menu entries.

.NOTES
  HKCU only - no admin required.
  Selected-files verbs use one visible batch runner for maximum reliability:
    * No hidden VBS/PowerShell launcher chain.
    * MultiSelectModel=Player on each leaf so the verb appears for large
      selections.
    * Explorer legacy verbs invoke once per file, so the runner queues those
      per-file calls briefly and then runs jpg2pdf once with --files-from.
    * Each command logs to %LOCALAPPDATA%\jpg2pdf\context.log and PAUSES on
      non-zero exit so users can read errors instead of seeing nothing.
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
# Build the selected-files batch runner and registry command.
# IMPORTANT: Explorer only runs the unnamed/default value under `command`.
# Do not write a literal "(default)" named value; use Set-Item -Value.
# ---------------------------------------------------------------
function Write-SelectedFilesRunner {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$ExePath
    )

    $safeExe = $ExePath.Replace('"', '')
    $content = @"
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "JPG2PDF_EXE=$safeExe"
set "LOG_DIR=%LOCALAPPDATA%\jpg2pdf"
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!" >nul 2>nul
set "LOG=!LOG_DIR!\context.log"
set "QUEUE_DIR=!LOG_DIR!\queue"
if not exist "!QUEUE_DIR!" mkdir "!QUEUE_DIR!" >nul 2>nul

if /I "%~1"=="--run" goto run

set "VERB_ID=%~1"
set "VERB_ARGS=%~2"
set "SELECTED_FILE=%~3"
if "!VERB_ID!"=="" exit /b 1
if "!SELECTED_FILE!"=="" exit /b 1

set "QUEUE=!QUEUE_DIR!\!VERB_ID!.lst"
set "LOCK=!QUEUE_DIR!\!VERB_ID!.lock"

>>"!LOG!" echo [%DATE% %TIME%] selected verb=!VERB_ID! file=!SELECTED_FILE!
>>"!QUEUE!" echo(!SELECTED_FILE!

mkdir "!LOCK!" >nul 2>nul
if errorlevel 1 exit /b 0

start "jpg2pdf selected !VERB_ID!" "%ComSpec%" /v:on /d /c ""%~f0" --run "!VERB_ID!" "!VERB_ARGS!" "!QUEUE!" "!LOCK!" "!LOG!""
exit /b 0

:run
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOCK=%~5"
set "LOG=%~6"

title jpg2pdf selected !VERB_ID!
timeout /t 2 /nobreak >nul 2>nul
echo.
echo [jpg2pdf] Combining selected files (!VERB_ID!)
echo [jpg2pdf] Queue: "!QUEUE!"
echo.
>>"!LOG!" echo [%DATE% %TIME%] run verb=!VERB_ID! queue=!QUEUE!
call "!JPG2PDF_EXE!" !VERB_ARGS! --files-from "!QUEUE!"
set "JPG2PDF_CODE=!ERRORLEVEL!"
>>"!LOG!" echo [%DATE% %TIME%] exit=!JPG2PDF_CODE! verb=!VERB_ID!
if not "!JPG2PDF_CODE!"=="0" (
  echo.
  echo [jpg2pdf] FAILED with exit code !JPG2PDF_CODE!.
  echo [jpg2pdf] Log: "!LOG!"
  pause
)
del "!QUEUE!" >nul 2>nul
rmdir "!LOCK!" >nul 2>nul
exit /b !JPG2PDF_CODE!
"@

    [System.IO.File]::WriteAllText($Path, $content, [System.Text.Encoding]::ASCII)
}

function Quote-CmdArg($value) {
    return '"' + ([string]$value).Replace('"', '""') + '"'
}

function New-SelectedFilesCommand {
    param(
        [Parameter(Mandatory=$true)][string]$RunnerPath,
        [Parameter(Mandatory=$true)][string]$VerbId,
        [Parameter(Mandatory=$true)][string]$VerbArgs,
        [Parameter(Mandatory=$true)][string]$Label
    )

    # Legacy static verbs get one %1 per selected file; %* is not a reliable
    # all-selected-files placeholder here. The runner batches those calls.
    $runner = (Quote-CmdArg $RunnerPath)
    $id = (Quote-CmdArg $VerbId)
    $args = (Quote-CmdArg $VerbArgs)
    return 'cmd.exe /d /c ""' + $RunnerPath + '" ' + $id + ' ' + $args + ' "%1""'
}

function New-Key($path) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
}

function Set-DefaultValue($path, $value) {
    Remove-ItemProperty -Path $path -Name "(default)" -ErrorAction SilentlyContinue
    Set-Item -Path $path -Value $value
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
        Set-DefaultValue $k $Label
        New-ItemProperty -Path $k -Name "MUIVerb" -Value $Label -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $k -Name "Icon"    -Value $exe   -PropertyType String -Force | Out-Null
        if ($MultiSelect) {
            # CRITICAL: must live on each LEAF when using ExtendedSubCommandsKey
            New-ItemProperty -Path $k -Name "MultiSelectModel" -Value "Player" -PropertyType String -Force | Out-Null
        }
        New-Key "$k\command"
        Set-DefaultValue "$k\command" $Command
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
        # Files: each leaf invokes cmd.exe directly, visibly, passing all
        # selected paths via %*. This avoids the previous hidden launcher chain
        # and also avoids relying on generated .cmd files being unblocked.
        $i = 10
        foreach ($v in $verbs) {
            $cmd = New-SelectedFilesCommand -ExePath $exe -VerbArgs $v.Args -Label $v.Label
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
    Set-DefaultValue $parent "Combine into PDF"
    New-ItemProperty -Path $parent -Name "MUIVerb"  -Value "Combine into PDF" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "Icon"     -Value $exe               -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "SubCommands" -Value "" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "ExtendedSubCommandsKey" -Value $ClassName -PropertyType String -Force | Out-Null
}

Write-Host "[ctx] Registering context menu (HKCU)..." -ForegroundColor Cyan
Write-Host "[ctx] Selected-file verbs use direct visible cmd.exe commands." -ForegroundColor Cyan

# Clean up obsolete launcher files from older installs.
foreach ($stale in @("jpg2pdf-selected-launcher.ps1", "jpg2pdf-selected-launcher.vbs", "jpg2pdf-files-*.cmd")) {
    $p = Join-Path $binDir $stale
    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $p -Force -ErrorAction SilentlyContinue
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
