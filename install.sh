#!/usr/bin/env bash
# One-liner installer for jpg2pdf on Linux & macOS.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.sh | bash
#
#   # Pin a specific version:
#   curl -fsSL https://raw.githubusercontent.com/alimtvnetwork/img-pdf-v2/main/install.sh | JPG2PDF_VERSION=v1.5.0 bash
#
#   # Install elsewhere (default: $HOME/.local/bin):
#   curl -fsSL https://.../install.sh | JPG2PDF_PREFIX=$HOME/bin bash
#
# What it does:
#   1. Detects OS + arch.
#   2. Resolves the latest GitHub Release (or $JPG2PDF_VERSION).
#   3. If no release is available, falls back to the latest successful main-branch artifact.
#   4. If no binary exists, falls back to a Python source install.
#   5. Installs into $JPG2PDF_PREFIX (default $HOME/.local/bin), chmod +x, and reports next steps.

if (set -o pipefail) 2>/dev/null; then set -o pipefail; fi
set -e

PWD_SAFE="$(pwd 2>/dev/null || printf /tmp)"
TMP_DIR="${TMPDIR:-/tmp}"
if [ ! -d "$TMP_DIR" ]; then TMP_DIR="/tmp"; fi
if [ ! -d "$TMP_DIR" ]; then TMP_DIR="$PWD_SAFE"; fi
HOME_DIR="${HOME:-$PWD_SAFE}"
DEBUG="${JPG2PDF_DEBUG:-0}"
SHOW_HELP=0
for _arg in "$@"; do
  case "$_arg" in
    --debug|--verbose|-d|-v) DEBUG=1 ;;
    --help|-h) SHOW_HELP=1 ;;
  esac
done
if [ "$SHOW_HELP" = "1" ]; then
  printf '%s\n' 'Usage: install.sh [--debug] [--help]'
  printf '%s\n' 'Env: JPG2PDF_VERSION=vX.Y.Z JPG2PDF_PREFIX=$HOME/bin JPG2PDF_REPO=owner/repo'
  exit 0
fi

LOG_FILE="${JPG2PDF_LOG:-$TMP_DIR/jpg2pdf-install-$(date +%Y%m%d-%H%M%S)-$$.log}"
: > "$LOG_FILE" 2>/dev/null || LOG_FILE=""
SAFE_DIE_MARKER="$TMP_DIR/jpg2pdf-install-die-$$.flag"
rm -f "$SAFE_DIE_MARKER" 2>/dev/null || true
CRASH_REPORTS=""
CRASH_REPORT_FILE="$TMP_DIR/jpg2pdf-install-crash-$$.log"
rm -f "$CRASH_REPORT_FILE" 2>/dev/null || true
CRASH_REPORT_WRITTEN=0

_log() { [ -n "$LOG_FILE" ] && printf '%s %s\n' "$(date +%H:%M:%S)" "$*" >> "$LOG_FILE" 2>/dev/null || true; }
info() { _log "INFO  $*"; printf '\033[36m[jpg2pdf]\033[0m %s\n' "$*"; }
warn() { _log "WARN  $*"; printf '\033[33m[jpg2pdf]\033[0m %s\n' "$*" >&2; }
debug(){ _log "DEBUG $*"; [ "$DEBUG" = "1" ] && printf '\033[35m[jpg2pdf:debug]\033[0m %s\n' "$*" >&2 || true; }
add_crash_report() {
  cr_var="$1"
  cr_where="$2"
  cr_fallback="$3"
  cr_error="$4"
  _log "CRASH variable=$cr_var where=$cr_where fallback=$cr_fallback error=$cr_error"
  printf 'variable=%s where=%s fallback=%s error=%s\n' "$cr_var" "$cr_where" "$cr_fallback" "$cr_error" >> "$CRASH_REPORT_FILE" 2>/dev/null || true
  CRASH_REPORTS="${CRASH_REPORTS}
variable=$cr_var where=$cr_where fallback=$cr_fallback error=$cr_error"
}
write_crash_report_section() {
  cr_reason="$1"
  [ -n "$LOG_FILE" ] || return 0
  [ "$CRASH_REPORT_WRITTEN" = "0" ] || return 0
  CRASH_REPORT_WRITTEN=1
  {
    printf '\n===== Installer crash report =====\n'
    printf 'Reason: %s\n' "$cr_reason"
    if [ -s "$CRASH_REPORT_FILE" ]; then
      sed '/^$/d' "$CRASH_REPORT_FILE" 2>/dev/null || true
    elif [ -n "$CRASH_REPORTS" ]; then
      printf '%s\n' "$CRASH_REPORTS" | sed '/^$/d'
    else
      printf 'No guarded read failures were recorded before exit.\n'
    fi
    printf 'Last fallback: %s\n' "${LAST_FALLBACK:-none}"
    printf '===== End installer crash report =====\n'
  } >> "$LOG_FILE" 2>/dev/null || true
}
die()  { _log "ERROR $*"; add_crash_report "fatal" "die" "exit 1" "$*"; write_crash_report_section "$*"; : > "$SAFE_DIE_MARKER" 2>/dev/null || true; printf '\033[31m[jpg2pdf]\033[0m %s\n' "$*" >&2; [ -n "$LOG_FILE" ] && printf '\033[31m[jpg2pdf]\033[0m Full log: %s\n' "$LOG_FILE" >&2; exit 1; }
safe_read_file() { sed -n '1,$p' "$1" 2>/dev/null || true; }
run_step() {
  rs_name="$1"
  shift
  debug "STEP $rs_name"
  if "$@"; then
    return 0
  fi
  rs_code=$?
  add_crash_report "$rs_name" "$rs_name" "continue safely" "exit $rs_code"
  warn "$rs_name failed safely (exit $rs_code)."
  return "$rs_code"
}
on_exit() {
  code=$?
  if [ "$code" -ne 0 ]; then
    write_crash_report_section "exit $code"
    warn "Installer failed safely before completion (exit $code)."
    [ -n "$LOG_FILE" ] && warn "Detailed log: $LOG_FILE"
  fi
}
on_signal() { warn "Installer interrupted safely before completion."; exit 1; }
trap on_exit 0
trap on_signal HUP INT TERM

