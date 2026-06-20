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
        "agents": {"include": include_agents, "min_size_kb": min_agent_kb, "include_compaction": False},
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
    AGENT_HTML_MAP,
    parse_chat_json,
    generate_html,
    get_chat_timestamp,
    generate_output_filename,
    ICON_BASE64,
    ICON_FAVICON_BASE64,
    KNOWN_MESSAGE_TYPES,
    KNOWN_METADATA_TYPES,
    KNOWN_CONTENT_TYPES,
    is_caveat_message,
    is_stdout_message,
    is_task_notification,
    parse_command_tags,
    is_image_source_message,
)

# ---------------------------------------------------------------------------
# Hash & file utilities
# ---------------------------------------------------------------------------


def agent_hash_from_filename(filename: str) -> str:
    """Unique id for an agent chat: the final '-' segment of agent-[name-]<hash>
    (the agentId-like suffix). Unique even across same-named agents, unlike a
    fixed-length prefix that collides once there are hundreds of agents."""
    stem = Path(filename).stem
    body = stem[len("agent-"):] if stem.startswith("agent-") else stem
    return body.rsplit("-", 1)[-1]


def get_hash_from_filename(filename: str) -> str:
    """Extract the hash prefix from a JSONL or HTML filename.

    Regular chats use the first 8 chars of the UUID; agent chats use the full
    agentId-like suffix (see agent_hash_from_filename) so 675 agents don't collide.
    """
    name = Path(filename).stem

    if name.startswith("agent-"):
        return agent_hash_from_filename(name)

    parts = name.split()
    if parts:
        last_part = parts[-1]
        if last_part.startswith("Agent-"):
            return last_part[len("Agent-"):]
        return last_part[:8]

    return name.split("-")[0][:8]


def is_fork_context_ref(jsonl_path: Path) -> bool:
    """A file under subagents/ whose first record is a fork context reference
    (`type: fork-context-ref`), not a real agent chat with navigable messages."""
    try:
        with open(jsonl_path, encoding="utf-8") as fh:
            first = fh.readline()
        return json.loads(first).get("type") == "fork-context-ref"
    except (OSError, ValueError):
        return False


def agent_first_record(jsonl_path: Path) -> dict:
    """First JSONL record of an agent chat (carries agentId, slug, sessionId…)."""
    try:
        with open(jsonl_path, encoding="utf-8") as fh:
            return json.loads(fh.readline())
    except (OSError, ValueError):
        return {}


def build_agent_invocations(parent_jsonl: Path) -> dict:
    """Map {agentId: (subagent_type, description)} for the agents a parent session
    launched. The Agent tool_use carries subagent_type + description; the matching
    tool_result's `toolUseResult.agentId` ties it to the agent chat by tool_use_id.
    """
    tu = {}    # tool_use_id -> (subagent_type, description)
    res = {}   # agentId -> tool_use_id
    try:
        with open(parent_jsonl, encoding="utf-8") as fh:
            for line in fh:
                if '"Agent"' not in line and '"toolUseResult"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                msg = o.get("message", {})
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, list):
                    for it in content:
                        if not isinstance(it, dict):
                            continue
                        if it.get("type") == "tool_use" and it.get("name") == "Agent":
                            inp = it.get("input", {}) if isinstance(it.get("input"), dict) else {}
                            tu[it.get("id")] = (inp.get("subagent_type", "") or "", inp.get("description", "") or "")
                        elif it.get("type") == "tool_result":
                            tur = o.get("toolUseResult")
                            if isinstance(tur, dict) and tur.get("agentId"):
                                res[tur["agentId"]] = it.get("tool_use_id")
    except OSError:
        return {}
    return {aid: tu[tuid] for aid, tuid in res.items() if tuid in tu}


_AGENT_INV_CACHE = {}  # parent sessionId -> {agentId: (subagent_type, description)}


def agent_label(jsonl_path: Path) -> str:
    """'[subagent_type] · [description]' for an agent chat (from its parent
    session), or '' if it can't be resolved. Parent invocations are cached per
    session so the (possibly large) parent JSONL is read once."""
    try:
        psess = jsonl_path.parent.parent.name
        if psess not in _AGENT_INV_CACHE:
            _AGENT_INV_CACHE[psess] = build_agent_invocations(
                jsonl_path.parent.parent.parent / (psess + ".jsonl"))
        rec = agent_first_record(jsonl_path)
        sub, desc = _AGENT_INV_CACHE.get(psess, {}).get(rec.get("agentId", ""), ("", ""))
        return " · ".join(p for p in (sub, desc) if p)
    except (OSError, ValueError, IndexError):
        return ""


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
      4. JSONL ai-title (above the first prompt, below summary)
      5. JSONL first_prompt (truncated to 60 chars)
      6. "Untitled"
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

    # ai-title sits above the first prompt but below /rename and summary.
    return index_title or jsonl_meta.get("ai_title") or first_prompt or "Untitled"


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
        # Agent chat: the subagents/ folder hangs off the invoking session's UUID.
        agent_of = jsonl_path.parent.parent.name if agent_suffix else None
        if agent_suffix:
            label = agent_label(jsonl_path)
            if label:
                chat_title = label

        with redirect_stdout(io.StringIO()):
            generate_html(
                messages, str(output_path),
                dashboard_url=dashboard_filename,
                chat_title=chat_title,
                chat_uuid=jsonl_path.stem,
                history_entries=history_entries,
                time_format=time_format,
                agent_of=agent_of,
            )

        return base_name, None
    except Exception as e:
        return None, str(e)


def find_jsonl_for_html(projects_path: Path, html_name: str) -> Path | None:
    """Find the original JSONL file corresponding to an HTML by hash matching.

    Agent chats live under <project>/<session>/subagents/agent-*.jsonl, matched
    by their full agentId-like hash; regular chats sit at the project root.
    """
    hash_prefix = get_hash_from_filename(html_name)
    is_agent = "Agent-" in html_name

    for project_dir in projects_path.iterdir():
        if not project_dir.is_dir():
            continue
        if is_agent:
            for jsonl_file in project_dir.glob("*/subagents/agent-*.jsonl"):
                if agent_hash_from_filename(jsonl_file.name) == hash_prefix:
                    return jsonl_file
        else:
            for jsonl_file in project_dir.glob("*.jsonl"):
                if get_hash_from_filename(jsonl_file.name) == hash_prefix:
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
        "ai_title": "",
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

                # Capture AI-generated title (keep the last one seen)
                if obj.get("type") == "ai-title":
                    t = obj.get("aiTitle", "")
                    if isinstance(t, str) and t.strip():
                        result["ai_title"] = t.strip()
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

                # Skip non-real user messages (caveats, commands, stdout, task
                # notifications, image-source references): they are not prompts
                # and must not be counted or used as first_prompt / chat name.
                check_text = content if isinstance(content, str) else ""
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            check_text = item.get("text", "") or ""
                            break
                if (is_caveat_message(check_text)
                        or is_stdout_message(check_text)
                        or is_task_notification(check_text)
                        or parse_command_tags(check_text)
                        or is_image_source_message(content)):
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
        # Auxiliary dashboards (BTW, Audit) are reached from the "+" menu in the
        # toolbar, not listed as chat rows.
        if html_path.name == "btw.html" or html_path.name.startswith("CCV-Audit"):
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
                elif name == "Untitled" and jsonl_meta.get("ai_title"):
                    name = jsonl_meta["ai_title"]
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
                elif jsonl_meta.get("ai_title"):
                    name = jsonl_meta["ai_title"]
                elif "Agent-" in html_path.name:
                    # Agent name: "[subagent_type] · [Task description]" from the
                    # parent session (the agent JSONL has no descriptive title of
                    # its own); falls back to the invocation prompt.
                    name = (agent_label(jsonl_file) if jsonl_file else "") or first_prompt or name

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

        # Agent chats: the subagents/ folder hangs off the invoking session's
        # UUID, so parent_session links the agent to the chat that launched it.
        is_agent_chat = "Agent-" in html_path.name
        parent_session = ""
        if is_agent_chat and jsonl_file:
            parent_session = jsonl_file.parent.parent.name

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
                "jsonl_path": str(jsonl_file) if jsonl_file else "",
                "btw_count": btw_counts.get(session_id_full, 0),
                "is_agent": is_agent_chat,
                "parent_session": parent_session,
            }
        )

    # Flag orphan agents: their invoking chat (parent session) isn't among the
    # generated chats, so they can't be nested under it. Nesting itself is done
    # later via parent_session / data-parent.
    invoker_ids = {c["session_id_full"] for c in chats_data if not c["is_agent"]}
    for c in chats_data:
        c["is_orphan_agent"] = c["is_agent"] and c["parent_session"] not in invoker_ids

    # Order: normal chats by recency; each immediately followed by its agents in
    # invocation order (created asc); orphan agents (no invoker) go last.
    normals = sorted((c for c in chats_data if not c["is_agent"]),
                     key=lambda x: x["modified_sort"], reverse=True)
    agents_by_inv = sorted((c for c in chats_data if c["is_agent"]),
                           key=lambda x: x["created_sort"])
    by_parent = {}
    for ag in agents_by_inv:
        by_parent.setdefault(ag["parent_session"], []).append(ag)
    ordered = []
    for c in normals:
        ordered.append(c)
        ordered.extend(by_parent.get(c["session_id_full"], []))
    ordered.extend(ag for ag in agents_by_inv if ag.get("is_orphan_agent"))
    return ordered


