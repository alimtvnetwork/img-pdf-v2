<#
.SYNOPSIS
  Register Windows Explorer context-menu entries for jpg2pdf.

.PARAMETER ExePath
  Full path to jpg2pdf.exe (or jpg2pdf.cmd shim) used by all menu entries.

.NOTES
  HKCU only - no admin required.

  As of v2.1.2 the grouped menu is:
    Combine into PDF  ->  PDF    ->  A4 / Letter / Legal / A4 + pencil
                          Image  ->  rotations / no-auto-rotate / pencil
                          UI     ->  Open selection / folder in jpg2pdf UI

  Selected-files verbs (file selection in Explorer) are routed through a tiny
  WScript launcher (`jpg2pdf-selected-launcher.vbs`) that runs the queueing
  cmd HIDDEN. Only one visible console is opened later by the runner via
  `start` when it wins the rename race and actually executes jpg2pdf. This
  replaces the previous design where Explorer's per-file invocation produced
  one flashing cmd window per selected file.

  The runner still:
    * Queues each file path to %LOCALAPPDATA%\jpg2pdf\queue\<verb>.lst.
    * Waits for queue size to stabilise (Explorer batches its per-file calls).
    * The first invocation to win an atomic rename runs jpg2pdf; the rest exit.
    * MultiSelectModel=Player on each leaf so the verb appears for big
      selections.
    * Logs to %LOCALAPPDATA%\jpg2pdf\context.log and PAUSES on non-zero exit.

  ASCII-only file: no fancy arrows in labels - Explorer draws the chevron on
  any node that has children.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)] [string]$ExePath
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ExePath)) { Write-Error "Not found: $ExePath"; exit 1 }
$exe    = (Resolve-Path $ExePath).Path
$binDir = Split-Path -Parent $exe
$guiExe = Join-Path $binDir "jpg2pdf-gui.exe"