main() {

if [ "$DEBUG" = "1" ]; then
  info "Debug mode enabled. Log: ${LOG_FILE:-<unavailable>}"
  debug "uname: $(uname -a 2>/dev/null || echo unknown)"
  debug "shell: ${SHELL:-unknown}  user: $(id -un 2>/dev/null || echo unknown)"
  debug "PATH: ${PATH:-}"
  if [ -n "$LOG_FILE" ]; then
    exec 9>>"$LOG_FILE" 2>/dev/null || true
    BASH_XTRACEFD=9
  fi
  set -x
fi

DEFAULT_PREFIX="$HOME_DIR/.local/bin"
if [ -z "${HOME:-}" ] && [ -z "${JPG2PDF_PREFIX:-}" ]; then
  DEFAULT_PREFIX="$PWD_SAFE/.local/bin"
fi
REPO="${JPG2PDF_REPO:-alimtvnetwork/img-pdf-v2}"
VERSION="${JPG2PDF_VERSION:-}"
PREFIX="${JPG2PDF_PREFIX:-$DEFAULT_PREFIX}"
GITHUB_API="https://api.github.com"

if [ -z "$REPO" ]; then
  die "Set the repo: JPG2PDF_REPO=your-user/your-repo curl ... | bash"
fi

if ! uname_s="$(uname -s 2>/dev/null)"; then add_crash_report "uname -s" "Platform detection" "unsupported OS" "uname failed"; die "Could not detect OS."; fi
if ! uname_m="$(uname -m 2>/dev/null)"; then add_crash_report "uname -m" "Platform detection" "unsupported arch" "uname failed"; die "Could not detect architecture."; fi
case "$uname_s" in
  Linux)  os=linux  ;;
  Darwin) os=macos  ;;
  *)      die "Unsupported OS: $uname_s (Windows: use install.ps1)";;
esac
case "$uname_m" in
  x86_64|amd64) arch=x64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) die "Unsupported architecture: $uname_m" ;;
esac

asset="jpg2pdf-${os}-${arch}"
case "$asset" in
  jpg2pdf-windows-*) die "Use install.ps1 on Windows." ;;
esac

if command -v curl >/dev/null 2>&1; then
  GET() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      curl -fsSL -H "User-Agent: jpg2pdf-installer" -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $GITHUB_TOKEN" "$1"
    else
      curl -fsSL -H "User-Agent: jpg2pdf-installer" -H "Accept: application/vnd.github+json" "$1"
    fi
  }
  DL() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      curl -fL -H "User-Agent: jpg2pdf-installer" -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $GITHUB_TOKEN" "$1" -o "$2"
    else
      curl -fL -H "User-Agent: jpg2pdf-installer" -H "Accept: application/vnd.github+json" "$1" -o "$2"
    fi
  }
elif command -v wget >/dev/null 2>&1; then
  GET() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      wget -qO- --header="User-Agent: jpg2pdf-installer" --header="Accept: application/vnd.github+json" --header="Authorization: Bearer $GITHUB_TOKEN" "$1"
    else
      wget -qO- --header="User-Agent: jpg2pdf-installer" --header="Accept: application/vnd.github+json" "$1"
    fi
  }
  DL() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      wget -O "$2" --header="User-Agent: jpg2pdf-installer" --header="Accept: application/vnd.github+json" --header="Authorization: Bearer $GITHUB_TOKEN" "$1"
    else
      wget -O "$2" --header="User-Agent: jpg2pdf-installer" --header="Accept: application/vnd.github+json" "$1"
    fi
  }
