<#
.SYNOPSIS
  One-shot bootstrap for jpg2pdf on Windows:
    pull repo → install Python deps → compile jpg2pdf.exe →
    add to User PATH → register Explorer context menu.

.USAGE
  .\run.ps1
  .\run.ps1 -RepoUrl https://github.com/<you>/<repo>.git
  .\run.ps1 -NoCompile           # use .cmd shim instead of compiled .exe
  .\run.ps1 -NoContextMenu       # skip Explorer registry entries
  .\run.ps1 -Unregister          # remove context menu and exit
  .\run.ps1 -Force               # rebuild .exe even if it already exists

.NOTES
  Open a NEW terminal after install so PATH changes take effect.
#>
[CmdletBinding()]
param(
    [string]$RepoUrl     = "https://github.com/CHANGE_ME/jpg2pdf.git",
    [string]$InstallDir  = (Join-Path $HOME "Tools\jpg2pdf"),
    [string]$Branch      = "main",
    [switch]$NoCompile,
    [switch]$NoContextMenu,
    [switch]$Unregister,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
function Info($m){ Write-Host "[jpg2pdf] $m" -ForegroundColor Cyan }
function Warn($m){ Write-Host "[jpg2pdf] $m" -ForegroundColor Yellow }
function Die ($m){ Write-Host "[jpg2pdf] $m" -ForegroundColor Red; exit 1 }

function Get-Python {
    foreach ($n in @("python","py")) {
        $c = Get-Command $n -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    return $null
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path","User")
}

# ---------- Locate repo (local checkout preferred) ----------
$localRepo = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "tools\jpg2pdf\src\jpg2pdf.py"))) {
    $localRepo = $PSScriptRoot
    $InstallDir = $localRepo
}

# ---------- -Unregister short-circuit ----------
if ($Unregister) {
    $unreg = Join-Path $InstallDir "tools\jpg2pdf\scripts\unregister-context-menu.ps1"
    if (-not (Test-Path $unreg)) { Die "Missing $unreg" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $unreg
    exit $LASTEXITCODE
}

# ---------- 1. Python ----------
$py = Get-Python
if (-not $py) {
    Info "Python not found. Installing via winget..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Die "winget unavailable. Install Python 3 from https://python.org and re-run."
    }
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $py = Get-Python
    if (-not $py) { Die "Python installed but not on PATH. Open a new terminal and re-run." }
}
Info "Python: $py"

# ---------- 2. Git ----------
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Info "Git not found. Installing..."
    winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $git = Get-Command git -ErrorAction SilentlyContinue
}

# ---------- 3. Pull / clone repo ----------
if ($localRepo) {
    Info "Using local repo at: $localRepo"
    if ($git -and (Test-Path (Join-Path $localRepo ".git"))) {
        Info "git pull..."
        try { git -C $localRepo pull --ff-only } catch { Warn "git pull failed (continuing): $_" }
    }
} elseif ($git) {
    if (Test-Path (Join-Path $InstallDir ".git")) {
        Info "Updating repo in $InstallDir ..."
        git -C $InstallDir fetch --depth=1 origin $Branch
        git -C $InstallDir reset --hard "origin/$Branch"
    } else {
        Info "Cloning $RepoUrl -> $InstallDir ..."
        New-Item -ItemType Directory -Force -Path (Split-Path $InstallDir) | Out-Null
        git clone --depth=1 --branch $Branch $RepoUrl $InstallDir
    }
} else {
    Die "Git unavailable and no local repo. Install Git or run from a cloned copy."
}

$srcScript = Join-Path $InstallDir "tools\jpg2pdf\src\jpg2pdf.py"
$reqsFile  = Join-Path $InstallDir "tools\jpg2pdf\requirements.txt"
$regScript = Join-Path $InstallDir "tools\jpg2pdf\scripts\register-context-menu.ps1"
if (-not (Test-Path $srcScript)) { Die "Missing $srcScript" }

# ---------- 4. Python deps ----------
Info "Installing Python dependencies..."
& $py -m pip install --user --upgrade --quiet -r $reqsFile
if ($LASTEXITCODE -ne 0) { Die "pip install failed." }

# ---------- 5. Compile (PyInstaller) or shim ----------
$binDir = Join-Path $HOME "Tools\bin"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
$exePath  = Join-Path $binDir "jpg2pdf.exe"
$shimPath = Join-Path $binDir "jpg2pdf.cmd"
$entryPath = $null

