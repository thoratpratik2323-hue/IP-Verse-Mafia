"""
file_explorer.py — Disk usage explorer mapping recursive tree models and locating duplicate files.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/file_explorer.py
# IP Prime - Full File Explorer Automation
# Features: browse, search, copy, move, delete, rename, compress, watch, preview, duplicates & more

import os
import re
import sys
import json
import time
import shutil
import hashlib
import zipfile
import fnmatch
import datetime
import threading
import subprocess
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────────────────────
IPPRIME_DIR   = Path.home() / ".ipprime"
BOOKMARKS_FILE = IPPRIME_DIR / "file_bookmarks.json"
RECENT_FILE    = IPPRIME_DIR / "file_recent.json"
MAX_RECENT     = 20

# ─── Watcher State ────────────────────────────────────────────────────────────
_watcher_thread: threading.Thread | None = None
_watcher_stop   = threading.Event()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _size_str(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _fmt_time(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _safe_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p


def _load_json(path: Path, default) -> dict | list:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, data) -> None:
    IPPRIME_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _add_recent(path_str: str) -> None:
    recent: list = _load_json(RECENT_FILE, [])
    if path_str in recent:
        recent.remove(path_str)
    recent.insert(0, path_str)
    _save_json(RECENT_FILE, recent[:MAX_RECENT])


# ─── 1. LIST / BROWSE ─────────────────────────────────────────────────────────

def browse_directory(path: str = "~", show_hidden: bool = False, sort_by: str = "name") -> str:
    """List contents of a directory with size, type, date."""
    p = _safe_path(path)
    if not p.exists():
        return f"Directory not found: {p}"
    if not p.is_dir():
        return f"Not a directory: {p}"

    _add_recent(str(p))
    entries = []
    try:
        for item in p.iterdir():
            if not show_hidden and item.name.startswith("."):
                continue
            try:
                stat = item.stat()
                entries.append({
                    "name":    item.name,
                    "type":    "DIR" if item.is_dir() else "FILE",
                    "size":    stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime,
                    "ext":     item.suffix.lower(),
                })
            except PermissionError:
                entries.append({"name": item.name, "type": "??", "size": 0, "modified": 0, "ext": ""})
    except PermissionError:
        return f"Permission denied: {p}"

    key_map = {"name": lambda e: e["name"].lower(),
               "size": lambda e: e["size"],
               "date": lambda e: e["modified"],
               "type": lambda e: e["type"]}
    entries.sort(key=key_map.get(sort_by, key_map["name"]))

    lines = [f"### Directory: `{p}`  ({len(entries)} items)\n",
             f"{'TYPE':<5} {'SIZE':>10}  {'MODIFIED':<20}  NAME"]
    lines.append("-" * 70)
    for e in entries:
        sz  = _size_str(e["size"]) if e["type"] == "FILE" else "<dir>"
        mod = _fmt_time(e["modified"]) if e["modified"] else "---"
        lines.append(f"{e['type']:<5} {sz:>10}  {mod:<20}  {e['name']}")
    return "\n".join(lines)


# ─── 2. FILE INFO ─────────────────────────────────────────────────────────────

def file_info(path: str) -> str:
    """Get detailed information about a file or folder."""
    p = _safe_path(path)
    if not p.exists():
        return f"Path not found: {p}"
    stat = p.stat()
    kind = "Directory" if p.is_dir() else "File"
    size = shutil.disk_usage(p).used if p.is_dir() else stat.st_size

    info = [
        f"### File Info: `{p.name}`",
        f"- **Type**: {kind}",
        f"- **Full Path**: `{p}`",
        f"- **Size**: {_size_str(size)}",
        f"- **Created**: {_fmt_time(stat.st_ctime)}",
        f"- **Modified**: {_fmt_time(stat.st_mtime)}",
        f"- **Accessed**: {_fmt_time(stat.st_atime)}",
    ]
    if p.is_file():
        info.append(f"- **Extension**: `{p.suffix or 'none'}`")
        # MD5
        try:
            md5 = hashlib.md5(p.read_bytes()).hexdigest()
            info.append(f"- **MD5**: `{md5}`")
        except Exception:
            pass
    else:
        try:
            item_count = sum(1 for _ in p.rglob("*"))
            info.append(f"- **Items inside (recursive)**: {item_count}")
        except Exception:
            pass
    return "\n".join(info)


# ─── 3. SEARCH FILES ──────────────────────────────────────────────────────────

def search_files(root: str = "~", pattern: str = "*", search_content: str = "",
                 max_results: int = 50) -> str:
    """Search files by name pattern and optionally by content."""
    root_p = _safe_path(root)
    if not root_p.exists():
        return f"Root path not found: {root_p}"

    results = []
    try:
        for item in root_p.rglob("*"):
            if len(results) >= max_results:
                break
            try:
                if not fnmatch.fnmatch(item.name, pattern):
                    continue
                if search_content and item.is_file():
                    try:
                        text = item.read_text(encoding="utf-8", errors="ignore")
                        if search_content.lower() not in text.lower():
                            continue
                    except Exception:
                        continue
                results.append(item)
            except Exception:
                continue
    except PermissionError:
        return f"Permission denied searching: {root_p}"

    if not results:
        return f"No files found matching `{pattern}`" + (f" containing `{search_content}`" if search_content else "")

    lines = [f"### Search Results ({len(results)} found)\n",
             f"Root: `{root_p}` | Pattern: `{pattern}`" + (f" | Content: `{search_content}`" if search_content else ""), ""]
    for r in results:
        kind = "DIR " if r.is_dir() else "FILE"
        try:
            sz = _size_str(r.stat().st_size) if r.is_file() else ""
        except Exception:
            sz = ""
        lines.append(f"[{kind}] {r}  {sz}")
    return "\n".join(lines)


# ─── 4. COPY ──────────────────────────────────────────────────────────────────

def copy_item(src: str, dst: str) -> str:
    """Copy a file or directory to a destination."""
    src_p, dst_p = _safe_path(src), _safe_path(dst)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    try:
        if src_p.is_dir():
            shutil.copytree(str(src_p), str(dst_p), dirs_exist_ok=True)
        else:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_p), str(dst_p))
        return f"Copied `{src_p.name}` → `{dst_p}`"
    except Exception as e:
        return f"Copy failed: {e}"


# ─── 5. MOVE / RENAME ─────────────────────────────────────────────────────────

def move_item(src: str, dst: str) -> str:
    """Move or rename a file/directory."""
    src_p, dst_p = _safe_path(src), _safe_path(dst)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    try:
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_p), str(dst_p))
        return f"Moved `{src_p}` → `{dst_p}`"
    except Exception as e:
        return f"Move failed: {e}"


def rename_item(path: str, new_name: str) -> str:
    """Rename a file or folder."""
    p = _safe_path(path)
    if not p.exists():
        return f"Not found: {p}"
    new_p = p.parent / new_name
    try:
        p.rename(new_p)
        return f"Renamed `{p.name}` → `{new_name}`"
    except Exception as e:
        return f"Rename failed: {e}"


# ─── 6. DELETE ────────────────────────────────────────────────────────────────

def delete_item(path: str, force: bool = False) -> str:
    """Delete a file or directory. Requires force=True for directories."""
    p = _safe_path(path)
    if not p.exists():
        return f"Not found: {p}"
    try:
        if p.is_dir():
            if not force:
                return f"'{p}' is a directory. Set force=True to delete recursively."
            shutil.rmtree(str(p))
        else:
            p.unlink()
        return f"Deleted: `{p}`"
    except Exception as e:
        return f"Delete failed: {e}"


# ─── 7. CREATE ────────────────────────────────────────────────────────────────

def create_item(path: str, item_type: str = "file", content: str = "") -> str:
    """Create a new file or directory."""
    p = _safe_path(path)
    try:
        if item_type == "dir":
            p.mkdir(parents=True, exist_ok=True)
            return f"Directory created: `{p}`"
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"File created: `{p}` ({_size_str(len(content.encode()))})"
    except Exception as e:
        return f"Create failed: {e}"


# ─── 8. PREVIEW FILE ──────────────────────────────────────────────────────────

def preview_file(path: str, lines: int = 50) -> str:
    """Preview the first N lines of a text file."""
    p = _safe_path(path)
    if not p.exists():
        return f"File not found: {p}"
    if not p.is_file():
        return f"Not a file: {p}"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        preview   = all_lines[:lines]
        result    = f"### Preview: `{p.name}` (first {min(lines, len(all_lines))} of {len(all_lines)} lines)\n\n"
        result   += "\n".join(f"{i+1:>4} | {l}" for i, l in enumerate(preview))
        if len(all_lines) > lines:
            result += f"\n\n... ({len(all_lines) - lines} more lines)"
        return result
    except Exception as e:
        return f"Preview failed: {e}"


# ─── 9. OPEN FILE / FOLDER ────────────────────────────────────────────────────

def open_item(path: str) -> str:
    """Open a file or folder with its default system application."""
    p = _safe_path(path)
    if not p.exists():
        return f"Not found: {p}"
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return f"Opened: `{p}`"
    except Exception as e:
        return f"Open failed: {e}"


# ─── 10. FOLDER SIZE ──────────────────────────────────────────────────────────

def folder_size(path: str) -> str:
    """Calculate total size of a directory recursively."""
    p = _safe_path(path)
    if not p.exists():
        return f"Not found: {p}"
    total = 0
    count = 0
    try:
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                    count += 1
                except Exception:
                    pass
    except Exception as e:
        return f"Size calculation failed: {e}"
    return f"### Folder Size: `{p.name}`\n- **Total Size**: {_size_str(total)}\n- **Files**: {count}"


# ─── 11. COMPRESS (ZIP) ───────────────────────────────────────────────────────

def compress_to_zip(source: str, output_zip: str = "") -> str:
    """Compress a file or folder to a ZIP archive."""
    src_p = _safe_path(source)
    if not src_p.exists():
        return f"Source not found: {src_p}"
    if not output_zip:
        output_zip = str(src_p.parent / (src_p.stem + ".zip"))
    out_p = _safe_path(output_zip)
    try:
        with zipfile.ZipFile(str(out_p), "w", zipfile.ZIP_DEFLATED) as zf:
            if src_p.is_dir():
                for f in src_p.rglob("*"):
                    zf.write(f, f.relative_to(src_p.parent))
            else:
                zf.write(src_p, src_p.name)
        return f"Compressed → `{out_p}` ({_size_str(out_p.stat().st_size)})"
    except Exception as e:
        return f"Compression failed: {e}"


# ─── 12. EXTRACT (UNZIP) ──────────────────────────────────────────────────────

def extract_zip(zip_path: str, extract_to: str = "") -> str:
    """Extract a ZIP archive."""
    zp = _safe_path(zip_path)
    if not zp.exists():
        return f"ZIP not found: {zp}"
    if not extract_to:
        extract_to = str(zp.parent / zp.stem)
    out_p = _safe_path(extract_to)
    try:
        out_p.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(zp), "r") as zf:
            zf.extractall(str(out_p))
        return f"Extracted `{zp.name}` → `{out_p}`"
    except Exception as e:
        return f"Extraction failed: {e}"


# ─── 13. FIND DUPLICATES ──────────────────────────────────────────────────────

def find_duplicates(root: str = "~", min_size_kb: int = 1) -> str:
    """Find duplicate files by MD5 hash in a directory."""
    root_p = _safe_path(root)
    if not root_p.exists():
        return f"Not found: {root_p}"
    hashes: dict[str, list] = {}
    min_bytes = min_size_kb * 1024
    try:
        for f in root_p.rglob("*"):
            if f.is_file():
                try:
                    if f.stat().st_size < min_bytes:
                        continue
                    md5 = hashlib.md5(f.read_bytes()).hexdigest()
                    hashes.setdefault(md5, []).append(str(f))
                except Exception:
                    pass
    except Exception as e:
        return f"Duplicate scan failed: {e}"

    dupes = {h: paths for h, paths in hashes.items() if len(paths) > 1}
    if not dupes:
        return f"No duplicates found in `{root_p}`"

    lines = [f"### Duplicate Files Found ({len(dupes)} groups)\n"]
    total_waste = 0
    for h, paths in dupes.items():
        try:
            sz  = Path(paths[0]).stat().st_size
            waste = sz * (len(paths) - 1)
            total_waste += waste
            lines.append(f"**Hash `{h[:12]}...`** — {len(paths)} copies ({_size_str(sz)} each)")
            for pp in paths:
                lines.append(f"  - `{pp}`")
        except Exception:
            pass
    lines.append(f"\n**Total wasted space**: {_size_str(total_waste)}")
    return "\n".join(lines)


# ─── 14. BULK RENAME ──────────────────────────────────────────────────────────

def bulk_rename(directory: str, pattern: str, replacement: str,
                dry_run: bool = True) -> str:
    """Bulk rename files matching a regex pattern. dry_run=True to preview."""
    dir_p = _safe_path(directory)
    if not dir_p.is_dir():
        return f"Not a directory: {dir_p}"
    results = []
    try:
        rgx = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex: {e}"

    for f in sorted(dir_p.iterdir()):
        if rgx.search(f.name):
            new_name = rgx.sub(replacement, f.name)
            if new_name != f.name:
                results.append((f, f.parent / new_name))

    if not results:
        return f"No files matched pattern `{pattern}` in `{dir_p}`"

    lines = [f"### Bulk Rename {'(DRY RUN - no changes made)' if dry_run else '(APPLIED)'}\n"]
    for old, new in results:
        lines.append(f"  `{old.name}` → `{new.name}`")
        if not dry_run:
            try:
                old.rename(new)
            except Exception as e:
                lines[-1] += f"  [ERROR: {e}]"

    if dry_run:
        lines.append(f"\n{len(results)} files would be renamed. Run with dry_run=False to apply.")
    else:
        lines.append(f"\n{len(results)} files renamed.")
    return "\n".join(lines)


# ─── 15. DISK USAGE ───────────────────────────────────────────────────────────

def disk_usage(path: str = "~") -> str:
    """Show disk usage stats for a drive or path."""
    p = _safe_path(path)
    try:
        usage = shutil.disk_usage(str(p))
        pct   = (usage.used / usage.total) * 100
        bar_len = 30
        filled  = int(bar_len * usage.used / usage.total)
        bar     = "█" * filled + "░" * (bar_len - filled)
        return (
            f"### Disk Usage: `{p}`\n"
            f"- **Total**: {_size_str(usage.total)}\n"
            f"- **Used**:  {_size_str(usage.used)} ({pct:.1f}%)\n"
            f"- **Free**:  {_size_str(usage.free)}\n"
            f"- `[{bar}]` {pct:.0f}%"
        )
    except Exception as e:
        return f"Disk usage failed: {e}"


# ─── 16. RECENT FILES ─────────────────────────────────────────────────────────

def recent_files() -> str:
    """Show recently accessed files/directories."""
    recent: list = _load_json(RECENT_FILE, [])
    if not recent:
        return "No recent files/directories recorded yet."
    lines = ["### Recent Files / Directories\n"]
    for i, r in enumerate(recent, 1):
        p = Path(r)
        exists_mark = "" if p.exists() else " [missing]"
        lines.append(f"{i:>2}. `{r}`{exists_mark}")
    return "\n".join(lines)


# ─── 17. BOOKMARKS ────────────────────────────────────────────────────────────

def add_bookmark(path: str, label: str = "") -> str:
    bmarks: dict = _load_json(BOOKMARKS_FILE, {})
    p     = _safe_path(path)
    key   = label or p.name
    bmarks[key] = str(p)
    _save_json(BOOKMARKS_FILE, bmarks)
    return f"Bookmark added: `{key}` → `{p}`"


def list_bookmarks() -> str:
    bmarks: dict = _load_json(BOOKMARKS_FILE, {})
    if not bmarks:
        return "No bookmarks saved yet."
    lines = ["### Bookmarks\n"]
    for k, v in bmarks.items():
        exists = Path(v).exists()
        lines.append(f"- **{k}**: `{v}`" + ("" if exists else " [missing]"))
    return "\n".join(lines)


def remove_bookmark(label: str) -> str:
    bmarks: dict = _load_json(BOOKMARKS_FILE, {})
    if label not in bmarks:
        return f"Bookmark `{label}` not found."
    del bmarks[label]
    _save_json(BOOKMARKS_FILE, bmarks)
    return f"Bookmark `{label}` removed."


def go_bookmark(label: str) -> str:
    """Browse the path stored in a bookmark."""
    bmarks: dict = _load_json(BOOKMARKS_FILE, {})
    if label not in bmarks:
        return f"Bookmark `{label}` not found."
    return browse_directory(bmarks[label])


# ─── 18. FILE WATCHER ─────────────────────────────────────────────────────────

def start_file_watcher(directory: str, interval: int = 5, player=None) -> str:
    """Start a background watcher that logs file changes in a directory."""
    global _watcher_thread, _watcher_stop
    dir_p = _safe_path(directory)
    if not dir_p.is_dir():
        return f"Not a directory: {dir_p}"
    if _watcher_thread and _watcher_thread.is_alive():
        return "File watcher is already running. Stop it first."

    _watcher_stop.clear()
    log_file = IPPRIME_DIR / "file_watcher.log"
    IPPRIME_DIR.mkdir(parents=True, exist_ok=True)

    def _snapshot(d: Path) -> dict:
        snap = {}
        try:
            for f in d.rglob("*"):
                try:
                    snap[str(f)] = f.stat().st_mtime
                except Exception:
                    pass
        except Exception:
            pass
        return snap

    def _watch():
        prev = _snapshot(dir_p)
        while not _watcher_stop.is_set():
            time.sleep(interval)
            curr = _snapshot(dir_p)
            now  = datetime.datetime.now().strftime("%H:%M:%S")
            events = []
            for p, mt in curr.items():
                if p not in prev:
                    events.append(f"[CREATED] {p}")
                elif mt != prev.get(p):
                    events.append(f"[MODIFIED] {p}")
            for p in prev:
                if p not in curr:
                    events.append(f"[DELETED] {p}")
            if events:
                msg = f"[{now}] " + " | ".join(events)
                with open(log_file, "a", encoding="utf-8") as lf:
                    lf.write(msg + "\n")
                if player:
                    try:
                        player.write_log(f"[FileWatcher] {msg}")
                    except Exception:
                        pass
            prev = curr

    _watcher_thread = threading.Thread(target=_watch, daemon=True, name="IPPrimeFileWatcher")
    _watcher_thread.start()
    return f"File watcher started on `{dir_p}` (checking every {interval}s). Log: `{log_file}`"


def stop_file_watcher() -> str:
    global _watcher_thread, _watcher_stop
    if not _watcher_thread or not _watcher_thread.is_alive():
        return "No file watcher is running."
    _watcher_stop.set()
    _watcher_thread.join(timeout=10)
    return "File watcher stopped."


# ─── 19. FIND LARGE FILES ─────────────────────────────────────────────────────

def find_large_files(root: str = "~", min_mb: float = 100, top_n: int = 20) -> str:
    """Find the largest files in a directory tree."""
    root_p = _safe_path(root)
    min_bytes = int(min_mb * 1024 * 1024)
    large = []
    try:
        for f in root_p.rglob("*"):
            if f.is_file():
                try:
                    sz = f.stat().st_size
                    if sz >= min_bytes:
                        large.append((sz, f))
                except Exception:
                    pass
    except Exception as e:
        return f"Scan failed: {e}"

    if not large:
        return f"No files larger than {min_mb}MB found in `{root_p}`"

    large.sort(reverse=True)
    lines = [f"### Large Files (>= {min_mb}MB) in `{root_p}`\n"]
    for sz, f in large[:top_n]:
        lines.append(f"- {_size_str(sz):>12}  `{f}`")
    return "\n".join(lines)


# ─── 20. FILE TYPE STATS ──────────────────────────────────────────────────────

def file_type_stats(root: str = "~") -> str:
    """Show breakdown of file types (extensions) in a directory."""
    root_p = _safe_path(root)
    stats: dict[str, list] = {}
    try:
        for f in root_p.rglob("*"):
            if f.is_file():
                ext = f.suffix.lower() or "(no ext)"
                try:
                    sz = f.stat().st_size
                except Exception:
                    sz = 0
                stats.setdefault(ext, []).append(sz)
    except Exception as e:
        return f"Scan failed: {e}"

    if not stats:
        return f"No files found in `{root_p}`"

    rows = [(ext, len(szs), sum(szs)) for ext, szs in stats.items()]
    rows.sort(key=lambda r: r[2], reverse=True)
    lines = [f"### File Type Stats: `{root_p}`\n",
             f"{'EXTENSION':<15} {'COUNT':>7}  {'TOTAL SIZE':>12}"]
    lines.append("-" * 40)
    for ext, cnt, total in rows[:30]:
        lines.append(f"{ext:<15} {cnt:>7}  {_size_str(total):>12}")
    return "\n".join(lines)


# ─── 21. TREE VIEW ────────────────────────────────────────────────────────────

def tree_view(root: str = ".", max_depth: int = 3, max_items: int = 200) -> str:
    """Show directory tree structure."""
    root_p = _safe_path(root)
    if not root_p.exists():
        return f"Not found: {root_p}"
    lines  = [f"`{root_p}`"]
    count  = [0]

    def _walk(path: Path, depth: int, prefix: str):
        if depth > max_depth or count[0] >= max_items:
            return
        try:
            children = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        for i, child in enumerate(children):
            if count[0] >= max_items:
                lines.append(prefix + "  ... (truncated)")
                return
            is_last   = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            icon      = "📁 " if child.is_dir() else "📄 "
            lines.append(prefix + connector + icon + child.name)
            count[0] += 1
            if child.is_dir():
                extension = "    " if is_last else "│   "
                _walk(child, depth + 1, prefix + extension)

    _walk(root_p, 1, "")
    if count[0] >= max_items:
        lines.append(f"\n(showing first {max_items} items)")
    return "\n".join(lines)


# ─── MAIN DISPATCHER ──────────────────────────────────────────────────────────

def file_explorer(parameters: dict, player=None) -> str:
    """
    Main dispatcher for File Explorer Automation.

    Actions:
      browse        — list directory contents
      info          — detailed file/folder info
      search        — search files by name/content
      copy          — copy file or folder
      move          — move/rename file or folder
      rename        — rename file or folder
      delete        — delete file or folder
      create        — create file or directory
      preview       — preview text file contents
      open          — open with default app
      folder_size   — calculate folder size
      compress      — zip a file/folder
      extract       — unzip an archive
      duplicates    — find duplicate files
      bulk_rename   — bulk rename with regex
      disk_usage    — disk space info
      recent        — show recently accessed paths
      bookmark_add  — add a bookmark
      bookmark_list — list bookmarks
      bookmark_go   — browse a bookmarked path
      bookmark_del  — remove a bookmark
      watch_start   — start file watcher
      watch_stop    — stop file watcher
      large_files   — find large files
      type_stats    — file extension breakdown
      tree          — show directory tree
    """
    params = parameters or {}
    action = params.get("action", "browse").lower().strip()

    # Default workspace root — always CODING PROJECTS
    _CP = r"C:\Users\thora\.gemini\antigravity\scratch\IP Prime\CODING PROJECTS"

    if player:
        player.write_log(f"[FileExplorer] {action}")

    try:
        if action == "browse":
            return browse_directory(
                params.get("path", _CP),
                params.get("show_hidden", False),
                params.get("sort_by", "name"),
            )
        elif action == "info":
            return file_info(params.get("path", "~"))
        elif action == "search":
            return search_files(
                params.get("root", _CP),
                params.get("pattern", "*"),
                params.get("content", ""),
                int(params.get("max_results", 50)),
            )
        elif action == "copy":
            return copy_item(params["src"], params["dst"])
        elif action == "move":
            return move_item(params["src"], params["dst"])
        elif action == "rename":
            return rename_item(params["path"], params["new_name"])
        elif action == "delete":
            return delete_item(params["path"], bool(params.get("force", False)))
        elif action == "create":
            return create_item(
                params["path"],
                params.get("type", "file"),
                params.get("content", ""),
            )
        elif action == "preview":
            return preview_file(params["path"], int(params.get("lines", 50)))
        elif action == "open":
            return open_item(params["path"])
        elif action == "folder_size":
            return folder_size(params.get("path", "~"))
        elif action == "compress":
            return compress_to_zip(params["src"], params.get("output", ""))
        elif action == "extract":
            return extract_zip(params["path"], params.get("extract_to", ""))
        elif action == "duplicates":
            return find_duplicates(
                params.get("root", "~"),
                int(params.get("min_size_kb", 1)),
            )
        elif action == "bulk_rename":
            return bulk_rename(
                params["directory"],
                params["pattern"],
                params["replacement"],
                bool(params.get("dry_run", True)),
            )
        elif action == "disk_usage":
            return disk_usage(params.get("path", "~"))
        elif action == "recent":
            return recent_files()
        elif action == "bookmark_add":
            return add_bookmark(params["path"], params.get("label", ""))
        elif action == "bookmark_list":
            return list_bookmarks()
        elif action == "bookmark_go":
            return go_bookmark(params["label"])
        elif action == "bookmark_del":
            return remove_bookmark(params["label"])
        elif action == "watch_start":
            return start_file_watcher(
                params.get("path", "~"),
                int(params.get("interval", 5)),
                player,
            )
        elif action == "watch_stop":
            return stop_file_watcher()
        elif action == "large_files":
            return find_large_files(
                params.get("root", "~"),
                float(params.get("min_mb", 100)),
                int(params.get("top_n", 20)),
            )
        elif action == "type_stats":
            return file_type_stats(params.get("root", "~"))
        elif action == "tree":
            return tree_view(
                params.get("path", "."),
                int(params.get("max_depth", 3)),
                int(params.get("max_items", 200)),
            )
        else:
            return (
                f"Unknown action `{action}`. Available: browse, info, search, copy, move, rename, "
                "delete, create, preview, open, folder_size, compress, extract, duplicates, "
                "bulk_rename, disk_usage, recent, bookmark_add, bookmark_list, bookmark_go, "
                "bookmark_del, watch_start, watch_stop, large_files, type_stats, tree"
            )
    except KeyError as e:
        return f"Missing required parameter: {e}"
    except Exception as e:
        return f"File Explorer error ({action}): {e}"