else
  die "Need curl or wget to download."
fi

try_get() {
  tg_desc="$1"
  tg_url="$2"
  tg_err_file="$TMP_DIR/jpg2pdf-installer-get-$$.err"
  if tg_body="$(GET "$tg_url" 2>"$tg_err_file")"; then
    rm -f "$tg_err_file"
    printf '%s' "$tg_body"
    return 0
  fi
  tg_err="$(safe_read_file "$tg_err_file")"
  rm -f "$tg_err_file"
  add_crash_report "$tg_desc" "try_get" "continue to next fallback" "$tg_err"
  warn "$tg_desc failed: $tg_err"
  return 1
}

try_download() {
  td_desc="$1"
  td_url="$2"
  td_dest="$3"
  if DL "$td_url" "$td_dest"; then
    return 0
  fi
  add_crash_report "$td_desc" "try_download" "continue to next fallback" "$td_url"
  warn "$td_desc failed: $td_url"
  return 1
}

json_value() {
  key="$1"
  sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1 || true
}

download_release_asset() {
  tag="$1"
  out="$2"
  url="https://github.com/$REPO/releases/download/$tag/$asset"
  info "Downloading $url"
  try_download "Release download" "$url" "$out"
}

unpack_artifact() {
  zip_file="$1"
  extract_dir="$2"
  if ! mkdir -p "$extract_dir"; then
    add_crash_report "extract_dir" "Artifact extraction setup" "try source fallback later" "$extract_dir"
    return 1
  fi
  if command -v unzip >/dev/null 2>&1; then
    if unzip -q "$zip_file" -d "$extract_dir"; then return 0; fi
    add_crash_report "unzip" "Artifact extraction" "try python/ditto extraction" "$zip_file"
  fi
  if command -v python3 >/dev/null 2>&1; then
    if python3 - "$zip_file" "$extract_dir" <<'PYC'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
PYC
    then return 0; fi
    add_crash_report "python unzip" "Artifact extraction" "try ditto/source fallback" "$zip_file"
  fi
  if [ "$os" = "macos" ] && command -v ditto >/dev/null 2>&1; then
    if ditto -x -k "$zip_file" "$extract_dir"; then return 0; fi
    add_crash_report "ditto" "Artifact extraction" "source/Python fallback" "$zip_file"
  fi
  return 1
}

download_main_artifact() {
  out="$1"
  info "Looking for latest main-branch artifact named $asset ..."
  if [ -z "${GITHUB_TOKEN:-}" ]; then
    add_crash_report "GITHUB_TOKEN" "Main-branch artifact download" "source/Python fallback" "GitHub artifact archive downloads require authentication"
    warn "Skipping main-branch artifact download because GitHub requires authentication for workflow artifact archives. Set GITHUB_TOKEN to enable this fallback."
    return 1
  fi
  runs_json="$(try_get "Main-branch workflow lookup" "$GITHUB_API/repos/$REPO/actions/workflows/release.yml/runs?branch=main&status=success&per_page=10")" || return 1
  artifacts_urls="$(printf '%s' "$runs_json" | grep -o '"artifacts_url"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -n 's/.*"artifacts_url":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 10 || true)"
  if [ -z "$artifacts_urls" ]; then
    add_crash_report "artifacts_url" "Main-branch artifact lookup" "source/Python fallback" "no successful main runs with artifacts"
    return 1
  fi

  for artifacts_url in $artifacts_urls; do
    artifacts_json="$(try_get "Artifact lookup" "$artifacts_url?per_page=100")" || continue
    artifact_line="$(printf '%s\n' "$artifacts_json" | tr '{' '\n' | grep '"name"[[:space:]]*:[[:space:]]*"'"$asset"'"' | grep -v '"expired"[[:space:]]*:[[:space:]]*true' | head -n 1 || true)"
    [ -n "$artifact_line" ] || continue
    archive_url="$(printf '%s' "$artifact_line" | json_value archive_download_url)"
    [ -n "$archive_url" ] || continue

    tmp_base="$TMP_DIR"
    tmp_root="$tmp_base/jpg2pdf-artifact-$$"
    zip_file="$tmp_root/artifact.zip"
    extract_dir="$tmp_root/unzipped"
    rm -rf "$tmp_root"
    if ! mkdir -p "$tmp_root"; then
      add_crash_report "artifact temp" "Main-branch artifact temp setup" "try next fallback" "$tmp_root"
      continue
    fi
    if try_download "Main-branch artifact download" "$archive_url" "$zip_file"; then
      if unpack_artifact "$zip_file" "$extract_dir"; then
        candidate="$extract_dir/$asset"
        if [ ! -f "$candidate" ]; then
          candidate="$(find "$extract_dir" -type f -name "$asset" 2>/dev/null | head -n 1 || true)"
        fi
        if [ -n "$candidate" ] && [ -f "$candidate" ]; then
          if cp "$candidate" "$out"; then
            rm -rf "$tmp_root"
            return 0
          fi
          add_crash_report "artifact copy" "Main-branch artifact install" "try next fallback" "$candidate -> $out"
        fi
        warn "Artifact archive did not contain $asset."
      else
        warn "Could not unpack artifact archive. Install unzip, python3, or ditto."
      fi
    fi
    rm -rf "$tmp_root"
  done
  return 1
}


