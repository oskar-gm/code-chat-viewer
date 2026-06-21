#!/usr/bin/env python3
"""
Code Chat Viewer v2.6.0

Converts Claude Code chat JSON files (JSONL format) into formatted HTML
visualizations with terminal-style aesthetics, syntax highlighting, and
interactive features.

Copyright (c) 2025-2026 Óscar González Martín
Licensed under the MIT License - see LICENSE for details

Author: Óscar González Martín
Version: 2.6.0
Contact: oscar@nucleoia.es
Website: https://nucleoia.es
Repository: https://github.com/oskar-gm/code-chat-viewer
LinkedIn: https://linkedin.com/in/oscar-gonz

For usage instructions, see README.md or visit the repository.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from html import escape

sys.stdout.reconfigure(encoding="utf-8")

# Icon embedded as base64 for favicon and header (self-contained, no external files)
# 32x32 PNG resized from original icon.png
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACx"
    "jwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAQGSURBVFhHrZdZrF5TFMdb1Dy15sQUQxpDJGii"
    "EkEiUbwIQYImJJWaQkRiSDzRh0qUh6qYIpHyIER4MISEEFTVFTGUKqlLcsNtDG3uxe25+/9bsk73"
    "/uxv9bT33rq/l/N9e41nD2uvM2PG/wDYw8wOBo4ws8OBg8xs96g3bQCHAlcBjwEfAj+Z2SZgVNIo"
    "8CcwCHwEPJ1SWgScEP1MGTM708yelfSHTRGgAd4Bro5+J8TMDgAeB6LfnQL4BJgf43QCnAF8Vxn3"
    "ZSHpZ+AVM3sQuDOldAdwH/BkXp7RWr+QZ+SiGK8PMztf0kg26AsOvAZcYmZ7R7sa4KiU0q3AV5Vt"
    "6wf43sx2jTYtwKlACd6LDfwCXB71J2JgYGAWcBcwXiXSnQCwl6R1VfCS8RfAMVF/KgBnm9l7wOqm"
    "ac6J8hbgoY7gG/z4Rd1pBzixTFOJ7/+bppkXdXeEmc2KY5MCeKrj7R+JegXgkC1btpwWxuZK2mBm"
    "i305J9qoPYA5wOaSgD9zZTss6jrANb4ps/7canyZj6WUrgPeB34ELuy37iCldGV2VifwctQDjs9n"
    "vwV41cwOdJnfAfmkjAwPD+8LrCh6kh42sz2jvx6SHi1vXx27G4vczHZJKd1ezdIQsLD2ASzIsufK"
    "WEppIdCWb+DLpmnOrW16SHo3K5Wknd5RAe4ug/mkbLO2kl7I8gX1uC+jpJWV/aW1vEXS2iysK97J"
    "RQ7cVMYlrYg1Ie+hv4Fhv6KDbL+yNzLX1/J2eiX9kIPWCZxU63n9lvRplnkiy8omBRaV5ILNzcDG"
    "bOP744Za3mJmMyW1l069BF65oq7jewP4Nev4heONyNvZrF22sbExrymrK19+QXWeqBZgVVasJ2Fx"
    "1CuY2WzfC5JWARdI8htusNT38fHxK7I/L7vnRfttAJ6pEijH8K2o14Vfw9l2aRnzZQVO8dnt1+71"
    "GPf7BTU0NLR1MwPXZie9fQCoaZqzooOImR2bUrrH+8Eo66JaLo+xpB30KZW0Kc4CsBbYJzrZWYDl"
    "5UXzc3ktXFInUJLIV+icPk9TxF/Ce8ry5hX/XcteXID1Phpz8AYCuLjP6yQBLgO+KRGLz65S78re"
    "Df0ekijLMRj1uwD2B+allO4FPqsDV8G98M2Oti3A6UBbmEoi+fmty/NMrQQ+l/SmpJfM7EVJrwNr"
    "JA0X28pH/fsDrx0xbh+5tD4B/BWWwduqgcr3dqmD5v8jwAOdveD2AG4rziT1e5wkktZLWurHNfqf"
    "EOANd9LbjVsd/gas870i6R9J48CYpM2AfyusAZ73b4Wmaeab2W7R76TIvX8f3rblD9GZeZmONLPj"
    "zOxob9F22HRMBT+3wNdV4I+BiWv6dOHrlQNvBG6J8unkX69xdeZmL3NhAAAAAElFTkSuQmCC"
)

# Dark version for favicon (visible on white browser tab)
ICON_FAVICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAECElEQVR4nJ2XXYhVVRTHf+fcq2NZ"
    "OoWWmR+DEKVGxUhCERX4kJWQYURKVFAJgVAQ9FIv9hAW5FNIBGVUBOlDhEXRQ4VYoaRRDAh+RPRF"
    "fuQ4YurtjnNiw3/B333P3Lnjgs0+5+y91/f673UKJqYGcN7epwNLgMXAAuCKoiimVVV1BhgBfgcO"
    "aPyT8amAMXqkQiNRH7AaeB/4RQpVE4y/gM+ADcD8TJGerA56HNifMR8F/tOcCx6t+X4K2ALME8+S"
    "HoTPBz7PGJ+rEXgSOAIcA85ka+ezM0eBVd2UaGheDvyhQ22NYJLi+i7wCLAUmAVcDsyUhbcDzwFf"
    "WqiS8i09J8/dpPCWLjxelimZQrgzeRWYS+90C/ChKf+v5he13nThaVxllo+a8F+BOzJPNXQmkjUs"
    "aoixW/ew3J94nQYGcw80NH9SY/khlVuiKVYZdVS6VaYQCs8TChvOp6n5ARM+JgVGVO8hPGfcLZvd"
    "C3npFflLExiSYC+jpzLhxTh17PmTrHRqZN6pVXplTdx/zAS64KWqhLW2Vgj90tkbgZfMe5Fj49IH"
    "sr5t1j+ptaYJn6oMjmzeZjwG9e0doWalEK6v8cYFdImyPIAjzWcNteLQXcBeK6nNQL/l0GZ9f0hn"
    "NtrelNwD2teRxDeb1TH/ZGVSZsy+A+6284WM+FsWJ0DClP5Z544JvDoA6EG7pUKBHbZ+pQnfCUyz"
    "xEwhSXSf1t+ztT4L27eGgtNzTzxt1gfkfmSMkrbPCvMjOZObnbZpbWXm4gTpn5oBmzoSsizLZ2oU"
    "+NjiHwwXAVuN2VfC9H5dQikEl5rXXre9+4AVZvkFIVhnCRgh2Ju5ybM3XTZfaF/qD9bo+Y2wCdij"
    "b8PA84YjblDhDCvLg0oWzcu0dViNuF9n8b3TGKdSfQtYaPsdome7B/rlvlAgwvBCDQSHIh7nHzTi"
    "nsjLLCC7oYTcoXzaaonKdhMe98Bx4Noa7d2iQkz6akIWgt1zb2YNy+JgtiLDgQCk74HLzPLJUH4z"
    "viaeLcn5DZjhjCOx2pkyu4EbulgYz9EHhGeCBuyaj14yPb/smhbqAY+Mo8RpoV+eiN0oKf2KKiEX"
    "PiRAKpuKeal+/n41orN0oGnolS6bb/RttZQ6oX0NQfACYcNtwK2WwG0ZOUUNzipdaKVrHJZdD+yy"
    "RInEXCtFIlQTjTF1xN6ipwqYY57vIG8e1puFY0K+fXZbtuSdtuaWBLYMTyqD70dNzoT/BYWe/8yq"
    "otdxTnFOPyP3mGEdONGsUaAQk41qwVtW5wmi3xZ4Xa0SLeSRYf2OHQYOWo8x3j9mLZWar5H7w/IR"
    "IWNcv71SdFPFZA5g3U2Kf7pw0k3oe7oN/1+YNEWsHgO+Bu7NBF8U0270P4j3d982oq+XAAAAAElF"
    "TkSuQmCC"
)

def parse_chat_json(json_file: str) -> List[Dict]:
    """Read and parse a JSONL file line by line."""
    messages = []
    with open(json_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    data['_line_number'] = line_num
                    messages.append(data)
                except json.JSONDecodeError as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    continue
    return messages

# Application version — single source of truth (used in headers and meta tags).
APP_VERSION = "2.6.0"

# Time display format for timestamps: "12h" (AM/PM) or "24h".
# Set by generate_html() from config; "12h" is the default.
TIME_FORMAT = "12h"

# ====== KNOWN JSONL SCHEMA ======
# What CCV recognizes today. Single source of truth shared by two tools:
#   - the audit report (manager.py) flags anything OUTSIDE these sets as a
#     possible format change, so a genuinely new Claude Code type gets noticed;
#   - the coverage tests check the renderers handle everything INSIDE them.
# When a new type appears, confirm what it is and add it to the right set.

# Top-level types CCV renders as conversation messages.
KNOWN_MESSAGE_TYPES = frozenset({
    'user', 'assistant', 'summary', 'file-history-snapshot',
})

# Session metadata/state entries Claude Code writes to the JSONL that are NOT
# conversation messages — CCV ignores them on purpose. Known and expected, so
# the audit must not flag them as format changes.
KNOWN_METADATA_TYPES = frozenset({
    'system', 'custom-title', 'attachment', 'agent-name', 'last-prompt',
    'permission-mode', 'mode', 'ai-title', 'queue-operation', 'bridge-session',
})

# Content-item types inside a message's content list. 'image' is part of the
# format but CCV has no dedicated renderer for it yet (shown as a generic block).
KNOWN_CONTENT_TYPES = frozenset({
    'text', 'thinking', 'tool_use', 'tool_result', 'image',
})


def _time_pattern() -> str:
    """strftime pattern for the time portion, per TIME_FORMAT."""
    return '%H:%M' if TIME_FORMAT == "24h" else '%I:%M %p'


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to `YYYY-MM-DD <time>` in local timezone.

    The time portion follows TIME_FORMAT: 12h (AM/PM, default) or 24h.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).astimezone()
        return dt.strftime(f'%Y-%m-%d {_time_pattern()}')
    except (ValueError, TypeError, AttributeError):
        return ""


def _format_system_markers(html: str) -> str:
    """Style system markers embedded in already-escaped message text.

    - <system-reminder>...</system-reminder>  -> orange span, tags stripped
    - [Request interrupted by user] -> red span (the "for tool use" twin is hidden upstream)

    Runs after HTML escaping, so the angle-bracket tags appear as &lt;...&gt;.
    Both markers can be embedded mid-text, so this works inline (not per-message).
    """
    def _reminder(m):
        inner = m.group(1)
        inner = re.sub(r'^(<br>)+', '', inner)
        inner = re.sub(r'(<br>)+$', '', inner)
        return f'<span class="system-reminder">{inner}</span>'

    html = re.sub(
        r'&lt;system-reminder&gt;(.*?)&lt;/system-reminder&gt;',
        _reminder, html, flags=re.DOTALL)
    html = re.sub(
        r'(\[Request interrupted by user\])',
        r'<span class="request-interrupted">\1</span>', html)
    # Bash commands sent with "!" in Claude Code arrive as <bash-input>cmd</bash-input>
    # plus <bash-stdout>/<bash-stderr>. Show the command as "! cmd" in red (as the CLI
    # colours it) and the output cleanly (stderr only when non-empty), tags stripped.
    html = re.sub(r'&lt;bash-input&gt;(.*?)&lt;/bash-input&gt;',
                  lambda m: f'<span class="bash-bang">! {m.group(1).strip()}</span>', html, flags=re.DOTALL)
    html = re.sub(r'&lt;bash-stdout&gt;(.*?)&lt;/bash-stdout&gt;',
                  lambda m: f'<span class="bash-out">{m.group(1)}</span>' if m.group(1).strip() else '', html, flags=re.DOTALL)
    html = re.sub(r'&lt;bash-stderr&gt;(.*?)&lt;/bash-stderr&gt;',
                  lambda m: f'<span class="bash-err">{m.group(1)}</span>' if m.group(1).strip() else '', html, flags=re.DOTALL)
    return html


def escape_html_preserve_structure(text: str) -> str:
    """Escape HTML while preserving text structure (newlines, spaces)."""
    if not text:
        return ""

    text = text.replace('\r', '')  # Normalize Windows line endings
    text = escape(text)
    text = text.replace('\n', '<br>')
    # Compact excessive empty lines: 3+ breaks → 2 (preserve paragraph breaks)
    text = re.sub(r'(<br>){3,}', '<br><br>', text)
    text = re.sub(r'  +', lambda m: '&nbsp;' * len(m.group()), text)
    # Strip leading/trailing breaks to avoid blank space at top/bottom
    text = re.sub(r'^(<br>)+', '', text)
    text = re.sub(r'(<br>)+$', '', text)

    return _format_system_markers(text)

def is_tool_result_message(content) -> bool:
    """Determine if a message is a tool_result (not a real user message)."""
    if isinstance(content, list):
        return any(isinstance(item, dict) and item.get('type') == 'tool_result' for item in content)
    return False

# ====== HELPER FUNCTIONS FOR SPECIAL MESSAGE TYPES ======

def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes (full and bare) from text."""
    text = text.replace('\r', '')  # Normalize Windows line endings
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)  # Full ANSI with ESC prefix
    text = re.sub(r'\[\d+m', '', text)  # Bare ANSI codes (without ESC prefix)
    text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse excessive newlines
    return text.strip()

def _get_text_from_content(content) -> str:
    """Extract first text value from a content list or string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                return item.get('text', '')
            elif isinstance(item, str):
                return item
    return ''

def _get_message_text(msg: Dict) -> str:
    """Extract text from a full message dict (top-level JSONL entry)."""
    message_data = msg.get('message', {})
    if not message_data:
        return ''
    return _get_text_from_content(message_data.get('content', []))

def extract_tag_content(text: str, tag_name: str) -> str:
    """Extract content from an XML-like tag. Returns content or empty string."""
    match = re.search(rf'<{re.escape(tag_name)}>(.*?)</{re.escape(tag_name)}>', text, re.DOTALL)
    return match.group(1) if match else ''

def has_tag(text: str, tag_name: str) -> bool:
    """Check if text contains a specific XML-like tag."""
    return f'<{tag_name}>' in text

def parse_command_tags(text: str) -> dict:
    """Parse command-name, command-message and command-args tags from text.
    Returns dict with name, message, args, display or None if not a command."""
    if '<command-name>' not in text:
        return None
    cmd_name = extract_tag_content(text, 'command-name')
    cmd_message = extract_tag_content(text, 'command-message')
    cmd_args = extract_tag_content(text, 'command-args')
    if not cmd_name:
        return None
    # Build display: /command args
    display = cmd_name if cmd_name.startswith('/') else f'/{cmd_name}'
    if cmd_args:
        display = f'{display} {cmd_args}'
    return {'name': cmd_name, 'message': cmd_message, 'args': cmd_args, 'display': display}

def is_compact_summary(text: str) -> bool:
    """Check if text is a compact summary (continuation marker)."""
    return text.strip().startswith('This session is being continued from a previous conversation')

def is_caveat_message(text: str) -> bool:
    """Check if text contains local-command-caveat (internal system text)."""
    return '<local-command-caveat>' in text

def is_stdout_message(text: str) -> bool:
    """Check if text contains local-command-stdout."""
    return '<local-command-stdout>' in text

def is_task_notification(text: str) -> bool:
    """Check if text contains task-notification tags."""
    return '<task-notification>' in text


def is_image_source_message(content) -> bool:
    """True if a user message is ONLY '[Image: source: ...]' reference lines.

    Claude Code writes a redundant text twin of an attached image as a separate
    user message (the cache path). The real image is shown as an Open-image
    link in its own message, so this reference is hidden to avoid duplication.

    Returns False if any non-text item (e.g. the actual image) is present, so
    the message carrying the real image is never hidden.
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text', '') or '')
            elif isinstance(item, str):
                parts.append(item)
            else:
                return False
        text = '\n'.join(parts)
    else:
        return False
    lines = [ln.strip() for ln in text.strip().split('\n') if ln.strip()]
    return bool(lines) and all(re.match(r'^\[Image: source: .+\]$', ln) for ln in lines)


