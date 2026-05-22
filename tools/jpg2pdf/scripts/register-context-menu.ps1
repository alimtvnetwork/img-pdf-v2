<#
.SYNOPSIS
  Register Windows Explorer context-menu entries for jpg2pdf.

.PARAMETER ExePath
  Full path to jpg2pdf.exe (or jpg2pdf.cmd shim) used by all menu entries.

.NOTES
  HKCU only - no admin required.
  As of Step 15 the menu is grouped:
    Combine into PDF  ->  PDF      ->  paper-size leaves (A4, Letter, Legal, ...)
                          Image    ->  image-specific leaves (rotations, pencil, ...)
  ASCII-only file: no fancy arrows in labels - Explorer draws the chevron on
  any node that has children.

  Selected-files verbs still use one visible batch runner for reliability:
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
# Grouped verb specs. Each verb has: Id, Label, Args (without --files).
# Files mode (Explorer file selection): verbs operate on selected files.
# ---------------------------------------------------------------
$filesGroups = @(
    @{
        Key    = "PDF"
        Label  = "PDF"
        Verbs  = @(
            @{ Id = "a4";     Label = "Combine into PDF (A4)";     Args = "--size a4" },
            @{ Id = "letter"; Label = "Combine into PDF (Letter)"; Args = "--size letter" },
            @{ Id = "legal";  Label = "Combine into PDF (Legal)";  Args = "--size legal" }
        )
    },
    @{
        Key    = "Image"
        Label  = "Image"
        Verbs  = @(
            @{ Id = "a4-cw";     Label = "A4, rotate 90 CW";        Args = "--size a4 --rotate 270" },
            @{ Id = "a4-ccw";    Label = "A4, rotate 90 CCW";       Args = "--size a4 --rotate 90" },
            @{ Id = "a4-180";    Label = "A4, rotate 180";          Args = "--size a4 --rotate 180" },
            @{ Id = "a4-noar";   Label = "A4, no auto-rotate";      Args = "--size a4 --no-auto-rotate" },
            @{ Id = "a4-pencil"; Label = "A4, pencil / paper look"; Args = "--size a4 --style pencil --ask-strength" }
        )
    }
)

# Folder mode (right-click on a folder or folder background): pass "%V".
$folderGroups = @(
    @{
        Key   = "PDF"
        Label = "PDF"
        Verbs = @(
            @{ Id = "a4";       Label = "All to A4";              Args = "--size a4" },
            @{ Id = "letter";   Label = "All to Letter";          Args = "--size letter" },
            @{ Id = "legal";    Label = "All to Legal";           Args = "--size legal" },
            @{ Id = "a4-r";     Label = "All to A4 (recursive)";  Args = "--size a4 --recursive" }
        )
    },
    @{
        Key   = "Image"
        Label = "Image"
        Verbs = @(
            @{ Id = "a4-cw";     Label = "All to A4 (rotate 90 CW)";     Args = "--size a4 --rotate 270" },
            @{ Id = "a4-ccw";    Label = "All to A4 (rotate 90 CCW)";    Args = "--size a4 --rotate 90" },
            @{ Id = "a4-180";    Label = "All to A4 (rotate 180)";       Args = "--size a4 --rotate 180" },
            @{ Id = "a4-noar";   Label = "All to A4 (no auto-rotate)";   Args = "--size a4 --no-auto-rotate" },
            @{ Id = "a4-pencil"; Label = "All to A4 (pencil / paper)";   Args = "--size a4 --style pencil --ask-strength" }
        )
    }
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

>>"!LOG!" echo [%DATE% %TIME%] selected verb=!VERB_ID! file=!SELECTED_FILE!
>>"!QUEUE!" echo(!SELECTED_FILE!

call "%~f0" --run "!VERB_ID!" "!VERB_ARGS!" "!QUEUE!" "!LOG!"
exit /b !ERRORLEVEL!

:run
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOG=%~5"

title jpg2pdf selected !VERB_ID!
set "LAST_SIZE=-1"
for /L %%I in (1,1,10) do (
  for %%A in ("!QUEUE!") do set "NOW_SIZE=%%~zA"
  if "!NOW_SIZE!"=="!LAST_SIZE!" goto queue_ready
  set "LAST_SIZE=!NOW_SIZE!"
  timeout /t 1 /nobreak >nul 2>nul
)
:queue_ready
set "WORK_NAME=!VERB_ID!-work-%RANDOM%%RANDOM%.lst"
ren "!QUEUE!" "!WORK_NAME!" >nul 2>nul
if errorlevel 1 exit /b 0
set "QUEUE=!QUEUE_DIR!\!WORK_NAME!"
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
        [Parameter(Mandatory=$true)][string]$VerbArgs
    )
    $id = (Quote-CmdArg $VerbId)
    $a  = (Quote-CmdArg $VerbArgs)
    return 'cmd.exe /d /c ""' + $RunnerPath + '" ' + $id + ' ' + $a + ' "%1""'
}