find_python() {
  if command -v python3 >/dev/null 2>&1; then printf '%s' "$(command -v python3)"; return 0; fi
  if command -v python >/dev/null 2>&1; then printf '%s' "$(command -v python)"; return 0; fi
  return 1
}

install_source_from_ref() {
  is_ref="$1"
  is_out="$2"
  is_url_kind="$3"
  py_cmd="$(find_python || true)"
  if [ -z "$py_cmd" ]; then
    add_crash_report "python" "Install source fallback" "binary-only install unavailable" "python3/python not found"
    return 1
  fi

  tmp_base="$TMP_DIR"
  tmp_root="$tmp_base/jpg2pdf-source-$$"
  tar_file="$tmp_root/source.tar.gz"
  extract_dir="$tmp_root/extracted"
  rm -rf "$tmp_root" 2>/dev/null || true
  if ! mkdir -p "$extract_dir"; then
    add_crash_report "source temp" "Install source fallback" "try next fallback" "$tmp_root"
    return 1
  fi

  if [ "$is_url_kind" = "tag" ]; then
    src_url="https://github.com/$REPO/archive/refs/tags/$is_ref.tar.gz"
  else
    src_url="https://github.com/$REPO/archive/refs/heads/$is_ref.tar.gz"
  fi
  info "Downloading source fallback $src_url"
  if ! try_download "Source fallback download" "$src_url" "$tar_file"; then
    rm -rf "$tmp_root" 2>/dev/null || true
    return 1
  fi

  if command -v tar >/dev/null 2>&1; then
    if ! tar -xzf "$tar_file" -C "$extract_dir"; then
      add_crash_report "source archive" "Source fallback extraction" "try next fallback" "$tar_file"
      rm -rf "$tmp_root" 2>/dev/null || true
      return 1
    fi
  else
    add_crash_report "tar" "Source fallback extraction" "try next fallback" "tar not found"
    rm -rf "$tmp_root" 2>/dev/null || true
    return 1
  fi

  src_root="$(find "$extract_dir" -type f -path '*/tools/jpg2pdf/src/jpg2pdf.py' -print 2>/dev/null | sed 's#/tools/jpg2pdf/src/jpg2pdf.py$##' | head -n 1 || true)"
  if [ -z "$src_root" ]; then
    add_crash_report "source tree" "Source fallback lookup" "try next fallback" "tools/jpg2pdf/src/jpg2pdf.py not found"
    rm -rf "$tmp_root" 2>/dev/null || true
    return 1
  fi

  install_root="$PREFIX/jpg2pdf-source"
  if ! rm -rf "$install_root" 2>/dev/null; then
    add_crash_report "install_root" "Source fallback cleanup" "overwrite in place" "$install_root"
  fi
  if ! cp -R "$src_root" "$install_root"; then
    add_crash_report "source copy" "Source fallback install" "try next fallback" "$install_root"
    rm -rf "$tmp_root" 2>/dev/null || true
    return 1
  fi

  req_file="$install_root/tools/jpg2pdf/requirements.txt"
  vendor_dir="$install_root/vendor"
  if [ -f "$req_file" ]; then
    mkdir -p "$vendor_dir" 2>/dev/null || add_crash_report "vendor_dir" "Source fallback dependencies" "try user-site pip install" "$vendor_dir"
    set +e
    "$py_cmd" -m pip install --target "$vendor_dir" -r "$req_file" >> "${LOG_FILE:-/dev/null}" 2>&1
    pip_code=$?
    set -e
    if [ "$pip_code" -ne 0 ]; then
      add_crash_report "pip vendor requirements" "Source fallback dependencies" "try user-site pip install" "pip install failed"
      set +e
      "$py_cmd" -m pip install --user -r "$req_file" >> "${LOG_FILE:-/dev/null}" 2>&1
      pip_code=$?
      set -e
      if [ "$pip_code" -ne 0 ]; then
        add_crash_report "pip user requirements" "Source fallback dependencies" "write wrapper anyway" "pip install failed"
        warn "Python dependency install failed; writing wrapper anyway. Check the log for pip output."
      fi
    fi
  else
    add_crash_report "requirements.txt" "Source fallback dependencies" "write wrapper without pip" "requirements file missing"
  fi

  script_path="$install_root/tools/jpg2pdf/src/jpg2pdf.py"
  if ! cat > "$is_out" <<EOF
#!/usr/bin/env sh
if [ -d "$vendor_dir" ]; then
  PYTHONPATH="$vendor_dir\${PYTHONPATH:+:\$PYTHONPATH}"
  export PYTHONPATH
fi
exec "$py_cmd" "$script_path" "\$@"
EOF
  then
    add_crash_report "wrapper write" "Source fallback wrapper" "try next fallback" "$is_out"
    rm -rf "$tmp_root" 2>/dev/null || true
    return 1
  fi
  if ! chmod +x "$is_out"; then
    add_crash_report "wrapper chmod" "Source fallback wrapper" "continue" "$is_out"
  fi
  rm -rf "$tmp_root" 2>/dev/null || true
  return 0
}