def is_tool_use_interrupted_message(content) -> bool:
    """True if a user message is ONLY '[Request interrupted by user for tool use]'.

    Claude Code writes this as the text twin of a tool rejection, which CCV
    already renders as a [REJECTED] block, so it is hidden to avoid the duplicate.
    The plain '[Request interrupted by user]' (a real interruption, no tool) is
    NOT matched here and stays visible.
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text', '') or '')
            elif isinstance(item, str):
                parts.append(item)
            else:
                return False
        text = '\n'.join(parts)
    else:
        return False
    return text.strip() == '[Request interrupted by user for tool use]'

# AskUserQuestion result wording differs across Claude Code versions: older builds
# said "User has answered your questions:", newer ones "Your questions have been
# answered:". Both must be recognised or the answers render as a raw tool result.
_ASK_RESULT_PREFIXES = ('Your questions have been answered:',
                        'User has answered your questions:')


def parse_ask_result(text: str) -> list:
    """Parse AskUserQuestion tool result text into Q&A pairs.
    Returns list of dicts [{question, answer, notes, markdown}].
    Handles markdown with and without backtick wrappers."""
    prefix = next((p for p in _ASK_RESULT_PREFIXES if text.startswith(p)), None)
    if not prefix:
        return []

    # Remove prefix and suffix
    body = text[len(prefix):].strip()
    suffix_match = re.search(r'\.\s*You can now continue', body)
    if suffix_match:
        body = body[:suffix_match.start()]

    # Split by ", followed by " (separator between Q&A pairs)
    pairs = re.split(r',\s*(?=")', body.strip())

    results = []
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue

        notes = ''
        markdown = ''

        # 1. Extract user notes (remove from pair first)
        notes_match = re.search(r'\s*user notes:\s*(.+?)(?:,\s*"|\s*$)', pair, re.DOTALL)
        if notes_match:
            notes = notes_match.group(1).strip().rstrip(',').strip()
            pair = pair[:notes_match.start()] + pair[notes_match.end():]
            pair = pair.strip().rstrip(',').strip()

        # 2. Extract selected markdown — try with backticks first
        md_match = re.search(r'selected markdown:\s*```(.*?)```', pair, re.DOTALL)
        if md_match:
            raw_md = md_match.group(1).strip()
            # Strip language identifier from first line (e.g., 'python', 'js')
            lines = raw_md.split('\n')
            if lines and re.match(r'^[a-zA-Z]+$', lines[0].strip()):
                raw_md = '\n'.join(lines[1:])
            markdown = raw_md
            # Remove markdown from pair (discard trailing text after closing ```)
            pair = pair[:md_match.start()]
            pair = pair.strip().rstrip(',').strip()
        else:
            # Try without backticks — raw content after "selected markdown:"
            md_match = re.search(r'selected markdown:\s*(.+)', pair, re.DOTALL)
            if md_match:
                markdown = md_match.group(1).strip().rstrip(',').strip()
                pair = pair[:md_match.start()]
                pair = pair.strip().rstrip(',').strip()

        # 3. Extract Q="A" pattern
        qa_match = re.match(r'"([^"]*?)"\s*=\s*"([^"]*?)"', pair)
        if qa_match:
            results.append({
                'question': qa_match.group(1),
                'answer': qa_match.group(2),
                'notes': notes,
                'markdown': markdown
            })
        elif pair.strip():
            clean = pair.strip().strip('"')
            if clean:
                results.append({
                    'question': '',
                    'answer': clean,
                    'notes': notes,
                    'markdown': markdown
                })

    return results


def parse_user_rejection(text: str) -> dict | None:
    """Detect and parse a tool_use rejection with optional user feedback.

    Returns dict with 'feedback' (user message or empty) and 'has_feedback' flag,
    or None if not a rejection pattern.
    """
    if "doesn't want to proceed" not in text:
        return None
    feedback = ''
    if 'the user said:\n' in text:
        feedback = text.split('the user said:\n', 1)[1].strip()
    elif 'the user said:' in text:
        feedback = text.split('the user said:', 1)[1].strip()
    return {'feedback': feedback, 'has_feedback': bool(feedback)}


def _get_tool_result_text(item: dict) -> str:
    """Extract text from a tool_result item."""
    content = item.get('content', '')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for sub in content:
            if isinstance(sub, dict) and sub.get('type') == 'text':
                return sub.get('text', '')
    return ''


def _coerce_json_list(value):
    """Return a list from a value that may already be a list or a JSON string.

    Some clients serialize structured tool inputs (e.g. AskUserQuestion's
    `questions`, MultiEdit's `edits`) as a JSON-encoded string instead of a
    real array. Returns [] for anything that isn't a list or a string that
    decodes to one, so callers can iterate without exploding.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return value if isinstance(value, list) else []


def _coerce_json_dict(value):
    """Return a dict from a value that may already be a dict or a JSON string."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


# ====== SPECIAL MESSAGE RENDERING FUNCTIONS ======

def render_command_message(cmd_display: str, time_str: str, metadata_str: str, uuid: str, cwd: str) -> str:
    """Render a /command message with darker user-blue styling."""
    return f'''<div class="message user-msg command-msg">
<div class="msg-header">
<span class="bullet" style="color:#0066CC; font-size:12px;">&#9656;</span> <span class="label" style="color:#1E1E1E;">[COMMAND]</span> <span class="metadata">{escape(metadata_str)}</span>
</div>
<div class="msg-content" style="color:#0066CC; background:#EBF2FF; border-left:3px solid #0066CC;">{escape(cmd_display)}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator"></div>
</div>
'''

def render_stdout_message(clean_text: str, time_str: str, metadata_str: str, uuid: str, cwd: str) -> str:
    """Render a local-command-stdout message (non-compact) with grey styling."""
    return f'''<div class="message user-msg stdout-msg nav-skip">
<div class="msg-header">
<span class="bullet" style="color:#6B7280;">&#9654;</span> <span class="label" style="color:#6B7280;">[OUTPUT]</span> <span class="metadata">{escape(metadata_str)}</span>
</div>
<div class="msg-content" style="color:#374151; background:#F9FAFB; border-left:3px solid #9CA3AF;">{escape_html_preserve_structure(clean_text)}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator"></div>
</div>
'''

# {agentId: "subagent_type · description"} for the agents launched in the chat
# being rendered, so "agent completed" notifications can name which agent ran.
# Populated per chat in generate_html().
_TASK_AGENT_LABELS = {}

# {agentId: html_filename} for ALL generated agent chats — lets "agent completed"
# notices link to the agent's own chat (new tab). The manager fills this once,
# before rendering the invoking chats; empty means "no link" (e.g. standalone).
AGENT_HTML_MAP = {}


def _chat_agent_labels(messages: List[Dict]) -> dict:
    """Cross the Agent tool_uses (subagent_type + description) with their results
    (toolUseResult.agentId) within one chat → {agentId: label}."""
    tu, res = {}, {}
    for m in messages:
        msg = m.get("message", {})
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "tool_use" and it.get("name") == "Agent":
                inp = it.get("input", {}) if isinstance(it.get("input"), dict) else {}
                tu[it.get("id")] = (inp.get("subagent_type", "") or "", inp.get("description", "") or "")
            elif it.get("type") == "tool_result":
                tur = m.get("toolUseResult")
                if isinstance(tur, dict) and tur.get("agentId"):
                    res[tur["agentId"]] = it.get("tool_use_id")
    labels = {}
    for aid, tuid in res.items():
        if tuid in tu:
            labels[aid] = " · ".join(p for p in tu[tuid] if p)
    return labels


def render_task_notification(text: str, uuid: str) -> str:
    """Render a task-notification as a styled system message."""
    summary = extract_tag_content(text, 'summary')
    status = extract_tag_content(text, 'status')
    clean = re.sub(r'<[^>]+>', '', text).strip()
    status_upper = status.upper() if status else ''
    display_text = summary or clean or 'Task notification'

    # Name which agent ran (from <task-id> = agentId), if known in this chat, and
    # link to its chat (new tab) when the agent HTML exists.
    task_id = extract_tag_content(text, 'task-id')
    agent_suffix = ''
    if task_id and task_id in _TASK_AGENT_LABELS:
        agent_suffix = f' <span style="opacity:0.75; font-weight:600;">&middot; {escape(_TASK_AGENT_LABELS[task_id])}</span>'
    if task_id and AGENT_HTML_MAP.get(task_id):
        agent_suffix += f' <a href="{escape(AGENT_HTML_MAP[task_id])}" target="_blank" rel="noopener" class="agent-open" title="Open this agent&#39;s chat in a new tab">&#8599; open chat</a>'

    # Style based on status
    if status_upper == 'COMPLETED':
        icon = '&#10003;'
        accent = '#10893E'
        bg = '#F0FFF4'
        border_color = '#10893E'
    elif status_upper == 'IN_PROGRESS':
        icon = '&#9656;'
        accent = '#0066CC'
        bg = '#F0F7FF'
        border_color = '#0066CC'
    elif status_upper == 'FAILED':
        icon = '&#10007;'
        accent = '#DC2626'
        bg = '#FFF1F2'
        border_color = '#F87171'
    else:
        icon = '&#8226;'
        accent = '#6B7280'
        bg = '#F9FAFB'
        border_color = '#D1D5DB'

    return f'''<div class="message user-msg nav-skip"><div class="msg-content" style="color:{accent}; background:{bg}; border-left:3px solid {border_color}; padding:6px 12px; margin-left:15px; font-size:12px; border-radius:4px;"><span style="font-weight:700;">{icon}</span> <span style="font-weight:600;">[{escape(status_upper) if status_upper else 'TASK'}]</span> {escape(display_text)}{agent_suffix}</div><div class="separator"></div></div>
'''

def extract_ask_data(item: dict, msg: dict) -> list:
    """Normalize an AskUserQuestion tool_result into render-ready items.

    Prefers the STRUCTURED payload Claude Code stores in `msg.toolUseResult`
    (`questions` with their `options`, `answers` keyed by question, `annotations`
    with notes) — robust to result-text wording changes. Falls back to parsing
    the result text for older messages that lack the structured field. Returns
    None when the item is not an AskUserQuestion result.

    Each item: {question, header, multiSelect, options:[{label,description,
    selected}], answer, answer_is_free, notes, markdown}.
    """
    tur = msg.get('toolUseResult') if isinstance(msg, dict) else None
    if isinstance(tur, dict) and isinstance(tur.get('questions'), list) and isinstance(tur.get('answers'), dict):
        answers = tur['answers']
        annotations = tur.get('annotations') if isinstance(tur.get('annotations'), dict) else {}
        items = []
        for q in tur['questions']:
            if not isinstance(q, dict):
                continue
            qtext = q.get('question', '') or ''
            ans = answers.get(qtext, '')
            ans = ans if isinstance(ans, str) else str(ans)
            multi = bool(q.get('multiSelect'))
            opts_raw = q.get('options') if isinstance(q.get('options'), list) else []
            labels = [o.get('label', '') for o in opts_raw if isinstance(o, dict)]

            # Which offered option(s) match the answer. Multi-select answers may
            # arrive comma-joined; only split when nothing matched as a whole so
            # a legitimate comma inside a single label/free answer is preserved.
            selected = set()
            if ans:
                if ans in labels:
                    selected.add(ans)
                elif multi:
                    for part in (p.strip() for p in ans.split(',')):
                        if part in labels:
                            selected.add(part)
            answer_is_free = bool(ans) and not selected  # 'Other' / free text

            options = [{
                'label': o.get('label', '') or '',
                'description': o.get('description', '') or '',
                'selected': (o.get('label', '') or '') in selected,
            } for o in opts_raw if isinstance(o, dict)]

            note = ''
            ann = annotations.get(qtext)
            if isinstance(ann, dict):
                note = ann.get('notes', '') or ''

            items.append({
                'question': qtext, 'header': q.get('header', '') or '',
                'multiSelect': multi, 'options': options, 'answer': ans,
                'answer_is_free': answer_is_free, 'notes': note, 'markdown': '',
            })
        if items:
            return items

    # Fallback: parse the result text (older messages without toolUseResult)
    text = _get_tool_result_text(item)
    if text.startswith(_ASK_RESULT_PREFIXES):
        pairs = parse_ask_result(text)
        if pairs:
            for p in pairs:
                p.setdefault('header', '')
                p.setdefault('multiSelect', False)
                p.setdefault('options', [])
                p.setdefault('answer_is_free', False)
            return pairs
    return None


def render_ask_result_block(items: list, tool_use_id: str, uuid: str) -> str:
    """Render an AskUserQuestion result as an elegant amber block (open, not
    collapsible).

    Each item may carry the original `options` (with the chosen one flagged), so
    the block shows the question (with its header as a chip), the offered options
    with the selected one highlighted, free-text ('Other') answers, and notes —
    each part only when present. Items without `options` (text fallback) degrade
    to a clean question -> answer line.
    """
    blocks = []
    for i, it in enumerate(items):
        question = it.get('question', '') or ''
        header = it.get('header', '') or ''
        options = it.get('options') or []
        answer = it.get('answer', '') or ''
        note = it.get('notes', '') or ''
        markdown = it.get('markdown', '') or ''

        rows = []
        if question or header:
            chip = f'<span class="ask-chip">{escape(header)}</span>' if header else ''
            qtxt = f'<span class="ask-q-text">{escape(question)}</span>' if question else ''
            rows.append(f'<div class="ask-q">{chip}{qtxt}</div>')

        if options:
            opts_html = []
            for o in options:
                lbl = escape(o.get('label', ''))
                if o.get('selected'):
                    desc = o.get('description', '')
                    desc_html = f'<div class="ask-opt-desc">{escape(desc)}</div>' if desc else ''
                    opts_html.append(
                        f'<div class="ask-opt ask-opt-sel"><span class="ask-opt-mark">&#10003;</span>'
                        f'<span class="ask-opt-body"><span class="ask-opt-label">{lbl}</span>{desc_html}</span></div>')
                else:
                    opts_html.append(
                        f'<div class="ask-opt"><span class="ask-opt-mark">&#9675;</span>'
                        f'<span class="ask-opt-body"><span class="ask-opt-label">{lbl}</span></span></div>')
            rows.append(f'<div class="ask-opts">{"".join(opts_html)}</div>')
            if it.get('answer_is_free') and answer:
                rows.append(f'<div class="ask-free"><span class="ask-free-mark">&#9998;</span> {escape(answer)}</div>')
        elif answer:
            rows.append(f'<div class="ask-free"><span class="ask-free-mark">&#8594;</span> {escape(answer)}</div>')

        if note and note.strip() and note.strip() != answer.strip():
            rows.append(f'<div class="ask-note"><span class="ask-free-mark">&#9998;</span> {escape(note)}</div>')

        if markdown:
            rows.append(f'<pre class="ask-md">{escape(markdown)}</pre>')

        sep = '<div class="ask-sep"></div>' if i < len(items) - 1 else ''
        blocks.append(''.join(rows) + sep)

    content = ''.join(blocks)

    return f'''<div class="message user-msg ask-result-msg nav-always">
<div class="msg-header">
<span class="bullet" style="color:#D97706; font-size:14px;">&#10067;</span> <span class="label" style="color:#D97706;">[USER RESPONSE]</span> <span class="metadata">Tool ID: {escape(tool_use_id[-12:]) if tool_use_id else 'N/A'}</span>
</div>
<div class="ask-inner">
<div class="ask-body">{content}</div>
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator"></div>
</div>
'''


def render_user_rejection_block(rejection: dict, tool_use_id: str, uuid: str) -> str:
    """Render a tool_use rejection with optional user feedback.

    Shows a coral/red indicator for the rejection, and if the user provided
    feedback, displays it prominently as a user message.
    """
    feedback = rejection.get('feedback', '')

    if feedback:
        feedback_html = escape_html_preserve_structure(feedback)
        return f'''<div class="message user-msg reject-msg nav-always">
<div class="ask-inner" style="background:#FFF1F2; border-left:3px solid #F87171;">
<div class="msg-header">
<span class="bullet" style="color:#DC2626; font-size:14px;">&#10060;</span> <span class="label" style="color:#DC2626;">[REJECTED]</span> <span class="metadata">Tool ID: {escape(tool_use_id[-12:]) if tool_use_id else 'N/A'}</span>
</div>
<div style="padding:6px 12px; color:#1E1E1E; white-space:normal; margin-left:15px;">
<div style="font-weight:700; color:#991B1B; margin-bottom:4px;">User feedback:</div>
<div style="color:#1E1E1E;">{feedback_html}</div>
</div>
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator"></div>
</div>
'''
    else:
        return f'''<div class="message user-msg nav-skip"><div class="msg-content" style="color:#DC2626; background:#FFF1F2; border-left:3px solid #F87171; padding:6px 12px; margin-left:15px; font-size:12px; border-radius:4px;"><span style="font-weight:700;">&#10060;</span> <span style="font-weight:600;">[REJECTED]</span> Tool use rejected by user</div><div class="separator"></div></div>
'''


def render_compact_block(compact_data: dict) -> str:
    """Render a grouped compact block (collapsible, purple styling).
    compact_data: {summary_text, command_display, pre_compact, timestamp, uuid, cwd}"""
    summary_text = compact_data.get('summary_text', '')
    command_display = compact_data.get('command_display', '/compact')
    pre_compact = compact_data.get('pre_compact', '')
    time_str = compact_data.get('time_str', '')
    uuid = compact_data.get('uuid', '')

    # Collapse excessive newlines in pre-compact text
    if pre_compact:
        pre_compact = re.sub(r'\n{2,}', '\n', pre_compact)

    # Build collapsible content
    content_parts = []
    if pre_compact:
        content_parts.append(f'<div style="margin-bottom:10px;"><strong style="color:#7C3AED; display:block; margin-bottom:4px;">Pre-compact:</strong><pre style="background:#EDE9FE; padding:8px; border-radius:4px; font-size:12px; white-space:pre-wrap; max-height:300px; overflow-y:auto; margin:0;">{escape(pre_compact)}</pre></div>')
    if summary_text:
        content_parts.append(f'<div><strong style="color:#7C3AED; display:block; margin-bottom:4px;">Summary:</strong><pre style="background:#EDE9FE; padding:8px; border-radius:4px; font-size:12px; white-space:pre-wrap; max-height:300px; overflow-y:auto; margin:0;">{escape(summary_text)}</pre></div>')

    inner_content = '\n'.join(content_parts)

    # Unique ID for toggle
    block_id = f'compact-{uuid[-8:]}' if uuid else f'compact-{id(compact_data)}'

    return f'''<div class="message compact-msg nav-always" data-msg-uuid="{escape(uuid)}">
<div class="compact-inner">
<div class="msg-header compact-header" onclick="(function(){{ var c=document.getElementById('{block_id}'); c.style.display = c.style.display==='none'?'block':'none'; var t=document.getElementById('{block_id}-toggle'); t.textContent = c.style.display==='none'? '\\u25B6':'\\u25BC'; }})()" style="cursor:pointer;">
<span id="{block_id}-toggle" style="font-size:12px; color:#8B5CF6;">&#9654;</span>
<span class="bullet" style="color:#8B5CF6;">&#128230;</span> <span class="label" style="color:#7C3AED;">[COMPACT]</span> <span style="color:#6D28D9; font-size:13px; margin-left:8px;">{escape(command_display)}</span> <span class="metadata">{time_str}</span>
</div>
<div id="{block_id}" class="compact-content" style="display:none; max-height:600px; overflow-y:auto; padding:8px 12px; margin-left:15px;">
{inner_content}
</div>
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator"></div>
</div>
'''


# ====== COMPACT MESSAGE GROUPING ======

def group_compact_messages(messages: list) -> list:
    """Pre-process messages to group compact-related messages into single blocks.
    Returns a new list where compact groups are replaced by a single dict with _compact_group=True."""
    result = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        text = _get_message_text(msg)

        # Check if this is a compact summary message
        if (msg.get('message', {}).get('role') == 'user'
                and not is_tool_result_message(msg.get('message', {}).get('content', []))
                and is_compact_summary(text)):

            # Start collecting compact-related messages
            compact_data = {
                '_compact_group': True,
                'summary_text': text,
                'command_display': '/compact',
                'pre_compact': '',
                'time_str': format_timestamp(msg.get('timestamp', '')),
                'uuid': msg.get('uuid', ''),
                'cwd': msg.get('cwd', ''),
            }

            # Look ahead for related messages (up to 5)
            j = i + 1
            lookahead = 0
            while j < len(messages) and lookahead < 5:
                next_msg = messages[j]
                next_text = _get_message_text(next_msg)
                next_type = next_msg.get('type', '')
                next_role = next_msg.get('message', {}).get('role', '')

                # Snapshots pass through (not consumed by compact)
                if next_type == 'file-history-snapshot':
                    result.append(next_msg)
                    j += 1
                    lookahead += 1
                    continue

                # Caveat: consume and discard
                if next_role == 'user' and is_caveat_message(next_text):
                    j += 1
                    lookahead += 1
                    continue

                # Command with /compact: consume and record
                if next_role == 'user' and not is_tool_result_message(next_msg.get('message', {}).get('content', [])):
                    cmd = parse_command_tags(next_text)
                    if cmd and 'compact' in cmd.get('name', '').lower():
                        compact_data['command_display'] = cmd['display']
                        if next_msg.get('timestamp'):
                            compact_data['time_str'] = format_timestamp(next_msg['timestamp'])
                        j += 1
                        lookahead += 1
                        continue

                # Stdout: consume and clean ANSI
                if next_role == 'user' and is_stdout_message(next_text):
                    stdout_content = extract_tag_content(next_text, 'local-command-stdout')
                    compact_data['pre_compact'] = strip_ansi_codes(stdout_content)
                    j += 1
                    lookahead += 1
                    continue

                # Any other message type: stop looking
                break

            result.append(compact_data)
            i = j
        else:
            result.append(msg)
            i += 1

    return result


def format_tool_result_content(tool_result_data: Dict) -> str:
    """Format tool_result content - displays full content without truncation."""
    content = tool_result_data.get('content', '')
    tool_use_id = tool_result_data.get('tool_use_id', '')

    if isinstance(content, str):
        return escape_html_preserve_structure(content)
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    parts.append(escape_html_preserve_structure(text))
                else:
                    parts.append(f"[{item.get('type')}]")
        return '<br>'.join(parts)
    else:
        return escape(str(content))

def render_ask_tool_use(tool_id: str, tool_input: dict) -> str:
    """Render AskUserQuestion tool_use with structured questions and markdown previews."""
    questions = _coerce_json_list(tool_input.get('questions', []))
    if not questions:
        return None

    parts = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        question_text = q.get('question', '')
        header_text = q.get('header', '')
        multi = q.get('multiSelect', False)
        options = _coerce_json_list(q.get('options', []))

        q_html = f'<div style="font-weight:700; color:#E8E8E8; margin-bottom:4px;">{escape(question_text)}</div>'
        if header_text:
            q_html += f'<div style="color:#999; font-size:11px; margin-bottom:4px;">[{escape(header_text)}] {"Multi-select" if multi else "Single-select"}</div>'

        opts_html = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            label = opt.get('label', '')
            desc = opt.get('description', '')
            md = opt.get('markdown', '')
            opt_line = f'<div style="padding:2px 0 2px 12px; color:#E8E8E8;">&#8226; <strong>{escape(label)}</strong>'
            if desc:
                opt_line += f' &mdash; <span style="color:#999;">{escape(desc)}</span>'
            opt_line += '</div>'
            if md:
                opt_line += f'<pre style="background:#3C3C3E; color:#D4D4D4; padding:8px; margin:2px 0 4px 24px; border-radius:4px; font-size:11px; line-height:1.3; overflow-x:auto; white-space:pre;">{escape(md)}</pre>'
            opts_html.append(opt_line)

        parts.append(q_html + ''.join(opts_html))

    content = '<hr style="border:none; border-top:1px solid #5A5A5C; margin:6px 0;">'.join(parts)

    return f'''<details class="tool-use"><summary>Tool: AskUserQuestion</summary><div class="tool-use-content" style="white-space:normal;">
   ID: {escape(tool_id[:16])}...
<div style="margin-top:6px;">{content}</div>
</div></details>'''


# ====== /btw history injection ======
#
# Claude Code's `/btw` command (when used inline, without explicit fork) does
# NOT persist to disk in recent versions (>= ~v2.1.97). The only durable
# record is the user-typed prompt in `~/.claude/history.jsonl`. We pull those
# prompts back into the main chat flow as pseudo-messages so users can at
# least see WHEN and WHAT they asked, even if Claude's response wasn't kept.


def merge_btw_history_into_messages(messages: list, btw_entries: list) -> list:
    """Insert /btw pseudo-entries from history.jsonl into the message list at
    their timestamp position. Each pseudo-entry carries `_btw_inline_history`."""
    if not btw_entries:
        return messages

    pseudos = []
    for e in btw_entries:
        ts_ms = e.get('timestamp', 0) or 0
        try:
            ts_iso = datetime.fromtimestamp(ts_ms / 1000).astimezone().isoformat()
        except (ValueError, OSError, OverflowError):
            ts_iso = ''
        pseudos.append({
            '_btw_inline_history': True,
            'query': e.get('query', '') or e.get('display', '').replace('/btw', '', 1).strip(),
            'timestamp': ts_iso,
            'timestamp_ms': ts_ms,
        })

    pseudos.sort(key=lambda p: p['timestamp_ms'])

    def msg_ts(m):
        return m.get('timestamp', '') if isinstance(m, dict) else ''

    result = list(messages)
    for pseudo in reversed(pseudos):
        pseudo_ts = pseudo['timestamp']
        insert_at = 0
        for i, m in enumerate(result):
            if msg_ts(m) and msg_ts(m) <= pseudo_ts:
                insert_at = i + 1
        result.insert(insert_at, pseudo)
    return result


def render_btw_history_message(btw_data: dict) -> str:
    """Render a /btw pseudo-entry as a user-style message with Claude-cream
    styling and an English disclaimer next to the [USER] label."""
    query = btw_data.get('query', '') or ''
    timestamp_iso = btw_data.get('timestamp', '') or ''
    time_str = format_timestamp(timestamp_iso) if timestamp_iso else ''

    return f'''<div class="message user-msg btw-history-msg">
<div class="msg-header">
<span class="bullet">•</span> <span class="label">[USER]:</span> <span class="btw-history-note">/btw — Claude doesn't persist the answer</span> <span class="metadata">{escape(time_str)}</span>
</div>
<div class="msg-content btw-history-content">/btw {escape(query)}</div>
<div class="msg-footer">
<span class="uuid-small">from history.jsonl</span>
</div>
<div class="separator"></div>
</div>
'''


def render_write_tool_use(tool_id: str, tool_input: dict) -> str:
    """Render a Write tool_use as a full-width content block. Visually echoes the
    `new_string` side of an Edit diff (it IS new content being written) but with
    a distinct blue accent so it's easy to differentiate from Edits at a glance.
    Shares the collapsible `<details class="tool-use ...">` structure so the
    global Edit/Write toggle button operates on both."""
    file_path = tool_input.get('file_path', '')
    content = tool_input.get('content', '') or ''

    file_hint = f' <span class="tool-use-hint">&mdash; {escape(file_path)}</span>' if file_path else ''
    summary = f'Tool: Write{file_hint}'

    meta_lines = [f'   ID: {escape(tool_id[:16])}...']
    if file_path:
        meta_lines.append(f'   file_path: {escape(file_path)}')
    metadata = '<br>'.join(meta_lines)

    return (
        f'<details class="tool-use tool-use-write" data-tool-name="Write">'
        f'<summary>{summary}</summary>'
        f'<div class="tool-use-content" style="white-space:normal;">'
        f'{metadata}'
        f'<div class="edit-diff-container">'
        f'<div class="write-block">'
        f'<div class="write-block-head">content:</div>'
        f'<pre class="write-block-body">{escape(content)}</pre>'
        f'</div>'
        f'</div>'
        f'</div></details>'
    )


def render_edit_tool_use(tool_id: str, tool_name: str, tool_input: dict) -> str:
    """Render Edit / MultiEdit tool_use with a two-column diff view (old vs new)."""
    file_path = tool_input.get('file_path', '')

    if tool_name == 'MultiEdit':
        edits = _coerce_json_list(tool_input.get('edits', []))
    else:  # Edit (or Write fallback uses main path)
        edits = [{
            'old_string': tool_input.get('old_string', ''),
            'new_string': tool_input.get('new_string', ''),
            'replace_all': tool_input.get('replace_all', False),
        }]

    if not edits:
        return None

    file_hint = f' <span class="tool-use-hint">&mdash; {escape(file_path)}</span>' if file_path else ''
    summary = f'Tool: {escape(tool_name)}{file_hint}'

    meta_lines = [f'   ID: {escape(tool_id[:16])}...']
    if file_path:
        meta_lines.append(f'   file_path: {escape(file_path)}')
    metadata = '<br>'.join(meta_lines)

    total = len(edits)
    diff_blocks = []
    for idx, edit in enumerate(edits):
        if not isinstance(edit, dict):
            continue
        old_s = edit.get('old_string', '') or ''
        new_s = edit.get('new_string', '') or ''
        replace_all = bool(edit.get('replace_all', False))

        label_html = ''
        if total > 1:
            label_html = f'<div class="edit-diff-label">&#9472;&#9472; Edit {idx + 1}/{total} &#9472;&#9472;</div>'

        badge_html = ''
        if replace_all:
            badge_html = ' <span class="edit-replace-all">replace_all</span>'

        diff_blocks.append(
            f'{label_html}'
            f'<div class="edit-diff">'
            f'<div class="edit-diff-col edit-diff-old">'
            f'<div class="edit-diff-head">old_string:{badge_html}</div>'
            f'<pre class="edit-diff-body">{escape(old_s)}</pre>'
            f'</div>'
            f'<div class="edit-diff-col edit-diff-new">'
            f'<div class="edit-diff-head">new_string:</div>'
            f'<pre class="edit-diff-body">{escape(new_s)}</pre>'
            f'</div>'
            f'</div>'
        )

    diff_html = ''.join(diff_blocks)

    return (
        f'<details class="tool-use tool-use-edit" data-tool-name="{escape(tool_name)}">'
        f'<summary>{summary}</summary>'
        f'<div class="tool-use-content" style="white-space:normal;">'
        f'{metadata}'
        f'<div class="edit-diff-container">{diff_html}</div>'
        f'</div></details>'
    )


def _image_link_html(data: str, media: str, size_kb: int, label: str, inline: bool = False) -> str:
    """Build the clickable link that opens an image in the modal.

    inline=False -> the standalone blue button. inline=True -> a discreet text
    link used to replace an [Image #N] marker inside the user's message text.
    """
    if inline:
        return (
            f'<a class="msg-image-link inline-img" href="#" '
            f'onclick="openImage(this); return false;" '
            f'data-img="{escape(data)}" data-media="{escape(media)}" '
            f'title="{escape(media)}, {size_kb} KB">{escape(label)}</a>'
        )
    return (
        f'<a class="msg-image-link" href="#" '
        f'onclick="openImage(this); return false;" '
        f'data-img="{escape(data)}" data-media="{escape(media)}" '
        f'style="display:inline-block; margin:2px 0; padding:4px 10px; '
        f'background:#1E5BAA; color:#FFFFFF; border-radius:4px; '
        f'text-decoration:none; font-size:12px;">'
        f'&#128247; {escape(label)}</a>'
    )


def _render_text_with_inline_images(text: str, images: list, nums: list) -> str:
    """Escape the user's text and replace each [Image #N] marker with an inline link
    to the matching image. `nums` is the sorted list of DISTINCT marker numbers;
    marker N maps to images[nums.index(N)] — robust to non-consecutive numbers
    (e.g. [Image #1] + [Image #3]), unlike a plain N - n_min offset that fell out
    of range and left the marker as raw text."""
    escaped = escape_html_preserve_structure(text)

    def repl(m):
        n = int(m.group(1))
        idx = nums.index(n) if n in nums else -1
        if 0 <= idx < len(images):
            src = images[idx].get('source', {})
            if isinstance(src, dict) and src.get('type') == 'base64':
                data = src.get('data', '')
                if data:
                    media = src.get('media_type', 'image/png')
                    kb = max(1, len(data) * 3 // 4 // 1024)
                    return _image_link_html(data, media, kb, f'[Image #{n}]', inline=True)
        return m.group(0)

    return re.sub(r'\[Image #(\d+)\]', repl, escaped)


def format_content_item(item) -> str:
    """Format an individual content item."""
    if isinstance(item, str):
        return escape_html_preserve_structure(item)

    if not isinstance(item, dict):
        return str(item)

    item_type = item.get('type', '')

    if item_type == 'text':
        text = item.get('text', '')
        if text.strip() == '(no content)':
            return ''
        return escape_html_preserve_structure(text)

    if item_type == 'thinking':
        thinking_text = item.get('thinking', '')
        first_line = escape(thinking_text.strip().split('\n')[0])
        preview = f' <span class="thinking-preview">{first_line}...</span>' if first_line else '...'
        return f'<details class="thinking"><summary>☉ Thinking:{preview}</summary><div class="thinking-content">{escape_html_preserve_structure(thinking_text)}</div></details>'

    if item_type == 'tool_use':
        tool_name = item.get('name', 'unknown')
        tool_id = item.get('id', '')
        tool_input = _coerce_json_dict(item.get('input', {}))

        # Special rendering for AskUserQuestion with structured Q&A
        if tool_name == 'AskUserQuestion' and 'questions' in tool_input:
            ask_html = render_ask_tool_use(tool_id, tool_input)
            if ask_html:
                return ask_html

        # Special rendering for Edit / MultiEdit with diff view
        if tool_name in ('Edit', 'MultiEdit'):
            edit_html = render_edit_tool_use(tool_id, tool_name, tool_input)
            if edit_html:
                return edit_html

        # Special rendering for Write — full-width block, blue accent
        if tool_name == 'Write':
            write_html = render_write_tool_use(tool_id, tool_input)
            if write_html:
                return write_html

        input_lines = []
        for key, value in tool_input.items():
            input_lines.append(f'{escape(key)}: {escape(str(value))}')

        input_str = '<br>'.join(input_lines) if input_lines else '(no parameters)'

        # Same structure as Edit/Write/Ask (white-space:normal, no leading newline
        # or literal indent) so the top breathing room is identical across all tools.
        return (
            f'<details class="tool-use"><summary>Tool: {escape(tool_name)}</summary>'
            f'<div class="tool-use-content" style="white-space:normal;">'
            f'ID: {escape(tool_id[:16])}...<br>Parameters:<br>{input_str}'
            f'</div></details>'
        )

    if item_type == 'image':
        source = item.get('source', {})
        if isinstance(source, dict) and source.get('type') == 'base64':
            media = source.get('media_type', 'image/png')
            data = source.get('data', '')
            if data:
                # Standalone button. When the user's text references the image
                # with an [Image #N] marker, it is rendered inline instead (see
                # _render_text_with_inline_images) and this button is skipped.
                size_kb = max(1, len(data) * 3 // 4 // 1024)
                return _image_link_html(data, media, size_kb, f'Open image ({media}, {size_kb} KB)')
        return '<div class="unknown-type">[Image]</div>'

    if item_type == 'tool_result':
        return ''

    return f'<div class="unknown-type">[Type: {item_type}]</div>'

# Lines that are system/control text, not human conversation. Skipped when
# labelling a rewind and when counting the real turns it discarded.
_SYS_LINE_PREFIXES = ('<command-', '<local-command-', '<task-', '[Request interrupted', '[Image:')

def _first_human_line(msg: Dict) -> str:
    """First line of *human* conversation text in a message: skips blank lines,
    whole <system-reminder>…</system-reminder> blocks and control markers
    (commands, tool interruptions, image refs). Returns '' when the message
    carries no human text (e.g. it only holds tool_use/tool_result/thinking) —
    which is what tells a real conversation rewind apart from tool-call noise."""
    md = msg.get('message', {})
    content = md.get('content') if isinstance(md, dict) else None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = '\n'.join(it.get('text', '') for it in content
                         if isinstance(it, dict) and it.get('type') == 'text')
    else:
        return ''
    in_reminder = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('<system-reminder>'):
            in_reminder = '</system-reminder>' not in line
            continue
        if in_reminder:
            in_reminder = '</system-reminder>' not in line
            continue
        if any(line.startswith(p) for p in _SYS_LINE_PREFIXES):
            continue
        return line
    return ''


def format_message_html(msg: Dict, index: int, rewind_dest: dict = None) -> str:
    """Convert a complete message to HTML in terminal format."""

    msg_type = msg.get('type', '')

    # ====== HANDLE SUMMARIES ======
    if msg_type == 'summary':
        summary_text = msg.get('summary', '')
        leaf_uuid = msg.get('leafUuid', '')
        return f'''<div class="message summary-msg">
<div class="summary-header">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</div>
<div class="summary-content">
{escape(summary_text)}
<br><br>
<span class="uuid-small">Leaf UUID: {leaf_uuid[-12:]}</span>
</div>
</div>
'''

    # ====== HANDLE SNAPSHOTS ======
    if msg_type == 'file-history-snapshot':
        message_id = msg.get('messageId', '')
        entry = (rewind_dest or {}).get(message_id)
        if not entry:
            return ''  # not a rewind (guard snapshot): omit (also skipped in the loop)
        dest_uuid, dest_line, n_back = entry
        # Keep a generous slice; the visual truncation (…) is done by CSS so it
        # adapts to the available width and never wraps to a second line.
        snippet = escape(dest_line[:150]) if dest_line else 'an earlier point'
        # The destination can sit right above the marker (n_back == 0): show
        # "just above" instead of "0 messages back". Always render the count so
        # every rewind reads consistently.
        if n_back == 0:
            count_label = 'just above'
        else:
            count_label = f"{n_back} message{'' if n_back == 1 else 's'} back"
        count_html = (f'<span class="rewind-count">{count_label}</span>'
                      '<span class="rewind-sep">&middot;</span>')
        arrow = ('<svg class="rewind-arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
                 'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
                 '<path d="M8 12.5 V4 M4.5 7.5 L8 4 L11.5 7.5"/></svg>')
        goto = (f'<button type="button" class="rewind-goto" '
                f'onclick="gotoMessage(\'{escape(dest_uuid)}\')" '
                f'title="Go to where the conversation resumed">{arrow}<span>Go</span></button>')
        return (f'<div class="rewind">'
                f'<span class="rewind-icon">&#8634;</span>'
                f'<span class="rewind-label">Rewind</span>'
                f'<span class="rewind-sep">&middot;</span>'
                f'{count_html}'
                f'<span class="rewind-dest">&laquo;{snippet}&raquo;</span>'
                f'{goto}'
                f'</div>\n')

    # ====== HANDLE MESSAGES ======
    message_data = msg.get('message', {})
    if not message_data:
        return ''

    role = message_data.get('role', '')
    content = message_data.get('content', [])
    model = message_data.get('model', '')
    timestamp = msg.get('timestamp', '')
    uuid = msg.get('uuid', '')
    cwd = msg.get('cwd', '')
    git_branch = msg.get('gitBranch', '')

    if not content:
        return ''

    # ====== DETECT SPECIAL USER MESSAGE TYPES ======
    if role == 'user' and not is_tool_result_message(content):
        text = _get_text_from_content(content)

        # Image-source reference lines: redundant text twin of an attached image
        # (already shown as an Open-image link). Hide to avoid the duplicate.
        if is_image_source_message(content):
            return ''

        # Tool-use interruption: redundant text twin of a rejection (already
        # shown as a [REJECTED] block). Hide to avoid the duplicate.
        if is_tool_use_interrupted_message(content):
            return ''

        # Caveat messages: always hide
        if is_caveat_message(text):
            return ''

        # Task notifications: render as system message
        if is_task_notification(text):
            return render_task_notification(text, uuid)

        # Command messages: render with blue styling
        cmd = parse_command_tags(text)
        if cmd:
            time_str = format_timestamp(timestamp)
            metadata_parts = []
            if time_str:
                metadata_parts.append(time_str)
            if git_branch:
                metadata_parts.append(f'[{git_branch}]')
            metadata_str = '  '.join(metadata_parts) if metadata_parts else ''
            return render_command_message(cmd['display'], time_str, metadata_str, uuid, cwd)

        # Stdout messages (non-compact): render with grey styling
        if is_stdout_message(text):
            stdout_content = extract_tag_content(text, 'local-command-stdout')
            clean_text = strip_ansi_codes(stdout_content)
            time_str = format_timestamp(timestamp)
            metadata_parts = []
            if time_str:
                metadata_parts.append(time_str)
            if git_branch:
                metadata_parts.append(f'[{git_branch}]')
            metadata_str = '  '.join(metadata_parts) if metadata_parts else ''
            return render_stdout_message(clean_text, time_str, metadata_str, uuid, cwd)

    # ====== DETECT TOOL_RESULT (NOT A REAL USER MESSAGE) ======
    if role == 'user' and is_tool_result_message(content):
        tool_results_html = []
        # Collect inline user comments (text items alongside tool_results)
        user_comments = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                comment = item.get('text', '').strip()
                if comment:
                    user_comments.append(comment)
            elif isinstance(item, dict) and item.get('type') == 'tool_result':
                result_text = _get_tool_result_text(item)

                # AskUserQuestion result: prefer the structured toolUseResult,
                # fall back to the result-text wording (see extract_ask_data)
                ask_items = extract_ask_data(item, msg)
                if ask_items:
                    tool_results_html.append(render_ask_result_block(
                        ask_items, item.get('tool_use_id', ''), uuid))
                    continue

                # Check if this is a user rejection (with optional feedback)
                rejection = parse_user_rejection(result_text)
                if rejection:
                    tool_results_html.append(render_user_rejection_block(
                        rejection, item.get('tool_use_id', ''), uuid))
                    continue

                result_content = format_tool_result_content(item)
                tool_use_id = item.get('tool_use_id', 'N/A')

                tool_results_html.append(f'''<div class="tool-result-msg">
<div class="msg-header">
<span class="tool-result-toggle">&#9654;</span><span class="bullet">&#128228;</span> <span class="label">[TOOL RESULT]</span> <span class="metadata">Tool ID: {escape(tool_use_id[-12:])}</span>
</div>
<div class="msg-content">{result_content}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator"></div>
</div>''')

        # Render inline user comments as a visible user feedback block
        if user_comments:
            comment_text = escape_html_preserve_structure('<br>'.join(user_comments))
            tool_results_html.append(f'''<div class="message user-msg ask-result-msg nav-always">
<div class="ask-inner">
<div class="msg-header">
<span class="bullet" style="color:#D97706; font-size:14px;">&#128172;</span> <span class="label" style="color:#D97706;">[USER COMMENT]</span>
</div>
<div style="padding:4px 12px; color:#1E1E1E; white-space:normal; margin-left:15px;">{comment_text}</div>
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator"></div>
</div>''')

        return '\n'.join(tool_results_html)

    # ====== REAL MESSAGES (USER OR ASSISTANT) ======
    if role == 'user':
        icon = '👤'
        label = 'USER'
        msg_class = 'user-msg'
    elif role == 'assistant':
        icon = '🤖'
        label = 'ASSISTANT'
        msg_class = 'assistant-msg'
    else:
        icon = '❓'
        label = role.upper()
        msg_class = 'other-msg'

    time_str = format_timestamp(timestamp)
    # F2: model first, then the date/time in bold (the most useful anchor when
    # scanning), then the branch. Each part is escaped on its own so the
    # <strong> wrapper is not escaped away by a global escape().
    meta_parts = []
    if model:
        meta_parts.append(escape(model))
    if time_str:
        meta_parts.append(f'<strong>{escape(time_str)}</strong>')
    if git_branch:
        meta_parts.append(f'[{escape(git_branch)}]')
    metadata_html = '  '.join(meta_parts)

    # Process content (excluding tool_result handled above)
    content_parts = []

    if isinstance(content, str):
        content_parts.append(escape_html_preserve_structure(content))
    elif isinstance(content, list):
        # F1: render [Image #N] markers inline as links. Each distinct marker maps to
        # one image by position (sorted markers <-> images in pasting order), so
        # non-consecutive numbers (#1 + #3) map correctly. The first `referenced`
        # images go inline; any extra image with no marker still gets its button.
        imgs = [it for it in content if isinstance(it, dict) and it.get('type') == 'image']
        full_text = ' '.join(it.get('text', '') for it in content
                             if isinstance(it, dict) and it.get('type') == 'text')
        nums = sorted(set(int(n) for n in re.findall(r'\[Image #(\d+)\]', full_text)))
        inline_imgs = bool(imgs) and bool(nums)
        referenced = min(len(nums), len(imgs))
        shown_inline = 0
        for item in content:
            if (inline_imgs and isinstance(item, dict) and item.get('type') == 'image'
                    and shown_inline < referenced):
                shown_inline += 1
                continue  # rendered inline inside the text
            if inline_imgs and isinstance(item, dict) and item.get('type') == 'text':
                formatted = _render_text_with_inline_images(item.get('text', ''), imgs, nums)
            else:
                formatted = format_content_item(item)
            if formatted:
                content_parts.append(formatted)

    content_html = '<br>'.join(content_parts)

    if not content_html.strip():
        return ''

    # Mark messages that only contain thinking/tool blocks (no real text)
    has_text = False
    if isinstance(content, str) and content.strip():
        has_text = True
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str) and item.strip():
                has_text = True
                break
            elif isinstance(item, dict) and item.get('type') == 'text' and (item.get('text') or '').strip():
                has_text = True
                break
    if not has_text:
        msg_class += ' nav-skip'

    message_html = f'''<div class="message {msg_class}" data-msg-uuid="{escape(uuid)}">
<div class="msg-header">
<span class="bullet">•</span> <span class="label">[{label}]:</span> <span class="metadata">{metadata_html}</span>
</div>
<div class="msg-content">{content_html}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator"></div>
</div>
'''

    return message_html


def is_queued_user_message(m) -> bool:
    """True if `m` is a user message that was queued while the assistant worked.
    Claude Code stores these as type='attachment' with attachment.type='queued_command'
    (the text in attachment.prompt) and NO message.role, so the normal user/assistant
    passes skip them and the message disappears from the HTML."""
    if not (isinstance(m, dict) and m.get('type') == 'attachment'
            and isinstance(m.get('attachment'), dict)
            and m['attachment'].get('type') == 'queued_command'):
        return False
    prompt = m['attachment'].get('prompt')
    return bool(prompt.strip()) if isinstance(prompt, str) else bool(prompt)


def render_queued_message(msg, index, rewind_dest=None):
    """Render a queued user message as a normal user message. The prompt is usually a
    string, but can be a content-block list (e.g. queued text with pasted images)."""
    prompt = msg.get('attachment', {}).get('prompt', '')
    if isinstance(prompt, list):
        content = prompt
    else:
        content = [{'type': 'text', 'text': prompt if isinstance(prompt, str) else str(prompt)}]
    synthetic = {
        'type': 'user',
        'uuid': msg.get('uuid', ''),
        'timestamp': msg.get('timestamp'),
        'gitBranch': msg.get('gitBranch'),
        'message': {'role': 'user', 'content': content},
    }
    return format_message_html(synthetic, index, rewind_dest)


def generate_html(messages: List[Dict], output_file: str, dashboard_url: str = None, chat_title: str = "", chat_uuid: str = "", history_entries=None, time_format: str = "12h", agent_of: str = None):
    """Generate the complete HTML document in terminal style.

    `history_entries`, when provided, is a list of /btw entries from
    ~/.claude/history.jsonl. The ones matching `chat_uuid` are merged into the
    flow as pseudo-messages styled in Claude cream so users can see /btw
    queries that Claude Code doesn't persist as full Q+A any more.

    `time_format` controls the time portion of timestamps: "12h" (AM/PM,
    default) or "24h".
    """
    global TIME_FORMAT, _TASK_AGENT_LABELS
    TIME_FORMAT = time_format if time_format in ("12h", "24h") else "12h"
    _TASK_AGENT_LABELS = _chat_agent_labels(messages)

    # Count statistics (distinguishing tool_results)
    total_lines = len(messages)
    real_user_msgs = 0
    tool_result_msgs = 0
    assistant_msgs = 0
    summaries = 0

    for m in messages:
        if m.get('type') == 'summary':
            summaries += 1
        elif is_queued_user_message(m):
            real_user_msgs += 1
        elif m.get('message', {}).get('role') == 'user':
            content = m.get('message', {}).get('content', [])
            if is_tool_result_message(content):
                tool_result_msgs += 1
            else:
                text = _get_message_text(m)
                if is_compact_summary(text):
                    summaries += 1
                else:
                    real_user_msgs += 1
        elif m.get('message', {}).get('role') == 'assistant':
            assistant_msgs += 1

    # Pre-process: group compact-related messages, then inject /btw entries
    # from history.jsonl (those matching this session) at their timestamps.
    processed_messages = group_compact_messages(messages)

    btw_for_session = []
    if history_entries and chat_uuid:
        btw_for_session = [e for e in history_entries if e.get('sessionId') == chat_uuid]
    if btw_for_session:
        processed_messages = merge_btw_history_into_messages(processed_messages, btw_for_session)

    btw_count = sum(1 for m in processed_messages if isinstance(m, dict) and m.get('_btw_inline_history'))

    # F3: detect conversation rewinds. A real rewind = an abandoned prompt with
    # human text whose parent has a LATER sibling that is also human text (the
    # retry); forks made only of tool_use/tool_result are ignored. The label is
    # the nearest ancestor with human text; N is how many human messages sit
    # between that destination and the rewind marker ON SCREEN (the snapshot's
    # position) — i.e. how far up the Go button scrolls. Measuring the abandoned
    # branch instead gave huge, confusing counts when the destination is right
    # above (e.g. two retries of the same prompt showing "24 messages back").
    msg_nodes = {}
    siblings = {}
    for idx, m in enumerate(messages):
        if isinstance(m, dict) and m.get('uuid') and m.get('type') in ('user', 'assistant', 'system'):
            u = m['uuid']
            msg_nodes[u] = {'parent': m.get('parentUuid'), 'idx': idx, 'line': _first_human_line(m)}
            siblings.setdefault(m.get('parentUuid'), []).append((idx, u))

    def _rewind_destination(prompt_uuid):
        node = msg_nodes.get(prompt_uuid)
        if not node or not node['line']:
            return None  # the abandoned prompt must itself be human text
        later = [si for si, su in siblings.get(node['parent'], [])
                 if su != prompt_uuid and si > node['idx'] and msg_nodes[su]['line']]
        if not later:
            return None  # no human retry after it -> active branch, not a rewind
        cur, seen = node['parent'], set()
        while cur and cur in msg_nodes and cur not in seen:
            seen.add(cur)
            if msg_nodes[cur]['line']:
                return cur
            cur = msg_nodes[cur]['parent']
        return None

    rewind_dest = {}
    for snap_idx, m in enumerate(messages):
        if isinstance(m, dict) and m.get('type') == 'file-history-snapshot':
            mid = m.get('messageId', '')
            if mid and mid not in rewind_dest:
                dest = _rewind_destination(mid)
                if dest:
                    dest_idx = msg_nodes[dest]['idx']
                    n_back = sum(1 for nd in msg_nodes.values()
                                 if dest_idx < nd['idx'] < snap_idx and nd['line'])
                    rewind_dest[mid] = (dest, msg_nodes[dest]['line'], n_back)

    # Generate HTML for all messages
    messages_html = []
    shown_rewind_mids = set()
    for i, msg in enumerate(processed_messages):
        # F3: render only snapshots that are real rewinds (skip guards/duplicates)
        if isinstance(msg, dict) and msg.get('type') == 'file-history-snapshot':
            mid = msg.get('messageId', '')
            if mid not in rewind_dest or mid in shown_rewind_mids:
                continue
            shown_rewind_mids.add(mid)
        # Compact groups are rendered directly
        if isinstance(msg, dict) and msg.get('_compact_group'):
            msg_html = render_compact_block(msg)
        elif isinstance(msg, dict) and msg.get('_btw_inline_history'):
            msg_html = render_btw_history_message(msg)
        elif is_queued_user_message(msg):
            msg_html = render_queued_message(msg, i, rewind_dest)
        else:
            msg_html = format_message_html(msg, i, rewind_dest)
        if msg_html:
            messages_html.append(msg_html)

    messages_content = '\n'.join(messages_html)

    # Extract chat date and time (converted to local timezone)
    chat_timestamp = get_chat_timestamp(messages)
    if chat_timestamp:
        try:
            dt = datetime.fromisoformat(chat_timestamp.replace('Z', '+00:00')).astimezone()
            # Date format follows the chosen time format: 24h -> DD/MM/YYYY
            # (European), 12h -> MM/DD/YYYY (US, consistent with AM/PM).
            date_fmt = '%m/%d/%Y' if TIME_FORMAT == '12h' else '%d/%m/%Y'
            chat_date = dt.strftime(date_fmt)
            chat_time = dt.strftime(_time_pattern())
        except (ValueError, TypeError):
            chat_date = "N/A"
            chat_time = "N/A"
    else:
        chat_date = "N/A"
        chat_time = "N/A"

    # Build header action buttons
    header_actions_parts = []
    if dashboard_url:
        header_actions_parts.append(
            f'<a href="{escape(dashboard_url)}" class="header-btn" title="Back to Dashboard">&#9664; Dashboard</a>'
        )
    header_actions_parts.append(
        '<a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener" class="header-btn feedback" title="Report an issue or send feedback on GitHub">Feedback</a>'
    )
    header_actions_parts.append(
        '<a href="https://github.com/oskar-gm/code-chat-viewer/releases/latest" target="_blank" rel="noopener" class="header-btn release" title="Latest release — check for updates">Latest release</a>'
    )
    header_actions_html = '\n                '.join(header_actions_parts)

    # JS string literal for the per-chat sessionStorage key (safely quoted).
    chat_state_key = json.dumps(chat_uuid or "")

    # Complete HTML template in terminal style
    html_template = f'''<!DOCTYPE html>
<!--
=============================================================================
Code Chat Viewer v{APP_VERSION} - Professional Chat Log HTML Exporter
Generated HTML Visualization
=============================================================================

Created with: Code Chat Viewer
Repository: https://github.com/oskar-gm/code-chat-viewer
Website: https://nucleoia.es
License: MIT License

This HTML file was generated by Code Chat Viewer, an open-source tool
for converting Claude Code, VS Code, and Visual Studio Code chat logs (JSONL)
into readable, professional HTML visualizations with terminal-style aesthetics.

Learn more: https://github.com/oskar-gm/code-chat-viewer
Developer: https://nucleoia.es

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=============================================================================
-->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- SEO Meta Tags -->
    <meta name="description" content="Claude Code conversation visualization - Convert JSONL chat logs to professional HTML. Export AI coding conversations with terminal-style UI, collapsible tool results, conversation filter, and interactive dashboard. Works with Claude Code, VS Code, and AI coding assistants.">
    <meta name="keywords" content="Claude Code, Claude Code history, chat history, conversation history, claude code chat history, chat viewer, conversation export, JSONL to HTML, AI chat visualization, Claude Code logs, export claude code chats, chat log viewer, VS Code chat export, developer tools, Claude AI, AI conversation viewer, terminal UI, chat dashboard">

    <meta name="generator" content="Code Chat Viewer v{APP_VERSION} - https://github.com/oskar-gm/code-chat-viewer">
    <meta name="robots" content="index, follow">
    <meta name="language" content="English, Spanish">

    <!-- Open Graph / Social Media Meta Tags -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="Claude Code Conversation - Professional Terminal Visualization">
    <meta property="og:description" content="Professional visualization of Claude Code chat logs. Convert JSONL to HTML with terminal-style aesthetics. Created with Code Chat Viewer.">
    <meta property="og:url" content="https://github.com/oskar-gm/code-chat-viewer">
    <meta property="og:site_name" content="Code Chat Viewer">
    <meta property="og:locale" content="en_US">
    <meta property="og:locale:alternate" content="es_ES">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Claude Code Conversation Visualization">
    <meta name="twitter:description" content="Professional HTML export from Claude Code JSONL chat logs">

    <!-- Author & Publisher -->
    <link rel="author" href="https://nucleoia.es">
    <link rel="canonical" href="https://github.com/oskar-gm/code-chat-viewer">
    <meta name="publisher" content="nucleoia.es">

    <link rel="icon" type="image/png" href="data:image/png;base64,{ICON_FAVICON_BASE64}">
    <title>{escape(chat_title) + ' - ' if chat_title else ''}Code Chat Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html, body {{
            height: 100%;
        }}

        body {{
            font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #FFFFFF;
            color: #1E1E1E;
            line-height: 1.4;
            font-size: 13px;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
        }}

        /* Loading overlay: hides the brief double-jump while the saved scroll /
           state is restored on load; removed once restoration is done. */
        .chat-loading {{
            position: fixed;
            inset: 0;
            z-index: 3000;
            background: #FFFFFF;
            display: flex;
            flex-direction: column;
            gap: 14px;
            align-items: center;
            justify-content: center;
            transition: opacity 0.25s ease;
        }}
        .chat-loading-msg {{ color: #9AA0A6; font-size: 13px; letter-spacing: 0.2px; }}
        .chat-loading.hidden {{ opacity: 0; pointer-events: none; }}
        .chat-loading-spin {{
            width: 28px;
            height: 28px;
            border: 3px solid rgba(0,0,0,0.12);
            border-top-color: #999;
            border-radius: 50%;
            animation: chatSpin 0.7s linear infinite;
        }}
        @keyframes chatSpin {{ to {{ transform: rotate(360deg); }} }}

        .container {{
            width: 100%;
            background: #FFFFFF;
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }}

        .terminal-header {{
            background: #2D2D30;
            color: #CCCCCC;
            padding: 8px 15px;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .terminal-title {{
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .chat-name {{
            color: #FFFFFF;
            font-weight: 500;
            font-size: 13px;
        }}

        .chat-name-sep {{
            color: #666;
        }}

        .terminal-controls {{
            display: flex;
            gap: 8px;
        }}

        .terminal-btn {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }}

        .btn-close {{ background: #E81123; }}
        .btn-minimize {{ background: #FFB900; }}
        .btn-maximize {{ background: #10893E; }}

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

        .stats-bar {{
            background: #F3F3F3;
            border-bottom: 1px solid #E0E0E0;
            padding: 6px 15px;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
        }}

        .search-bar {{
            background: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            padding: 8px 15px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .search-input {{
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            font-family: inherit;
            font-size: 13px;
            background: white;
        }}

        .search-input:focus {{
            outline: none;
            border-color: #007ACC;
            box-shadow: 0 0 0 1px #007ACC;
        }}

        .filter-toggle {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            color: #333;
            cursor: pointer;
            white-space: nowrap;
            user-select: none;
        }}
        .filter-toggle input {{
            cursor: pointer;
            margin: 0;
            accent-color: #007ACC;
        }}

        .toolbar-divider {{
            width: 1px;
            height: 22px;
            background: #DDDDDD;
            flex-shrink: 0;
        }}

        /* User message navigation */

        .msg-nav {{
            display: flex;
            align-items: center;
            gap: 4px;
            background: #FFFFFF;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 3px 8px;
        }}

        .nav-mode-btn {{
            background: none;
            border: 1px solid transparent;
            border-radius: 3px;
            width: 28px;
            height: 28px;
            cursor: pointer;
            color: #999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }}

        .nav-mode-btn:hover {{
            color: #333;
            background: #F0F0F0;
        }}

        .nav-mode-btn.active#navUser {{
            color: #0066CC;
            border-color: #0066CC;
            background: #F0F7FF;
        }}
        .nav-mode-btn.active#navAssistant {{
            color: #10893E;
            border-color: #10893E;
            background: #F0FFF4;
        }}
        .nav-mode-btn.active#navAll {{
            border-color: #0077AA;
            background: linear-gradient(135deg, #F0F7FF, #F0FFF4);
        }}
        .nav-mode-btn.active#navAll svg path {{
            fill: url(#navGrad);
        }}

        .nav-arrow-btn {{
            background: #F0F0F0;
            border: 1px solid #CCCCCC;
            border-radius: 3px;
            width: 28px;
            height: 28px;
            cursor: pointer;
            font-size: 12px;
            color: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }}

        .nav-arrow-btn:hover {{
            background: #0066CC;
            border-color: #0066CC;
            color: white;
        }}

        .nav-arrow-btn:active {{
            transform: scale(0.95);
        }}

        .nav-counter {{
            font-size: 11px;
            color: #666;
            min-width: 35px;
            text-align: center;
            font-family: 'Consolas', monospace;
        }}

        /* Message highlight during navigation */
        .message.user-msg.nav-highlight {{
            animation: navPulseUser 1.5s ease-out;
        }}
        .message.assistant-msg.nav-highlight {{
            animation: navPulseAssistant 1.5s ease-out;
        }}

        @keyframes navPulseUser {{
            0% {{ box-shadow: 0 0 0 0 rgba(0, 102, 204, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(0, 102, 204, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0, 102, 204, 0); }}
        }}
        @keyframes navPulseAssistant {{
            0% {{ box-shadow: 0 0 0 0 rgba(16, 137, 62, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(16, 137, 62, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(16, 137, 62, 0); }}
        }}

        .terminal-content {{
            padding: 6px 12px;
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            background: #FFFFFF;
        }}

        .message {{
            position: relative;
            margin-bottom: 4px;
            font-size: 13px;
            line-height: 1.4;
        }}

        .copy-btn {{
            position: absolute;
            top: -1px;
            right: 4px;
            opacity: 0.6;
            background: none;
            border: none;
            cursor: pointer;
            padding: 3px;
            color: #6B7280;
            transition: opacity 0.12s, color 0.12s;
            line-height: 0;
        }}
        .copy-btn:hover {{
            opacity: 1;
            color: #1E5BAA;
        }}
        .copy-btn.copied {{
            color: #10893E;
            opacity: 1;
        }}
        .copy-btn svg {{
            width: 14px;
            height: 14px;
            display: block;
        }}

        .msg-image-link.inline-img {{
            display: inline-block;
            background: #D6E6FB;
            color: #1A4F8A;
            padding: 0 5px;
            border-radius: 3px;
            font-size: inherit;
            line-height: 1.35;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.12s;
        }}
        .msg-image-link.inline-img:hover {{
            background: #BBD4F5;
        }}

        /* User/Assistant/Command/Stdout/Reject/Task: their `.msg-header` is a
           direct child of `.message` (no inner box). Indent it by 11px so the
           bullet aligns with the chevron of boxed wrappers (border 3 + pad 8).
           Compact keeps its header inside `.compact-inner` and naturally inherits
           that 11px inset, so this selector skips it. The ask-result header IS a
           direct child here, so it aligns like user/assistant; tool-result has no
           `.message` wrapper at all. */
        .message > .msg-header {{
            padding-left: 11px;
        }}

        .msg-header {{
            display: flex;
            align-items: baseline;
            margin-bottom: 2px;
            gap: 6px;
            padding-right: 30px;
        }}

        .bullet {{
            font-weight: bold;
            font-size: 13px;
            margin-right: 3px;
        }}

        /* Higher specificity to prevent CSS cascade conflicts */
        .message.user-msg .bullet {{
            color: #0066CC;
        }}

        .assistant-msg .bullet {{
            color: #10893E;
        }}

        .label {{
            font-weight: 700;
            color: #1E1E1E;
            font-size: 12px;
        }}

        .user-msg .label,
        .assistant-msg .label {{
            font-size: 12px;
            letter-spacing: 0.3px;
        }}

        .metadata {{
            color: #999;
            font-size: 11px;
            margin-left: auto;
        }}
        .metadata strong {{
            color: #555555;
            font-weight: 700;
        }}

        .msg-content {{
            padding-left: 15px;
            color: #1E1E1E;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .tool-result-msg .msg-content {{
            padding-left: 10px;
        }}

        /* Higher specificity to prevent CSS cascade conflicts */
        .message.user-msg .msg-content {{
            padding: 4px 10px;
            color: #0066CC;
            background: #F8FBFF;
            border-left: 3px solid #0066CC;
            border-radius: 3px;
            margin-left: 12px;
            font-size: 13px;
            line-height: 1.4;
        }}

        .assistant-msg .msg-content {{
            padding: 4px 10px;
            color: #1E1E1E;
            background: #FAFFF8;
            border-left: 3px solid #10893E;
            border-radius: 3px;
            margin-left: 12px;
            font-size: 13px;
            line-height: 1.4;
        }}

        /* Tool-result: no envelope box on the wrapper itself. The header sits
           at the same X as the user/assistant headers (padding-left: 11px).
           The collapsible content gets its own gray box + orange border with
           margin-left to align with .msg-content of user/assistant. */
        .tool-result-msg {{
            margin-bottom: 4px;
        }}

        .tool-result-msg > .msg-header {{
            padding-left: 11px;
            cursor: pointer;
            user-select: none;
        }}

        .tool-result-msg > .msg-header:hover {{
            opacity: 0.85;
        }}

        .tool-result-msg > .msg-content {{
            display: none;
            background: #F8F8F8;
            border-left: 3px solid #FF6B00;
            padding: 4px 8px;
            margin: 4px 0 0 11px;
            border-radius: 3px;
            color: #333;
            font-size: 12px;
        }}

        .tool-result-msg > .msg-content.expanded {{
            display: block;
        }}

        .tool-result-toggle {{
            display: inline-block;
            font-size: 10px;
            color: #FF6B00;
            margin-right: 4px;
            transition: transform 0.15s;
        }}

        .tool-result-toggle.expanded {{
            transform: rotate(90deg);
        }}

        .thinking {{
            background: #FFFFFF;
            border-left: 3px solid #B8C8B8;
            margin: 3px 0;
            font-style: italic;
            color: #666;
            border-radius: 3px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
            font-size: 12px;
            line-height: 1.4;
        }}
        .thinking summary {{
            padding: 4px 8px;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .thinking[open] .thinking-preview {{
            display: none;
        }}
        .thinking-content {{
            padding: 6px 8px 5px;
            border-top: 1px solid #E0E8E0;
        }}

        .tool-use {{
            background: #48484A;
            border-left: 3px solid #6A6A6C;
            margin: 3px 0;
            color: #E8E8E8;
            border-radius: 3px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            font-size: 12px;
            line-height: 1.4;
        }}
        .tool-use summary {{
            padding: 4px 8px;
            cursor: pointer;
            user-select: none;
        }}
        .tool-use-content {{
            padding: 6px 8px 5px;
            border-top: 1px solid #5A5A5C;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}

        .tool-use-hint {{
            color: #9A9A9C;
            font-weight: 400;
            font-size: 12px;
        }}

        /* ====== Edit / MultiEdit diff view ====== */
        .edit-diff-container {{
            margin-top: 8px;
        }}
        /* Let the .tool-use-content padding own the vertical breathing room so
           Edit/Write match the generic tool block and thinking (6px top / 5px
           bottom). Without this, the last .edit-diff/.write-block margin-bottom
           stacks on the padding and leaves 11px below vs 6px above. */
        .edit-diff-container > :first-child {{
            margin-top: 0;
        }}
        .edit-diff-container > :last-child {{
            margin-bottom: 0;
        }}

        .edit-diff {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin: 6px 0;
        }}

        .edit-diff-col {{
            background: #3A3A3C;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}

        .edit-diff-old {{
            border-left: 3px solid #D16969;
        }}

        .edit-diff-new {{
            border-left: 3px solid #6AB06F;
        }}

        .edit-diff-head {{
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
            background: rgba(0,0,0,0.22);
            border-bottom: 1px solid rgba(0,0,0,0.3);
            font-family: 'Consolas', 'Courier New', monospace;
        }}

        .edit-diff-old .edit-diff-head {{
            color: #FFB3B3;
        }}

        .edit-diff-new .edit-diff-head {{
            color: #B3F0BD;
        }}

        .edit-diff-body {{
            padding: 8px;
            margin: 0;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.45;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
            max-height: 420px;
            overflow-y: auto;
        }}

        .edit-diff-old .edit-diff-body {{
            color: #FFB3B3;
        }}

        .edit-diff-new .edit-diff-body {{
            color: #B3F0BD;
        }}

        .edit-diff-label {{
            font-size: 11px;
            color: #BBB;
            margin: 10px 0 4px;
            font-family: 'Consolas', 'Courier New', monospace;
            letter-spacing: 0.5px;
        }}

        .edit-replace-all {{
            background: #5A5A5C;
            color: #FFD699;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
            margin-left: 4px;
            letter-spacing: 0.3px;
        }}

        /* Light theme (toggle A) */
        body.edit-diff-light .edit-diff-old {{
            background: #FFE4E4;
            border-left-color: #C42B1C;
        }}
        body.edit-diff-light .edit-diff-new {{
            background: #DFF7E0;
            border-left-color: #107C10;
        }}
        body.edit-diff-light .edit-diff-old .edit-diff-head {{
            background: rgba(196,43,28,0.14);
            color: #8B0000;
            border-bottom-color: rgba(196,43,28,0.22);
        }}
        body.edit-diff-light .edit-diff-new .edit-diff-head {{
            background: rgba(16,124,16,0.14);
            color: #0A5F0A;
            border-bottom-color: rgba(16,124,16,0.22);
        }}
        body.edit-diff-light .edit-diff-old .edit-diff-body {{
            color: #8B0000;
        }}
        body.edit-diff-light .edit-diff-new .edit-diff-body {{
            color: #0A5F0A;
        }}

        /* ====== Write tool: full-width block, blue accent ====== */
        .write-block {{
            background: #3A3A3C;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            min-width: 0;
            border-left: 3px solid #4A90E2;
            margin: 6px 0;
        }}
        .write-block-head {{
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
            background: rgba(0,0,0,0.22);
            border-bottom: 1px solid rgba(0,0,0,0.3);
            font-family: 'Consolas', 'Courier New', monospace;
            color: #A8C8FF;
        }}
        .write-block-body {{
            padding: 8px;
            margin: 0;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.45;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
            max-height: 420px;
            overflow-y: auto;
            color: #A8C8FF;
        }}
        body.edit-diff-light .write-block {{
            background: #E4EEFB;
            border-left-color: #1E5BAA;
        }}
        body.edit-diff-light .write-block-head {{
            background: rgba(30,91,170,0.14);
            color: #0B3F86;
            border-bottom-color: rgba(30,91,170,0.22);
        }}
        body.edit-diff-light .write-block-body {{
            color: #0B3F86;
        }}

        /* ====== /btw injected from history.jsonl ====== */
        .btw-history-msg .msg-content,
        .btw-history-content {{
            background: #F4F0E8 !important;
            color: #1E1E1E !important;
            border-left: 3px solid #C76A4D !important;
        }}
        .btw-history-msg .label {{
            color: #9A4A2E !important;
        }}
        .btw-history-msg .bullet {{
            color: #C76A4D !important;
        }}
        .btw-history-note {{
            color: #9A4A2E;
            font-size: 10px;
            font-style: italic;
            margin-left: 6px;
            opacity: 0.85;
        }}

        @media (max-width: 900px) {{
            .edit-diff {{
                grid-template-columns: 1fr;
            }}
        }}

        /* ====== Edit controls in search bar ====== */
        .edit-ctrl-group {{
            display: inline-flex;
            gap: 2px;
            align-items: center;
        }}

        .edit-ctrl-group .edit-ctrl-btn {{
            border-radius: 0;
        }}

        .edit-ctrl-group .edit-ctrl-btn:first-child {{
            border-top-left-radius: 3px;
            border-bottom-left-radius: 3px;
        }}

        .edit-ctrl-group .edit-ctrl-btn:last-child {{
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }}

        /* The theme toggle previews the CURRENT diff theme: a dark button while
           the diff is dark, a light/cream one once switched to light. The label
           says where a click takes you ("Switch to …"). Scoped to
           .edit-ctrl-group so it outweighs the generic .edit-ctrl-btn rules
           without touching the neighbouring Edits/Writes button. */
        .edit-ctrl-group .edit-ctrl-btn-theme {{
            border-left-width: 0 !important;
            background: #5E5E5E;
            border-color: #787878;
            color: #F5F5F5;
            min-width: 122px;
            justify-content: center;
        }}
        .edit-ctrl-group .edit-ctrl-btn-theme:hover {{
            background: #6B6B6B;
            border-color: #888888;
        }}

        .edit-ctrl-btn {{
            background: #F0F0F0;
            border: 1px solid #CCCCCC;
            border-radius: 3px;
            height: 28px;
            padding: 0 10px;
            cursor: pointer;
            font-size: 11px;
            color: #333;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-family: inherit;
            transition: all 0.15s;
            white-space: nowrap;
        }}

        .edit-ctrl-btn:hover {{
            background: #E4E4E4;
            border-color: #AAA;
        }}

        .edit-ctrl-btn:active {{
            transform: scale(0.97);
        }}

        .edit-ctrl-btn .edit-ctrl-icon {{
            font-size: 10px;
            font-family: 'Consolas', monospace;
            line-height: 1;
        }}

        .edit-ctrl-group .edit-ctrl-btn-theme.is-light {{
            background: #FFF5E1;
            border-color: #E0B060;
            color: #7A4E00;
        }}
        .edit-ctrl-group .edit-ctrl-btn-theme.is-light:hover {{
            background: #FBEFD0;
            border-color: #D4A050;
        }}

        /* ====== Chat UUID in header ====== */
        .chat-uuid-wrap {{
            display: inline-flex;
            align-items: stretch;
            background: rgba(255,255,255,0.04);
            border: 1px solid #444;
            border-radius: 3px;
            overflow: hidden;
        }}

        .chat-uuid {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
            color: #9AAFC4;
            user-select: all;
            padding: 3px 8px;
            letter-spacing: 0.3px;
            white-space: nowrap;
            line-height: 18px;
        }}

        .chat-uuid-copy {{
            background: none;
            border: none;
            border-left: 1px solid #444;
            cursor: pointer;
            padding: 0 7px;
            color: #9AAFC4;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 10px;
        }}

        .chat-uuid-copy:hover {{
            background: rgba(255,255,255,0.08);
            color: #FFF;
        }}

        .chat-uuid-copy.copied {{
            color: #6AB06F;
        }}

        @media (max-width: 900px) {{
            .chat-uuid-wrap {{
                display: none;
            }}
        }}

        .msg-footer {{
            padding-left: 12px;
            margin-top: 1px;
            font-size: 10px;
            color: #BBB;
            display: flex;
            gap: 16px;
        }}

        .separator {{
            border-top: 1px solid #EEEEEE;
            margin: 5px 0 0;
        }}

        .summary-msg {{
            background: #F8F8F8;
            border: 1px solid #E0E0E0;
            padding: 6px 10px;
            margin: 6px 0;
        }}

        .summary-header {{
            color: #666;
            font-size: 11px;
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        }}

        .summary-content {{
            color: #1E1E1E;
            padding-left: 8px;
        }}

        .rewind {{
            display: flex;
            align-items: center;
            gap: 5px;
            background: #F0FDFA;
            border-left: 3px solid #14B8A6;
            border-radius: 3px;
            padding: 4px 10px;
            margin: 4px 0;
            font-size: 13px;
            color: #0F766E;
        }}
        /* Everything keeps its size; only the destination shrinks + ellipsises,
           so the rewind stays on a single line at any width. */
        .rewind-icon, .rewind-label, .rewind-sep, .rewind-count, .rewind-goto {{
            flex-shrink: 0;
        }}
        .rewind-icon {{
            font-size: 15px;
            color: #0F766E;
            line-height: 1;
        }}
        .rewind-label {{
            font-weight: 600;
            color: #0F766E;
        }}
        .rewind-sep {{
            color: #3F9189;
        }}
        .rewind-count {{
            color: #3F6E68;
            font-size: 12px;
        }}
        .rewind-dest {{
            flex: 1 1 auto;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #115E59;
            font-style: italic;
        }}
        .rewind-goto {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: none;
            border: 1px solid #0D9488;
            color: #0F766E;
            cursor: pointer;
            font-size: 12px;
            padding: 2px 9px 2px 7px;
            border-radius: 3px;
            transition: background 0.12s;
        }}
        .rewind-goto:hover {{
            background: #CCFBF1;
        }}
        .rewind-arrow {{
            width: 12px;
            height: 12px;
            display: block;
        }}

        .system-reminder {{
            display: inline-block;
            color: #C2410C;
            background: #FFF7ED;
            border-left: 3px solid #FB923C;
            padding: 4px 10px;
            margin: 2px 0;
            border-radius: 4px;
            font-size: 12px;
            white-space: normal;
        }}

        .request-interrupted {{
            display: inline-block;
            color: #DC2626;
            background: #FFF1F2;
            border: 1px solid #FECACA;
            padding: 2px 8px;
            margin: 1px 0;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        }}

        /* Bash commands sent with "!" in Claude Code (and their output) */
        .bash-bang {{ color: #C0392B; font-weight: 600; }}
        .bash-out {{ color: #5A6270; }}
        .bash-err {{ color: #C0392B; }}
        .agent-open {{
            display: inline-block; margin-left: 8px; padding: 1px 8px;
            background: #E7F7EE; color: #157347; border: 1px solid #A6E3C4;
            border-radius: 10px; font-size: 11px; font-weight: 600; text-decoration: none;
            vertical-align: middle;
        }}
        .agent-open:hover {{ background: #CFEEDD; }}

        .img-modal {{
            display: none;
            position: fixed; top: 0; right: 0; bottom: 0; left: 0;
            background: rgba(0,0,0,0.55);
            z-index: 1000;
            justify-content: center; align-items: center;
            padding: 20px;
        }}
        .img-modal.open {{ display: flex; }}
        .img-modal-img {{
            max-width: 92vw; max-height: 88vh;
            object-fit: contain;
            border-radius: 4px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        }}
        .img-modal-figure {{
            position: relative;
            display: inline-block;
            line-height: 0;
        }}
        .img-modal-close {{
            position: absolute; top: 8px; right: 8px;
            background: rgba(0,0,0,0.55); border: none;
            color: #FFFFFF; font-size: 28px; line-height: 1;
            cursor: pointer; padding: 0;
            width: 40px; height: 40px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            text-shadow: 0 1px 3px rgba(0,0,0,0.9);
            z-index: 1;
        }}
        .img-modal-close:hover {{ color: #FCA5A5; background: rgba(0,0,0,0.75); }}
        .img-modal-close:focus-visible {{ outline: 2px solid #FFFFFF; outline-offset: 2px; }}

        .nav-toast {{
            position: fixed;
            bottom: 24px; left: 50%;
            transform: translateX(-50%) translateY(8px);
            background: #1F2937; color: #F9FAFB;
            padding: 8px 16px; border-radius: 6px;
            font-size: 13px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            opacity: 0; transition: opacity 0.25s, transform 0.25s;
            z-index: 1100; pointer-events: none;
        }}
        .nav-toast.show {{
            opacity: 1; transform: translateX(-50%) translateY(0);
        }}

        .uuid-small, .cwd-small {{
            font-family: 'Consolas', monospace;
            font-size: 9px;
        }}

        .footer {{
            background: #F3F3F3;
            border-top: 1px solid #E0E0E0;
            padding: 8px 15px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}

        /* Base styling for unknown content types */
        .unknown-type {{
            color: #999;
            font-style: italic;
            padding: 5px 0;
        }}

        /* Blue theme for unknown-type elements inside user messages */
        .user-msg .unknown-type {{
            color: #0066CC;
            background: #F0F7FF;
            padding: 8px 12px;
            border-radius: 4px;
            border-left: 2px solid #0066CC;
            display: inline-block;
            font-style: italic;
        }}

        /* Command messages */
        .command-msg {{
            margin-bottom: 8px;
        }}

        /* Compact messages */
        .compact-msg {{
            margin-bottom: 4px;
        }}
        .compact-inner {{
            background: #F5F3FF;
            border-left: 3px solid #8B5CF6;
            padding: 4px 8px;
            border-radius: 3px;
        }}
        .compact-msg .compact-header {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .compact-msg .compact-header:hover {{
            opacity: 0.85;
        }}

        /* AskUserQuestion result */
        .ask-result-msg {{
            margin-bottom: 4px;
        }}
        .ask-inner {{
            background: #FFFBEB;
            border-left: 3px solid #FCD34D;
            padding: 4px 8px;
            border-radius: 3px;
            margin-left: 12px;
        }}
        .ask-body {{
            padding: 4px 12px;
            color: #451A03;
            white-space: normal;
        }}
        .ask-q {{
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 6px;
            margin: 2px 0 4px;
        }}
        .ask-chip {{
            display: inline-block;
            background: #F59E0B;
            color: #3A2206;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            padding: 1px 6px;
            border-radius: 4px;
        }}
        .ask-q-text {{
            color: #78350F;
            font-weight: 600;
            font-size: 12px;
        }}
        .agent-chip {{
            display: inline-block;
            background: #7C3AED;
            color: #FFFFFF;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 1px 7px;
            border-radius: 4px;
            margin-left: 8px;
            vertical-align: middle;
        }}
        .ask-opts {{
            margin-top: 2px;
        }}
        .ask-opt {{
            display: flex;
            align-items: flex-start;
            gap: 6px;
            padding: 2px 0;
            color: #6E5A3E;
            font-size: 12px;
        }}
        .ask-opt-mark {{
            flex-shrink: 0;
            color: #C9A86A;
            font-size: 11px;
            line-height: 1.5;
        }}
        .ask-opt-body {{
            min-width: 0;
        }}
        .ask-opt-sel {{
            background: #FEF3C7;
            border-left: 2px solid #D97706;
            border-radius: 3px;
            padding: 3px 6px;
            margin: 1px 0;
            color: #5B3410;
        }}
        .ask-opt-sel .ask-opt-mark {{
            color: #B45309;
            font-weight: 700;
        }}
        .ask-opt-sel .ask-opt-label {{
            color: #92400E;
            font-weight: 700;
        }}
        .ask-opt-desc {{
            color: #6E5A3E;
            font-size: 11px;
            line-height: 1.35;
            margin-top: 2px;
        }}
        .ask-free {{
            background: #FEF3C7;
            border-left: 2px solid #D97706;
            border-radius: 3px;
            padding: 3px 8px;
            margin-top: 3px;
            color: #7C2D12;
            font-weight: 600;
            font-size: 12px;
        }}
        .ask-free-mark {{
            color: #B45309;
            font-weight: 700;
            margin-right: 2px;
        }}
        .ask-note {{
            color: #6E5A3E;
            font-style: italic;
            font-size: 11px;
            margin-top: 3px;
        }}
        .ask-md {{
            background: #FFF7ED;
            color: #78350F;
            padding: 8px;
            margin: 4px 0 0;
            border-radius: 4px;
            font-size: 11px;
            line-height: 1.3;
            overflow-x: auto;
            white-space: pre;
            border: 1px solid #FDE68A;
        }}
        .ask-sep {{
            border-top: 1px solid #FDE68A;
            margin: 8px 0;
        }}

        /* Stdout messages */
        .stdout-msg {{
            margin-bottom: 8px;
        }}

        /* Nav-always highlight animations (specific per type) */
        .message.compact-msg.nav-highlight {{
            animation: navPulseCompact 1.5s ease-out;
        }}
        .message.ask-result-msg.nav-highlight {{
            animation: navPulseAsk 1.5s ease-out;
        }}
        .message.reject-msg.nav-highlight {{
            animation: navPulseReject 1.5s ease-out;
        }}
        @keyframes navPulseCompact {{
            0% {{ box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(139, 92, 246, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }}
        }}
        @keyframes navPulseAsk {{
            0% {{ box-shadow: 0 0 0 0 rgba(217, 119, 6, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(217, 119, 6, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(217, 119, 6, 0); }}
        }}
        @keyframes navPulseReject {{
            0% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(220, 38, 38, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }}
        }}

        /* Custom scrollbar */
        .terminal-content::-webkit-scrollbar {{
            width: 12px;
        }}

        .terminal-content::-webkit-scrollbar-track {{
            background: #F0F0F0;
        }}

        .terminal-content::-webkit-scrollbar-thumb {{
            background: #C0C0C0;
            border-radius: 6px;
        }}

        .terminal-content::-webkit-scrollbar-thumb:hover {{
            background: #A0A0A0;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            body {{
                padding: 0;
            }}

            .container {{
                border: none;
            }}

            .terminal-content {{
                padding: 10px;
            }}

            .msg-content {{
                padding-left: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div id="chatLoading" class="chat-loading"><div class="chat-loading-spin"></div><div class="chat-loading-msg">Loading your chat… hang tight!</div></div>
    <div class="container">
        <div class="terminal-header">
            <div class="terminal-title">
                <img src="data:image/png;base64,{ICON_BASE64}" alt="" style="height:16px;width:16px;vertical-align:middle;margin-right:6px;" onerror="this.style.display='none'">
                <span>Code Chat Viewer</span>
                <span class="app-version" style="color:#777;font-size:11px;margin-left:8px;">v{APP_VERSION}</span>
                {'<span class="chat-name-sep">|</span><span class="chat-name">' + escape(chat_title) + '</span>' if chat_title else ''}
                {('<span class="agent-chip" title="Agent chat &mdash; a sub-chat launched by the Task tool, invoked by session ' + escape(agent_of) + '">AGENT CHAT</span>') if agent_of else ''}
            </div>
            <div class="header-actions">
                {('<span class="chat-uuid-wrap" title="Chat UUID"><span class="chat-uuid">' + escape(chat_uuid) + '</span><button class="chat-uuid-copy" onclick="copyChatUuid(this)" title="Copy UUID"><svg xmlns=\"http://www.w3.org/2000/svg\" width=\"12\" height=\"12\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"9\" y=\"9\" width=\"13\" height=\"13\" rx=\"2\" ry=\"2\"/><path d=\"M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1\"/></svg></button></span>') if chat_uuid else ''}
                {header_actions_html}
            </div>
            <div class="terminal-controls">
                <span class="terminal-btn btn-close"></span>
                <span class="terminal-btn btn-minimize"></span>
                <span class="terminal-btn btn-maximize"></span>
            </div>
        </div>

        <div class="stats-bar">
            <div>
                Total: {total_lines} lines |
                User: {real_user_msgs} |
                Assistant: {assistant_msgs} |
                Tool Results: {tool_result_msgs} |
                Summaries: {summaries} |
                Rewinds: {len(rewind_dest)} |
                BTW: {btw_count}
            </div>
            <div>
                Created: {chat_date} {chat_time}
            </div>
        </div>

        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="Filter conversation..." autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
            <label class="filter-toggle" title="Show only user and assistant messages (hide tools, thinking, compacts, snapshots...)">
                <input type="checkbox" id="messagesOnly">
                <span>Messages only</span>
            </label>
            <span class="toolbar-divider"></span>
            <div class="edit-ctrl-group">
                <button class="edit-ctrl-btn" id="editToggleCollapse" title="Expand / collapse all Edit and Write blocks">
                    <span class="edit-ctrl-icon" id="editToggleIcon">&#9654;</span>
                    <span>Edits/Writes</span>
                </button>
                <button class="edit-ctrl-btn edit-ctrl-btn-theme" id="editToggleTheme" title="Switch the Edit/Write diff theme between dark and light">
                    <span id="editToggleThemeLabel">Switch to light</span>
                </button>
            </div>
            <div class="msg-nav">
                <button class="nav-mode-btn active" id="navAll" title="All messages">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><defs><linearGradient id="navGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#0066CC"/><stop offset="100%" stop-color="#10893E"/></linearGradient></defs><path d="M21 6h-2v9H6v2c0 .55.45 1 1 1h11l4 4V7c0-.55-.45-1-1-1zm-4 6V3c0-.55-.45-1-1-1H3c-.55 0-1 .45-1 1v14l4-4h10c.55 0 1-.45 1-1z"/></svg>
                </button>
                <button class="nav-mode-btn" id="navUser" title="User messages">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.2 4.8-4.8S14.7 2.4 12 2.4 7.2 4.6 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>
                </button>
                <button class="nav-mode-btn" id="navAssistant" title="Assistant messages">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4c1.66 0 3-1.34 3-3s-1.34-3-3-3zM7.5 11.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5S9.83 13 9 13s-1.5-.67-1.5-1.5zM16 17H8v-2h8v2zm-1-4c-.83 0-1.5-.67-1.5-1.5S14.17 10 15 10s1.5.67 1.5 1.5S15.83 13 15 13z"/></svg>
                </button>
                <button class="nav-arrow-btn" id="prevMsg" title="Previous (P)">&#9650;</button>
                <button class="nav-arrow-btn" id="nextMsg" title="Next (N)">&#9660;</button>
                <span class="nav-counter" id="navCounter">0/0</span>
            </div>
        </div>

        <div class="terminal-content" id="terminalContent">
{messages_content}
        </div>

        <div class="footer">
            <a href="https://github.com/oskar-gm/code-chat-viewer" target="_blank" style="color: #666; text-decoration: none;">Code Chat Viewer</a> |
            Processed {len(messages_html)} elements from {total_lines} total lines |
            <a href="https://github.com/oskar-gm/code-chat-viewer/issues" target="_blank" rel="noopener" style="color: #666; text-decoration: none;">Feedback</a>
        </div>
    </div>

    <script>
        // ====== MESSAGE NAVIGATION ======
        let navMessages = [];
        let currentNavIndex = -1;
        let navMode = 'all';
        let observerActive = true;
        let navObserver = null;

        // ====== STATE PERSISTENCE (per-open, sessionStorage) ======
        // Persists the controls a reader expects to survive a refresh (F5): scroll
        // position, theme of the Edit/Write diffs, the user/bot/all selector, the
        // search box + "Messages only", and which Edit/Write blocks are open. Uses
        // sessionStorage on purpose — state survives a reload but is wiped when the
        // tab closes, so reopening the chat starts clean. Thinking and other
        // non-button <details> are never persisted.
        const CHAT_STATE_KEY = 'ccv-chat-state-' + {chat_state_key};
        // Memory survives a refresh (F5 / back-forward) but a fresh open starts
        // clean. sessionStorage alone isn't enough — a file:// reopen can reuse it
        // — so the navigation type is the reliable signal: wipe this chat's saved
        // state unless we arrived here by reloading.
        (function() {{
            var t = '';
            try {{ var e = performance.getEntriesByType('navigation'); t = e && e[0] ? e[0].type : ''; }} catch (err) {{}}
            if (t !== 'reload' && t !== 'back_forward') {{
                try {{ sessionStorage.removeItem(CHAT_STATE_KEY); }} catch (err) {{}}
            }}
        }})();
        function loadChatState() {{
            try {{ return JSON.parse(sessionStorage.getItem(CHAT_STATE_KEY)) || {{}}; }}
            catch (e) {{ return {{}}; }}
        }}
        function saveChatState(patch) {{
            try {{
                var s = loadChatState();
                for (var k in patch) {{ s[k] = patch[k]; }}
                sessionStorage.setItem(CHAT_STATE_KEY, JSON.stringify(s));
            }} catch (e) {{}}
        }}
        function saveEditBlocksState() {{
            var blocks = document.querySelectorAll('details.tool-use-edit, details.tool-use-write');
            var open = [];
            blocks.forEach(function(d, i) {{ if (d.open) open.push(i); }});
            saveChatState({{ editBlocksOpen: open }});
        }}
        function restoreChatState() {{
            var s = loadChatState();
            if (s.editTheme === 'light') {{
                document.body.classList.add('edit-diff-light');
                var tb = document.getElementById('editToggleTheme');
                var tl = document.getElementById('editToggleThemeLabel');
                if (tb) tb.classList.add('is-light');
                if (tl) tl.textContent = 'Switch to dark';
            }}
            if (Array.isArray(s.editBlocksOpen)) {{
                var blocks = document.querySelectorAll('details.tool-use-edit, details.tool-use-write');
                s.editBlocksOpen.forEach(function(i) {{ if (blocks[i]) blocks[i].open = true; }});
            }}
            if (s.messagesOnly) {{ var mo = document.getElementById('messagesOnly'); if (mo) mo.checked = true; }}
            if (s.search) {{ var si = document.getElementById('searchInput'); if (si) si.value = s.search; }}
            if (s.navMode && s.navMode !== 'all') {{ setNavMode(s.navMode); }}
            if (s.search || s.messagesOnly) {{ applyConversationFilter(); }}
        }}

        function getNavSelector() {{
            const always = ', .message.nav-always';
            if (navMode === 'user') return '.message.user-msg:not(.nav-skip)' + always;
            if (navMode === 'assistant') return '.message.assistant-msg:not(.nav-skip)' + always;
            return '.message.user-msg:not(.nav-skip), .message.assistant-msg:not(.nav-skip)' + always;
        }}

        function initNavigation() {{
            navMessages = Array.from(document.querySelectorAll(getNavSelector()));
            currentNavIndex = -1;
            updateNavCounter();
            setupScrollObserver();
        }}

        function updateNavCounter() {{
            const counter = document.getElementById('navCounter');
            if (navMessages.length === 0) {{
                counter.textContent = '0/0';
            }} else {{
                counter.textContent = `${{currentNavIndex + 1}}/${{navMessages.length}}`;
            }}
        }}

        function scrollToNavMessage(index) {{
            if (navMessages.length === 0) return;
            observerActive = false;
            navMessages.forEach(msg => msg.classList.remove('nav-highlight'));
            currentNavIndex = index;
            const targetMsg = navMessages[currentNavIndex];
            const container = document.getElementById('terminalContent');
            const block = targetMsg.offsetHeight >= container.clientHeight ? 'start' : 'center';
            targetMsg.scrollIntoView({{ behavior: 'auto', block }});
            targetMsg.classList.add('nav-highlight');
            updateNavCounter();
            setTimeout(() => {{ observerActive = true; }}, 100);
        }}

        // The "current" position is recomputed from the actual scroll position
        // every time, so prev/next always step from what the user is looking at —
        // reliable even after a native Ctrl+F jump or manual scrolling, when
        // currentNavIndex (kept loosely by the observer, and -1 until a message
        // crosses its 0.5 threshold) would otherwise send the jump to an extreme.
        function currentNavIndexFromScroll() {{
            if (navMessages.length === 0) return -1;
            const container = document.getElementById('terminalContent');
            const cRect = container.getBoundingClientRect();
            const cMid = cRect.top + cRect.height / 2;
            let best = 0, bestDist = Infinity;
            for (let i = 0; i < navMessages.length; i++) {{
                const r = navMessages[i].getBoundingClientRect();
                const dist = Math.abs((r.top + r.height / 2) - cMid);
                if (dist < bestDist) {{ bestDist = dist; best = i; }}
            }}
            return best;
        }}

        function goToPrev() {{
            if (navMessages.length === 0) return;
            const base = currentNavIndexFromScroll();
            scrollToNavMessage(base <= 0 ? navMessages.length - 1 : base - 1);
        }}

        function goToNext() {{
            if (navMessages.length === 0) return;
            const base = currentNavIndexFromScroll();
            scrollToNavMessage(base >= navMessages.length - 1 ? 0 : base + 1);
        }}

        function setNavMode(mode) {{
            navMode = mode;
            saveChatState({{ navMode: mode }});
            document.querySelectorAll('.nav-mode-btn').forEach(btn => btn.classList.remove('active'));
            const id = 'nav' + mode.charAt(0).toUpperCase() + mode.slice(1);
            document.getElementById(id).classList.add('active');
            if (navObserver) navObserver.disconnect();
            initNavigation();
        }}

        // Navigation buttons
        document.getElementById('prevMsg').addEventListener('click', goToPrev);
        document.getElementById('nextMsg').addEventListener('click', goToNext);
        document.getElementById('navAll').addEventListener('click', () => setNavMode('all'));
        document.getElementById('navUser').addEventListener('click', () => setNavMode('user'));
        document.getElementById('navAssistant').addEventListener('click', () => setNavMode('assistant'));

        // Keyboard shortcuts (N = next, P = previous)
        document.addEventListener('keydown', function(e) {{
            if (e.target.tagName === 'INPUT') return;
            if (e.key === 'n' || e.key === 'N') goToNext();
            if (e.key === 'p' || e.key === 'P') goToPrev();
        }});

        // Intersection Observer for scroll tracking
        function setupScrollObserver() {{
            const container = document.getElementById('terminalContent');
            if (navObserver) navObserver.disconnect();
            navObserver = new IntersectionObserver((entries) => {{
                if (!observerActive) return;
                entries.forEach(entry => {{
                    if (entry.isIntersecting && entry.intersectionRatio > 0.5) {{
                        const visibleIndex = navMessages.indexOf(entry.target);
                        if (visibleIndex !== -1 && visibleIndex !== currentNavIndex) {{
                            currentNavIndex = visibleIndex;
                            updateNavCounter();
                        }}
                    }}
                }});
            }}, {{
                root: container,
                threshold: 0.5
            }});
            navMessages.forEach(msg => navObserver.observe(msg));
        }}

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            initNavigation();
            restoreChatState();
        }});

        // ====== SEARCH + TYPE FILTER ======
        // Combined filter: free-text match AND, optionally, "Messages only"
        // (keep just user/assistant messages carrying real text; hide tools,
        // thinking, compacts, commands, snapshots, summaries, rewinds, etc.).
        function isConversationMsg(el) {{
            return (el.classList.contains('user-msg') || el.classList.contains('assistant-msg'))
                   && !el.classList.contains('nav-skip');
        }}
        function applyConversationFilter() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const msgsOnly = document.getElementById('messagesOnly').checked;
            const messages = document.querySelectorAll('.message, .summary-msg, .tool-result-msg, .rewind');
            let visibleCount = 0;
            messages.forEach(message => {{
                let show = message.textContent.toLowerCase().includes(searchTerm);
                if (show && msgsOnly && !isConversationMsg(message)) show = false;
                message.style.display = show ? '' : 'none';
                if (show) visibleCount++;
            }});
            console.log(`Showing ${{visibleCount}} of ${{messages.length}} messages`);
            saveChatState({{ search: document.getElementById('searchInput').value, messagesOnly: msgsOnly }});
        }}
        document.getElementById('searchInput').addEventListener('input', applyConversationFilter);
        document.getElementById('messagesOnly').addEventListener('change', applyConversationFilter);

        // Toggle for collapsible tool results — the `▶` marker is already in
        // the server-rendered HTML; here we only attach the click handler.
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.tool-result-msg').forEach(toolResult => {{
                const header = toolResult.querySelector(':scope > .msg-header');
                const content = toolResult.querySelector(':scope > .msg-content');
                const toggle = header && header.querySelector(':scope > .tool-result-toggle');
                if (!header || !content || !toggle) return;

                header.addEventListener('click', function() {{
                    const open = content.classList.toggle('expanded');
                    toggle.classList.toggle('expanded', open);
                }});
            }});
        }});

        // ====== Chat UUID: copy to clipboard ======
        function copyChatUuid(btn) {{
            const uuid = btn.parentNode.querySelector('.chat-uuid').textContent;
            navigator.clipboard.writeText(uuid).then(function() {{
                const orig = btn.innerHTML;
                btn.innerHTML = '✓';
                btn.classList.add('copied');
                setTimeout(function() {{
                    btn.innerHTML = orig;
                    btn.classList.remove('copied');
                }}, 1200);
            }});
        }}

        // ====== Edit blocks: expand / collapse all ======
        (function() {{
            const btn = document.getElementById('editToggleCollapse');
            if (!btn) return;
            const icon = document.getElementById('editToggleIcon');
            const getBlocks = () => document.querySelectorAll('details.tool-use-edit, details.tool-use-write');
            const refresh = () => {{
                const blocks = getBlocks();
                const anyOpen = Array.from(blocks).some(d => d.open);
                icon.innerHTML = anyOpen ? '&#9660;' : '&#9654;';
            }};
            btn.addEventListener('click', function() {{
                const blocks = getBlocks();
                if (!blocks.length) return;
                const anyOpen = Array.from(blocks).some(d => d.open);
                blocks.forEach(d => {{ d.open = !anyOpen; }});
                refresh();
            }});
            document.addEventListener('toggle', function(e) {{
                if (e.target && e.target.classList && (e.target.classList.contains('tool-use-edit') || e.target.classList.contains('tool-use-write'))) {{
                    refresh();
                    saveEditBlocksState();
                }}
            }}, true);
            refresh();
        }})();

        // ====== Edit diff: theme toggle (dark default / light) ======
        (function() {{
            const btn = document.getElementById('editToggleTheme');
            if (!btn) return;
            const label = document.getElementById('editToggleThemeLabel');
            btn.addEventListener('click', function() {{
                const isLight = document.body.classList.toggle('edit-diff-light');
                btn.classList.toggle('is-light', isLight);
                label.textContent = isLight ? 'Switch to dark' : 'Switch to light';
                saveChatState({{ editTheme: isLight ? 'light' : 'dark' }});
            }});
        }})();

        // Restore saved scroll position after layout settles (default: top);
        // persist scroll as the reader moves (throttled).
        window.addEventListener('load', function() {{
            const content = document.getElementById('terminalContent');
            var st = loadChatState();
            content.scrollTop = (typeof st.scroll === 'number') ? st.scroll : 0;
            var saveTimer = null;
            content.addEventListener('scroll', function() {{
                if (saveTimer) clearTimeout(saveTimer);
                saveTimer = setTimeout(function() {{ saveChatState({{ scroll: content.scrollTop }}); }}, 200);
            }});
            // State restored — drop the loading overlay (one frame later so the
            // restored scroll position is already painted underneath).
            requestAnimationFrame(function() {{
                var ld = document.getElementById('chatLoading');
                if (ld) {{ ld.classList.add('hidden'); setTimeout(function() {{ ld.remove(); }}, 300); }}
            }});
        }});

        // Show a brief, non-blocking toast — visible fallback so a navigation
        // button never feels dead when its target can't be located.
        function showNavToast(message) {{
            var t = document.createElement('div');
            t.className = 'nav-toast';
            t.textContent = message;
            document.body.appendChild(t);
            requestAnimationFrame(function() {{ t.classList.add('show'); }});
            setTimeout(function() {{
                t.classList.remove('show');
                setTimeout(function() {{ t.remove(); }}, 300);
            }}, 2200);
        }}
        // Scroll to a message by uuid and highlight it (used by the rewind button).
        function gotoMessage(uuid) {{
            var target = document.querySelector('[data-msg-uuid="' + uuid + '"]');
            if (!target) {{ showNavToast("Couldn't locate that point in the chat"); return; }}
            // If an active filter (search / "Messages only") hides the target,
            // scrollIntoView would do nothing — clear the filter first so the
            // destination and its surrounding context become visible.
            if (target.offsetParent === null) {{
                var si = document.getElementById('searchInput');
                var mo = document.getElementById('messagesOnly');
                if (si) si.value = '';
                if (mo) mo.checked = false;
                if (typeof applyConversationFilter === 'function') applyConversationFilter();
                showNavToast('Filter cleared to show the destination');
            }}
            document.querySelectorAll('.nav-highlight').forEach(function(m) {{ m.classList.remove('nav-highlight'); }});
            var container = document.getElementById('terminalContent');
            var block = (container && target.offsetHeight >= container.clientHeight) ? 'start' : 'center';
            target.scrollIntoView({{ behavior: 'smooth', block: block }});
            target.classList.add('nav-highlight');
        }}
        // Open an embedded image (base64) in a modal/lightbox. The image is
        // decoded to a Blob URL on click, shown in an overlay, and the URL is
        // revoked on close to free memory. Focus moves into the dialog and
        // returns to the trigger on close (accessible modal).
        var lastFocusedBeforeModal = null;
        function openImage(el) {{
            try {{
                var b64 = el.getAttribute('data-img');
                var media = el.getAttribute('data-media') || 'image/png';
                var bin = atob(b64);
                var bytes = new Uint8Array(bin.length);
                for (var i = 0; i < bin.length; i++) {{ bytes[i] = bin.charCodeAt(i); }}
                var url = URL.createObjectURL(new Blob([bytes], {{ type: media }}));
                var img = document.getElementById('imgModalImg');
                if (img.dataset.url) URL.revokeObjectURL(img.dataset.url);
                img.src = url;
                img.dataset.url = url;
                lastFocusedBeforeModal = el;
                document.getElementById('imgModal').classList.add('open');
                var closeBtn = document.querySelector('.img-modal-close');
                if (closeBtn) closeBtn.focus();
            }} catch (e) {{
                alert('Could not open image: ' + e.message);
            }}
        }}
        function closeImageModal() {{
            var modal = document.getElementById('imgModal');
            var img = document.getElementById('imgModalImg');
            modal.classList.remove('open');
            if (img.dataset.url) {{ URL.revokeObjectURL(img.dataset.url); img.removeAttribute('data-url'); }}
            img.removeAttribute('src');
            if (lastFocusedBeforeModal && lastFocusedBeforeModal.focus) {{ lastFocusedBeforeModal.focus(); }}
            lastFocusedBeforeModal = null;
        }}
        document.addEventListener('keydown', function(e) {{
            var modal = document.getElementById('imgModal');
            if (!modal || !modal.classList.contains('open')) return;
            if (e.key === 'Escape') {{ closeImageModal(); }}
            // Only the close button is focusable: keep Tab inside the dialog.
            else if (e.key === 'Tab') {{ e.preventDefault(); var b = document.querySelector('.img-modal-close'); if (b) b.focus(); }}
        }});
        // Copy button on every message (added client-side to avoid touching each renderer)
        document.addEventListener('DOMContentLoaded', function() {{
            var COPY = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5.5" y="5.5" width="8" height="8" rx="1.3"/><path d="M3 10.5V3.2A1.2 1.2 0 0 1 4.2 2H11"/></svg>';
            var CHECK = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8.5l3.3 3.3L13 4.5"/></svg>';
            document.querySelectorAll('.message').forEach(function(msg) {{
                var content = msg.querySelector('.msg-content');
                if (!content) return;
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'copy-btn';
                btn.title = 'Copy message';
                btn.innerHTML = COPY;
                btn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    navigator.clipboard.writeText(content.innerText).then(function() {{
                        btn.innerHTML = CHECK;
                        btn.classList.add('copied');
                        setTimeout(function() {{ btn.innerHTML = COPY; btn.classList.remove('copied'); }}, 1200);
                    }});
                }});
                msg.appendChild(btn);
            }});
        }});
    </script>
    <div id="imgModal" class="img-modal" role="dialog" aria-modal="true" aria-label="Image viewer" onclick="if(event.target===this)closeImageModal()">
        <div class="img-modal-figure">
            <button type="button" class="img-modal-close" onclick="closeImageModal()" aria-label="Close image viewer">&times;</button>
            <img id="imgModalImg" class="img-modal-img" alt="Expanded chat image">
        </div>
    </div>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"HTML generated successfully: {output_file}")
    print(f"Statistics:")
    print(f"   - Total lines processed: {total_lines}")
    print(f"   - Real user messages: {real_user_msgs}")
    print(f"   - Assistant messages: {assistant_msgs}")
    print(f"   - Tool results: {tool_result_msgs}")
    print(f"   - Summaries: {summaries}")
    print(f"   - Rewinds: {len(rewind_dest)}")
    print(f"   - BTW (history): {btw_count}")
    print(f"   - HTML elements generated: {len(messages_html)}")

def get_chat_timestamp(messages: List[Dict]) -> str:
    """Extract the timestamp from the first message for file naming."""
    for msg in messages:
        if 'snapshot' in msg and 'timestamp' in msg['snapshot']:
            return msg['snapshot']['timestamp']
        if 'timestamp' in msg:
            return msg['timestamp']
    return None

def generate_output_filename(input_file: str, messages: List[Dict]) -> str:
    """Generate output filename with format: Chat YYYY-MM-DD HH-MM hash.html"""
    input_name = Path(input_file).stem
    hash_short = input_name.split('-')[0] if '-' in input_name else input_name[:8]

    timestamp = get_chat_timestamp(messages)

    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone()
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H-%M')
            return f"Chat {date_str} {time_str} {hash_short}.html"
        except (ValueError, TypeError):
            pass

    return f"Chat {hash_short}.html"

def _wait_if_interactive():
    """Pause before closing if running in an interactive console (e.g. double-click on Windows).

    When called from Claude Code or another process, stdout is piped
    so isatty() returns False and this does nothing.
    """
    if sys.stdout.isatty() and os.name == 'nt':
        input("\nPress Enter to close...")


def main():
    """Main entry point."""

    if len(sys.argv) < 2:
        print("Usage: python visualizer.py <json_file> [output.html]")
        _wait_if_interactive()
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"Error: File {input_file} not found")
        _wait_if_interactive()
        sys.exit(1)

    print(f"Reading {input_file}...")
    messages = parse_chat_json(input_file)
    print(f"{len(messages)} lines parsed")

    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = generate_output_filename(input_file, messages)
        print(f"Generated filename: {output_file}")

    print(f"Generating HTML in terminal style...")
    chat_uuid = Path(input_file).stem

    # Load history.jsonl from `~/.claude/` (input_file is .../projects/<proj>/<uuid>.jsonl)
    history_entries = []
    try:
        history_path = Path(input_file).resolve().parent.parent.parent / 'history.jsonl'
        if history_path.exists():
            with open(history_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    disp = e.get('display', '') or ''
                    if not disp.startswith('/btw'):
                        continue
                    rest = disp[len('/btw'):].lstrip()
                    if not rest:
                        continue
                    history_entries.append({
                        'query': rest,
                        'timestamp': e.get('timestamp', 0),
                        'sessionId': e.get('sessionId', ''),
                    })
    except OSError:
        history_entries = []

    generate_html(messages, output_file, chat_uuid=chat_uuid, history_entries=history_entries)

    print(f"\nConversion completed!")
    print(f"Open file: {output_file}")
    _wait_if_interactive()

if __name__ == "__main__":
    main()
