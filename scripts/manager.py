#!/usr/bin/env python3
"""
Code Chat Viewer - Chat Manager

Scans Claude Code projects, generates/updates HTML visualizations,
organizes chats by activity, and creates an interactive dashboard.

Reads configuration from config.json (see config.example.json for template).
If config.json is not found, the script exits with setup instructions.
Use with Claude Code for interactive configuration setup.

Copyright (c) 2025-2026 Óscar González Martín
Licensed under the MIT License - see LICENSE for details

Author: Óscar González Martín
Repository: https://github.com/oskar-gm/code-chat-viewer
"""

import json
import os
import re
import shutil
import sys
import io
import threading
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import redirect_stdout
from html import escape

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent


def find_config() -> Path | None:
    """Find config.json in standard locations.

    Search order: project root, script directory, current working directory.
    """
    for location in [PROJECT_ROOT, SCRIPT_DIR, Path.cwd()]:
        config_path = location / "config.json"
        if config_path.exists():
            return config_path
    return None


def _prompt(label: str, default: str) -> str:
    """Prompt for text input with a default value."""
    val = input(f"  {label} [{default}]: ").strip()
    return val if val else default


def _prompt_yn(label: str, default_yes: bool = True) -> bool:
    """Prompt for yes/no input. Returns True for yes."""
    hint = "Y/n" if default_yes else "y/N"
    val = input(f"  {label} [{hint}]: ").strip().lower()
    if not val:
        return default_yes
    return val in ("y", "yes")


def _prompt_int(label: str, default: int) -> int:
    """Prompt for integer input with a default value."""
    val = input(f"  {label} [{default}]: ").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"    Invalid number, using default: {default}")
        return default


def interactive_setup() -> Path:
    """Guide the user through creating config.json step by step."""
    home = Path.home()
    print("  No config.json found. Let's set it up!")
    print()
    print("  Press Enter to accept defaults shown in [brackets].")
    print()

    # --- Paths ---
    print("  --- Paths ---")
    source = _prompt(
        "Claude Code chats folder",
        "~/.claude/projects",
    )
    output = _prompt(
        "Output folder (HTMLs + dashboard)",
        str(home / "Code Chat Viewer"),
    )
    dashboard = _prompt("Dashboard filename", "CCV-Dashboard.html")
    print()

    # --- Agents ---
    print("  --- Agent chats ---")
    print("  Claude Code creates sub-chats for background tasks.")
    include_agents = _prompt_yn("Include agent chats?")
    min_agent_kb = 3
    if include_agents:
        min_agent_kb = _prompt_int(
            "Min agent size in KB (skip tiny ones)", 3
        )
    print()

    # --- Organization ---
    print("  --- Chat organization ---")
    print("  Inactive chats can be sorted into subfolders automatically.")
    inactive_days = _prompt_int("Days without activity to consider inactive", 5)
    print()

    shorts_enabled = _prompt_yn("Enable Shorts? (group small inactive chats)")
    shorts_max_kb = 40
    if shorts_enabled:
        shorts_max_kb = _prompt_int(
            "Max size in KB to count as 'short'", 40
        )

    archive_enabled = _prompt_yn("Enable Archive? (move old inactive chats)")
    print()

    # --- Save ---
    config = {
        "_readme": "Code Chat Viewer - Configuration. Edit or delete this file to reconfigure.",
        "source": {"projects_path": source},
        "output": {"folder": output, "index_filename": dashboard},
        "agents": {"include": include_agents, "min_size_kb": min_agent_kb},
        "inactive_days": inactive_days,
        "shorts": {
            "enabled": shorts_enabled,
            "folder": "Shorts",
            "max_size_kb": shorts_max_kb,
        },
        "archive": {"enabled": archive_enabled, "folder": "Archived"},
    }

    config_path = PROJECT_ROOT / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"  Config saved: {config_path}")
    print()
    return config_path


def load_config() -> dict:
    """Load and validate configuration from config.json."""
    config_path = find_config()
    if not config_path:
        if sys.stdout.isatty():
            config_path = interactive_setup()
        else:
            print("ERROR: config.json not found.")
            print()
            print("To set up configuration:")
            print("  1. Copy config.example.json as config.json")
            print("  2. Edit values to match your environment")
            print("  3. Or run this script manually for interactive setup")
            print()
            print(f"Expected location: {PROJECT_ROOT / 'config.json'}")
            sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Time display format for timestamps: "12h" (AM/PM, default) or "24h".
    tf = str(config.get("time_format", "12h")).lower()
    config["time_format"] = tf if tf in ("12h", "24h") else "12h"

    # Resolve paths
    source_path = Path(config["source"]["projects_path"]).expanduser().resolve()
    # Output folder precedence: CODE_CHAT_VIEWER_DIR env var > config.json.
    # Resolved once here; the rest of the code only reads _resolved paths.
    env_output = os.environ.get("CODE_CHAT_VIEWER_DIR", "").strip()
    output_path = Path(env_output if env_output else config["output"]["folder"]).expanduser()
    if not output_path.is_absolute():
        output_path = (PROJECT_ROOT / output_path).resolve()
    else:
        output_path = output_path.resolve()

    config["_resolved"] = {
        "source_path": source_path,
        "output_path": output_path,
        "chats_path": output_path / "Chats",
        "config_path": config_path,
        "output_from_env": bool(env_output),
    }

    # Validate source path
    if not source_path.exists():
        print(f"ERROR: Source path does not exist: {source_path}")
        print("Update source.projects_path in config.json")
        sys.exit(1)

    return config


# ---------------------------------------------------------------------------
# Import visualizer from the same directory
# ---------------------------------------------------------------------------

sys.path.insert(0, str(SCRIPT_DIR))
from visualizer import (  # noqa: E402
    APP_VERSION,
    parse_chat_json,
    generate_html,
    get_chat_timestamp,
    generate_output_filename,
    ICON_BASE64,
    ICON_FAVICON_BASE64,
)

# ---------------------------------------------------------------------------
# Hash & file utilities
# ---------------------------------------------------------------------------


def get_hash_from_filename(filename: str) -> str:
    """Extract the hash prefix from a JSONL or HTML filename.

    Handles both regular chats (UUID-based) and agent chats (agent-XX prefix).
    """
    name = Path(filename).stem

    if name.startswith("agent-"):
        return name.replace("agent-", "")[:8]

    parts = name.split()
    if parts:
        last_part = parts[-1]
        if last_part.startswith("Agent-"):
            last_part = parts[-2] if len(parts) > 1 else last_part
        return last_part[:8]

    return name.split("-")[0][:8]


def find_existing_html(output_path: Path, hash_prefix: str, is_agent: bool = False) -> Path | None:
    """Find an existing HTML file by hash prefix in root and subfolders."""
    for html_file in output_path.rglob("*.html"):
        html_name = html_file.stem
        if hash_prefix in html_name:
            if is_agent and "Agent-" in html_name:
                return html_file
            elif not is_agent and "Agent-" not in html_name:
                return html_file
    return None


def needs_update(jsonl_path: Path, html_path: Path) -> bool:
    """Check if the JSONL source is newer than the generated HTML."""
    return jsonl_path.stat().st_mtime > html_path.stat().st_mtime


def resolve_chat_title(jsonl_path: Path, sessions_meta: dict = None) -> str:
    """Resolve the display title for a chat.

    Uses the same resolution as the dashboard name column:
      1. JSONL custom_title (set by /rename) — highest priority
      2. sessions-index customTitle
      3. sessions-index summary
      4. JSONL first_prompt (truncated to 60 chars)
      5. "Untitled"
    """
    hash_prefix = get_hash_from_filename(jsonl_path.name)
    index_title = ""
    first_prompt = ""

    # sessions-index.json
    if sessions_meta:
        meta = sessions_meta.get(hash_prefix, {})
        index_title = (meta.get("customTitle")
                       or meta.get("summary")
                       or "")
        if not first_prompt:
            first_prompt = (meta.get("firstPrompt") or "")[:60]

    # JSONL metadata
    jsonl_meta = extract_jsonl_metadata(jsonl_path)
    if jsonl_meta.get("custom_title"):
        return jsonl_meta["custom_title"]
    if not first_prompt and jsonl_meta.get("first_prompt"):
        first_prompt = jsonl_meta["first_prompt"][:60]

    return index_title or first_prompt or "Untitled"


def generate_chat_html(
    jsonl_path: Path, output_dir: Path, agent_suffix: str = "",
    dashboard_filename: str = "CCV-Dashboard.html",
    sessions_meta: dict = None,
    history_entries: list = None,
    time_format: str = "12h",
) -> tuple[str | None, str | None]:
    """Generate HTML for a single chat file.

    Returns:
        (filename, None) on success, (None, error_message) on failure.
    """
    try:
        with redirect_stdout(io.StringIO()):
            messages = parse_chat_json(str(jsonl_path))

        if not messages:
            return None, "No messages"

        base_name = generate_output_filename(str(jsonl_path), messages)

        if agent_suffix:
            name_parts = base_name.rsplit(".", 1)
            name_without_ext = name_parts[0]
            if name_without_ext.endswith(" agent"):
                name_without_ext = name_without_ext[:-6]
            base_name = f"{name_without_ext} {agent_suffix}.html"

        output_path = output_dir / base_name

        chat_title = resolve_chat_title(jsonl_path, sessions_meta)

        with redirect_stdout(io.StringIO()):
            generate_html(
                messages, str(output_path),
                dashboard_url=dashboard_filename,
                chat_title=chat_title,
                chat_uuid=jsonl_path.stem,
                history_entries=history_entries,
                time_format=time_format,
            )

        return base_name, None
    except Exception as e:
        return None, str(e)