install_source_fallback() {
  out="$1"
  LAST_FALLBACK="source/Python fallback"
  if [ -n "$VERSION" ]; then
    if install_source_from_ref "$VERSION" "$out" "tag"; then
      installed_from="source fallback $VERSION"
      return 0
    fi
    warn "Pinned source fallback failed. Trying main branch source."
  fi
  if install_source_from_ref "main" "$out" "branch"; then
    installed_from="source fallback main"
    return 0
  fi
  return 1
}

if ! mkdir -p "$PREFIX"; then
  add_crash_report "PREFIX" "Create install directory" "abort install" "$PREFIX"
  die "Could not create install directory: $PREFIX"
fi
target="$PREFIX/jpg2pdf"
installed_from=""

if [ -n "$VERSION" ]; then
  info "Installing jpg2pdf $VERSION ($os/$arch)"
  if download_release_asset "$VERSION" "$target"; then
    installed_from="release $VERSION"
  fi
  if [ -z "$installed_from" ]; then
    warn "Release asset was not available. Falling back to the latest successful main-branch artifact."
    if download_main_artifact "$target"; then
      installed_from="latest main-branch artifact"
      VERSION=""
    fi
  fi
else
  info "Resolving latest release of $REPO ..."
  if api_json="$(try_get "Latest release lookup" "$GITHUB_API/repos/$REPO/releases/latest")"; then
    VERSION="$(printf '%s' "$api_json" | json_value tag_name)"
    if [ -n "$VERSION" ]; then
      info "Installing jpg2pdf $VERSION ($os/$arch)"
      if download_release_asset "$VERSION" "$target"; then
        installed_from="release $VERSION"
      fi
    fi
  else
    warn "No GitHub Release found. Falling back to the latest successful main-branch artifact."
  fi

  if [ -z "$installed_from" ]; then
    if download_main_artifact "$target"; then
      installed_from="latest main-branch artifact"
    fi
  fi
fi

if [ -z "$installed_from" ]; then
  warn "No usable binary was available. Falling back to source/Python install."
  if ! install_source_fallback "$target"; then
    die "Could not install jpg2pdf. Publish a release, run the main-branch build, install Python, or set GITHUB_TOKEN if artifact access requires it."
  fi
fi

if ! chmod +x "$target"; then
  add_crash_report "target chmod" "Finalize install" "continue" "$target"
fi

if [ "$os" = "macos" ] && command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$target" 2>/dev/null || true
fi

set +e
version_output="$("$target" --version 2>&1)"
version_code=$?
set -e
if [ "$version_code" -eq 0 ]; then
  info "Installed from $installed_from: $version_output -> $target"
else
  add_crash_report "installed binary verification" "Verify installed binary" "leave installed file in place" "--version exit $version_code: $version_output"
  warn "Installed from $installed_from, but --version did not run cleanly. The installer left the file in place; check the log for missing Python dependencies or a corrupt binary."
fi

# ----- GUI binary + macOS .app bundle (Steps 12-13) ----------------------
if [ "${JPG2PDF_NO_GUI:-}" = "1" ]; then
  info "Skipping GUI install (JPG2PDF_NO_GUI=1)."