if ($NoCompile) {
    Info "Writing .cmd shim (no compile)..."
    if (Test-Path $exePath) { Remove-Item $exePath -Force }
    @"
@echo off
"$py" "$srcScript" %*
"@ | Set-Content -Path $shimPath -Encoding ASCII
    $entryPath = $shimPath
    Info "Shim: $shimPath"
} else {
    if ((Test-Path $exePath) -and -not $Force) {
        Info "jpg2pdf.exe already exists. Use -Force to rebuild."
    } else {
        Info "Installing PyInstaller..."
        & $py -m pip install --user --upgrade --quiet pyinstaller
        if ($LASTEXITCODE -ne 0) { Die "Failed to install PyInstaller." }

        $buildDir = Join-Path $env:TEMP "jpg2pdf_build"
        $distDir  = Join-Path $env:TEMP "jpg2pdf_dist"
        $workDir  = Join-Path $env:TEMP "jpg2pdf_work"
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $buildDir,$distDir,$workDir

        Info "Compiling jpg2pdf.exe (PyInstaller, ~1 min)..."
        & $py -m PyInstaller --onefile --name jpg2pdf --console `
            --distpath $distDir --workpath $workDir --specpath $buildDir `
            $srcScript
        if ($LASTEXITCODE -ne 0) { Die "PyInstaller build failed." }
        Copy-Item -Force (Join-Path $distDir "jpg2pdf.exe") $exePath
        if (Test-Path $shimPath) { Remove-Item $shimPath -Force }
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $buildDir,$distDir,$workDir
        Info "Built: $exePath"
    }
    $entryPath = $exePath
}

# ---------- 6. Persist on User PATH (safe update) ----------
function Update-UserPath {
    param([Parameter(Mandatory=$true)][string]$Dir)

    # 1. Confirm the folder actually exists before touching PATH.
    if (-not (Test-Path -LiteralPath $Dir -PathType Container)) {
        Warn "Bin folder does not exist, skipping PATH update: $Dir"
        return $false
    }
    $resolved = (Resolve-Path -LiteralPath $Dir).Path.TrimEnd('\')

    # 2. Read current User PATH (may be $null on a fresh profile).
    $current = [Environment]::GetEnvironmentVariable("Path","User")
    if (-not $current) { $current = "" }

    # 3. Split, trim, drop empties, dedupe case-insensitively, normalise trailing slashes.
    $cmp = [System.StringComparer]::OrdinalIgnoreCase
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' $cmp
    $cleaned = New-Object 'System.Collections.Generic.List[string]'
    foreach ($entry in $current.Split(';')) {
        $e = $entry.Trim().TrimEnd('\')
        if (-not $e) { continue }
        if ($seen.Add($e)) { [void]$cleaned.Add($e) }
    }
    $alreadyPresent = $seen.Contains($resolved)
    $rawCount = ($current.Split(';') | Where-Object { $_.Trim() }).Count
    $hadDuplicates = ($cleaned.Count -lt $rawCount)

    if ($alreadyPresent -and -not $hadDuplicates) {
        Info "$resolved already on User PATH (no changes)."
    }
    else {
        if (-not $alreadyPresent) { [void]$cleaned.Add($resolved) }
        $newPath = ($cleaned -join ';')

        # Back up the previous value so the user can recover if needed.
        try {
            [Environment]::SetEnvironmentVariable("PathBackup_jpg2pdf", $current, "User")
        } catch { Warn "Could not write PATH backup: $_" }

        try {
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        } catch {
            Warn "Failed to update User PATH: $_"
            return $false
        }

        if ($alreadyPresent) {
            Info "User PATH cleaned (removed duplicates). $resolved already present."
        } else {
            Info "Added $resolved to User PATH (persistent). Backup in env var 'PathBackup_jpg2pdf'."
        }
    }

    # Update current session only if missing.
    $sessionEntries = $env:Path.Split(';') | ForEach-Object { $_.Trim().TrimEnd('\') }
    if ($sessionEntries -notcontains $resolved) {
        $env:Path = "$($env:Path.TrimEnd(';'));$resolved"
    }
    return $true
}

[void](Update-UserPath -Dir $binDir)

# ---------- 7. Register Explorer context menu ----------
if (-not $NoContextMenu) {
    if (-not (Test-Path $regScript)) {
        Warn "Missing $regScript — skipping context-menu registration."
    } else {
        Info "Registering Explorer context menu..."
        & powershell -NoProfile -ExecutionPolicy Bypass -File $regScript -ExePath $entryPath
    }
}

Info "Done! Open a NEW terminal, then try:"
Write-Host "    jpg2pdf `"C:\Photos`" --size a4" -ForegroundColor Green
Write-Host "    jpg2pdf . --size letter --fit cover --out album.pdf" -ForegroundColor Green
Write-Host "    jpg2pdf . --size legal --orientation landscape --recursive" -ForegroundColor Green
Write-Host ""
Info "Right-click a folder, folder background, or selected images:"
Write-Host "    Images to PDF >  Convert All / Selected to A4 / Letter / Legal" -ForegroundColor Green