# ---------------------------------------------------------------
# Grouped verb specs. Each verb has: Id, Label, Args (without --files).
# Files mode (Explorer file selection): verbs operate on selected files.
# ---------------------------------------------------------------
$filesGroups = @(
    @{
        Key    = "PDF"
        Label  = "PDF"
        Verbs  = @(
            @{ Id = "a4";        Label = "Combine into PDF (A4)";                Args = "--size a4" },
            @{ Id = "letter";    Label = "Combine into PDF (Letter)";            Args = "--size letter" },
            @{ Id = "legal";     Label = "Combine into PDF (Legal)";             Args = "--size legal" },
            @{ Id = "a4-pencil"; Label = "Combine into PDF (A4, pencil look)";   Args = "--size a4 --style pencil --ask-strength" }
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
    },
    @{
        Key    = "UI"
        Label  = "UI"
        Verbs  = @(
            @{ Id = "gui"; Label = "Open in jpg2pdf UI..."; Args = "" }
        )
    }
)

# Folder mode (right-click on a folder or folder background): pass "%V".
$folderGroups = @(
    @{
        Key   = "PDF"
        Label = "PDF"
        Verbs = @(
            @{ Id = "a4";        Label = "All to A4";                    Args = "--size a4" },
            @{ Id = "letter";    Label = "All to Letter";                Args = "--size letter" },
            @{ Id = "legal";     Label = "All to Legal";                 Args = "--size legal" },
            @{ Id = "a4-r";      Label = "All to A4 (recursive)";        Args = "--size a4 --recursive" },
            @{ Id = "a4-pencil"; Label = "All to A4 (pencil / paper)";   Args = "--size a4 --style pencil --ask-strength" }
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
    },
    @{
        Key   = "UI"
        Label = "UI"
        Verbs = @(
            @{ Id = "gui"; Label = "Open folder in jpg2pdf UI..."; Args = "--gui" }
        )
    }
)

# ---------------------------------------------------------------
# Hidden WScript launcher. Explorer calls wscript.exe so no cmd window
# appears for each per-file invocation. The VBS then runs the runner cmd
# hidden (intWindowStyle=0). The runner itself uses `start` when it needs
# a visible console for the actual jpg2pdf execution.
# ---------------------------------------------------------------
function Write-SelectedFilesLauncher {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$RunnerPath
    )
    $runnerEsc = $RunnerPath.Replace('"', '""')
    $content = @"
Option Explicit
Dim sh, args, i, quoted, cmdLine
Set sh = CreateObject("WScript.Shell")
args = ""
For i = 0 To WScript.Arguments.Count - 1
  quoted = Replace(WScript.Arguments(i), Chr(34), Chr(34) & Chr(34))
  args = args & " " & Chr(34) & quoted & Chr(34)
Next
cmdLine = "cmd.exe /d /c " & Chr(34) & Chr(34) & "$runnerEsc" & Chr(34) & args & Chr(34)
sh.Run cmdLine, 0, False
"@
    [System.IO.File]::WriteAllText($Path, $content, [System.Text.Encoding]::ASCII)
}

# ---------------------------------------------------------------
# GUI launcher VBS. Called by the runner's gui branch. Uses Shell.Run
# with intWindowStyle=1 (normal visible) so the Tk window is created by
# a process whose parent is wscript (foreground), not the hidden cmd that
# the queueing flow runs under. Without this, the GUI window inherits the
# hidden state of its grand-parent and never becomes visible on top.
# ---------------------------------------------------------------
function Write-GuiLaunchScript {
    param([Parameter(Mandatory=$true)][string]$Path)
    $content = @"
Option Explicit
Dim sh, exePath, queuePath, cmdLine
If WScript.Arguments.Count < 2 Then WScript.Quit 1
exePath   = WScript.Arguments(0)
queuePath = WScript.Arguments(1)
Set sh = CreateObject("WScript.Shell")
cmdLine = Chr(34) & exePath & Chr(34) & " --gui --files-from " & Chr(34) & queuePath & Chr(34)
sh.Run cmdLine, 1, False
"@
    [System.IO.File]::WriteAllText($Path, $content, [System.Text.Encoding]::ASCII)
}

# ---------------------------------------------------------------
# Runner: receives ONE selected file per call (Explorer legacy verbs).
# Appends to a per-verb queue, waits for stability, then atomically wins
# the right to run jpg2pdf. The single winner opens ONE visible console
# via `start`; all losers exit silently.
# ---------------------------------------------------------------
function Write-SelectedFilesRunner {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$ExePath,
        [Parameter(Mandatory=$true)][string]$GuiExePath
    )

    $safeExe    = $ExePath.Replace('"', '')
    $safeGuiExe = $GuiExePath.Replace('"', '')
    $content = @"
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "JPG2PDF_EXE=$safeExe"
set "JPG2PDF_GUI_EXE=$safeGuiExe"
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

if /I "!VERB_ID!"=="gui" (
  >>"!LOG!" echo [%DATE% %TIME%] gui verb=!VERB_ID! queue=!QUEUE!
  set "TARGET_EXE=!JPG2PDF_GUI_EXE!"
  if not exist "!TARGET_EXE!" set "TARGET_EXE=!JPG2PDF_EXE!"
  start "" "!TARGET_EXE!" --gui --files-from "!QUEUE!"
  exit /b 0
)

>>"!LOG!" echo [%DATE% %TIME%] launching visible console verb=!VERB_ID! queue=!QUEUE!
start "jpg2pdf - !VERB_ID!" cmd.exe /d /c "call ""%~f0"" --exec ""!VERB_ID!"" ""!VERB_ARGS!"" ""!QUEUE!"" ""!LOG!"""
exit /b 0

:exec_done

if /I "%~1"=="--exec" goto exec
exit /b 0

:exec
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOG=%~5"
title jpg2pdf !VERB_ID!
echo.
echo [jpg2pdf] Combining selected files (!VERB_ID!)
echo [jpg2pdf] Queue: "!QUEUE!"
echo.
>>"!LOG!" echo [%DATE% %TIME%] exec verb=!VERB_ID! queue=!QUEUE!
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

# The above runner has a broken control-flow goto (:exec_done). Fix by
# emitting a cleaner version that dispatches on the FIRST argument first.
function Write-SelectedFilesRunnerV2 {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$ExePath,
        [Parameter(Mandatory=$true)][string]$GuiExePath
    )

    $safeExe    = $ExePath.Replace('"', '')
    $safeGuiExe = $GuiExePath.Replace('"', '')
    $content = @"
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "JPG2PDF_EXE=$safeExe"
set "JPG2PDF_GUI_EXE=$safeGuiExe"
set "LOG_DIR=%LOCALAPPDATA%\jpg2pdf"
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!" >nul 2>nul
set "LOG=!LOG_DIR!\context.log"
set "QUEUE_DIR=!LOG_DIR!\queue"
if not exist "!QUEUE_DIR!" mkdir "!QUEUE_DIR!" >nul 2>nul

if /I "%~1"=="--exec" goto exec
if /I "%~1"=="--run"  goto run
goto queue

:queue
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
set "LAST_SIZE=-1"
for /L %%I in (1,1,12) do (
  for %%A in ("!QUEUE!") do set "NOW_SIZE=%%~zA"
  if "!NOW_SIZE!"=="!LAST_SIZE!" if %%I GTR 2 goto queue_ready
  set "LAST_SIZE=!NOW_SIZE!"
  rem `timeout` aborts with "Input redirection is not supported" when stdin
  rem is redirected (which happens under wscript-launched hidden cmd). Use
  rem `ping` for a portable sub-second sleep that works in hidden mode.
  ping -n 2 127.0.0.1 >nul 2>nul
)
:queue_ready
set "WORK_NAME=!VERB_ID!-work-%RANDOM%%RANDOM%.lst"
ren "!QUEUE!" "!WORK_NAME!" >nul 2>nul
if errorlevel 1 exit /b 0
set "QUEUE=!QUEUE_DIR!\!WORK_NAME!"

if /I "!VERB_ID!"=="gui" (
  >>"!LOG!" echo [%DATE% %TIME%] gui verb=!VERB_ID! queue=!QUEUE!
  set "TARGET_EXE=!JPG2PDF_GUI_EXE!"
  if not exist "!TARGET_EXE!" set "TARGET_EXE=!JPG2PDF_EXE!"
  rem Use the gui-launch.vbs sibling so the new process is created by
  rem wscript with intWindowStyle=1 (normal visible window). Without this
  rem the Tk window inherits the hidden state of our parent cmd and never
  rem becomes visible on some Windows builds.
  set "GUI_LAUNCH=%~dp0jpg2pdf-gui-launch.vbs"
  if exist "!GUI_LAUNCH!" (
    wscript.exe "!GUI_LAUNCH!" "!TARGET_EXE!" "!QUEUE!"
  ) else (
    start "" "!TARGET_EXE!" --gui --files-from "!QUEUE!"
  )
  exit /b 0
)

>>"!LOG!" echo [%DATE% %TIME%] launching visible console verb=!VERB_ID! queue=!QUEUE!
start "jpg2pdf - !VERB_ID!" cmd.exe /d /c "call ""%~f0"" --exec ""!VERB_ID!"" ""!VERB_ARGS!"" ""!QUEUE!"" ""!LOG!"""
exit /b 0

:exec
set "VERB_ID=%~2"
set "VERB_ARGS=%~3"
set "QUEUE=%~4"
set "LOG=%~5"
title jpg2pdf !VERB_ID!
echo.
echo [jpg2pdf] Combining selected files (!VERB_ID!)
echo [jpg2pdf] Queue: "!QUEUE!"
echo.
>>"!LOG!" echo [%DATE% %TIME%] exec verb=!VERB_ID! queue=!QUEUE!
call "!JPG2PDF_EXE!" !VERB_ARGS! --files-from "!QUEUE!"
set "JPG2PDF_CODE=!ERRORLEVEL!"
>>"!LOG!" echo [%DATE% %TIME%] exit=!JPG2PDF_CODE! verb=!VERB_ID!
if not "!JPG2PDF_CODE!"=="0" (
  echo.
  echo [jpg2pdf] FAILED with exit code !JPG2PDF_CODE!.
  echo [jpg2pdf] Log: "!LOG!"
)
echo.
echo [jpg2pdf] Done. Press any key to close this window.
pause >nul
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
        [Parameter(Mandatory=$true)][string]$LauncherPath,
        [Parameter(Mandatory=$true)][string]$VerbId,
        [Parameter(Mandatory=$true)][string]$VerbArgs
    )
    $id = (Quote-CmdArg $VerbId)
    $a  = (Quote-CmdArg $VerbArgs)
    return 'wscript.exe "' + $LauncherPath + '" ' + $id + ' ' + $a + ' "%1"'
}