else
  JPG2PDF_BIN="$PREFIX/jpg2pdf"
  gui_asset="jpg2pdf-gui-${os}-${arch}"
  gui_target="$PREFIX/jpg2pdf-gui"
  gui_installed_from=""
  if [ -n "$VERSION" ]; then
    gui_url="https://github.com/$REPO/releases/download/$VERSION/$gui_asset"
    info "Downloading $gui_url"
    if try_download "GUI binary download" "$gui_url" "$gui_target"; then
      gui_installed_from="release $VERSION"
    fi
  fi
  if [ -n "$gui_installed_from" ]; then
    chmod +x "$gui_target" 2>/dev/null || true
    [ "$os" = "macos" ] && command -v xattr >/dev/null 2>&1 && \
      xattr -dr com.apple.quarantine "$gui_target" 2>/dev/null || true
    info "GUI binary installed: $gui_target"
  else
    warn "GUI binary not available for this release; CLI is installed."
  fi

  # macOS .app bundle -> ~/Applications/jpg2pdf.app
  if [ "$os" = "macos" ] && [ -n "$VERSION" ] && [ "${JPG2PDF_NO_APP:-}" != "1" ]; then
    app_zip_name="jpg2pdf-gui-${os}-${arch}.app.zip"
    app_url="https://github.com/$REPO/releases/download/$VERSION/$app_zip_name"
    app_dest_parent="$HOME_DIR/Applications"
    if [ -w "/Applications" ] && [ "${JPG2PDF_APP_USER_ONLY:-}" != "1" ]; then
      app_dest_parent="/Applications"
    fi
    mkdir -p "$app_dest_parent" 2>/dev/null || true
    tmp_app_zip="$TMP_DIR/jpg2pdf-app-$$.zip"
    info "Downloading $app_url"
    if try_download ".app bundle download" "$app_url" "$tmp_app_zip"; then
      rm -rf "$app_dest_parent/jpg2pdf.app" 2>/dev/null || true
      if command -v ditto >/dev/null 2>&1; then
        ditto -x -k "$tmp_app_zip" "$app_dest_parent" \
          && info "Installed $app_dest_parent/jpg2pdf.app"
      elif command -v unzip >/dev/null 2>&1; then
        unzip -q "$tmp_app_zip" -d "$app_dest_parent" \
          && info "Installed $app_dest_parent/jpg2pdf.app"
      else
        warn "Need ditto or unzip to install the .app bundle."
      fi
      [ -d "$app_dest_parent/jpg2pdf.app" ] && command -v xattr >/dev/null 2>&1 \
        && xattr -dr com.apple.quarantine "$app_dest_parent/jpg2pdf.app" 2>/dev/null || true
    else
      warn ".app bundle not available for this release; CLI/GUI binary still installed."
    fi
    rm -f "$tmp_app_zip" 2>/dev/null || true
  fi

  # Linux .desktop entry -> ~/.local/share/applications/jpg2pdf.desktop (Step 14)
  if [ "$os" = "linux" ] && [ -x "$gui_target" ] && [ "${JPG2PDF_NO_DESKTOP:-}" != "1" ]; then
    desktop_dir="$HOME_DIR/.local/share/applications"
    desktop_file="$desktop_dir/jpg2pdf.desktop"
    if mkdir -p "$desktop_dir" 2>/dev/null; then
      if cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=jpg2pdf
GenericName=Image to PDF Converter
Comment=Merge images, PDFs, HTML and Word documents into a single PDF
Exec=$gui_target
Icon=application-pdf
Terminal=false
Categories=Office;Graphics;Utility;
MimeType=image/jpeg;image/png;image/webp;image/tiff;image/bmp;application/pdf;text/html;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/msword;
StartupNotify=true
EOF
      then
        chmod 644 "$desktop_file" 2>/dev/null || true
        command -v update-desktop-database >/dev/null 2>&1 && \
          update-desktop-database "$desktop_dir" >/dev/null 2>&1 || true
        info "Desktop entry installed: $desktop_file"
      else
        warn "Failed to write desktop entry at $desktop_file"
      fi
    else
      warn "Could not create $desktop_dir; skipping desktop entry."
    fi
  fi

  # Linux Nautilus scripts + KDE Dolphin servicemenu (Step 16) ----------------
  if [ "$os" = "linux" ] && [ -x "$JPG2PDF_BIN" ] && [ "${JPG2PDF_NO_FM_ACTIONS:-}" != "1" ]; then
    naut_dir="$HOME_DIR/.local/share/nautilus/scripts"
    if mkdir -p "$naut_dir" 2>/dev/null; then
      write_naut() {
        nf="$naut_dir/$1"
        cat > "$nf" <<NAUT
#!/usr/bin/env bash
set -e
list="\$(mktemp -t jpg2pdf-naut.XXXXXX)"
printf '%s\n' "\$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS" | sed '/^\$/d' > "\$list"
[ -s "\$list" ] || exit 0
"$JPG2PDF_BIN" $2 --files-from "\$list"
rc=\$?
rm -f "\$list" 2>/dev/null || true
exit \$rc
NAUT
        chmod 755 "$nf" 2>/dev/null || true
      }
      write_naut "jpg2pdf - Combine to PDF (A4)"         "--size a4"
      write_naut "jpg2pdf - Combine to PDF (Letter)"     "--size letter"
      write_naut "jpg2pdf - Combine to PDF (Legal)"      "--size legal"
      write_naut "jpg2pdf - Combine to PDF (A4, pencil)" "--size a4 --style pencil"
      info "Nautilus scripts installed: $naut_dir"
    else
      warn "Could not create $naut_dir; skipping Nautilus scripts."
    fi

    kde_dir="$HOME_DIR/.local/share/kio/servicemenus"
    kde_file="$kde_dir/jpg2pdf.desktop"
    if mkdir -p "$kde_dir" 2>/dev/null; then
      if cat > "$kde_file" <<EOF