def find_jsonl_for_html(projects_path: Path, html_name: str) -> Path | None:
    """Find the original JSONL file corresponding to an HTML by hash matching."""
    hash_prefix = get_hash_from_filename(html_name)
    is_agent = "Agent-" in html_name

    for project_dir in projects_path.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            filename = jsonl_file.name
            if is_agent:
                if filename.startswith("agent-"):
                    agent_id = filename.replace("agent-", "").replace(".jsonl", "")[:2]
                    if agent_id in html_name:
                        return jsonl_file
            else:
                jsonl_hash = get_hash_from_filename(filename)
                if jsonl_hash == hash_prefix:
                    return jsonl_file
    return None


# ---------------------------------------------------------------------------
# Direct chat opening (--current / --name)
# ---------------------------------------------------------------------------


def find_current_jsonl(source_path: Path) -> Path | None:
    """Auto-detect the current session JSONL from CWD.

    Encodes the current working directory to the Claude Code project
    directory format, then returns the most recently modified non-agent
    JSONL in that project directory.
    """
    cwd = Path.cwd()
    encoded = str(cwd).replace(":", "-").replace("\\", "-").replace("/", "-")

    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue
        if encoded in project_dir.name:
            jsonls = sorted(
                [f for f in project_dir.glob("*.jsonl")
                 if not f.name.startswith("agent-")],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            return jsonls[0] if jsonls else None
    return None


def find_chat_by_name(
    search_terms: str, source_path: Path, output_path: Path
) -> Path | None:
    """Find the HTML for a chat matching the search terms.

    Matching is flexible: all search words must appear somewhere in the
    chat's title/summary/prompt (case-insensitive, any order). Searches
    from most recent to oldest and returns the first match.

    Search sources (in order):
      1. sessions-index.json (customTitle, summary, firstPrompt) — fast
      2. JSONL custom_title for sessions not in the index — slower
    """
    search_words = search_terms.lower().split()
    if not search_words:
        return None

    candidates = []  # (mtime, jsonl_path)
    seen_sessions = set()

    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue

        # 1. sessions-index.json (fast, already indexed)
        index_file = project_dir / "sessions-index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("entries", []):
                    sid = entry.get("sessionId", "")
                    searchable = " ".join(filter(None, [
                        entry.get("customTitle", ""),
                        entry.get("summary", ""),
                        entry.get("firstPrompt", ""),
                    ])).lower()
                    if all(w in searchable for w in search_words):
                        jsonl_path = project_dir / f"{sid}.jsonl"
                        mtime = (jsonl_path.stat().st_mtime
                                 if jsonl_path.exists() else 0)
                        candidates.append((mtime, jsonl_path))
                        seen_sessions.add(sid)
            except Exception:
                pass

        # 2. JSONL files not in the index
        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue
            sid = jsonl_file.stem
            if sid in seen_sessions:
                continue
            meta = extract_jsonl_metadata(jsonl_file)
            title = meta.get("custom_title", "")
            if title and all(w in title.lower() for w in search_words):
                candidates.append((jsonl_file.stat().st_mtime, jsonl_file))

    if not candidates:
        return None

    # Most recent match
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_jsonl = candidates[0][1]

    hash_prefix = get_hash_from_filename(best_jsonl.name)
    return find_existing_html(output_path, hash_prefix)


def open_in_browser(path: Path):
    """Open a file in the default browser."""
    webbrowser.open(path.as_uri())


# ---------------------------------------------------------------------------
# Chat organization (Shorts / Archived)
# ---------------------------------------------------------------------------


def fix_dashboard_link(html_path: Path, index_filename: str):
    """Update dashboard link when an HTML file is moved deeper into a subfolder.

    Files in Chats/ have href="../dashboard". When moved to Chats/Shorts/ or
    Chats/Archived/, the link needs to become href="../../dashboard".
    """
    try:
        content = html_path.read_text(encoding="utf-8")
        old_href = f'href="../{index_filename}"'
        new_href = f'href="../../{index_filename}"'
        if old_href in content:
            content = content.replace(old_href, new_href)
            html_path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def manage_shorts(config: dict) -> dict:
    """Move small inactive HTML files to the Shorts subfolder.

    Only runs if shorts.enabled is true in config.
    """
    stats = {"moved": 0, "duplicates_removed": 0}

    if not config.get("shorts", {}).get("enabled", False):
        return stats

    chats_path = config["_resolved"]["chats_path"]
    source_path = config["_resolved"]["source_path"]
    folder_name = config["shorts"].get("folder", "Shorts")
    max_size = config["shorts"].get("max_size_kb", 40) * 1024
    inactive_days = config.get("inactive_days", 5)
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")

    shorts_path = chats_path / folder_name
    shorts_path.mkdir(exist_ok=True)
    cutoff_time = datetime.now() - timedelta(days=inactive_days)

    html_files = [f for f in chats_path.glob("*.html") if f.is_file()]

    for html_file in html_files:
        if html_file.stat().st_size < max_size:
            jsonl_file = find_jsonl_for_html(source_path, html_file.name)
            last_used = datetime.fromtimestamp(
                jsonl_file.stat().st_mtime if jsonl_file else html_file.stat().st_mtime
            )
            if last_used < cutoff_time:
                try:
                    dest = shorts_path / html_file.name
                    html_file.rename(dest)
                    fix_dashboard_link(dest, index_filename)
                    stats["moved"] += 1
                except Exception as e:
                    print(f"  Warning: could not move {html_file.name}: {e}")

    # Remove duplicates in shorts folder (keep newest)
    seen = {}
    for html_file in shorts_path.glob("*.html"):
        name = html_file.name
        if name in seen:
            existing = seen[name]
            if html_file.stat().st_mtime > existing.stat().st_mtime:
                existing.unlink()
                seen[name] = html_file
            else:
                html_file.unlink()
            stats["duplicates_removed"] += 1
        else:
            seen[name] = html_file

    return stats


def manage_archived(config: dict) -> dict:
    """Move large inactive HTML files to the Archived subfolder.

    Only runs if archive.enabled is true in config.
    """
    stats = {"archived": 0}

    if not config.get("archive", {}).get("enabled", False):
        return stats

    chats_path = config["_resolved"]["chats_path"]
    source_path = config["_resolved"]["source_path"]
    folder_name = config["archive"].get("folder", "Archived")
    inactive_days = config.get("inactive_days", 5)
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")

    archived_path = chats_path / folder_name
    archived_path.mkdir(exist_ok=True)
    cutoff_time = datetime.now() - timedelta(days=inactive_days)

    for html_file in chats_path.glob("*.html"):
        if not html_file.is_file():
            continue

        jsonl_file = find_jsonl_for_html(source_path, html_file.name)
        last_used = datetime.fromtimestamp(
            jsonl_file.stat().st_mtime if jsonl_file else html_file.stat().st_mtime
        )

        if last_used < cutoff_time:
            dest = archived_path / html_file.name
            try:
                if dest.exists():
                    if dest.stat().st_mtime < html_file.stat().st_mtime:
                        dest.unlink()
                        html_file.rename(dest)
                        fix_dashboard_link(dest, index_filename)
                    else:
                        html_file.unlink()
                else:
                    html_file.rename(dest)
                    fix_dashboard_link(dest, index_filename)
                stats["archived"] += 1
            except Exception as e:
                print(f"  Warning: could not archive {html_file.name}: {e}")

    return stats


# ---------------------------------------------------------------------------
# Dashboard (index) generation
# ---------------------------------------------------------------------------


def get_chat_category(html_path: Path, output_path: Path, config: dict) -> str:
    """Determine the category of a chat based on its location."""
    if html_path is None:
        return "No HTML"
    try:
        relative = html_path.relative_to(output_path)
    except ValueError:
        return "Active"
    parts = relative.parts
    # Structure: Chats/file.html (Active), Chats/Shorts/file.html, Chats/Archived/file.html
    if len(parts) > 2:
        archive_folder = config.get("archive", {}).get("folder", "Archived")
        shorts_folder = config.get("shorts", {}).get("folder", "Shorts")
        if parts[1] == archive_folder:
            return "Archived"
        elif parts[1] == shorts_folder:
            return "Short"
    return "Active"


def format_project_name(raw_name: str) -> str:
    """Format a Claude Code project directory name for display.

    Converts encoded paths like 'C--Users-john-projects-myapp' to 'projects/myapp'.
    """
    if not raw_name:
        return "Unknown"
    name = Path(raw_name).name

    # Claude Code encodes full paths with dashes as separators
    # Pattern: DriveLetter--Users-username-rest (Windows)
    # Pattern: -home-username-rest (Linux/Mac)
    parts = name.split("-")

    # Find 'Users' or 'home' to skip system prefix + username
    for i, part in enumerate(parts):
        if part.lower() in ("users", "home") and i + 1 < len(parts):
            meaningful = [p for p in parts[i + 2 :] if p]
            if meaningful:
                return "/".join(meaningful)
            break

    return name


def build_sessions_index(projects_path: Path) -> dict:
    """Build an index of rich metadata from all sessions-index.json files.

    Returns a dict keyed by session hash (first 8 chars).
    """
    index = {}
    for project_dir in projects_path.iterdir():
        if not project_dir.is_dir():
            continue
        index_file = project_dir / "sessions-index.json"
        if not index_file.exists():
            continue
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for entry in data.get("entries", []):
            sid = entry.get("sessionId", "")
            if sid:
                index[sid[:8]] = entry
    return index


def find_jsonl_project(projects_path: Path, hash_prefix: str) -> str:
    """Find which project directory contains a JSONL file by hash."""
    for project_dir in projects_path.iterdir():
        if not project_dir.is_dir():
            continue
        for _ in project_dir.glob(f"{hash_prefix}*.jsonl"):
            return format_project_name(project_dir.name)
    return ""


def parse_html_filename(filename: str) -> dict:
    """Extract date and hash from an HTML filename.

    Expected format: 'Chat YYYY-MM-DD HH-MM hash.html'
    """
    match = re.match(r"Chat (\d{4}-\d{2}-\d{2}) (\d{2}-\d{2})\s+(\S+)", filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2).replace("-", ":")
        hash_part = match.group(3).split(".")[0]
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            return {"date": dt, "hash": hash_part[:8]}
        except ValueError:
            pass
    return {"date": None, "hash": get_hash_from_filename(filename)}


def is_snapshot_only(jsonl_path: Path) -> bool:
    """Check if a JSONL file contains only file-history-snapshot entries."""
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                except (json.JSONDecodeError, ValueError):
                    continue
                if obj.get("type") in ("user", "assistant"):
                    return False
        return True
    except OSError:
        return True


def extract_jsonl_metadata(jsonl_path: Path) -> dict:
    """Extract enrichment metadata directly from a JSONL file.

    Reads the file once, collecting: real user message count,
    first user prompt text, working directory (cwd), git branch,
    and custom title (from /rename command).
    """
    result = {
        "messages": 0,
        "first_prompt": "",
        "first_prompt_full": "",
        "cwd": "",
        "git_branch": "",
        "custom_title": "",
        "recap": "",
    }

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                except (json.JSONDecodeError, ValueError):
                    continue

                # Capture custom title entries (from /rename command)
                if obj.get("type") == "custom-title":
                    result["custom_title"] = obj.get("customTitle", "")
                    continue

                # Recap: keep the LAST obtainable summary while scanning.
                # Sources: type=summary (auto-compaction), system away
                # summaries, and user messages flagged isCompactSummary.
                if obj.get("type") == "summary":
                    s = obj.get("summary", "")
                    if isinstance(s, str) and s.strip():
                        result["recap"] = s.strip()
                    continue

                if obj.get("type") == "system":
                    s = obj.get("awaySummary", "")
                    if isinstance(s, str) and s.strip():
                        result["recap"] = s.strip()
                    continue

                if obj.get("type") != "user":
                    continue

                if obj.get("isCompactSummary"):
                    msg_c = obj.get("message", {})
                    c = msg_c.get("content", "") if isinstance(msg_c, dict) else ""
                    txt = ""
                    if isinstance(c, str):
                        txt = c
                    elif isinstance(c, list):
                        for item in c:
                            if isinstance(item, dict) and item.get("type") == "text":
                                txt = item.get("text", "") or ""
                                break
                    if txt.strip():
                        result["recap"] = txt.strip()
                    continue

                msg = obj.get("message", {})
                content = msg.get("content", "")

                # Skip tool_result messages
                if isinstance(content, list):
                    if any(
                        isinstance(item, dict) and item.get("type") == "tool_result"
                        for item in content
                    ):
                        continue

                result["messages"] += 1

                # Capture metadata from first real user message
                if result["messages"] == 1:
                    result["cwd"] = obj.get("cwd", "")
                    result["git_branch"] = obj.get("gitBranch", "")

                    if isinstance(content, str):
                        result["first_prompt"] = content[:100]
                        result["first_prompt_full"] = content
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                t = item.get("text", "") or ""
                                result["first_prompt"] = t[:100]
                                result["first_prompt_full"] = t
                                break
    except OSError:
        pass

    return result


def _fmt_dt(dt, time_format: str = "12h") -> str:
    """Format a datetime as `YYYY-MM-DD <time>`; time per time_format (12h/24h)."""
    pat = "%H:%M" if time_format == "24h" else "%I:%M %p"
    return dt.strftime(f"%Y-%m-%d {pat}")


def collect_chats_data(config: dict) -> list[dict]:
    """Collect metadata for all generated HTML chat files."""
    output_path = config["_resolved"]["output_path"]
    source_path = config["_resolved"]["source_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")
    sessions_meta = build_sessions_index(source_path)

    # Pre-build a {sessionId: btw_count} map from history.jsonl so the dashboard
    # can show a /btw count column without re-reading each chat's HTML.
    history_path = source_path.parent / "history.jsonl"
    if not history_path.exists():
        history_path = Path.home() / ".claude" / "history.jsonl"
    btw_counts: dict[str, int] = {}
    if history_path.exists():
        for e in _collect_btw_history(history_path):
            sid = e.get("sessionId") or ""
            if sid:
                btw_counts[sid] = btw_counts.get(sid, 0) + 1

    chats_data = []
    seen_hashes = set()

    for html_path in output_path.rglob("*.html"):
        if html_path.name == index_filename:
            continue

        parsed = parse_html_filename(html_path.name)
        hash_prefix = parsed["hash"]

        chat_key = f"{hash_prefix}_{'Agent' if 'Agent-' in html_path.name else 'main'}"
        if chat_key in seen_hashes:
            continue
        seen_hashes.add(chat_key)

        category = get_chat_category(html_path, output_path, config)
        html_size = html_path.stat().st_size

        try:
            html_link = str(html_path.relative_to(output_path))
        except ValueError:
            html_link = html_path.name

        meta = sessions_meta.get(hash_prefix, {})

        if meta:
            name = meta.get("customTitle") or meta.get("summary") or "Untitled"
            project = format_project_name(meta.get("projectPath", ""))
            project_full = meta.get("projectPath", "")
            branch = meta.get("gitBranch", "")
            first_prompt = (meta.get("firstPrompt", "") or "")[:100]
            summary = meta.get("summary", "")

            # Enrich from JSONL (sessions-index may be stale)
            jsonl_file = find_jsonl_for_html(source_path, html_path.name)
            if jsonl_file:
                jsonl_meta = extract_jsonl_metadata(jsonl_file)
                messages = jsonl_meta["messages"] if jsonl_meta["messages"] > 0 else meta.get("messageCount", 0)
                recap = jsonl_meta["recap"]
                first_prompt_full = jsonl_meta["first_prompt_full"] or first_prompt

                # If sessions-index.json lacks customTitle, try JSONL
                if not meta.get("customTitle") and jsonl_meta.get("custom_title"):
                    name = jsonl_meta["custom_title"]
            else:
                messages = meta.get("messageCount", 0)
                recap = ""
                first_prompt_full = first_prompt

            created = meta.get("created", "")
            modified = meta.get("modified", "")
            try:
                created_dt = datetime.fromisoformat(
                    created.replace("Z", "+00:00")
                ).astimezone()
                created_str = _fmt_dt(created_dt, config["time_format"])
                created_sort = created_dt.timestamp()
            except (ValueError, OSError):
                created_str = (
                    _fmt_dt(parsed["date"], config["time_format"]) if parsed["date"] else "N/A"
                )
                created_sort = parsed["date"].timestamp() if parsed["date"] else 0
            try:
                modified_dt = datetime.fromisoformat(
                    modified.replace("Z", "+00:00")
                ).astimezone()
                modified_str = _fmt_dt(modified_dt, config["time_format"])
                modified_sort = modified_dt.timestamp()
            except (ValueError, OSError):
                modified_sort = 0

            # Always check JSONL mtime - sessions-index.json may be stale
            if jsonl_file:
                jsonl_mtime = jsonl_file.stat().st_mtime
                if jsonl_mtime > modified_sort:
                    mt = datetime.fromtimestamp(jsonl_mtime)
                    modified_str = _fmt_dt(mt, config["time_format"])
                    modified_sort = jsonl_mtime
            elif modified_sort == 0:
                modified_str = "N/A"
        else:
            name = html_path.stem
            if "Agent-" in name:
                name = f"[Agent] {name}"

            # Enrich from JSONL if available
            jsonl_file = find_jsonl_for_html(source_path, html_path.name)

            if jsonl_file:
                jsonl_meta = extract_jsonl_metadata(jsonl_file)
                messages = jsonl_meta["messages"]
                branch = jsonl_meta["git_branch"]
                first_prompt = jsonl_meta["first_prompt"]
                first_prompt_full = jsonl_meta["first_prompt_full"]
                recap = jsonl_meta["recap"]

                # Use custom title from JSONL if available (set by /rename)
                if jsonl_meta["custom_title"]:
                    name = jsonl_meta["custom_title"]

                if jsonl_meta["cwd"]:
                    project = format_project_name(jsonl_meta["cwd"])
                    project_full = jsonl_meta["cwd"]
                else:
                    project = find_jsonl_project(source_path, hash_prefix)
                    project_full = project
            else:
                project = find_jsonl_project(source_path, hash_prefix)
                project_full = project
                messages = 0
                branch = ""
                first_prompt = ""
                first_prompt_full = ""
                recap = ""

            summary = ""

            if parsed["date"]:
                created_str = _fmt_dt(parsed["date"], config["time_format"])
                created_sort = parsed["date"].timestamp()
            else:
                created_str = "N/A"
                created_sort = 0

            if jsonl_file:
                mt = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                modified_str = _fmt_dt(mt, config["time_format"])
                modified_sort = mt.timestamp()
            else:
                modified_str = created_str
                modified_sort = created_sort

        # Full session ID: from sessions-index, JSONL filename, or hash prefix
        if meta and meta.get("sessionId"):
            session_id_full = meta["sessionId"]
        elif jsonl_file and not jsonl_file.name.startswith("agent-"):
            session_id_full = jsonl_file.stem
        else:
            session_id_full = hash_prefix

        chats_data.append(
            {
                "session_id": hash_prefix,
                "session_id_full": session_id_full,
                "name": name,
                "project": project,
                "project_full": project_full,
                "category": category,
                "created": created_str,
                "created_sort": created_sort,
                "modified": modified_str,
                "modified_sort": modified_sort,
                "messages": messages,
                "branch": branch,
                "first_prompt": first_prompt,
                "first_prompt_full": first_prompt_full,
                "recap": recap,
                "summary": summary,
                "html_link": html_link,
                "html_size": html_size,
                "btw_count": btw_counts.get(session_id_full, 0),
            }
        )

    chats_data.sort(key=lambda x: x["modified_sort"], reverse=True)
    return chats_data


def _sub_row_html(kind: str, label: str, text: str, parent_uuid: str) -> str:
    """One collapsible sub-row (Recap / First prompt) below a dashboard row."""
    text = text.strip()
    preview = " ".join(text.split())[:220]
    return (
        f'\n<tr class="sub-row sub-{kind}" data-parent="{escape(parent_uuid)}" data-kind="{kind}">'
        f'<td colspan="99"><details class="sub-details" data-parent="{escape(parent_uuid)}" data-kind="{kind}">'
        f'<summary><span class="sub-label">{label}</span>'
        f'<span class="sub-preview">{escape(preview)}</span></summary>'
        f'<div class="sub-full">{escape(text)}</div></details></td></tr>'
    )


def generate_index(config: dict) -> int:
    """Generate the interactive dashboard HTML file.

    Returns the total number of chats included.
    """
    output_path = config["_resolved"]["output_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")
    inactive_days = config.get("inactive_days", 5)
    shorts_enabled = config.get("shorts", {}).get("enabled", False)
    archive_enabled = config.get("archive", {}).get("enabled", False)
    shorts_folder = config.get("shorts", {}).get("folder", "Shorts")
    archive_folder = config.get("archive", {}).get("folder", "Archived")
    shorts_max_kb = config.get("shorts", {}).get("max_size_kb", 40)

    chats_data = collect_chats_data(config)

    total_chats = len(chats_data)
    active_count = sum(1 for c in chats_data if c["category"] == "Active")
    short_count = sum(1 for c in chats_data if c["category"] == "Short")
    archived_count = sum(1 for c in chats_data if c["category"] == "Archived")

    # Build table rows
    rows_html = ""
    for chat in chats_data:
        link_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>'
        if chat["html_link"]:
            link_cell = f'<td class="link-cell"><a href="{escape(chat["html_link"])}" title="Open chat">{link_svg}</a></td>'
        else:
            link_cell = '<td class="link-cell"><span class="no-link">-</span></td>'

        cat_class = chat["category"].lower().replace(" ", "-")

        if chat["messages"] > 0:
            msgs_cell = f'<td class="num-cell">{chat["messages"]}</td>'
        else:
            # Native title tooltip: an HTML tooltip span here overflowed the cell
            # and stretched the whole fixed-layout table scroll area.
            msgs_cell = '<td class="num-cell" title="No enriched data available. This chat is not indexed in Claude Code sessions-index.json. Common with old, very short, agent, or recently active sessions.">?</td>'

        uuid_full = chat['session_id_full']

        btw_n = chat.get("btw_count", 0)
        btw_cell = (
            f'<td class="hidden-col btw-col num-cell">{btw_n}</td>'
            if btw_n
            else '<td class="hidden-col btw-col num-cell"></td>'
        )

        sub_rows = ""
        recap_txt = (chat.get("recap") or "").strip()
        fp_txt = (chat.get("first_prompt_full") or chat.get("first_prompt") or "").strip()
        if recap_txt:
            sub_rows += _sub_row_html("recap", "Recap", recap_txt, uuid_full)
        if fp_txt:
            sub_rows += _sub_row_html("prompt", "First prompt", fp_txt, uuid_full)

        rows_html += f'''<tr data-uuid="{escape(uuid_full)}" data-modified="{chat['modified_sort']}" data-created="{chat['created_sort']}" data-messages="{chat['messages']}" data-btw="{btw_n}" data-size="{chat['html_size']}">
<td class="name-cell" title="{escape(chat['name'])}">{escape(chat['name'])}</td>
{link_cell}
<td class="project-cell" title="{escape(chat['project_full'])}">{escape(chat['project'])}</td>
<td class="category-cell {cat_class}">{escape(chat['category'])}</td>
<td class="date-cell">{escape(str(chat['created']))}</td>
<td class="date-cell">{escape(str(chat['modified']))}</td>
{msgs_cell}
<td class="uuid-col" title="{escape(uuid_full)}"><span class="uuid-text">{escape(uuid_full)}</span> <button class="copy-btn" onclick="copyUuid(this)" title="Copy UUID"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></td>
{btw_cell}
<td class="hidden-col branch-col">{escape(chat['branch'])}</td>
<td class="hidden-col size-col">{chat['html_size'] // 1024}KB</td>
</tr>{sub_rows}
'''

    # Build category stats line
    stats_parts = [f"Total: {total_chats} chats", f"Active: {active_count}"]
    if shorts_enabled:
        stats_parts.append(f"Shorts: {short_count}")
    if archive_enabled:
        stats_parts.append(f"Archived: {archived_count}")
    stats_line = " | ".join(stats_parts)

    # Build category filter checkboxes
    filter_checkboxes = '<label><input type="checkbox" id="filterActive" checked> Active</label>'
    if shorts_enabled:
        filter_checkboxes += '\n            <label><input type="checkbox" id="filterShort"> Shorts</label>'
    if archive_enabled:
        filter_checkboxes += '\n            <label><input type="checkbox" id="filterArchived"> Archived</label>'

    # Build category tooltip
    tooltip_lines = f'<strong>Active:</strong> Chats used within the last {inactive_days} days. Kept in the root folder for quick access.'
    if shorts_enabled:
        tooltip_lines += f'<br><br><strong>Short:</strong> Small chats (&lt;{shorts_max_kb}KB) inactive for {inactive_days}+ days. Moved to {shorts_folder}/ to keep root clean.'
    if archive_enabled:
        tooltip_lines += f'<br><br><strong>Archived:</strong> Chats inactive for {inactive_days}+ days. Moved to {archive_folder}/ automatically.'

    # Build filter JS
    filter_js_vars = "const showActive = document.getElementById('filterActive').checked;"
    filter_js_listeners = "document.getElementById('filterActive').addEventListener('change', () => { filterTable(); saveState(); });"
    filter_js_conditions = "(category === 'Active' && showActive)"

    if shorts_enabled:
        filter_js_vars += "\n            const showShort = document.getElementById('filterShort').checked;"
        filter_js_listeners += "\n        document.getElementById('filterShort').addEventListener('change', () => { filterTable(); saveState(); });"
        filter_js_conditions += " ||\n                    (category === 'Short' && showShort)"

    if archive_enabled:
        filter_js_vars += "\n            const showArchived = document.getElementById('filterArchived').checked;"
        filter_js_listeners += "\n        document.getElementById('filterArchived').addEventListener('change', () => { filterTable(); saveState(); });"
        filter_js_conditions += " ||\n                    (category === 'Archived' && showArchived)"

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Code Chat Viewer v{APP_VERSION}">
    <link rel="icon" type="image/png" href="data:image/png;base64,{ICON_FAVICON_BASE64}">
    <title>Code Chat Viewer - Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        html, body {{
            height: 100%;
            overflow: hidden;
        }}

        body {{
            font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #FFFFFF;
            color: #1E1E1E;
            line-height: 1.4;
            font-size: 13px;
            display: flex;
            flex-direction: column;
        }}

        .header {{
            background: #2D2D30;
            color: #CCCCCC;
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-title {{
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .header-actions {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .header-btn {{
            color: #CCCCCC;
            text-decoration: none;
            font-size: 11px;
            padding: 4px 10px;
            border: 1px solid #555;
            border-radius: 3px;
            transition: all 0.15s;
            white-space: nowrap;
        }}

        .header-btn:hover {{
            background: #444;
            border-color: #888;
            color: #FFF;
        }}

        .header-btn.feedback {{
            border-color: #007ACC;
            color: #7EC8F0;
        }}

        .header-btn.feedback:hover {{
            background: #007ACC;
            border-color: #007ACC;
            color: #FFF;
        }}

        .header-btn.release {{
            border-color: #10893E;
            color: #6BCB8B;
        }}

        .header-btn.release:hover {{
            background: #10893E;
            border-color: #10893E;
            color: #FFF;
        }}

        .header-controls {{
            display: flex;
            gap: 8px;
        }}

        .terminal-btn {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}

        .btn-close {{ background: #E81123; }}
        .btn-minimize {{ background: #FFB900; }}
        .btn-maximize {{ background: #10893E; }}

        .stats-bar {{
            background: #F3F3F3;
            border-bottom: 1px solid #E0E0E0;
            padding: 10px 20px;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .toolbar {{
            background: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            padding: 12px 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}

        .search-input {{
            padding: 6px 12px;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            font-family: inherit;
            font-size: 13px;
            width: 280px;
        }}

        .search-input:focus {{
            outline: none;
            border-color: #007ACC;
        }}

        .exclude-input {{
            padding: 6px 12px;
            border: 1px solid #E8A0A0;
            border-radius: 4px;
            font-family: inherit;
            font-size: 13px;
            width: 200px;
            background: #FFF8F8;
        }}

        .exclude-input:focus {{
            outline: none;
            border-color: #C06060;
        }}

        .filter-group {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .filter-group label {{
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            font-size: 12px;
        }}

        .columns-toggle {{
            display: flex;
            gap: 8px;
            align-items: center;
            margin-left: auto;
        }}

        .columns-toggle label {{
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 3px;
            cursor: pointer;
            color: #666;
        }}

        .help-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            background: #666;
            color: white;
            border-radius: 50%;
            font-size: 11px;
            cursor: help;
            margin-left: 5px;
        }}

        .tooltip {{
            position: relative;
        }}

        .tooltip .tooltip-text {{
            visibility: hidden;
            width: 280px;
            background: #333;
            color: #fff;
            text-align: left;
            padding: 10px;
            border-radius: 6px;
            position: absolute;
            z-index: 1000;
            top: 125%;
            right: 0;
            font-size: 11px;
            line-height: 1.5;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}

        .tooltip:hover .tooltip-text {{
            visibility: visible;
        }}

        .table-container {{
            padding: 15px 20px;
            flex: 1;
            min-width: 0;
            overflow-y: scroll;
            overflow-x: auto;
        }}

        /* Column widths live as data-width on each <th>; syncColumnWidths()
           applies them (0px while hidden — in fixed layout Chromium lets
           display:none headers contribute their width as ghost columns).
           Name has no width: it flexes and absorbs the leftover space.
           The table min-width (visible columns + Name minimum) keeps
           horizontal scroll appearing only when columns no longer fit. */
        table {{
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: 12px;
        }}

        th, td {{
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #E0E0E0;
            overflow: hidden;
        }}

        th {{
            background: #F3F3F3;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}

        th:hover {{ background: #E8E8E8; }}
        th[data-sort="none"] {{ cursor: default; }}

        th.sorted-asc::after {{ content: " \\25B2"; font-size: 10px; }}
        th.sorted-desc::after {{ content: " \\25BC"; font-size: 10px; }}

        tr:hover {{ background: #F8F8F8; }}

        .link-cell {{ text-align: center; }}
        .link-cell a {{ color: #007ACC; display: inline-flex; }}
        .link-cell a:hover {{ color: #005A9E; }}
        .no-link {{ color: #CCC; }}

        .name-cell {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .project-cell {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .category-cell {{
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 3px;
            text-align: center;
            font-size: 11px;
        }}

        .category-cell.active {{ background: #E3F2E1; color: #10893E; }}
        .category-cell.short {{ background: #FFF3CD; color: #856404; }}
        .category-cell.archived {{ background: #F0F0F0; color: #666; }}
        .category-cell.no-html {{ background: #FFE0E0; color: #C00; }}

        .date-cell {{ white-space: nowrap; font-size: 11px; color: #666; }}
        .num-cell {{ text-align: right; font-family: monospace; white-space: nowrap; }}
        /* Hidden columns collapse to true 0px instead of display:none —
           in fixed layout Chromium keeps counting display:none cells in the
           table scroll area, leaving ghost blank space after the last column. */
        .hidden-col {{
            padding: 0 !important;
            border: 0 !important;
            font-size: 0;
            overflow: hidden;
            white-space: nowrap;
        }}
        .branch-col {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .uuid-col {{
            font-family: monospace;
            font-size: 10px;
            color: #999;
            overflow: hidden;
            white-space: nowrap;
        }}
        .uuid-col .uuid-text {{
            overflow: hidden;
            text-overflow: ellipsis;
            display: inline-block;
            max-width: 100px;
            vertical-align: middle;
        }}
        .copy-btn {{
            background: none;
            border: 1px solid #DDD;
            border-radius: 3px;
            cursor: pointer;
            padding: 2px 4px;
            color: #999;
            vertical-align: middle;
            line-height: 1;
            transition: all 0.15s;
        }}
        .copy-btn:hover {{
            background: #F0F0F0;
            border-color: #999;
            color: #333;
        }}

        /* Sub-rows: Recap / First prompt (collapsible, toggled from Columns) */
        .sub-row {{ display: none; }}
        .sub-row.show {{ display: table-row; }}
        .sub-row td {{
            background: #FAFAF7;
            padding: 0 10px 5px 38px;
        }}
        .sub-details summary {{
            cursor: pointer;
            list-style: none;
            display: flex;
            gap: 8px;
            align-items: baseline;
            padding: 4px 0 2px;
            font-size: 11px;
            color: #666;
        }}
        .sub-details summary::-webkit-details-marker {{ display: none; }}
        .sub-details summary::before {{ content: "\\25B6"; font-size: 8px; color: #999; flex: none; }}
        .sub-details[open] summary::before {{ content: "\\25BC"; }}
        .sub-label {{
            font-weight: 600;
            font-size: 10px;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: #777;
            flex: none;
        }}
        .sub-preview {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            min-width: 0;
            flex: 1;
        }}
        .sub-details[open] .sub-preview {{ display: none; }}
        .sub-full {{
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-size: 11.5px;
            color: #444;
            padding: 2px 0 6px 16px;
            max-height: 420px;
            overflow-y: auto;
        }}

        .btw-col {{
            font-family: monospace;
            font-size: 11px;
            text-align: right;
            white-space: nowrap;
        }}

        .footer {{
            background: #F3F3F3;
            border-top: 1px solid #E0E0E0;
            padding: 10px 20px;
            text-align: center;
            color: #666;
            font-size: 11px;
        }}

        .footer a {{ color: #666; text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
        .hidden-row {{ display: none; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            <img src="data:image/png;base64,{ICON_BASE64}" alt="" style="height:16px;width:16px;vertical-align:middle;margin-right:6px;" onerror="this.style.display='none'">
            <span>Code Chat Viewer - Dashboard</span>
            <span class="app-version" style="color:#999;font-size:11px;margin-left:8px;">v{APP_VERSION}</span>
        </div>
        <div class="header-actions">
            <a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener" class="header-btn feedback" title="Report an issue or send feedback on GitHub">Feedback</a>
            <a href="https://github.com/oskar-gm/code-chat-viewer/releases/latest" target="_blank" rel="noopener" class="header-btn release" title="Latest release — check for updates">Latest release</a>
        </div>
        <div class="header-controls">
            <span class="terminal-btn btn-close"></span>
            <span class="terminal-btn btn-minimize"></span>
            <span class="terminal-btn btn-maximize"></span>
        </div>
    </div>

    <div class="stats-bar">
        <div>{stats_line}</div>
        <div>Generated: {_fmt_dt(datetime.now(), config["time_format"])}</div>
    </div>

    <div class="toolbar">
        <input type="text" class="search-input" id="searchInput" placeholder="Filter by name, project...">
        <input type="text" class="exclude-input" id="excludeInput" placeholder="Exclude...">

        <div class="filter-group">
            <span>Filter:</span>
            {filter_checkboxes}
            <span class="tooltip">
                <span class="help-icon">?</span>
                <span class="tooltip-text">
                    <strong>Categories:</strong><br><br>
                    {tooltip_lines}
                </span>
            </span>
        </div>

        <div class="columns-toggle">
            <span>Columns:</span>
            <label><input type="checkbox" data-col="btw-col"> BTW</label>
            <label><input type="checkbox" data-col="branch-col"> Branch</label>
            <label><input type="checkbox" data-col="size-col"> Size</label>
            <label><input type="checkbox" data-sub="recap"> Recap</label>
            <label><input type="checkbox" data-sub="prompt"> First prompt</label>
        </div>
    </div>

    <div class="table-container">
        <table id="chatsTable">
            <thead>
                <tr>
                    <th data-sort="name">Name</th>
                    <th data-sort="none" data-width="40">Link</th>
                    <th data-sort="project" data-width="130">Project</th>
                    <th data-sort="category" data-width="95">Category</th>
                    <th data-sort="created" data-width="160">Created</th>
                    <th data-sort="modified" class="sorted-desc" data-width="160">Last Used</th>
                    <th data-sort="messages" data-width="64">Msgs</th>
                    <th class="uuid-col" data-sort="uuid" data-width="140">UUID</th>
                    <th class="hidden-col btw-col" data-sort="btw" data-width="64">BTW</th>
                    <th class="hidden-col branch-col" data-sort="branch" data-width="130">Branch</th>
                    <th class="hidden-col size-col" data-sort="size" data-width="72">Size</th>
                </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <a href="https://github.com/oskar-gm/code-chat-viewer" target="_blank">Code Chat Viewer</a> |        <a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener">Feedback</a>
    </div>

    <script>
        /* State persistence (localStorage, 5h TTL) */
        const STATE_KEY = 'ccv-dashboard-state';
        const STATE_TTL = 5 * 60 * 60 * 1000;

        function saveState() {{
            const state = {{
                ts: Date.now(),
                sort: currentSort,
                search: document.getElementById('searchInput').value,
                exclude: document.getElementById('excludeInput').value,
                filters: {{}},
                columns: {{}}
            }};
            document.querySelectorAll('.filter-group input[type="checkbox"]').forEach(cb => {{
                state.filters[cb.id] = cb.checked;
            }});
            document.querySelectorAll('.columns-toggle input[data-col]').forEach(cb => {{
                state.columns[cb.dataset.col] = cb.checked;
            }});
            state.subs = {{}};
            document.querySelectorAll('.columns-toggle input[data-sub]').forEach(cb => {{
                state.subs[cb.dataset.sub] = cb.checked;
            }});
            state.openSubs = {{}};
            document.querySelectorAll('#chatsTable .sub-details[open]').forEach(d => {{
                state.openSubs[d.dataset.parent + '|' + d.dataset.kind] = true;
            }});
            localStorage.setItem(STATE_KEY, JSON.stringify(state));
        }}

        function loadState() {{
            try {{
                const raw = localStorage.getItem(STATE_KEY);
                if (!raw) return null;
                const state = JSON.parse(raw);
                if (Date.now() - state.ts > STATE_TTL) {{
                    localStorage.removeItem(STATE_KEY);
                    return null;
                }}
                return state;
            }} catch (e) {{
                return null;
            }}
        }}

        /* Table sorting */
        let currentSort = {{ col: 'modified', dir: 'desc' }};

        document.querySelectorAll('th[data-sort]').forEach(th => {{
            if (th.dataset.sort === 'none') return;
            th.addEventListener('click', () => {{
                const col = th.dataset.sort;
                const dir = (currentSort.col === col && currentSort.dir === 'desc') ? 'asc' : 'desc';
                document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                th.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
                currentSort = {{ col, dir }};
                sortTable(col, dir);
                saveState();
            }});
        }});

        function sortTable(col, dir) {{
            const tbody = document.querySelector('#chatsTable tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not(.sub-row)'));
            rows.sort((a, b) => {{
                let aVal, bVal;
                if (col === 'modified' || col === 'created') {{
                    aVal = parseFloat(a.dataset[col]) || 0;
                    bVal = parseFloat(b.dataset[col]) || 0;
                }} else if (col === 'messages') {{
                    aVal = parseInt(a.dataset.messages) || 0;
                    bVal = parseInt(b.dataset.messages) || 0;
                }} else if (col === 'btw') {{
                    aVal = parseInt(a.dataset.btw) || 0;
                    bVal = parseInt(b.dataset.btw) || 0;
                }} else if (col === 'size') {{
                    aVal = parseInt(a.dataset.size) || 0;
                    bVal = parseInt(b.dataset.size) || 0;
                }} else {{
                    const colIndex = {{ name: 0, project: 2, category: 3, uuid: 7, branch: 9 }}[col] || 0;
                    aVal = (a.cells[colIndex]?.textContent || '').trim().toLowerCase();
                    bVal = (b.cells[colIndex]?.textContent || '').trim().toLowerCase();
                }}
                if (typeof aVal === 'number') {{
                    return dir === 'asc' ? aVal - bVal : bVal - aVal;
                }}
                return dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});
            /* Sub-rows travel glued to their parent row */
            rows.forEach(row => {{
                tbody.appendChild(row);
                (subRowsOf[row.dataset.uuid] || []).forEach(sr => tbody.appendChild(sr));
            }});
        }}

        /* Sub-rows (Recap / First prompt): index by parent, searchable text */
        const subRowsOf = {{}};
        const subTextOf = {{}};
        const mainRowOf = {{}};
        document.querySelectorAll('#chatsTable tbody tr:not(.sub-row)').forEach(r => {{
            if (r.dataset.uuid) mainRowOf[r.dataset.uuid] = r;
        }});
        document.querySelectorAll('#chatsTable .sub-row').forEach(sr => {{
            const p = sr.dataset.parent;
            (subRowsOf[p] = subRowsOf[p] || []).push(sr);
            subTextOf[p] = (subTextOf[p] || '') + ' ' + sr.textContent.toLowerCase();
        }});

        /* A sub-row is visible when its type toggle is on AND its parent row
           passes the current filters. */
        function syncSubRows() {{
            const on = {{}};
            document.querySelectorAll('.columns-toggle input[data-sub]').forEach(cb => {{
                on[cb.dataset.sub] = cb.checked;
            }});
            document.querySelectorAll('#chatsTable .sub-row').forEach(sr => {{
                const parent = mainRowOf[sr.dataset.parent];
                const visible = !!parent && !parent.classList.contains('hidden-row') && !!on[sr.dataset.kind];
                sr.classList.toggle('show', visible);
            }});
        }}

        document.querySelectorAll('.columns-toggle input[data-sub]').forEach(cb => {{
            cb.addEventListener('change', () => {{ syncSubRows(); saveState(); }});
        }});

        document.querySelectorAll('#chatsTable .sub-details').forEach(d => {{
            d.addEventListener('toggle', saveState);
        }});

        /* Search and filter */
        document.getElementById('searchInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        document.getElementById('excludeInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        {filter_js_listeners}

        function filterTable() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const exclude = document.getElementById('excludeInput').value.toLowerCase();
            {filter_js_vars}

            document.querySelectorAll('#chatsTable tbody tr').forEach(row => {{
                if (row.classList.contains('sub-row')) return;
                const text = row.textContent.toLowerCase() + (subTextOf[row.dataset.uuid] || '');
                const category = row.querySelector('.category-cell')?.textContent || '';
                const matchesSearch = !search || text.includes(search);
                const matchesExclude = !exclude || !text.includes(exclude);
                const matchesFilter =
                    {filter_js_conditions};
                row.classList.toggle('hidden-row', !(matchesSearch && matchesExclude && matchesFilter));
            }});
            syncSubRows();
        }}

        /* Column sizing (fixed layout): visible columns get their data-width,
           hidden ones get 0px so they cannot contribute ghost width to the
           table grid. Table min-width = visible columns + Name minimum, so
           horizontal scroll only appears when columns no longer fit and the
           flexible Name column never gets crushed below its minimum. */
        const NAME_MIN_PX = 240;
        function syncColumnWidths() {{
            let sum = NAME_MIN_PX;
            document.querySelectorAll('#chatsTable thead th').forEach(th => {{
                if (!th.dataset.width) return;
                const hidden = th.classList.contains('hidden-col');
                th.style.width = hidden ? '0px' : th.dataset.width + 'px';
                if (!hidden) sum += parseInt(th.dataset.width, 10);
            }});
            document.getElementById('chatsTable').style.minWidth = sum + 'px';
        }}

        /* Column toggles */
        document.querySelectorAll('.columns-toggle input[data-col]').forEach(checkbox => {{
            checkbox.addEventListener('change', () => {{
                const colClass = checkbox.dataset.col;
                const show = checkbox.checked;
                document.querySelectorAll('.' + colClass).forEach(el => {{
                    el.classList.toggle('hidden-col', !show);
                }});
                syncColumnWidths();
                saveState();
            }});
        }});

        /* Restore state on load */
        const saved = loadState();
        if (saved) {{
            if (saved.search) document.getElementById('searchInput').value = saved.search;
            if (saved.exclude) document.getElementById('excludeInput').value = saved.exclude;
            Object.entries(saved.filters || {{}}).forEach(([id, checked]) => {{
                const el = document.getElementById(id);
                if (el) el.checked = checked;
            }});
            Object.entries(saved.columns || {{}}).forEach(([col, checked]) => {{
                const cb = document.querySelector(`.columns-toggle input[data-col="${{col}}"]`);
                if (cb) {{
                    cb.checked = checked;
                    document.querySelectorAll('.' + col).forEach(el => {{
                        el.classList.toggle('hidden-col', !checked);
                    }});
                }}
            }});
            Object.entries(saved.subs || {{}}).forEach(([kind, checked]) => {{
                const cb = document.querySelector(`.columns-toggle input[data-sub="${{kind}}"]`);
                if (cb) cb.checked = checked;
            }});
            Object.keys(saved.openSubs || {{}}).forEach(key => {{
                const [p, kind] = key.split('|');
                const d = document.querySelector(`.sub-details[data-parent="${{p}}"][data-kind="${{kind}}"]`);
                if (d) d.open = true;
            }});
            if (saved.sort) {{
                currentSort = saved.sort;
                document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                const th = document.querySelector(`th[data-sort="${{saved.sort.col}}"]`);
                if (th) th.classList.add(saved.sort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
                sortTable(saved.sort.col, saved.sort.dir);
            }}
        }}

        syncColumnWidths();
        filterTable();

        /* Copy UUID to clipboard */
        function copyUuid(btn) {{
            const uuid = btn.closest('.uuid-col').querySelector('.uuid-text').textContent;
            navigator.clipboard.writeText(uuid);
            const orig = btn.innerHTML;
            btn.textContent = 'OK';
            setTimeout(function() {{ btn.innerHTML = orig; }}, 1000);
        }}
    </script>
</body>
</html>'''

    output_file = output_path / index_filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    return total_chats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# BTW Queries view (option [3])
# ---------------------------------------------------------------------------


def _collect_btw_history(history_path: Path) -> list[dict]:
    """Read ~/.claude/history.jsonl and return all `/btw <query>` entries.
    Skips empty `/btw` invocations (the ones that produced `Usage:` errors)."""
    entries = []
    if not history_path.exists():
        return entries
    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            display = e.get("display", "") or ""
            if not display.startswith("/btw"):
                continue
            # Strip "/btw " prefix to extract the question text
            rest = display[len("/btw"):].lstrip()
            if not rest:
                continue  # Skip empty `/btw` invocations
            entries.append({
                "query": rest,
                "timestamp": e.get("timestamp", 0),
                "project": e.get("project", ""),
                "sessionId": e.get("sessionId", ""),
            })
    return entries


def _find_jsonl_by_session(source_path: Path, session_id: str) -> Path | None:
    """Find a JSONL file in source_path by exact session ID."""
    if not session_id:
        return None
    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


def _resolve_session_meta(
    source_path: Path, session_id: str, project_field: str,
    sessions_meta: dict, output_path: Path
) -> dict:
    """Resolve human-readable metadata for a session given its ID + project path.

    Returns: {title, project, project_full, html_link}
      - html_link: relative path to the chat HTML (if generated) or empty.
    """
    title = "Untitled chat"
    project = format_project_name(Path(project_field).name) if project_field else ""
    project_full = project_field
    html_link = ""

    jsonl_file = _find_jsonl_by_session(source_path, session_id)
    if jsonl_file:
        try:
            title = resolve_chat_title(jsonl_file, sessions_meta)
        except Exception:
            pass
        project = format_project_name(jsonl_file.parent.name)
        # Try to locate the generated HTML
        hash_prefix = get_hash_from_filename(jsonl_file.name)
        existing = find_existing_html(output_path, hash_prefix)
        if existing:
            try:
                html_link = str(existing.relative_to(output_path))
            except ValueError:
                html_link = existing.name

    return {
        "title": title,
        "project": project,
        "project_full": project_full,
        "html_link": html_link,
    }


def generate_btw_view(config: dict) -> Path | None:
    """Aggregate all /btw queries from ~/.claude/history.jsonl and produce
    btw.html alongside the dashboard. Queries are grouped by chat (session),
    sorted by latest activity within each chat.

    Returns the output file path, or None if no /btw queries were found."""
    source_path = config["_resolved"]["source_path"]
    output_path = config["_resolved"]["output_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")

    # history.jsonl lives at ~/.claude/history.jsonl (the parent of projects/)
    history_path = source_path.parent / "history.jsonl"
    if not history_path.exists():
        history_path = Path.home() / ".claude" / "history.jsonl"

    entries = _collect_btw_history(history_path)
    if not entries:
        print(f"  No /btw queries found in {history_path}")
        return None

    print(f"  Found {len(entries)} /btw queries in history.jsonl")

    # Group by sessionId
    by_session: dict[str, list[dict]] = {}
    for e in entries:
        sid = e.get("sessionId") or "unknown"
        by_session.setdefault(sid, []).append(e)

    sessions_meta = build_sessions_index(source_path)

    groups = []
    for sid, items in by_session.items():
        items.sort(key=lambda x: x.get("timestamp", 0))
        latest = items[-1].get("timestamp", 0)
        first_project = items[0].get("project", "") if items else ""
        meta = _resolve_session_meta(
            source_path, sid, first_project, sessions_meta, output_path
        )
        groups.append({
            "session_id": sid,
            "title": meta["title"],
            "project": meta["project"],
            "project_full": meta["project_full"],
            "html_link": meta["html_link"],
            "queries": items,
            "latest_ts": latest,
            "count": len(items),
        })

    # Sort sessions by latest /btw activity (most recent first)
    groups.sort(key=lambda g: -g["latest_ts"])

    total_queries = sum(g["count"] for g in groups)
    total_sessions = len(groups)
    all_ts = [q["timestamp"] for g in groups for q in g["queries"] if q.get("timestamp")]
    first_dt = datetime.fromtimestamp(min(all_ts) / 1000).strftime("%Y-%m-%d") if all_ts else "—"
    last_dt = datetime.fromtimestamp(max(all_ts) / 1000).strftime("%Y-%m-%d") if all_ts else "—"

    # Build HTML for each group (each chat = collapsible <details>)
    sections_html = []
    for g in groups:
        title_html = escape(g["title"])
        if g["html_link"]:
            title_html = (
                f'<a href="{escape(g["html_link"])}" class="btw-session-link" '
                f'title="Open chat in CCV" onclick="event.stopPropagation()">{title_html} '
                f'<span class="btw-open-icon">↗</span></a>'
            )
        queries_html = []
        for q in g["queries"]:
            ts = q.get("timestamp", 0)
            try:
                dt_str = _fmt_dt(datetime.fromtimestamp(ts / 1000), config["time_format"])
            except (ValueError, OSError, OverflowError):
                dt_str = "—"
            queries_html.append(
                f'<article class="btw-query">'
                f'<div class="btw-q-text">{escape(q["query"])}</div>'
                f'<div class="btw-q-meta">{escape(dt_str)}</div>'
                f'</article>'
            )
        proj_chip = (
            f'<span class="btw-chip btw-chip-proj" title="{escape(g["project_full"])}">{escape(g["project"])}</span>'
            if g["project"] else ""
        )
        sections_html.append(
            f'<details class="btw-session">'
            f'<summary class="btw-session-header">'
            f'<span class="btw-toggle">▼</span>'
            f'<span class="btw-session-title">{title_html}</span>'
            f'<span class="btw-session-meta">'
            f'<span class="btw-chip btw-chip-count">{g["count"]}</span>'
            f'{proj_chip}'
            f'<span class="btw-chip btw-chip-uuid" title="Session UUID">{escape(g["session_id"][:8])}</span>'
            f'</span>'
            f'</summary>'
            f'<div class="btw-queries">'
            f'{"".join(queries_html)}'
            f'</div>'
            f'</details>'
        )

    sections_block = "\n".join(sections_html)
    gen_time = _fmt_dt(datetime.now(), config["time_format"])

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Code Chat Viewer v{APP_VERSION} — BTW view">
    <link rel="icon" type="image/png" href="data:image/png;base64,{ICON_FAVICON_BASE64}">
    <title>Code Chat Viewer — BTW Queries</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ height: 100%; }}
        body {{
            font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #FFFFFF;
            color: #1E1E1E;
            font-size: 12px;
            line-height: 1.45;
            display: flex;
            flex-direction: column;
        }}
        .btw-header {{
            background: #2D2D30;
            color: #CCCCCC;
            padding: 8px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            font-size: 12px;
        }}
        .btw-header-title {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }}
        .btw-header-title img {{ height: 14px; width: 14px; }}
        .btw-header a {{ color: #7EC8F0; text-decoration: none; font-size: 11px; }}
        .btw-header a:hover {{ text-decoration: underline; }}
        .btw-stats {{
            background: #F4F0E8;
            border-bottom: 1px solid #E0DBCB;
            padding: 6px 16px;
            font-size: 11px;
            color: #6B4226;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .btw-stats strong {{ color: #9A4A2E; font-weight: 600; }}
        .btw-toolbar {{
            background: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            padding: 6px 16px;
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .btw-search {{
            flex: 1;
            padding: 4px 10px;
            border: 1px solid #CCC;
            border-radius: 3px;
            font-family: inherit;
            font-size: 12px;
            background: #FFF;
        }}
        .btw-search:focus {{ outline: none; border-color: #C76A4D; }}
        .btw-tbtn {{
            padding: 4px 10px;
            border: 1px solid #D8CCB8;
            background: #F4F0E8;
            color: #6B4226;
            border-radius: 3px;
            cursor: pointer;
            font-family: inherit;
            font-size: 11px;
        }}
        .btw-tbtn:hover {{ background: #EFE6D8; }}
        .btw-container {{
            padding: 10px 16px;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }}
        .btw-session {{
            background: #FFFFFF;
            border: 1px solid #E5E0D2;
            border-left: 3px solid #C76A4D;
            border-radius: 4px;
            margin-bottom: 6px;
            overflow: hidden;
        }}
        .btw-session > summary {{
            list-style: none;
            cursor: pointer;
        }}
        .btw-session > summary::-webkit-details-marker {{ display: none; }}
        .btw-session-header {{
            background: #FAF7F2;
            padding: 6px 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }}
        .btw-toggle {{
            color: #C76A4D;
            font-size: 10px;
            display: inline-block;
            width: 10px;
            transition: transform 0.15s;
        }}
        .btw-session:not([open]) .btw-toggle {{ transform: rotate(-90deg); }}
        .btw-session-title {{
            font-size: 13px;
            font-weight: 600;
            color: #1E1E1E;
            flex: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .btw-session-link {{ color: #1E1E1E; text-decoration: none; }}
        .btw-session-link:hover {{ color: #9A4A2E; }}
        .btw-open-icon {{ color: #9A4A2E; font-size: 11px; margin-left: 3px; }}
        .btw-session-meta {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            flex-shrink: 0;
        }}
        .btw-chip {{
            padding: 1px 6px;
            border-radius: 8px;
            background: #EFE6D8;
            color: #6B4226;
            font-family: inherit;
            white-space: nowrap;
        }}
        .btw-chip-count {{ background: #C76A4D; color: #FFF; font-weight: 600; }}
        .btw-chip-uuid {{ font-size: 9px; color: #888; background: #F0F0F0; font-family: 'Consolas', monospace; }}
        .btw-queries {{ padding: 2px 10px 6px 10px; }}
        .btw-query {{
            padding: 6px 9px;
            margin-top: 4px;
            background: #FFFFFF;
            border: 1px solid #F0E8D8;
            border-left: 2px solid #C76A4D;
            border-radius: 3px;
        }}
        .btw-q-text {{
            font-size: 13px;
            color: #1E1E1E;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.45;
        }}
        .btw-q-meta {{
            margin-top: 3px;
            font-size: 9px;
            color: #999;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        .btw-query.hidden {{ display: none; }}
        .btw-session.hidden {{ display: none; }}
        .btw-footer {{
            background: #F3F3F3;
            border-top: 1px solid #E0E0E0;
            padding: 6px 16px;
            text-align: center;
            color: #666;
            font-size: 10px;
        }}
        .btw-footer a {{ color: #666; text-decoration: none; }}
        .btw-footer a:hover {{ text-decoration: underline; }}
        @media (max-width: 700px) {{
            .btw-stats, .btw-toolbar, .btw-header {{ flex-wrap: wrap; }}
            .btw-session-title {{ white-space: normal; }}
        }}
    </style>
</head>
<body>
    <header class="btw-header">
        <div class="btw-header-title">
            <img src="data:image/png;base64,{ICON_BASE64}" alt="">
            <span>Code Chat Viewer — BTW Queries</span>
        </div>
        <div><a href="{escape(index_filename)}">← Back to Dashboard</a></div>
    </header>

    <div class="btw-stats">
        <div>
            <strong>{total_queries}</strong> queries in <strong>{total_sessions}</strong> chats &nbsp;|&nbsp;
            From <strong>{first_dt}</strong> to <strong>{last_dt}</strong>
        </div>
        <div>Generated: {gen_time}</div>
    </div>

    <div class="btw-toolbar">
        <input type="text" class="btw-search" id="btwSearch"
               placeholder="Filter by query text, chat title or project..." autofocus>
        <button class="btw-tbtn" id="btwToggleAll" title="Expand / collapse all chats">▶ Expand all</button>
    </div>

    <main class="btw-container">
{sections_block}
    </main>

    <footer class="btw-footer">
        <a href="https://github.com/oskar-gm/code-chat-viewer" target="_blank">Code Chat Viewer</a> |        <a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener">Feedback</a>
    </footer>

    <script>
        const sessions = document.querySelectorAll('.btw-session');

        // Real-time filter: hide non-matching queries, hide sessions without visible queries,
        // and auto-open sessions that have matches (so the user sees them).
        const input = document.getElementById('btwSearch');
        input.addEventListener('input', function() {{
            const term = input.value.trim().toLowerCase();
            sessions.forEach(section => {{
                const sessionText = section.querySelector('.btw-session-header').textContent.toLowerCase();
                const sessionMatch = !term || sessionText.includes(term);
                let anyQueryVisible = false;
                section.querySelectorAll('.btw-query').forEach(q => {{
                    const t = q.textContent.toLowerCase();
                    const match = !term || t.includes(term) || sessionMatch;
                    q.classList.toggle('hidden', !match);
                    if (match) anyQueryVisible = true;
                }});
                section.classList.toggle('hidden', !anyQueryVisible);
                if (term && anyQueryVisible) section.open = true;
            }});
        }});

        // Toggle expand/collapse all (single button — label reflects next action)
        const toggleBtn = document.getElementById('btwToggleAll');
        const refreshToggleLabel = () => {{
            const visible = Array.from(sessions).filter(s => !s.classList.contains('hidden'));
            const anyOpen = visible.some(s => s.open);
            toggleBtn.textContent = anyOpen ? '▶ Collapse all' : '▼ Expand all';
        }};
        toggleBtn.addEventListener('click', () => {{
            const visible = Array.from(sessions).filter(s => !s.classList.contains('hidden'));
            const anyOpen = visible.some(s => s.open);
            visible.forEach(s => {{ s.open = !anyOpen; }});
            refreshToggleLabel();
        }});
        document.addEventListener('toggle', e => {{
            if (e.target && e.target.classList && e.target.classList.contains('btw-session')) {{
                refreshToggleLabel();
            }}
        }}, true);
        refreshToggleLabel();
    </script>
</body>
</html>"""

    output_file = output_path / "btw.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return output_file


def main():
    # Parse flags
    name_search = None
    current_mode = False
    current_jsonl_path = None
    force_regen = "--force" in sys.argv
    btw_mode = "--btw" in sys.argv

    if "--name" in sys.argv:
        idx = sys.argv.index("--name")
        if idx + 1 < len(sys.argv):
            name_search = sys.argv[idx + 1]

    if "--current" in sys.argv:
        current_mode = True
        idx = sys.argv.index("--current")
        if (idx + 1 < len(sys.argv)
                and not sys.argv[idx + 1].startswith("--")):
            current_jsonl_path = Path(sys.argv[idx + 1])

    print()
    print("=" * 52)
    print("  Code Chat Viewer - Chat Manager")
    print("=" * 52)
    print()

    config = load_config()
    output_path = config["_resolved"]["output_path"]
    chats_path = config["_resolved"]["chats_path"]
    source_path = config["_resolved"]["source_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")
    include_agents = config.get("agents", {}).get("include", True)
    min_agent_size = config.get("agents", {}).get("min_size_kb", 3) * 1024

    output_path.mkdir(parents=True, exist_ok=True)
    chats_path.mkdir(exist_ok=True)

    # Copy shortcut to output folder for easy access (only if missing)
    shortcut_src = PROJECT_ROOT / "Code Chat Viewer.lnk"
    shortcut_dst = output_path / "Update Chats.lnk"
    if shortcut_src.exists() and not shortcut_dst.exists():
        shutil.copy2(shortcut_src, shortcut_dst)

    stats = {"new": [], "updated": [], "skipped": 0, "errors": {}}
    sessions_meta = build_sessions_index(source_path)

    # Pre-load /btw entries from ~/.claude/history.jsonl once for the whole run.
    # Each chat will only see entries whose sessionId matches its UUID.
    history_path = source_path.parent / "history.jsonl"
    if not history_path.exists():
        history_path = Path.home() / ".claude" / "history.jsonl"
    history_entries = _collect_btw_history(history_path) if history_path.exists() else []

    env_note = "  (from CODE_CHAT_VIEWER_DIR)" if config["_resolved"]["output_from_env"] else ""
    print(f"  Source:  {source_path}")
    print(f"  Output:  {output_path}{env_note}")
    print(f"  Config:  {config['_resolved']['config_path']}")
    print()

    # Interactive mode selection (manual/double-click only)
    if (sys.stdout.isatty() and not name_search and not current_mode
            and not force_regen and not btw_mode):
        print("  [1] Normal — update only modified chats (fast)")
        print("  [2] Force  — regenerate ALL chats from scratch (slow)")
        print("  [3] BTW    — generate btw.html from /btw history (skip chats)")
        print()
        choice = input("  Select mode [1]: ").strip()
        if choice == "2":
            force_regen = True
            print()
            print("  Force mode: all chats will be regenerated.")
        elif choice == "3":
            btw_mode = True
            print()
            print("  BTW mode: generating btw.html from history.jsonl.")
        print()

    # ---- BTW mode short-circuit: skip chat scan / organize / dashboard ----
    if btw_mode:
        print("-" * 52)
        print("  Generating BTW view...")
        btw_file = generate_btw_view(config)
        print()
        print("=" * 52)
        if btw_file:
            print(f"  BTW view ready: {btw_file}")
            print("=" * 52)
            print()
            open_in_browser(btw_file)
        else:
            print("  No /btw queries found — nothing to generate.")
            print("=" * 52)
            print()
        if sys.stdout.isatty() and os.name == 'nt':
            _countdown_close(60)
        return

    print("-" * 52)
    print("  Scanning chats...")

    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            filename = jsonl_file.name
            file_size = jsonl_file.stat().st_size
            is_agent = filename.startswith("agent-")

            if is_agent and not include_agents:
                continue
            if is_agent and file_size < min_agent_size:
                continue
            if is_snapshot_only(jsonl_file):
                # Clean up existing HTML if it was generated before this filter
                temp_hash = get_hash_from_filename(filename) if not filename.startswith("agent-") else filename.replace("agent-", "").replace(".jsonl", "")[:2]
                orphan_html = find_existing_html(output_path, temp_hash, filename.startswith("agent-"))
                if orphan_html:
                    orphan_html.unlink()
                continue

            agent_suffix = ""
            if is_agent:
                agent_id = filename.replace("agent-", "").replace(".jsonl", "")[:2]
                agent_suffix = f"Agent-{agent_id}"
                hash_prefix = agent_id
            else:
                hash_prefix = get_hash_from_filename(filename)

            display_name = (
                f"{hash_prefix} {agent_suffix}".strip()
                if not is_agent
                else agent_suffix
            )

            existing_html = find_existing_html(output_path, hash_prefix, is_agent)

            if existing_html:
                if force_regen or needs_update(jsonl_file, existing_html):
                    existing_html.unlink()
                    result, error = generate_chat_html(
                        jsonl_file, chats_path, agent_suffix,
                        f"../{index_filename}", sessions_meta,
                        history_entries=history_entries,
                        time_format=config["time_format"],
                    )
                    if result:
                        print(f"  UPDATED: {display_name}")
                        stats["updated"].append(display_name)
                    else:
                        stats["errors"][error] = stats["errors"].get(error, 0) + 1
                else:
                    stats["skipped"] += 1
            else:
                result, error = generate_chat_html(
                    jsonl_file, chats_path, agent_suffix,
                    f"../{index_filename}", sessions_meta,
                    history_entries=history_entries,
                    time_format=config["time_format"],
                )
                if result:
                    print(f"  NEW:     {display_name}")
                    stats["new"].append(display_name)
                else:
                    stats["errors"][error] = stats["errors"].get(error, 0) + 1

    # Scan summary
    total_scanned = len(stats["new"]) + len(stats["updated"]) + stats["skipped"]
    print(f"  Done: {total_scanned} files scanned.")
    if stats["new"]:
        print(f"  New: {len(stats['new'])}")
    if stats["updated"]:
        print(f"  Updated: {len(stats['updated'])}")

    # Organize chats
    print()
    print("-" * 52)
    print()
    shorts_stats = manage_shorts(config)
    archived_stats = manage_archived(config)

    # Generate dashboard
    print("  Generating dashboard...")
    index_total = generate_index(config)

    # Summary
    total_processed = len(stats["new"]) + len(stats["updated"])

    print()
    print("=" * 52)
    print("  SUMMARY")
    print("-" * 52)

    if stats["new"]:
        print(f"  New:       {len(stats['new']):3}")
    if stats["updated"]:
        print(f"  Updated:   {len(stats['updated']):3}")
    if stats["skipped"]:
        print(f"  Unchanged: {stats['skipped']:3}")
    if stats["errors"]:
        for error_type, count in stats["errors"].items():
            print(f"  Error ({error_type}): {count}")

    if shorts_stats["moved"]:
        print(f"  Moved to Shorts:   {shorts_stats['moved']:3}")
    if shorts_stats.get("duplicates_removed", 0):
        print(f"  Duplicates removed: {shorts_stats['duplicates_removed']:3}")
    if archived_stats["archived"]:
        print(f"  Archived:  {archived_stats['archived']:3}")

    print(f"  Dashboard: {index_total:3} chats in {index_filename}")

    if total_processed == 0 and shorts_stats["moved"] == 0 and archived_stats["archived"] == 0:
        print("  Everything is up to date.")

    dashboard_path = output_path / index_filename
    print("=" * 52)
    print()

    # Determine what to open
    target_html = None

    if name_search:
        # --name: search by chat name (100% reliable)
        target_html = find_chat_by_name(name_search, source_path, output_path)
        if target_html:
            print(f"  Match: {target_html.name}")
        else:
            print(f"  No chat found matching: {name_search}")

    elif current_mode:
        # --current: auto-detect or use explicit path
        jsonl = current_jsonl_path or find_current_jsonl(source_path)
        if jsonl and jsonl.exists():
            hash_prefix = get_hash_from_filename(jsonl.name)
            target_html = find_existing_html(output_path, hash_prefix)
            if target_html:
                print(f"  Current: {target_html.name}")
            else:
                print(f"  HTML not found for: {jsonl.name}")
        else:
            print("  Could not detect current session.")

    if target_html:
        open_in_browser(target_html)
    elif sys.stdout.isatty():
        open_in_browser(dashboard_path)
    else:
        print(f"  Dashboard: {dashboard_path}")

    # Auto-close countdown in interactive mode (Windows terminal)
    if sys.stdout.isatty() and os.name == 'nt':
        _countdown_close(60)


def _countdown_close(seconds: int):
    """Show a countdown and close. Press Enter to close immediately."""
    stop_event = threading.Event()

    def wait_for_enter():
        try:
            input()
        except EOFError:
            pass
        stop_event.set()

    listener = threading.Thread(target=wait_for_enter, daemon=True)
    listener.start()

    for remaining in range(seconds, 0, -1):
        print(f"\r  Closing in {remaining}s — press Enter to close now...", end="", flush=True)
        if stop_event.wait(timeout=1):
            break

    print("\r" + " " * 60 + "\r", end="")


if __name__ == "__main__":
    main()