function New-Key($path) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
}

function Set-DefaultValue($path, $value) {
    Remove-ItemProperty -Path $path -Name "(default)" -ErrorAction SilentlyContinue
    Set-Item -Path $path -Value $value
}

function Add-LeafVerb {
    param(
        [Parameter(Mandatory=$true)][string]$BaseShell,
        [Parameter(Mandatory=$true)][string]$Id,
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$Command,
        [switch]$MultiSelect
    )
    $k = "$BaseShell\$Id"
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

function Add-GroupContainer {
    param(
        [Parameter(Mandatory=$true)][string]$BaseShell,
        [Parameter(Mandatory=$true)][string]$Id,
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$ChildClassName
    )
    $k = "$BaseShell\$Id"
    New-Key $k
    Set-DefaultValue $k $Label
    New-ItemProperty -Path $k -Name "MUIVerb"               -Value $Label          -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $k -Name "Icon"                  -Value $exe            -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $k -Name "SubCommands"           -Value ""              -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $k -Name "ExtendedSubCommandsKey" -Value $ChildClassName -PropertyType String -Force | Out-Null
}

# ---------------------------------------------------------------
# Build the submenu trees with PDF / Image grouping.
# Tree shape per Mode:
#   HKCU:\Software\Classes\<RootClass>\shell\01_PDF   (group container)
#   HKCU:\Software\Classes\<RootClass>\shell\02_Image (group container)
#   HKCU:\Software\Classes\<RootClass>.PDF\shell\<verb leaves>
#   HKCU:\Software\Classes\<RootClass>.Image\shell\<verb leaves>
# ---------------------------------------------------------------
function Build-GroupedSubmenu {
    param(
        [Parameter(Mandatory=$true)][string]$RootClass,
        [Parameter(Mandatory=$true)][ValidateSet('Folder','Files')][string]$Mode
    )

    # Clean root + group classes from any previous install.
    foreach ($cls in @($RootClass, "$RootClass.PDF", "$RootClass.Image")) {
        $p = "HKCU:\Software\Classes\$cls"
        if (Test-Path $p) { Remove-Item $p -Recurse -Force }
    }

    $rootShell = "HKCU:\Software\Classes\$RootClass\shell"
    New-Key $rootShell

    $groups = if ($Mode -eq 'Folder') { $folderGroups } else { $filesGroups }

    $gi = 1
    foreach ($g in $groups) {
        $childClass = "$RootClass.$($g.Key)"
        $childShell = "HKCU:\Software\Classes\$childClass\shell"
        New-Key $childShell

        # Container entry on root.
        $containerId = ("{0:D2}_{1}" -f $gi, $g.Key)
        Add-GroupContainer -BaseShell $rootShell -Id $containerId -Label $g.Label -ChildClassName $childClass

        # Leaves inside the group's child class.
        $vi = 1
        foreach ($v in $g.Verbs) {
            $leafId = ("{0:D2}_{1}" -f $vi, $v.Id)
            if ($Mode -eq 'Folder') {
                $q = '"' + $exe + '"'
                $cmd = $q + ' ' + $v.Args + ' "%V"'
                Add-LeafVerb -BaseShell $childShell -Id $leafId -Label $v.Label -Command $cmd
            } else {
                $cmd = New-SelectedFilesCommand -RunnerPath $selectedRunner -VerbId $v.Id -VerbArgs $v.Args
                Add-LeafVerb -BaseShell $childShell -Id $leafId -Label $v.Label -Command $cmd -MultiSelect
            }
            $vi++
        }
        $gi++
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
Write-Host "[ctx] Menu is grouped: Combine into PDF > PDF | Image > leaves." -ForegroundColor Cyan
Write-Host "[ctx] Selected-file verbs use a visible queued batch runner." -ForegroundColor Cyan

# Clean up obsolete launcher files from older installs.
foreach ($stale in @("jpg2pdf-selected-launcher.ps1", "jpg2pdf-selected-launcher.vbs", "jpg2pdf-files-*.cmd")) {
    $p = Join-Path $binDir $stale
    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $p -Force -ErrorAction SilentlyContinue
}

$selectedRunner = Join-Path $binDir "jpg2pdf-selected-runner.cmd"
Write-SelectedFilesRunner -Path $selectedRunner -ExePath $exe

Build-GroupedSubmenu -RootClass "Jpg2Pdf.FolderMenu" -Mode 'Folder'
Build-GroupedSubmenu -RootClass "Jpg2Pdf.FilesMenu"  -Mode 'Files'

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
Write-Host "[ctx] Selected-file verbs queue to %LOCALAPPDATA%\jpg2pdf\queue, log to context.log, and PAUSE on errors." -ForegroundColor Green
Write-Host "[ctx] If entries don't appear immediately, restart Explorer:" -ForegroundColor Yellow
Write-Host "      Stop-Process -Name explorer -Force; Start-Process explorer" -ForegroundColor Yellow