[Desktop Entry]
Type=Service
ServiceTypes=KonqPopupMenu/Plugin
MimeType=image/jpeg;image/png;image/webp;image/tiff;image/bmp;application/pdf;text/html;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/msword;
Actions=Jpg2PdfA4;Jpg2PdfLetter;Jpg2PdfLegal;Jpg2PdfPencil;
X-KDE-Submenu=Combine into PDF
Icon=application-pdf
X-KDE-Priority=TopLevel

[Desktop Action Jpg2PdfA4]
Name=A4
Icon=application-pdf
Exec=$JPG2PDF_BIN --size a4 %F

[Desktop Action Jpg2PdfLetter]
Name=Letter
Icon=application-pdf
Exec=$JPG2PDF_BIN --size letter %F

[Desktop Action Jpg2PdfLegal]
Name=Legal
Icon=application-pdf
Exec=$JPG2PDF_BIN --size legal %F

[Desktop Action Jpg2PdfPencil]
Name=A4 pencil / paper look
Icon=application-pdf
Exec=$JPG2PDF_BIN --size a4 --style pencil %F
EOF
      then
        chmod 644 "$kde_file" 2>/dev/null || true
        info "KDE Dolphin servicemenu installed: $kde_file"
      else
        warn "Failed to write KDE servicemenu at $kde_file"
      fi
    fi
  fi

  # macOS Quick Action (Finder Services) (Step 16) ----------------------------
  if [ "$os" = "macos" ] && [ -x "$JPG2PDF_BIN" ] && [ "${JPG2PDF_NO_QUICKACTION:-}" != "1" ]; then
    svc_root="$HOME_DIR/Library/Services"
    if mkdir -p "$svc_root" 2>/dev/null; then
      install_quick_action() {
        wf="$svc_root/$1.workflow"
        rm -rf "$wf" 2>/dev/null || true
        mkdir -p "$wf/Contents" || return 1
        cat > "$wf/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSServices</key>
  <array>
    <dict>
      <key>NSMenuItem</key>
      <dict><key>default</key><string>$1</string></dict>
      <key>NSMessage</key><string>runWorkflowAsService</string>
      <key>NSRequiredContext</key>
      <dict><key>NSApplicationIdentifier</key><string>com.apple.finder</string></dict>
      <key>NSSendFileTypes</key>
      <array>
        <string>public.image</string>
        <string>com.adobe.pdf</string>
        <string>public.html</string>
        <string>org.openxmlformats.wordprocessingml.document</string>
        <string>com.microsoft.word.doc</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
PLIST
        cat > "$wf/Contents/document.wflow" <<WFLOW
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>AMApplicationBuild</key><string>523</string>
  <key>AMApplicationVersion</key><string>2.10</string>
  <key>AMDocumentVersion</key><string>2</string>
  <key>actions</key>
  <array>
    <dict>
      <key>action</key>
      <dict>
        <key>AMAccepts</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Optional</key><false/>
          <key>Types</key><array><string>com.apple.cocoa.path</string></array>
        </dict>
        <key>AMActionVersion</key><string>2.0.3</string>
        <key>AMApplication</key><array><string>Automator</string></array>
        <key>AMParameterProperties</key>
        <dict>
          <key>COMMAND_STRING</key><dict/>
          <key>CheckedForUserDefaultShell</key><dict/>
          <key>inputMethod</key><dict/>
          <key>shell</key><dict/>
          <key>source</key><dict/>
        </dict>
        <key>AMProvides</key>
        <dict>
          <key>Container</key><string>List</string>
          <key>Types</key><array><string>com.apple.cocoa.string</string></array>
        </dict>
        <key>ActionBundlePath</key><string>/System/Library/Automator/Run Shell Script.action</string>
        <key>ActionName</key><string>Run Shell Script</string>
        <key>ActionParameters</key>
        <dict>
          <key>COMMAND_STRING</key>
          <string>list="\$(mktemp -t jpg2pdf-qa)"
for f in "\$@"; do printf '%s\n' "\$f" &gt;&gt; "\$list"; done
"$JPG2PDF_BIN" $2 --files-from "\$list"
rc=\$?
rm -f "\$list" 2&gt;/dev/null || true
exit \$rc</string>
          <key>CheckedForUserDefaultShell</key><true/>
          <key>inputMethod</key><integer>1</integer>
          <key>shell</key><string>/bin/bash</string>
          <key>source</key><string></string>
        </dict>
        <key>BundleIdentifier</key><string>com.apple.RunShellScript</string>
        <key>CFBundleVersion</key><string>2.0.3</string>
        <key>CanShowSelectedItemsWhenRun</key><false/>
        <key>CanShowWhenRun</key><true/>
        <key>Category</key><array><string>AMCategoryUtilities</string></array>
        <key>Class Name</key><string>RunShellScriptAction</string>
        <key>InputUUID</key><string>00000000-0000-0000-0000-000000000001</string>
        <key>Keywords</key><array><string>Shell</string></array>
        <key>OutputUUID</key><string>00000000-0000-0000-0000-000000000002</string>
        <key>UUID</key><string>00000000-0000-0000-0000-000000000003</string>
        <key>UnlocalizedApplications</key><array><string>Automator</string></array>
        <key>arguments</key>
        <dict>
          <key>0</key><dict><key>default value</key><integer>0</integer><key>name</key><string>inputMethod</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>0</string></dict>
          <key>1</key><dict><key>default value</key><false/><key>name</key><string>CheckedForUserDefaultShell</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>1</string></dict>
          <key>2</key><dict><key>default value</key><string></string><key>name</key><string>source</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>2</string></dict>
          <key>3</key><dict><key>default value</key><string></string><key>name</key><string>COMMAND_STRING</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>3</string></dict>
          <key>4</key><dict><key>default value</key><string>/bin/sh</string><key>name</key><string>shell</string><key>required</key><string>0</string><key>type</key><string>0</string><key>uuid</key><string>4</string></dict>
        </dict>
        <key>isViewVisible</key><true/>
        <key>location</key><string>309.000000:253.000000</string>
        <key>nibPath</key><string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib</string>
      </dict>
      <key>isViewVisible</key><true/>
    </dict>
  </array>
  <key>connectors</key><dict/>
  <key>workflowMetaData</key>
  <dict>
    <key>serviceInputTypeIdentifier</key><string>com.apple.Automator.fileSystemObject</string>
    <key>serviceOutputTypeIdentifier</key><string>com.apple.Automator.nothing</string>
    <key>serviceProcessesInput</key><integer>0</integer>
    <key>workflowTypeIdentifier</key><string>com.apple.Automator.servicesMenu</string>
  </dict>
</dict>
</plist>
WFLOW
        info "Quick Action installed: $wf"
      }
      install_quick_action "Combine into PDF (A4)"         "--size a4"
      install_quick_action "Combine into PDF (Letter)"     "--size letter"
      install_quick_action "Combine into PDF (Legal)"      "--size legal"
      install_quick_action "Combine into PDF (A4, pencil)" "--size a4 --style pencil"
      /System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
    else
      warn "Could not create $svc_root; skipping Quick Actions."
    fi
  fi