# Physical columns in the dashboard table — keep in sync with its <thead>:
# sel + Name + Link + Project + Category + Created + Last Used + Msgs +
# UUID + BTW + Branch + Size. Sub-rows span EXACTLY this number: a larger
# colspan would declare ghost columns in fixed layout and crush Name.
DASHBOARD_COLS = 12


def _sub_row_html(kind: str, label: str, text: str, parent_uuid: str) -> str:
    """One collapsible sub-row (Recap / First prompt) below a dashboard row."""
    text = text.strip()
    preview = " ".join(text.split())[:220]
    return (
        f'\n<tr class="sub-row sub-{kind}" data-parent="{escape(parent_uuid)}" data-kind="{kind}">'
        f'<td colspan="{DASHBOARD_COLS}"><details class="sub-details" data-parent="{escape(parent_uuid)}" data-kind="{kind}">'
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

    # "+" menu: auxiliary dashboards (BTW, Audit) reached from the toolbar instead
    # of being listed as chat rows.
    aux_items = []
    if (output_path / "btw.html").exists():
        aux_items.append(("btw.html", "BTW queries"))
    for audit in sorted(output_path.glob("CCV-Audit*.html"), reverse=True):
        aux_items.append((audit.name, audit.stem))
    if aux_items:
        _links = "".join(
            f'<a href="{escape(n)}">{escape(lbl)}</a>'
            for n, lbl in aux_items)
        plus_menu_html = (
            '<div class="tb-block plus-wrap">'
            '<button type="button" id="plusBtn" class="tb-btn" '
            'title="Other views: BTW queries and Audit reports" '
            'aria-haspopup="true" aria-expanded="false">+</button>'
            f'<div id="plusMenu" class="plus-menu">{_links}</div></div>'
        )
    else:
        plus_menu_html = ""

    # Build table rows. Orphan agents (no invoker generated) are grouped after a
    # collapsible header row at the very end.
    rows_html = ""
    orphan_count = sum(1 for c in chats_data if c.get("is_orphan_agent"))
    orphan_header_done = False
    for chat in chats_data:
        if chat.get("is_orphan_agent") and not orphan_header_done:
            rows_html += (f'<tr class="orphan-header" data-agent="1"><td colspan="{DASHBOARD_COLS}">'
                          f'<span class="orphan-tw">&#9654;</span> Orphan agents '
                          f'<span class="orphan-n">({orphan_count})</span>'
                          f'<span class="orphan-hint"> &mdash; invoking chat not generated</span></td></tr>\n')
            orphan_header_done = True
        link_svg ='<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>'
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

        # Agent chats render as child rows nested under their invoking chat
        # (data-parent ties them so they stay glued when the table is sorted);
        # orphans (no invoker found) drop the nesting and are flagged.
        is_agent = chat.get("is_agent")
        if is_agent:
            orphan = chat.get("is_orphan_agent")
            agent_attr = (f' class="agent-row{" agent-orphan" if orphan else ""}" '
                          f'data-agent="1" data-parent="{escape(chat.get("parent_session", ""))}"')
            btitle = ("Agent chat — invoking chat not found (orphan)" if orphan
                      else "Agent chat (launched by the Task tool)")
            name_badge = (f'<span class="agent-badge{" agent-badge-orphan" if orphan else ""}" '
                          f'title="{btitle}">AGENT</span> ')
        else:
            agent_attr = ''
            name_badge = ''

        rows_html += f'''<tr{agent_attr} data-uuid="{escape(uuid_full)}" data-modified="{chat['modified_sort']}" data-created="{chat['created_sort']}" data-messages="{chat['messages']}" data-btw="{btw_n}" data-size="{chat['html_size']}" data-jsonl="{escape(chat.get('jsonl_path', ''))}" data-html="{escape(chat['html_link'])}">
<td class="hidden-col sel-col"><input type="checkbox" class="sel-box"></td>
<td class="name-cell" title="{escape(chat['name'])}">{name_badge}{escape(chat['name'])}</td>
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
    agent_count = sum(1 for c in chats_data if c.get("is_agent"))
    stats_parts = [f"Total: {total_chats} chats", f"Active: {active_count}"]
    if agent_count:
        stats_parts.append(f"Agents: {agent_count}")
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

        /* Loading overlay: hides the brief jump while the saved state (filters,
           columns, sort, search) is restored on load; removed once done. */
        .dash-loading {{
            position: fixed; inset: 0; z-index: 3000;
            background: #FFFFFF;
            display: flex; flex-direction: column; gap: 14px; align-items: center; justify-content: center;
            transition: opacity 0.25s ease;
        }}
        .dash-loading-msg {{ color: #9AA0A6; font-size: 13px; letter-spacing: 0.2px; }}
        .dash-loading.hidden {{ opacity: 0; pointer-events: none; }}
        .dash-loading-spin {{
            width: 28px; height: 28px;
            border: 3px solid rgba(0,0,0,0.12);
            border-top-color: #999;
            border-radius: 50%;
            animation: dashSpin 0.7s linear infinite;
        }}
        @keyframes dashSpin {{ to {{ transform: rotate(360deg); }} }}

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
            padding: 6px 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            row-gap: 4px;
        }}
        .tb-block {{
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: center;
            padding: 2px 16px;
            border-left: 1px solid #E2E2E2;
        }}
        .tb-block:first-child {{ padding-left: 0; border-left: none; }}
        /* First block of each (wrapped) line drops its separator — set by JS. */
        .tb-block.tb-rowstart {{ border-left: none; }}
        #clearBtn {{ margin-left: 8px; }}
        /* Responsive line-break helpers: invisible flex items that force a wrap
           at each breakpoint. Salto 1: buttons | filter+columns. Salto 2: + filter | columns. */
        .tb-break {{ display: none; flex-basis: 100%; height: 0; }}
        @media (max-width: 1000px) {{ .tb-break-1 {{ display: block; }} }}
        @media (max-width: 680px) {{ .tb-break-2 {{ display: block; }} }}
        .search-row {{
            display: none;
            background: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            padding: 10px 20px;
            gap: 12px;
            align-items: center;
        }}
        .search-row.open {{ display: flex; }}
        .scope-check {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #333333; white-space: nowrap; cursor: pointer; }}
        .search-row .search-input,
        .search-row .exclude-input {{ flex: 0 1 320px; width: auto; min-width: 0; }}

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

        .group-label {{ font-weight: 600; color: #333333; }}

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

        /* The breathing space above the table is a margin (OUTSIDE the scroll
           area) — white from the page — so rows can't scroll through it and the
           sticky thead pins flush to the top edge with nothing peeking above. */
        .table-container {{
            padding: 0 16px 16px;
            margin-top: 14px;
            background: #FFFFFF;
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
            position: sticky;
            top: 0;
            z-index: 5;
            box-shadow: inset 0 -1px 0 #E0E0E0;
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

        /* Sub-rows: Recap / First prompt (collapsible, toggled from Columns).
           Each type has its own accent color, mirrored in its toolbar toggle. */
        .sub-row {{ display: none; }}
        .sub-row.show {{ display: table-row; }}
        .sub-row td {{
            padding: 0 10px 5px 10px;
        }}
        .sub-recap td {{ background: #F7F2FC; }}
        .sub-prompt td {{ background: #F2F8FD; }}
        .sub-recap .sub-label {{ color: #8B4FD6; }}
        .sub-prompt .sub-label {{ color: #1E6FBF; }}
        .sub-recap .sub-details summary::before {{ color: #8B4FD6; }}
        .sub-prompt .sub-details summary::before {{ color: #1E6FBF; }}
        .columns-toggle input[data-sub="recap"] {{ accent-color: #8B4FD6; }}
        .columns-toggle input[data-sub="prompt"] {{ accent-color: #1E6FBF; }}

        /* Agent chats */
        .agent-badge {{
            display: inline-block;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #FFFFFF;
            background: #2D6E6E;
            padding: 1px 5px;
            border-radius: 3px;
            margin-right: 6px;
            vertical-align: middle;
        }}
        /* Agents hang under their invoking chat with a subtle tree connector
           "└─" (replaces the old vertical rail) — reads as "comes from above". */
        tr.agent-row .name-cell {{ padding-left: 6px; }}
        tr.agent-row .name-cell::before {{
            content: "└─";
            color: #9CB8B8;
            margin: 0 6px 0 2px;
            font-family: 'Cascadia Code', 'Consolas', monospace;
        }}
        .agent-badge-orphan {{ background: #6B7280; }}
        /* Orphan agents: collapsible group at the end (header row + orphan rows). */
        .orphan-header td {{
            background: #F3F4F6; color: #6B7280; font-weight: 600; font-size: 11px;
            cursor: pointer; user-select: none; padding: 6px 12px;
            box-shadow: inset 3px 0 0 #9CA3AF;
        }}
        .orphan-header:hover td {{ background: #ECEEF1; }}
        .orphan-tw {{ display: inline-block; transition: transform 0.15s; color: #9CA3AF; margin-right: 4px; }}
        .orphan-header.open .orphan-tw {{ transform: rotate(90deg); }}
        .orphan-n {{ color: #9CA3AF; font-weight: 400; }}
        .orphan-hint {{ color: #B0B4BB; font-weight: 400; font-style: italic; }}

        /* "+" menu (BTW / Audit dashboards) */
        .plus-wrap {{ position: relative; }}
        .plus-menu {{
            display: none; position: absolute; top: 100%; left: 0; margin-top: 4px;
            background: #FFFFFF; border: 1px solid #D0D0D0; border-radius: 6px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.15); z-index: 100; min-width: 170px; padding: 4px;
        }}
        .plus-menu.open {{ display: block; }}
        .plus-menu a {{
            display: block; padding: 6px 10px; color: #1E1E1E; text-decoration: none;
            border-radius: 4px; font-size: 12px; white-space: nowrap;
        }}
        .plus-menu a:hover {{ background: #F0F0F0; }}
        /* Every data row stays on a single line (the Recap/First-prompt sub-rows
           are the only multi-line rows). */
        #chatsTable tbody tr:not(.sub-row) td {{ white-space: nowrap; }}
        /* Toggle labels: normal by default, bold + accent color when checked */
        .columns-toggle label:has(input[data-sub="recap"]:checked) {{ color: #8B4FD6; font-weight: 600; }}
        .columns-toggle label:has(input[data-sub="prompt"]:checked) {{ color: #1E6FBF; font-weight: 600; }}
        .columns-toggle input#agentsToggle {{ accent-color: #2D6E6E; }}
        .columns-toggle label:has(#agentsToggle:checked) {{ color: #2D6E6E; font-weight: 600; }}
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

        /* Select / Delete mode */
        .tb-btn {{
            font-family: inherit;
            font-size: 11px;
            padding: 4px 10px;
            border: 1px solid #CCC;
            border-radius: 3px;
            background: #FFF;
            color: #333;
            cursor: pointer;
        }}
        .tb-btn:hover {{ background: #F0F0F0; }}
        .tb-btn.active {{ background: #E8E8E8; border-color: #999; }}
        .tb-btn.danger {{ border-color: #D9534F; color: #C0392B; }}
        .tb-btn.danger:not(:disabled):hover {{ background: #FDECEA; }}
        .tb-btn:disabled {{ opacity: 0.45; cursor: default; }}
        #deleteBtn, #selectModeBtn, #searchToggle, #clearBtn {{
            padding: 3px 14px;
            text-align: center;
        }}
        #searchToggle.active {{ background: #E8E8E8; border-color: #999; }}
        .sel-col input {{ cursor: pointer; width: 13px; height: 13px; }}
        body.select-mode #chatsTable tbody tr:not(.sub-row) {{ cursor: pointer; }}

        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.45);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.open {{ display: flex; }}
        .modal-box {{
            background: #FFF;
            border-radius: 6px;
            width: min(760px, 92vw);
            max-height: 86vh;
            display: flex;
            flex-direction: column;
            padding: 18px 20px 14px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.35);
            font-size: 12px;
        }}
        .modal-title {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; }}
        .modal-warning {{
            background: #FDECEA;
            border: 1px solid #F5C6CB;
            color: #842029;
            border-radius: 4px;
            padding: 8px 10px;
            margin-bottom: 10px;
            line-height: 1.45;
        }}
        .modal-list {{
            list-style: none;
            margin: 0 0 10px;
            padding: 6px 10px;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            max-height: 150px;
            overflow-y: auto;
        }}
        .modal-list li {{
            padding: 2px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .modal-list li .del-date {{ color: #999; font-size: 11px; margin-left: 8px; }}
        .modal-tabs {{ display: flex; gap: 6px; align-items: center; margin-bottom: 8px; }}
        .del-tab {{
            font-family: inherit;
            font-size: 11px;
            padding: 4px 10px;
            border: 1px solid #CCC;
            border-radius: 3px;
            background: #FFF;
            cursor: pointer;
        }}
        .del-tab.active {{ background: #1E1E1E; color: #FFF; border-color: #1E1E1E; }}
        .del-perm {{ margin-left: auto; display: flex; gap: 5px; align-items: center; font-size: 11px; color: #842029; cursor: pointer; }}
        .modal-cmd {{
            font-family: 'Cascadia Code', 'Consolas', monospace;
            font-size: 11px;
            width: 100%;
            min-height: 92px;
            resize: vertical;
            border: 1px solid #DDD;
            border-radius: 4px;
            padding: 8px;
            background: #FAFAFA;
            color: #333;
            box-sizing: border-box;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .modal-actions {{ display: flex; gap: 8px; align-items: center; margin-top: 10px; }}
        .modal-hint {{ flex: 1; color: #888; font-size: 11px; }}

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
    <div id="dashLoading" class="dash-loading"><div class="dash-loading-spin"></div><div class="dash-loading-msg">Loading your chats… hang tight!</div></div>
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
        <div class="tb-block">
            <button id="selectModeBtn" class="tb-btn" title="Select chats to delete">Select</button>
            <button id="deleteBtn" class="tb-btn danger" disabled>Delete</button>
        </div>
        <div class="tb-block">
            <button type="button" id="searchToggle" class="tb-btn" aria-pressed="false">Search</button>
            <button type="button" id="clearBtn" class="tb-btn" title="Reset all options: filters, columns, selection, search">Clear</button>
        </div>
        <i class="tb-break tb-break-1"></i>
        <div class="tb-block filter-group">
            <span class="group-label">Filter:</span>
            {filter_checkboxes}
            <span class="tooltip">
                <span class="help-icon">?</span>
                <span class="tooltip-text">
                    <strong>Categories:</strong><br><br>
                    {tooltip_lines}
                </span>
            </span>
        </div>
        <i class="tb-break tb-break-2"></i>
        <div class="tb-block columns-toggle">
            <span class="group-label">View:</span>
            <label><input type="checkbox" id="agentsToggle" title="Show agent chats (sub-chats launched by the Task tool), nested under their invoker"> Agents</label>
            <label><input type="checkbox" data-sub="recap"> Recap</label>
            <label><input type="checkbox" data-sub="prompt"> First prompt</label>
        </div>
        {plus_menu_html}
        <div class="tb-block columns-toggle">
            <span class="group-label">Columns:</span>
            <label><input type="checkbox" data-col="branch-col"> Branch</label>
            <label><input type="checkbox" data-col="size-col"> Size</label>
        </div>
    </div>

    <div class="search-row" id="searchRow">
        <label class="scope-check"><input type="checkbox" id="searchScopeNames" checked> Search names only</label>
        <input type="text" class="search-input" id="searchInput" placeholder="Search by name, project..." autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
        <input type="text" class="exclude-input" id="excludeInput" placeholder="Exclude..." autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
    </div>

    <div class="modal-overlay" id="deleteModal">
        <div class="modal-box">
            <div class="modal-title">Delete <span id="delCount">0</span> chat(s)</div>
            <div class="modal-warning">This removes BOTH the generated HTML and the original Claude Code <code>.jsonl</code> session of each chat. With the permanent option this is <strong>IRRECOVERABLE</strong>.</div>
            <ul class="modal-list" id="delList"></ul>
            <div class="modal-tabs">
                <button class="del-tab" data-tab="powershell">PowerShell (Windows)</button>
                <button class="del-tab" data-tab="macos">macOS</button>
                <button class="del-tab" data-tab="linux">Linux</button>
                <label class="del-perm"><input type="checkbox" id="delPermanent"> Permanent (skip trash)</label>
            </div>
            <textarea class="modal-cmd" id="delCmd" readonly spellcheck="false"></textarea>
            <div class="modal-actions">
                <span class="modal-hint">Run the command in your terminal, then regenerate (Update Chats) to refresh the dashboard.</span>
                <button class="tb-btn" id="delCopy">Copy command</button>
                <button class="tb-btn" id="delClose">Close</button>
            </div>
        </div>
    </div>

    <div class="table-container">
        <table id="chatsTable">
            <thead>
                <tr>
                    <th class="hidden-col sel-col" data-sort="none" data-width="36"><input type="checkbox" id="selAll" title="Select / unselect all visible"></th>
                    <th data-sort="name">Name</th>
                    <th data-sort="none" data-width="40">Link</th>
                    <th data-sort="project" data-width="130">Project</th>
                    <th data-sort="category" data-width="95">Category</th>
                    <th data-sort="created" data-width="160">Created</th>
                    <th data-sort="modified" class="sorted-desc" data-width="160">Last Used</th>
                    <th data-sort="messages" data-width="64" title="Turns: one full assistant response (its text and tools) counts as 1 message. Counted the same across all chats.">Msgs</th>
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
                searchNamesOnly: document.getElementById('searchScopeNames').checked,
                searchActive: document.getElementById('searchToggle').classList.contains('active'),
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
            state.delTab = delTab;
            state.delMode = document.getElementById('delPermanent').checked;
            state.selectMode = selectMode;
            state.showAgents = showAgents;
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
            const cmp = (a, b) => {{
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
                    const colIndex = {{ name: 1, project: 3, category: 4, uuid: 8, branch: 10 }}[col] || 1;
                    aVal = (a.cells[colIndex]?.textContent || '').trim().toLowerCase();
                    bVal = (b.cells[colIndex]?.textContent || '').trim().toLowerCase();
                }}
                if (typeof aVal === 'number') return dir === 'asc' ? aVal - bVal : bVal - aVal;
                return dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }};
            // Only root chats are sorted. Agents stay glued under their invoker
            // (in invocation order); orphan agents are appended last. Every row
            // drags its own sub-rows (Recap / First prompt).
            const place = row => {{
                tbody.appendChild(row);
                (subRowsOf[row.dataset.uuid] || []).forEach(sr => tbody.appendChild(sr));
            }};
            const roots = Array.from(tbody.querySelectorAll('tr:not(.sub-row):not(.agent-row):not(.orphan-header)'));
            roots.sort(cmp);
            roots.forEach(row => {{
                place(row);
                (agentRowsOf[row.dataset.uuid] || []).forEach(place);
            }});
            // Orphan group last: header, then the orphan rows sorted like the rest.
            const orphanHeader = tbody.querySelector('.orphan-header');
            if (orphanHeader) tbody.appendChild(orphanHeader);
            Array.from(tbody.querySelectorAll('tr.agent-orphan')).sort(cmp).forEach(place);
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
        /* Agent rows indexed by their invoking chat's UUID, so they stay glued
           under it when the table is re-sorted (orphans handled separately). */
        const agentRowsOf = {{}};
        document.querySelectorAll('#chatsTable tbody tr.agent-row:not(.agent-orphan)').forEach(ar => {{
            const p = ar.dataset.parent;
            (agentRowsOf[p] = agentRowsOf[p] || []).push(ar);
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

        /* ---- Select & Delete mode ---- */
        let selectMode = false;
        let showAgents = false;
        let orphansOpen = false;
        const selectBtn = document.getElementById('selectModeBtn');
        const agentsBtn = document.getElementById('agentsToggle');
        if (agentsBtn) {{
            agentsBtn.addEventListener('change', () => {{
                showAgents = agentsBtn.checked;
                if (!showAgents) {{ orphansOpen = false; document.querySelectorAll('.orphan-header').forEach(o => o.classList.remove('open')); }}
                filterTable();
                saveState();
            }});
        }}

        // Orphan-agents group toggle (collapsed by default, not persisted).
        document.querySelectorAll('#chatsTable .orphan-header').forEach(oh => {{
            oh.addEventListener('click', () => {{
                orphansOpen = !orphansOpen;
                oh.classList.toggle('open', orphansOpen);
                filterTable();
            }});
        }});

        const plusBtn = document.getElementById('plusBtn');
        const plusMenu = document.getElementById('plusMenu');
        if (plusBtn && plusMenu) {{
            plusBtn.addEventListener('click', e => {{
                e.stopPropagation();
                const open = plusMenu.classList.toggle('open');
                plusBtn.setAttribute('aria-expanded', open);
            }});
            document.addEventListener('click', () => {{
                plusMenu.classList.remove('open');
                plusBtn.setAttribute('aria-expanded', 'false');
            }});
        }}
        const deleteBtn = document.getElementById('deleteBtn');
        const selAll = document.getElementById('selAll');
        const delModal = document.getElementById('deleteModal');
        let delTab = 'powershell';
        let delFiles = [];

        function selectedRows() {{
            // Only marked AND visible rows — never hidden ones (filtered out or
            // agents toggled off), so deletion can never silently include them.
            return Array.from(document.querySelectorAll('#chatsTable tbody tr:not(.sub-row):not(.hidden-row) .sel-box:checked'))
                .map(cb => cb.closest('tr'));
        }}

        function refreshDeleteUI() {{
            const n = selectedRows().length;
            deleteBtn.textContent = n ? `Delete (${{n}})` : 'Delete';
            deleteBtn.disabled = n === 0;
            const visBoxes = Array.from(document.querySelectorAll('#chatsTable tbody tr:not(.sub-row):not(.hidden-row) .sel-box'));
            const checkedVis = visBoxes.filter(cb => cb.checked).length;
            selAll.checked = visBoxes.length > 0 && checkedVis === visBoxes.length;
            selAll.indeterminate = checkedVis > 0 && checkedVis < visBoxes.length;
        }}

        selectBtn.addEventListener('click', () => {{
            selectMode = !selectMode;
            selectBtn.classList.toggle('active', selectMode);
            document.body.classList.toggle('select-mode', selectMode);
            document.querySelectorAll('.sel-col').forEach(el => el.classList.toggle('hidden-col', !selectMode));
            if (!selectMode) {{
                document.querySelectorAll('#chatsTable .sel-box').forEach(cb => {{ cb.checked = false; }});
            }}
            syncColumnWidths();
            refreshDeleteUI();
            saveState();
        }});

        /* In select mode, clicking anywhere on a row toggles its checkbox
           (links, buttons, inputs and the sub-row details stay clickable). */
        document.querySelectorAll('#chatsTable tbody tr:not(.sub-row)').forEach(tr => {{
            tr.addEventListener('click', e => {{
                if (!selectMode) return;
                if (e.target.closest('a, button, input, details')) return;
                const cb = tr.querySelector('.sel-box');
                if (cb) {{
                    cb.checked = !cb.checked;
                    refreshDeleteUI();
                }}
            }});
        }});

        selAll.addEventListener('change', () => {{
            const target = selAll.checked;
            document.querySelectorAll('#chatsTable tbody tr:not(.sub-row):not(.hidden-row) .sel-box').forEach(cb => {{ cb.checked = target; }});
            refreshDeleteUI();
        }});

        document.querySelectorAll('#chatsTable .sel-box').forEach(cb => {{
            cb.addEventListener('change', refreshDeleteUI);
        }});

        /* Path helpers — built without literal backslashes (template safety) */
        const BS = String.fromCharCode(92);
        const SQ = String.fromCharCode(39);

        function dashboardDir() {{
            let p = decodeURIComponent(location.pathname);
            p = p.substring(0, p.lastIndexOf('/'));
            if (p.charAt(0) === '/' && p.charAt(2) === ':') p = p.substring(1);
            return p;
        }}

        function rowFiles(tr) {{
            const dir = dashboardDir();
            const win = dir.charAt(1) === ':';
            const files = [];
            if (tr.dataset.jsonl) files.push(tr.dataset.jsonl);
            if (tr.dataset.html) {{
                const h = tr.dataset.html;
                files.push(win
                    ? dir.split('/').join(BS) + BS + h.split('/').join(BS)
                    : dir + '/' + h.split(BS).join('/'));
            }}
            return files;
        }}

        function psQuote(p) {{ return SQ + p.split(SQ).join(SQ + SQ) + SQ; }}
        function shQuote(p) {{ return SQ + p.split(SQ).join(SQ + BS + SQ + SQ) + SQ; }}

        function buildDelCmd() {{
            const files = delFiles.flatMap(x => x.files);
            const perm = document.getElementById('delPermanent').checked;
            let cmd = '';
            if (delTab === 'powershell') {{
                const arr = files.map(psQuote).join(', ');
                cmd = perm
                    ? `Remove-Item -LiteralPath @(${{arr}}) -Force`
                    : `Add-Type -AssemblyName Microsoft.VisualBasic; @(${{arr}}) | ForEach-Object {{ [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($_, 'OnlyErrorDialogs', 'SendToRecycleBin') }}`;
            }} else if (delTab === 'macos') {{
                cmd = perm
                    ? `rm -f -- ${{files.map(shQuote).join(' ')}}`
                    : `osascript -e ${{shQuote('tell application "Finder" to delete {{' + files.map(f => 'POSIX file "' + f.split('"').join(BS + '"') + '"').join(', ') + '}}')}}`;
            }} else {{
                cmd = perm
                    ? `rm -f -- ${{files.map(shQuote).join(' ')}}`
                    : `gio trash -- ${{files.map(shQuote).join(' ')}}`;
            }}
            document.getElementById('delCmd').value = cmd;
        }}

        deleteBtn.addEventListener('click', () => {{
            const rows = selectedRows();
            if (!rows.length) return;
            delFiles = rows.map(tr => ({{
                name: tr.querySelector('.name-cell')?.title || tr.dataset.uuid,
                date: tr.querySelector('.date-cell')?.textContent || '',
                files: rowFiles(tr)
            }}));
            document.getElementById('delCount').textContent = rows.length;
            const list = document.getElementById('delList');
            list.innerHTML = '';
            delFiles.forEach(x => {{
                const li = document.createElement('li');
                li.textContent = x.name;
                const sp = document.createElement('span');
                sp.className = 'del-date';
                sp.textContent = x.date;
                li.appendChild(sp);
                list.appendChild(li);
            }});
            buildDelCmd();
            delModal.classList.add('open');
        }});

        document.querySelectorAll('.del-tab').forEach(b => {{
            b.addEventListener('click', () => {{
                delTab = b.dataset.tab;
                document.querySelectorAll('.del-tab').forEach(x => x.classList.toggle('active', x === b));
                buildDelCmd();
                saveState();
            }});
        }});
        document.getElementById('delPermanent').addEventListener('change', () => {{ buildDelCmd(); saveState(); }});
        document.getElementById('delCopy').addEventListener('click', () => {{
            const ta = document.getElementById('delCmd');
            ta.select();
            navigator.clipboard.writeText(ta.value).then(() => {{
                document.getElementById('delCopy').textContent = 'Copied!';
                setTimeout(() => {{ document.getElementById('delCopy').textContent = 'Copy command'; }}, 1500);
            }});
        }});
        document.getElementById('delClose').addEventListener('click', () => delModal.classList.remove('open'));
        delModal.addEventListener('click', e => {{ if (e.target === delModal) delModal.classList.remove('open'); }});
        document.addEventListener('keydown', e => {{
            if (e.key === 'Escape') delModal.classList.remove('open');
        }});

        /* Search and filter */
        document.getElementById('searchInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        document.getElementById('excludeInput').addEventListener('input', () => {{ filterTable(); saveState(); }});
        function updateScopePlaceholder() {{
            const el = document.getElementById('searchScopeNames');
            const input = document.getElementById('searchInput');
            if (el && el.checked) {{ input.placeholder = 'Search by name...'; return; }}
            // Use the long hint only if the input is wide enough; else "Search...".
            // Falls back to viewport width when the row is hidden (clientWidth 0).
            const w = input.clientWidth;
            const narrow = w > 0 ? w < 300 : window.innerWidth <= 800;
            input.placeholder = narrow ? 'Search...' : 'Search by name, project, content...';
        }}
        document.getElementById('searchScopeNames').addEventListener('change', () => {{ updateScopePlaceholder(); filterTable(); saveState(); }});
        updateScopePlaceholder();
        function setSearchActive(active) {{
            document.getElementById('searchRow').classList.toggle('open', active);
            const btn = document.getElementById('searchToggle');
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
            filterTable();
            updateScopePlaceholder();
        }}
        document.getElementById('searchToggle').addEventListener('click', () => {{
            setSearchActive(!document.getElementById('searchToggle').classList.contains('active'));
            saveState();
        }});
        document.getElementById('clearBtn').addEventListener('click', () => {{
            localStorage.removeItem(STATE_KEY);
            location.reload();
        }});
        /* Hide the left separator of any toolbar block that is the first on its
           line (forced or natural wrap), so a wrapped block never shows a
           dangling separator. Robust at any width. */
        function syncToolbarSeparators() {{
            var blocks = Array.from(document.querySelectorAll('.toolbar .tb-block'));
            var prevTop = null;
            blocks.forEach(function(b) {{
                var top = b.offsetTop;
                b.classList.toggle('tb-rowstart', prevTop === null || Math.abs(top - prevTop) > 2);
                prevTop = top;
            }});
        }}
        window.addEventListener('resize', () => {{ syncToolbarSeparators(); updateScopePlaceholder(); }});
        syncToolbarSeparators();
        {filter_js_listeners}

        function filterTable() {{
            const searchActive = document.getElementById('searchToggle').classList.contains('active');
            const search = searchActive ? document.getElementById('searchInput').value.toLowerCase() : '';
            const exclude = searchActive ? document.getElementById('excludeInput').value.toLowerCase() : '';
            const scopeEl = document.getElementById('searchScopeNames');
            const namesOnly = scopeEl ? scopeEl.checked : true;
            {filter_js_vars}

            document.querySelectorAll('#chatsTable tbody tr').forEach(row => {{
                if (row.classList.contains('sub-row')) return;
                const nameCell = row.querySelector('.name-cell');
                const text = namesOnly
                    ? (nameCell ? nameCell.textContent.toLowerCase() : '')
                    : row.textContent.toLowerCase() + (subTextOf[row.dataset.uuid] || '');
                const category = row.querySelector('.category-cell')?.textContent || '';
                const matchesSearch = !search || text.includes(search);
                const matchesExclude = !exclude || !text.includes(exclude);
                const matchesFilter =
                    {filter_js_conditions};
                if (row.classList.contains('orphan-header')) {{
                    // Header shows only when Agents is on (no search/filter applies).
                    row.classList.toggle('hidden-row', !showAgents);
                    return;
                }}
                if (row.classList.contains('agent-orphan')) {{
                    // Orphans are a separate group at the end, opened on purpose:
                    // show them when the group is open + Agents on + they match the
                    // search, REGARDLESS of the Active/Archived filter (orphans are
                    // usually old/Archived, which would otherwise hide them all).
                    const ok = orphansOpen && showAgents && matchesSearch && matchesExclude;
                    row.classList.toggle('hidden-row', !ok);
                    if (!ok) {{ const sb = row.querySelector('.sel-box'); if (sb && sb.checked) sb.checked = false; }}
                    return;
                }}
                const matchesAgents = showAgents || row.dataset.agent !== '1';
                const hide = !(matchesSearch && matchesExclude && matchesFilter && matchesAgents);
                row.classList.toggle('hidden-row', hide);
                // Never keep a hidden row selected (safety against deleting unseen chats).
                if (hide) {{ const sb = row.querySelector('.sel-box'); if (sb && sb.checked) sb.checked = false; }}
            }});
            syncSubRows();
            refreshDeleteUI();
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
            if (typeof saved.searchNamesOnly === 'boolean') document.getElementById('searchScopeNames').checked = saved.searchNamesOnly;
            if (saved.searchActive) setSearchActive(true);
            updateScopePlaceholder();
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
            if (saved.delTab) delTab = saved.delTab;
            if (saved.delMode) document.getElementById('delPermanent').checked = true;
            // Restore the Select mode (column visible); the individual delete
            // marks are intentionally NOT persisted (transient, avoids accidental
            // deletes after a refresh).
            if (saved.selectMode) selectBtn.click();
            if (saved.showAgents && agentsBtn) {{
                showAgents = true;
                agentsBtn.checked = true;
            }}
            if (saved.sort) {{
                currentSort = saved.sort;
                document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
                const th = document.querySelector(`th[data-sort="${{saved.sort.col}}"]`);
                if (th) th.classList.add(saved.sort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
                sortTable(saved.sort.col, saved.sort.dir);
            }}
        }}

        document.querySelectorAll('.del-tab').forEach(x => x.classList.toggle('active', x.dataset.tab === delTab));
        syncColumnWidths();
        filterTable();

        // State restored — drop the loading overlay after layout settles.
        window.addEventListener('load', function() {{
            var ld = document.getElementById('dashLoading');
            if (ld) {{ ld.classList.add('hidden'); setTimeout(function() {{ ld.remove(); }}, 300); }}
        }});

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
        try:
            cwd = extract_jsonl_metadata(jsonl_file).get("cwd", "")
        except Exception:
            cwd = ""
        project = format_project_name(cwd) if cwd else format_project_name(jsonl_file.parent.name)
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
            margin: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
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
            flex: 1;
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
               placeholder="Filter by query text, chat title or project..." autofocus autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
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


def _audit_object(obj, chat_name: str, findings: dict):
    """Inspect one JSONL object and accumulate anomalies into `findings`."""
    if not isinstance(obj, dict):
        return

    mtype = obj.get("type", "")
    findings["message_type_counts"][mtype] = findings["message_type_counts"].get(mtype, 0) + 1
    if mtype and mtype not in KNOWN_MESSAGE_TYPES and mtype not in KNOWN_METADATA_TYPES:
        slot = findings["unknown_message_types"].setdefault(mtype, {"count": 0, "chats": set()})
        slot["count"] += 1
        slot["chats"].add(chat_name)

    message = obj.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return

    for item in content:
        if not isinstance(item, dict):
            continue
        ctype = item.get("type", "")
        findings["content_type_counts"][ctype] = findings["content_type_counts"].get(ctype, 0) + 1
        if ctype and ctype not in KNOWN_CONTENT_TYPES:
            slot = findings["unknown_content_types"].setdefault(ctype, {"count": 0, "chats": set()})
            slot["count"] += 1
            slot["chats"].add(chat_name)
        if ctype == "thinking" and not (item.get("thinking") or "").strip():
            findings["empty_thinking"]["count"] += 1
            findings["empty_thinking"]["chats"].add(chat_name)
        if ctype == "text" and not (item.get("text") or "").strip():
            findings["empty_text"]["count"] += 1
            findings["empty_text"]["chats"].add(chat_name)
        if ctype == "tool_use":
            tname = item.get("name", "")
            if tname:
                findings["tool_names"][tname] = findings["tool_names"].get(tname, 0) + 1


def audit_chats(config: dict, scan_count="50") -> dict:
    """Scan the most recent JSONL files for format anomalies (read-only).

    `scan_count` is an int-like (the N most recent by mtime) or "all". Returns a
    structured findings dict consumed by generate_audit_view. Never writes.
    """
    source_path = config["_resolved"]["source_path"]

    files = []
    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            files.append(jsonl_file)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    scan_all = str(scan_count).lower() == "all"
    if not scan_all:
        try:
            n = int(scan_count)
        except (TypeError, ValueError):
            n = 50
        files = files[: max(0, n)]

    findings = {
        "scanned": 0,
        "scan_all": scan_all,
        "unknown_message_types": {},
        "unknown_content_types": {},
        "empty_thinking": {"count": 0, "chats": set()},
        "empty_text": {"count": 0, "chats": set()},
        "parse_errors": [],
        "message_type_counts": {},
        "content_type_counts": {},
        "tool_names": {},
    }

    for jsonl_file in files:
        findings["scanned"] += 1
        chat_name = jsonl_file.name
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        findings["parse_errors"].append({"chat": chat_name, "line": line_num})
                        continue
                    _audit_object(obj, chat_name, findings)
        except OSError:
            continue

    return findings


def _audit_has_findings(findings: dict) -> bool:
    """True if there is any actionable anomaly (excludes the plain summary)."""
    return bool(
        findings["unknown_message_types"]
        or findings["unknown_content_types"]
        or findings["empty_thinking"]["count"]
        or findings["empty_text"]["count"]
        or findings["parse_errors"]
    )


def _audit_section(css: str, title: str, intro: str, items_html: str) -> str:
    return (
        f'<section class="audit-section audit-{css}">'
        f'<h2 class="audit-title">{title}</h2>'
        f'<p class="audit-intro">{intro}</p>'
        f'<ul class="audit-list">{items_html}</ul>'
        f'</section>'
    )


def generate_audit_view(config: dict, scan_count="50"):
    """Generate an HTML format-audit report next to the dashboard.

    Returns (path, findings). The report is always written (even with zero
    findings, to confirm "all clear"). Read-only over the JSONL files.
    """
    output_path = config["_resolved"]["output_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")

    findings = audit_chats(config, scan_count)
    scope = "all chats" if findings["scan_all"] else f"{findings['scanned']} most recent chats"

    sections = []

    # 1. Possible format changes
    fmt_rows = []
    for t, d in sorted(findings["unknown_message_types"].items(), key=lambda kv: -kv[1]["count"]):
        fmt_rows.append(("message type", t, d["count"], len(d["chats"])))
    for t, d in sorted(findings["unknown_content_types"].items(), key=lambda kv: -kv[1]["count"]):
        fmt_rows.append(("content type", t, d["count"], len(d["chats"])))
    if fmt_rows:
        items = "".join(
            f'<li><code>{escape(t)}</code> <span class="audit-kind">({kind})</span> — '
            f'{count} occurrence(s) across {chats} chat(s). CCV shows it as a generic block.</li>'
            for kind, t, count, chats in fmt_rows
        )
        sections.append(_audit_section(
            "format", "🆕 Possible format changes",
            "Types not in CCV&#39;s known schema. This may be something new introduced by "
            "Claude Code. If any should render in a specific way, please report it.", items))

    # 2. Possibly dropped content
    drop_items = []
    if findings["empty_thinking"]["count"]:
        drop_items.append(
            f'<li><code>thinking</code> — {findings["empty_thinking"]["count"]} empty block(s) '
            f'across {len(findings["empty_thinking"]["chats"])} chat(s).</li>')
    if findings["empty_text"]["count"]:
        drop_items.append(
            f'<li><code>text</code> — {findings["empty_text"]["count"]} empty block(s) '
            f'across {len(findings["empty_text"]["chats"])} chat(s).</li>')
    if drop_items:
        sections.append(_audit_section(
            "dropped", "⚠️ Possibly dropped content",
            "Empty blocks that normally carry text. These may be content the Claude Code "
            "client did not persist (a known pattern) — not a CCV fault. The text itself is "
            "not in the JSONL, so it cannot be recovered.", "".join(drop_items)))

    # 3. Unexpected errors
    if findings["parse_errors"]:
        shown = findings["parse_errors"][:50]
        err_items = "".join(
            f'<li><code>{escape(e["chat"])}</code> — line {e["line"]} is not valid JSON.</li>'
            for e in shown)
        extra = ""
        if len(findings["parse_errors"]) > len(shown):
            extra = f'<li>… and {len(findings["parse_errors"]) - len(shown)} more.</li>'
        sections.append(_audit_section(
            "error", "🔴 Unexpected errors",
            "Lines that could not be parsed as JSON. Possible corruption or truncation of the "
            "source file.", err_items + extra))

    # 4. Summary (always present)
    def _counts_list(counts):
        return "".join(
            f'<li><code>{escape(str(k) or "(none)")}</code> — {v}</li>'
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    summary_items = (
        f'<li><strong>Scope:</strong> {escape(scope)}</li>'
        f'<li><strong>Message types seen:</strong></li>'
        f'<ul class="audit-sublist">{_counts_list(findings["message_type_counts"])}</ul>'
        f'<li><strong>Content types seen:</strong></li>'
        f'<ul class="audit-sublist">{_counts_list(findings["content_type_counts"])}</ul>'
        f'<li><strong>Tools seen:</strong></li>'
        f'<ul class="audit-sublist">{_counts_list(findings["tool_names"]) or "<li>(none)</li>"}</ul>'
    )
    sections.append(_audit_section("summary", "📊 Summary", "What was scanned and seen.", summary_items))

    has_findings = _audit_has_findings(findings)
    copy_btn = ('<span class="audit-arrow" aria-hidden="true">&rarr;</span>'
                '<button type="button" class="audit-copy" onclick="copyAuditReport()">'
                'Copy report</button>')
    if has_findings:
        banner = (
            '<div class="audit-banner audit-banner-warn">'
            '<span class="audit-banner-text">Some items were flagged below. If you think any of '
            'them should be fixed, <a href="https://github.com/oskar-gm/code-chat-viewer/issues" '
            'target="_blank" rel="noopener">open an issue on GitHub</a>.</span>'
            f'{copy_btn}</div>'
        )
    else:
        banner = (
            '<div class="audit-banner audit-banner-ok">'
            '<span class="audit-banner-text">All clear — everything scanned matches CCV&#39;s known '
            'schema, with no empty blocks or parse errors.</span>'
            f'{copy_btn}</div>'
        )

    sections_block = "\n".join(sections)
    gen_time = _fmt_dt(datetime.now(), config["time_format"])

    # Plain-text version of the report, for the Copy button (e.g. to paste in an issue).
    plain_lines = [
        "Code Chat Viewer - Format Audit",
        f"Scope: {scope}",
        f"Generated: {gen_time}",
        "",
    ]
    if fmt_rows:
        plain_lines.append("== Possible format changes ==")
        plain_lines += [f"- {t} ({kind}): {count} occurrence(s) across {chats} chat(s)"
                        for kind, t, count, chats in fmt_rows]
        plain_lines.append("")
    if findings["empty_thinking"]["count"] or findings["empty_text"]["count"]:
        plain_lines.append("== Possibly dropped content ==")
        if findings["empty_thinking"]["count"]:
            plain_lines.append(f"- thinking: {findings['empty_thinking']['count']} empty block(s) "
                               f"across {len(findings['empty_thinking']['chats'])} chat(s)")
        if findings["empty_text"]["count"]:
            plain_lines.append(f"- text: {findings['empty_text']['count']} empty block(s) "
                               f"across {len(findings['empty_text']['chats'])} chat(s)")
        plain_lines.append("")
    if findings["parse_errors"]:
        plain_lines.append("== Unexpected errors ==")
        plain_lines += [f"- {e['chat']}: line {e['line']} is not valid JSON"
                        for e in findings["parse_errors"][:50]]
        plain_lines.append("")
    plain_lines.append("== Summary ==")
    plain_lines.append("Message types seen: " + ", ".join(
        f"{k or '(none)'}={v}" for k, v in sorted(findings["message_type_counts"].items(), key=lambda kv: -kv[1])))
    plain_lines.append("Content types seen: " + ", ".join(
        f"{k or '(none)'}={v}" for k, v in sorted(findings["content_type_counts"].items(), key=lambda kv: -kv[1])))
    plain_lines.append("Tools seen: " + (", ".join(
        f"{k}={v}" for k, v in sorted(findings["tool_names"].items(), key=lambda kv: -kv[1])) or "(none)"))
    plain_report = "\n".join(plain_lines)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Code Chat Viewer v{APP_VERSION} — Format Audit">
    <link rel="icon" type="image/png" href="data:image/png;base64,{ICON_FAVICON_BASE64}">
    <title>Code Chat Viewer — Format Audit</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #FFFFFF; color: #1E1E1E; font-size: 12px; line-height: 1.5;
        }}
        .audit-header {{
            background: #2D2D30; color: #CCCCCC; padding: 8px 16px;
            display: flex; justify-content: space-between; align-items: center; gap: 10px;
            font-size: 12px;
        }}
        .audit-header-title {{ display: flex; align-items: center; gap: 8px; font-weight: 600; }}
        .audit-header-title img {{ height: 14px; width: 14px; }}
        .audit-header a {{ color: #7EC8F0; text-decoration: none; font-size: 11px; }}
        .audit-header a:hover {{ text-decoration: underline; }}
        .audit-copy {{
            flex-shrink: 0;
            background: #2D2D30; color: #FFFFFF; border: none;
            border-radius: 4px; padding: 5px 14px; font-family: inherit;
            font-size: 11px; font-weight: 600; cursor: pointer;
        }}
        .audit-copy:hover {{ background: #1E1E20; }}
        .audit-meta {{
            background: #F5F5F5; border-bottom: 1px solid #E0E0E0;
            padding: 6px 16px; font-size: 11px; color: #555;
        }}
        .audit-banner {{ padding: 10px 16px; font-size: 12px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
        .audit-banner-ok {{ background: #F0FFF4; color: #176B3A; border-bottom: 1px solid #C6F6D5; }}
        .audit-banner-warn {{ background: #FFFBEB; color: #92400E; border-bottom: 1px solid #FDE68A; }}
        .audit-banner a {{ color: #9A3412; font-weight: 600; }}
        .audit-arrow {{ font-weight: 700; font-size: 14px; opacity: 0.65; }}
        .audit-container {{ padding: 12px 16px; max-width: 1100px; margin: 0 auto; }}
        .audit-section {{
            border: 1px solid #E5E5E5; border-left: 3px solid #999;
            border-radius: 4px; margin-bottom: 10px; padding: 10px 12px;
        }}
        .audit-format {{ border-left-color: #2563EB; }}
        .audit-dropped {{ border-left-color: #D97706; }}
        .audit-error {{ border-left-color: #DC2626; }}
        .audit-summary {{ border-left-color: #6B7280; }}
        .audit-title {{ font-size: 13px; margin-bottom: 4px; }}
        .audit-intro {{ color: #666; font-size: 11px; margin-bottom: 8px; }}
        .audit-list {{ list-style: none; }}
        .audit-list > li {{ padding: 3px 0; border-bottom: 1px solid #F0F0F0; }}
        .audit-sublist {{ list-style: none; margin: 2px 0 6px 16px; }}
        .audit-sublist > li {{ padding: 1px 0; color: #444; border: none; }}
        .audit-kind {{ color: #888; }}
        code {{ background: #F3F4F6; padding: 1px 5px; border-radius: 3px; color: #B45309; }}
        .audit-footer {{
            background: #F3F3F3;
            border-top: 1px solid #E0E0E0;
            padding: 6px 16px;
            text-align: center;
            color: #666;
            font-size: 10px;
        }}
        .audit-footer a {{ color: #666; text-decoration: none; }}
        .audit-footer a:hover {{ text-decoration: underline; }}
        .audit-header-actions {{ display: flex; align-items: center; gap: 12px; }}
        .audit-del-btn {{ background: transparent; border: 1px solid #EF4444; color: #FCA5A5; font-size: 11px; padding: 2px 8px; border-radius: 4px; cursor: pointer; }}
        .audit-del-btn:hover {{ background: #EF4444; color: #FFFFFF; }}
        .audit-modal {{ display: none; position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,0.45); align-items: center; justify-content: center; }}
        .audit-modal.open {{ display: flex; }}
        .audit-modal-box {{ background: #FFFFFF; border-radius: 8px; padding: 18px 20px; max-width: 560px; width: 90%; box-shadow: 0 12px 44px rgba(0,0,0,0.35); }}
        .audit-modal-title {{ font-size: 14px; font-weight: 700; color: #991B1B; margin-bottom: 8px; }}
        .audit-modal-text {{ font-size: 12px; color: #555; margin-bottom: 10px; }}
        #auditDelCmd {{ width: 100%; box-sizing: border-box; font-family: 'Cascadia Code', monospace; font-size: 11px; padding: 8px; border: 1px solid #E0E0E0; border-radius: 4px; resize: none; }}
        .audit-modal-actions {{ display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }}
        .audit-modal-btn {{ font-size: 12px; padding: 5px 14px; border-radius: 4px; cursor: pointer; border: 1px solid #D0D0D0; background: #F3F3F3; color: #333; }}
        .audit-modal-btn:hover {{ background: #E8E8E8; }}
        .audit-modal-primary {{ border-color: #DC2626; background: #FEF2F2; color: #B91C1C; }}
        .audit-modal-primary:hover {{ background: #FEE2E2; }}
    </style>
</head>
<body>
    <div class="audit-header">
        <div class="audit-header-title">
            <img src="data:image/png;base64,{ICON_BASE64}" alt="">
            Format Audit · v{APP_VERSION}
        </div>
        <div class="audit-header-actions">
            <button type="button" id="auditDelBtn" class="audit-del-btn" title="Show the command to delete this report file">&#128465; Delete this report</button>
            <a href="{index_filename}">&#8592; Back to Dashboard</a>
        </div>
    </div>
    <div id="auditDelModal" class="audit-modal">
        <div class="audit-modal-box">
            <div class="audit-modal-title">Delete this report</div>
            <div class="audit-modal-text">Run this command in a terminal to delete this report file:</div>
            <textarea id="auditDelCmd" readonly rows="2"></textarea>
            <div class="audit-modal-actions">
                <button type="button" id="auditDelCopy" class="audit-modal-btn audit-modal-primary">Copy command</button>
                <button type="button" id="auditDelClose" class="audit-modal-btn">Close</button>
            </div>
        </div>
    </div>
    <div class="audit-meta">Scope: {escape(scope)} · Generated: {escape(gen_time)}</div>
    {banner}
    <div class="audit-container">
        {sections_block}
    </div>
    <div class="audit-footer">
        <a href="https://github.com/oskar-gm/code-chat-viewer" target="_blank" rel="noopener">Code Chat Viewer</a> | <a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener">Feedback</a>
    </div>
    <textarea id="audit-report-text" readonly aria-hidden="true" style="position:absolute; left:-9999px; top:-9999px;">{escape(plain_report)}</textarea>
    <script>
        function copyAuditReport() {{
            var ta = document.getElementById('audit-report-text');
            var btn = document.querySelector('.audit-copy');
            var done = function() {{
                var original = btn.getAttribute('data-label') || btn.textContent;
                btn.setAttribute('data-label', original);
                btn.textContent = '\\u2713 Copied';
                setTimeout(function() {{ btn.textContent = btn.getAttribute('data-label'); }}, 1500);
            }};
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(ta.value).then(done, function() {{ ta.select(); document.execCommand('copy'); done(); }});
            }} else {{
                ta.select(); document.execCommand('copy'); done();
            }}
        }}

        // "Delete this report" — show the OS-appropriate command for this file.
        (function(){{
            var btn = document.getElementById('auditDelBtn');
            var modal = document.getElementById('auditDelModal');
            var cmd = document.getElementById('auditDelCmd');
            if (!btn) return;
            function delCmd(){{
                var p = decodeURIComponent(location.pathname);
                var BS = String.fromCharCode(92), Q = String.fromCharCode(39);
                var win = navigator.platform.indexOf('Win') === 0 || (p.charAt(0) === '/' && p.charAt(2) === ':');
                if (win) {{
                    if (p.charAt(0) === '/' && p.charAt(2) === ':') p = p.substring(1);
                    p = p.split('/').join(BS);
                    return 'Remove-Item -LiteralPath ' + Q + p + Q + ' -Force';
                }}
                return 'rm -f -- ' + Q + p.split(Q).join(Q + BS + Q + Q) + Q;
            }}
            btn.addEventListener('click', function(){{
                cmd.value = delCmd();
                modal.classList.add('open');
            }});
            document.getElementById('auditDelClose').addEventListener('click', function(){{ modal.classList.remove('open'); }});
            modal.addEventListener('click', function(e){{ if (e.target === modal) modal.classList.remove('open'); }});
            document.getElementById('auditDelCopy').addEventListener('click', function(){{
                cmd.select();
                if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(cmd.value);
                else document.execCommand('copy');
            }});
        }})();
    </script>
</body>
</html>"""

    audit_filename = f"CCV-Audit {datetime.now().strftime('%Y-%m-%d %H-%M')}.html"
    audit_path = output_path / audit_filename
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(html)

    return audit_path, findings


def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split(".")[:3])
    except (ValueError, AttributeError):
        return None


def _needs_force_recommendation(last, current):
    """A minor/major bump (e.g. 2.5.x -> 2.6.0 / 3.0.0) — or no record at all —
    warrants re-running Force; a patch bump (2.5.0 -> 2.5.1) or same version does not."""
    cur = _version_tuple(current)
    if not cur:
        return False
    lt = _version_tuple(last)
    if not lt:
        return True  # no record (feature is new) -> assume a jump to this version
    return (cur[0], cur[1]) > (lt[0], lt[1])


def _get_last_run_version():
    """Version that last ran a Force, read straight from config.json (or None)."""
    try:
        p = find_config()
        if p and p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f).get("last_run_version")
    except (OSError, ValueError):
        pass
    return None


def _save_last_run_version(version):
    """Record the version that last ran a Force into config.json (best-effort)."""
    try:
        p = find_config()
        if not p or not p.exists():
            return
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        data["last_run_version"] = version
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except (OSError, ValueError):
        pass


def main():
    # Parse flags
    name_search = None
    current_mode = False
    current_jsonl_path = None
    force_regen = "--force" in sys.argv
    btw_mode = "--btw" in sys.argv
    audit_mode = "--audit" in sys.argv
    audit_scan = "50"
    if audit_mode:
        idx = sys.argv.index("--audit")
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--"):
            audit_scan = sys.argv[idx + 1]

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
    print(f"  Code Chat Viewer v{APP_VERSION} - Chat Manager")
    print("=" * 52)
    print()

    config = load_config()
    output_path = config["_resolved"]["output_path"]
    chats_path = config["_resolved"]["chats_path"]
    source_path = config["_resolved"]["source_path"]
    index_filename = config["output"].get("index_filename", "CCV-Dashboard.html")
    include_agents = config.get("agents", {}).get("include", True)
    min_agent_size = config.get("agents", {}).get("min_size_kb", 3) * 1024
    # Compaction agents (agent-acompact-*) are noise by default; opt in via config.
    include_compaction = config.get("agents", {}).get("include_compaction", False)

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

    # Recommend a Force re-render after a minor/major version bump.
    last_run = _get_last_run_version()
    version_notice_shown = _needs_force_recommendation(last_run, APP_VERSION)
    if version_notice_shown:
        was = f" (was v{last_run})" if last_run else ""
        print("  " + "═" * 50)
        print(f"   ⚡  Updated to v{APP_VERSION}{was}")
        print("   Run Force [2] to rebuild everything with this version —")
        print("   it applies every fix and keeps all chats consistent.")
        print("  " + "═" * 50)
        print()

    # Interactive mode selection (manual/double-click only)
    if (sys.stdout.isatty() and not name_search and not current_mode
            and not force_regen and not btw_mode and not audit_mode):
        print("  [1] Normal — update only modified chats (fast)")
        print("  [2] Force  — regenerate ALL chats from scratch (slow)")
        print("  [3] BTW    — generate btw.html from /btw history (skip chats)")
        print("  [4] Audit  — scan recent chats for format anomalies (skip chats)")
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
        elif choice == "4":
            audit_mode = True
            print()
            print("  Audit mode: scanning the 50 most recent chats for anomalies.")
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

    # ---- Audit mode short-circuit: scan recent chats, skip generate/organize ----
    if audit_mode:
        print("-" * 52)
        print("  Generating format audit...")
        audit_file, findings = generate_audit_view(config, audit_scan)
        print()
        print("=" * 52)
        print(f"  Audit ready: {audit_file}")
        print(f"  Scanned: {findings['scanned']} chat(s)")
        if _audit_has_findings(findings):
            print("  Findings detected - see the report. If something looks wrong,")
            print("  feedback is welcome: github.com/oskar-gm/code-chat-viewer/issues")
        else:
            print("  All clear - no anomalies.")
        print("=" * 52)
        print()
        open_in_browser(audit_file)
        if sys.stdout.isatty() and os.name == 'nt':
            _countdown_close(60)
        return

    print("-" * 52)
    print("  Scanning chats...")

    # Files to process: top-level chats + agent chats under <session>/subagents/.
    # Agents are detected by location; compaction agents and fork-context refs
    # are skipped by default, plus anything below the size threshold.
    scan_items = []  # (jsonl_file, is_agent)
    for project_dir in source_path.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            scan_items.append((jsonl_file, False))
        if include_agents:
            for agent_file in project_dir.glob("*/subagents/agent-*.jsonl"):
                scan_items.append((agent_file, True))

    # Generate agents first so the agentId -> html map is complete before the
    # invoking chats render their "agent completed" links.
    scan_items.sort(key=lambda x: not x[1])
    AGENT_HTML_MAP.clear()

    # A Force run re-renders everything with the current version — record it so we
    # only recommend Force again after the next minor/major bump.
    if force_regen:
        _save_last_run_version(APP_VERSION)
        if version_notice_shown:
            print(f"  ✓ Rebuilding with v{APP_VERSION} — this update notice won't show again.")
            print()

    for jsonl_file, is_agent in scan_items:
        filename = jsonl_file.name
        file_size = jsonl_file.stat().st_size

        if is_agent:
            if not include_compaction and filename.startswith("agent-acompact-"):
                continue
            if file_size < min_agent_size:
                continue
            if is_fork_context_ref(jsonl_file):
                continue
        if is_snapshot_only(jsonl_file):
            # Clean up existing HTML if it was generated before this filter
            temp_hash = agent_hash_from_filename(filename) if is_agent else get_hash_from_filename(filename)
            orphan_html = find_existing_html(output_path, temp_hash, is_agent)
            if orphan_html:
                orphan_html.unlink()
            continue

        agent_suffix = ""
        if is_agent:
            agent_id = agent_hash_from_filename(filename)
            agent_suffix = f"Agent-{agent_id}"
            hash_prefix = agent_id
        else:
            hash_prefix = get_hash_from_filename(filename)

        display_name = (
            f"{hash_prefix} {agent_suffix}".strip()
            if not is_agent
            else agent_suffix
        )

        result = None
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

        # Remember each agent's HTML (generated or already present) so invoking
        # chats can link their "agent completed" notices to it.
        if is_agent:
            agent_fn = result or (existing_html.name if existing_html else None)
            if agent_fn:
                AGENT_HTML_MAP[agent_id] = agent_fn

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

    # Always refresh the BTW view so it never goes stale; the dashboard links to
    # it from the "+" menu.
    print("  Generating dashboard...")
    with redirect_stdout(io.StringIO()):
        generate_btw_view(config)
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
