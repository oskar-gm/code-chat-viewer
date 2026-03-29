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

    # Resolve paths
    source_path = Path(config["source"]["projects_path"]).expanduser().resolve()
    output_path = Path(config["output"]["folder"]).expanduser()
    if not output_path.is_absolute():
        output_path = (PROJECT_ROOT / output_path).resolve()
    else:
        output_path = output_path.resolve()

    config["_resolved"] = {
        "source_path": source_path,
        "output_path": output_path,
        "chats_path": output_path / "Chats",
        "config_path": config_path,
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
    sessions_meta: dict = None
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
        "cwd": "",
        "git_branch": "",
        "custom_title": "",
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

                if obj.get("type") != "user":
                    continue

                if obj.get("isCompactSummary"):
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
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                result["first_prompt"] = (item.get("text", "") or "")[:100]
                                break
    except OSError:
        pass

    return result


def collect_chats_data(config: dict) -> list[dict]:
    """Collect metadata for all generated HTML chat files."""
    output_path = config["_resolved"]["output_path"]
    source_path = config["_resolved"]["source_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")
    sessions_meta = build_sessions_index(source_path)

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

                # If sessions-index.json lacks customTitle, try JSONL
                if not meta.get("customTitle") and jsonl_meta.get("custom_title"):
                    name = jsonl_meta["custom_title"]
            else:
                messages = meta.get("messageCount", 0)

            created = meta.get("created", "")
            modified = meta.get("modified", "")
            try:
                created_dt = datetime.fromisoformat(
                    created.replace("Z", "+00:00")
                ).astimezone()
                created_str = created_dt.strftime("%Y-%m-%d %H:%M")
                created_sort = created_dt.timestamp()
            except (ValueError, OSError):
                created_str = (
                    parsed["date"].strftime("%Y-%m-%d %H:%M") if parsed["date"] else "N/A"
                )
                created_sort = parsed["date"].timestamp() if parsed["date"] else 0
            try:
                modified_dt = datetime.fromisoformat(
                    modified.replace("Z", "+00:00")
                ).astimezone()
                modified_str = modified_dt.strftime("%Y-%m-%d %H:%M")
                modified_sort = modified_dt.timestamp()
            except (ValueError, OSError):
                modified_sort = 0

            # Always check JSONL mtime - sessions-index.json may be stale
            if jsonl_file:
                jsonl_mtime = jsonl_file.stat().st_mtime
                if jsonl_mtime > modified_sort:
                    mt = datetime.fromtimestamp(jsonl_mtime)
                    modified_str = mt.strftime("%Y-%m-%d %H:%M")
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

            summary = ""

            if parsed["date"]:
                created_str = parsed["date"].strftime("%Y-%m-%d %H:%M")
                created_sort = parsed["date"].timestamp()
            else:
                created_str = "N/A"
                created_sort = 0

            if jsonl_file:
                mt = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                modified_str = mt.strftime("%Y-%m-%d %H:%M")
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
                "summary": summary,
                "html_link": html_link,
                "html_size": html_size,
            }
        )

    chats_data.sort(key=lambda x: x["modified_sort"], reverse=True)
    return chats_data


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
            msgs_cell = '<td class="num-cell"><span class="tooltip"><span class="help-icon">?</span><span class="tooltip-text">No enriched data available. This chat is not indexed in Claude Code sessions-index.json. Common with old, very short, agent, or recently active sessions.</span></span></td>'

        uuid_full = chat['session_id_full']

        rows_html += f'''<tr data-modified="{chat['modified_sort']}" data-created="{chat['created_sort']}" data-messages="{chat['messages']}">
<td class="name-cell" title="{escape(chat['name'])}">{escape(chat['name'])}</td>
{link_cell}
<td class="project-cell" title="{escape(chat['project_full'])}">{escape(chat['project'])}</td>
<td class="category-cell {cat_class}">{escape(chat['category'])}</td>
<td class="date-cell">{escape(str(chat['created']))}</td>
<td class="date-cell">{escape(str(chat['modified']))}</td>
{msgs_cell}
<td class="hidden-col uuid-col" title="{escape(uuid_full)}"><span class="uuid-text">{escape(uuid_full)}</span> <button class="copy-btn" onclick="copyUuid(this)" title="Copy UUID"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></td>
<td class="hidden-col branch-col">{escape(chat['branch'])}</td>
<td class="hidden-col size-col">{chat['html_size'] // 1024}KB</td>
<td class="hidden-col prompt-col" title="{escape(chat['first_prompt'])}">{escape(chat['first_prompt'][:40])}{"..." if len(chat['first_prompt']) > 40 else ""}</td>
</tr>
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
    <meta name="generator" content="Code Chat Viewer v2.2.0">
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
            overflow: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        th, td {{
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #E0E0E0;
        }}

        th {{
            background: #F3F3F3;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}

        th:hover {{ background: #E8E8E8; }}

        th.sorted-asc::after {{ content: " \\25B2"; font-size: 10px; }}
        th.sorted-desc::after {{ content: " \\25BC"; font-size: 10px; }}

        tr:hover {{ background: #F8F8F8; }}

        .link-cell {{ width: 30px; text-align: center; }}
        .link-cell a {{ color: #007ACC; display: inline-flex; }}
        .link-cell a:hover {{ color: #005A9E; }}
        .no-link {{ color: #CCC; }}

        .name-cell {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .project-cell {{
            max-width: 150px;
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
        .num-cell {{ text-align: right; font-family: monospace; }}
        .hidden-col {{ display: none; }}
        .uuid-col {{
            font-family: monospace;
            font-size: 10px;
            color: #999;
            max-width: 140px;
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

        .prompt-col {{
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
            color: #666;
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
        </div>
        <div class="header-actions">
            <a href="mailto:oscar@nucleoia.es?subject=Code%20Chat%20Viewer%20-%20Feedback" class="header-btn feedback" title="Send feedback">Feedback</a>
        </div>
        <div class="header-controls">
            <span class="terminal-btn btn-close"></span>
            <span class="terminal-btn btn-minimize"></span>
            <span class="terminal-btn btn-maximize"></span>
        </div>
    </div>

    <div class="stats-bar">
        <div>{stats_line}</div>
        <div>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
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
            <label><input type="checkbox" data-col="uuid-col"> UUID</label>
            <label><input type="checkbox" data-col="branch-col"> Branch</label>
            <label><input type="checkbox" data-col="size-col"> Size</label>
            <label><input type="checkbox" data-col="prompt-col"> First prompt</label>
        </div>
    </div>

    <div class="table-container">
        <table id="chatsTable">
            <thead>
                <tr>
                    <th data-sort="name">Name</th>
                    <th data-sort="none">Link</th>
                    <th data-sort="project">Project</th>
                    <th data-sort="category">Category</th>
                    <th data-sort="created">Created</th>
                    <th data-sort="modified" class="sorted-desc">Last Used</th>
                    <th data-sort="messages">Msgs</th>
                    <th class="hidden-col uuid-col" data-sort="none">UUID</th>
                    <th class="hidden-col branch-col" data-sort="branch">Branch</th>
                    <th class="hidden-col size-col" data-sort="none">Size</th>
                    <th class="hidden-col prompt-col" data-sort="none">First prompt</th>
                </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <a href="https://github.com/oskar-gm/code-chat-viewer" target="_blank">Code Chat Viewer</a> |
        <a href="https://nucleoia.es" target="_blank">nucleoia.es</a> |
        <a href="mailto:oscar@nucleoia.es?subject=Code%20Chat%20Viewer%20-%20Feedback">Feedback</a>
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
            const rows = Array.from(tbody.querySelectorAll('tr'));
            rows.sort((a, b) => {{
                let aVal, bVal;
                if (col === 'modified' || col === 'created') {{
                    aVal = parseFloat(a.dataset[col]) || 0;
                    bVal = parseFloat(b.dataset[col]) || 0;
                }} else if (col === 'messages') {{
                    aVal = parseInt(a.dataset.messages) || 0;
                    bVal = parseInt(b.dataset.messages) || 0;
                }} else {{
                    const colIndex = {{ name: 0, project: 2, category: 3, branch: 8 }}[col] || 0;
                    aVal = a.cells[colIndex]?.textContent.toLowerCase() || '';
                    bVal = b.cells[colIndex]?.textContent.toLowerCase() || '';
                }}
                if (typeof aVal === 'number') {{
                    return dir === 'asc' ? aVal - bVal : bVal - aVal;
                }}
                return dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});
            rows.forEach(row => tbody.appendChild(row));
        }}

        /* Search and filter */
        document.getElementById('searchInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        document.getElementById('excludeInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        {filter_js_listeners}

        function filterTable() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const exclude = document.getElementById('excludeInput').value.toLowerCase();
            {filter_js_vars}

            document.querySelectorAll('#chatsTable tbody tr').forEach(row => {{
                const text = row.textContent.toLowerCase();
                const category = row.querySelector('.category-cell')?.textContent || '';
                const matchesSearch = !search || text.includes(search);
                const matchesExclude = !exclude || !text.includes(exclude);
                const matchesFilter =
                    {filter_js_conditions};
                row.classList.toggle('hidden-row', !(matchesSearch && matchesExclude && matchesFilter));
            }});
        }}

        /* Column toggles */
        document.querySelectorAll('.columns-toggle input[data-col]').forEach(checkbox => {{
            checkbox.addEventListener('change', () => {{
                const colClass = checkbox.dataset.col;
                const show = checkbox.checked;
                document.querySelectorAll('.' + colClass).forEach(el => {{
                    el.classList.toggle('hidden-col', !show);
                }});
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
            if (saved.sort) {{
                currentSort = saved.sort;
                document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                const th = document.querySelector(`th[data-sort="${{saved.sort.col}}"]`);
                if (th) th.classList.add(saved.sort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
                sortTable(saved.sort.col, saved.sort.dir);
            }}
        }}

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


def main():
    # Parse flags
    name_search = None
    current_mode = False
    current_jsonl_path = None
    force_regen = "--force" in sys.argv

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

    print(f"  Source:  {source_path}")
    print(f"  Output:  {output_path}")
    print(f"  Config:  {config['_resolved']['config_path']}")
    print()

    # Interactive mode selection (manual/double-click only)
    if sys.stdout.isatty() and not name_search and not current_mode and not force_regen:
        print("  [1] Normal — update only modified chats (fast)")
        print("  [2] Force  — regenerate ALL chats from scratch (slow)")
        print()
        choice = input("  Select mode [1]: ").strip()
        if choice == "2":
            force_regen = True
            print()
            print("  Force mode: all chats will be regenerated.")
        print()

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