fi



case ":${PATH:-}:" in
  *":$PREFIX:"*) info "$PREFIX is already on PATH." ;;
  *)
    warn "$PREFIX is not on your PATH."
    [ -n "$HOME_DIR" ] || HOME_DIR="$PREFIX"
    case "${SHELL:-}" in
      */zsh)  rc="$HOME_DIR/.zshrc"  ;;
      */bash) rc="$HOME_DIR/.bashrc" ;;
      *)      rc="$HOME_DIR/.profile" ;;
    esac
    printf '       Add this line to %s :\n         export PATH="%s:$PATH"\n' "$rc" "$PREFIX"
    ;;
esac

write_crash_report_section "installer completed"
if [ -s "$CRASH_REPORT_FILE" ] && [ -n "$LOG_FILE" ]; then
  warn "Diagnostic log: $LOG_FILE"
fi
info "Done. Try:"
printf '    jpg2pdf ~/Pictures --size a4\n'
printf '    jpg2pdf . --size a4 --style pencil\n'
}

if ! ( set -eu; main "$@" ); then
  if [ -f "$SAFE_DIE_MARKER" ]; then
    rm -f "$SAFE_DIE_MARKER" 2>/dev/null || true
    exit 1
  fi
  die "Installer failed safely before completion. Re-run with --debug for details."
fi