function New-Key($path) {
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
}

function Set-DefaultValue($path, $value) {
    Remove-ItemProperty -Path $path -Name "(default)" -ErrorAction SilentlyContinue
    Set-Item -Path $path -Value $value
}

function Remove-MenuParent($shellRoot) {
    $p = "$shellRoot\Jpg2PdfMenu"
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}

function Remove-LegacyMenus {
    foreach ($root in @(
        "HKCU:\Software\Classes\*\shell",
        "HKCU:\Software\Classes\AllFilesystemObjects\shell",
        "HKCU:\Software\Classes\Directory\shell",
        "HKCU:\Software\Classes\Directory\Background\shell"
    )) {
        Remove-MenuParent $root
    }

    foreach ($cls in @(
        "Jpg2Pdf.FolderMenu",
        "Jpg2Pdf.FolderMenu.PDF",
        "Jpg2Pdf.FolderMenu.Image",
        "Jpg2Pdf.FolderMenu.UI",
        "Jpg2Pdf.FilesMenu",
        "Jpg2Pdf.FilesMenu.PDF",
        "Jpg2Pdf.FilesMenu.Image",
        "Jpg2Pdf.FilesMenu.UI"
    )) {
        $p = "HKCU:\Software\Classes\$cls"
        if (Test-Path $p) { Remove-Item $p -Recurse -Force }
    }
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

function Build-GroupedSubmenu {
    param(
        [Parameter(Mandatory=$true)][string]$RootClass,
        [Parameter(Mandatory=$true)][ValidateSet('Folder','Files')][string]$Mode
    )

    foreach ($cls in @($RootClass, "$RootClass.PDF", "$RootClass.Image", "$RootClass.UI")) {
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

        $containerId = ("{0:D2}_{1}" -f $gi, $g.Key)
        Add-GroupContainer -BaseShell $rootShell -Id $containerId -Label $g.Label -ChildClassName $childClass

        $vi = 1
        foreach ($v in $g.Verbs) {
            $leafId = ("{0:D2}_{1}" -f $vi, $v.Id)
            $isGui  = ($v.Id -eq "gui")
            if ($Mode -eq 'Folder') {
                if ($isGui) {
                    $targetExe = if (Test-Path $guiExe) { $guiExe } else { $exe }
                    $q = '"' + $targetExe + '"'
                    $cmd = $q + ' --gui "%V"'
                } else {
                    $q = '"' + $exe + '"'
                    $cmd = $q + ' ' + $v.Args + ' "%V"'
                }
                Add-LeafVerb -BaseShell $childShell -Id $leafId -Label $v.Label -Command $cmd
            } else {
                $cmd = New-SelectedFilesCommand -LauncherPath $selectedLauncher -VerbId $v.Id -VerbArgs $v.Args
                Add-LeafVerb -BaseShell $childShell -Id $leafId -Label $v.Label -Command $cmd -MultiSelect
            }
            $vi++
        }
        $gi++
    }
}

function Register-Parent {
    param([string]$Root, [string]$ClassName)
    Remove-MenuParent $Root
    $parent = "$Root\Jpg2PdfMenu"
    New-Key $parent
    Set-DefaultValue $parent "Combine into PDF"
    New-ItemProperty -Path $parent -Name "MUIVerb"  -Value "Combine into PDF" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "Icon"     -Value $exe               -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "SubCommands" -Value "" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $parent -Name "ExtendedSubCommandsKey" -Value $ClassName -PropertyType String -Force | Out-Null
}

Write-Host "[ctx] Registering context menu (HKCU)..." -ForegroundColor Cyan
Write-Host "[ctx] Groups: PDF (A4/Letter/Legal/+pencil) | Image (rotations/pencil) | UI" -ForegroundColor Cyan
Write-Host "[ctx] Selected-file verbs run hidden via WScript; one visible console for the actual conversion." -ForegroundColor Cyan

Remove-LegacyMenus

# Clean up obsolete launcher files from older installs (we keep our new vbs).
foreach ($stale in @("jpg2pdf-files-*.cmd")) {
    $p = Join-Path $binDir $stale
    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $p -Force -ErrorAction SilentlyContinue
}

$selectedRunner   = Join-Path $binDir "jpg2pdf-selected-runner.cmd"
$selectedLauncher = Join-Path $binDir "jpg2pdf-selected-launcher.vbs"
$guiLaunch        = Join-Path $binDir "jpg2pdf-gui-launch.vbs"
Write-SelectedFilesRunnerV2 -Path $selectedRunner -ExePath $exe -GuiExePath $guiExe
Write-SelectedFilesLauncher -Path $selectedLauncher -RunnerPath $selectedRunner
Write-GuiLaunchScript       -Path $guiLaunch

Build-GroupedSubmenu -RootClass "Jpg2Pdf.FolderMenu" -Mode 'Folder'
Build-GroupedSubmenu -RootClass "Jpg2Pdf.FilesMenu"  -Mode 'Files'

Register-Parent "HKCU:\Software\Classes\Directory\shell"            "Jpg2Pdf.FolderMenu"
Register-Parent "HKCU:\Software\Classes\Directory\Background\shell" "Jpg2Pdf.FolderMenu"

$exts = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff",
          ".pdf", ".html", ".htm", ".docx", ".doc")
foreach ($ext in $exts) {
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
Write-Host "[ctx] No more multiple flashing consoles - per-file calls are hidden, one window opens for the run." -ForegroundColor Green
Write-Host "[ctx] If entries don't appear immediately, restart Explorer:" -ForegroundColor Yellow
Write-Host "      Stop-Process -Name explorer -Force; Start-Process explorer" -ForegroundColor Yellow
