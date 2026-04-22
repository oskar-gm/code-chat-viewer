#!/usr/bin/env python3
"""
Code Chat Viewer v2.2.0

Converts Claude Code chat JSON files (JSONL format) into formatted HTML
visualizations with terminal-style aesthetics, syntax highlighting, and
interactive features.

Copyright (c) 2025-2026 Óscar González Martín
Licensed under the MIT License - see LICENSE for details

Author: Óscar González Martín
Version: 2.2.0
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

def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to HH:MM AM/PM in local timezone."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).astimezone()
        return dt.strftime('%I:%M %p').lstrip('0')
    except (ValueError, TypeError):
        return ""


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

    return text

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

def parse_ask_result(text: str) -> list:
    """Parse AskUserQuestion tool result text into Q&A pairs.
    Returns list of dicts [{question, answer, notes, markdown}].
    Handles markdown with and without backtick wrappers."""
    if not text.startswith('User has answered your questions:'):
        return []

    # Remove prefix and suffix
    body = text.replace('User has answered your questions:', '').strip()
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


# ====== SPECIAL MESSAGE RENDERING FUNCTIONS ======

def render_command_message(cmd_display: str, time_str: str, metadata_str: str, uuid: str, cwd: str) -> str:
    """Render a /command message with darker user-blue styling."""
    separator = '─' * 80
    return f'''<div class="message user-msg command-msg">
<div class="msg-header">
<span class="bullet" style="color:#0066CC; font-size:12px;">&#9656;</span> <span class="label" style="color:#1E1E1E;">[COMMAND]</span> <span class="metadata">{escape(metadata_str)}</span>
</div>
<div class="msg-content" style="color:#0066CC; background:#EBF2FF; border-left:3px solid #0066CC;">{escape(cmd_display)}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator">{separator}</div>
</div>
'''

def render_stdout_message(clean_text: str, time_str: str, metadata_str: str, uuid: str, cwd: str) -> str:
    """Render a local-command-stdout message (non-compact) with grey styling."""
    separator = '─' * 80
    return f'''<div class="message user-msg stdout-msg nav-skip">
<div class="msg-header">
<span class="bullet" style="color:#6B7280;">&#9654;</span> <span class="label" style="color:#6B7280;">[OUTPUT]</span> <span class="metadata">{escape(metadata_str)}</span>
</div>
<div class="msg-content" style="color:#374151; background:#F9FAFB; border-left:3px solid #9CA3AF;">{escape_html_preserve_structure(clean_text)}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator">{separator}</div>
</div>
'''

def render_task_notification(text: str, uuid: str) -> str:
    """Render a task-notification as a styled system message."""
    summary = extract_tag_content(text, 'summary')
    status = extract_tag_content(text, 'status')
    clean = re.sub(r'<[^>]+>', '', text).strip()
    status_upper = status.upper() if status else ''
    display_text = summary or clean or 'Task notification'

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
    else:
        icon = '&#8226;'
        accent = '#6B7280'
        bg = '#F9FAFB'
        border_color = '#D1D5DB'

    separator = '─' * 80
    return f'''<div class="message user-msg nav-skip"><div class="msg-content" style="color:{accent}; background:{bg}; border-left:3px solid {border_color}; padding:6px 12px; margin-left:15px; font-size:12px; border-radius:4px;"><span style="font-weight:700;">{icon}</span> <span style="font-weight:600;">[{escape(status_upper) if status_upper else 'TASK'}]</span> {escape(display_text)}</div><div class="separator">{separator}</div></div>
'''

def render_ask_result_block(qa_pairs: list, tool_use_id: str, uuid: str) -> str:
    """Render AskUserQuestion result as a visual amber block (open, not collapsible)."""
    items_html = []
    for i, qa in enumerate(qa_pairs):
        q_html = f'<div style="font-weight:700; color:#92400E; margin-bottom:2px;">Q: {escape(qa["question"])}</div>' if qa['question'] else ''
        a_html = f'<div style="padding-left:16px; color:#B45309;">A: {escape(qa["answer"])}</div>'
        notes_html = f'<div style="padding-left:16px; color:#9CA3AF; font-style:italic; margin-top:2px;">Note: {escape(qa["notes"])}</div>' if qa.get('notes') else ''
        md_html = ''
        if qa.get('markdown'):
            md_html = f'<pre style="background:#FFF7ED; color:#78350F; padding:8px; margin:4px 0 0 16px; border-radius:4px; font-size:11px; line-height:1.3; overflow-x:auto; white-space:pre; border:1px solid #FDE68A;">{escape(qa["markdown"])}</pre>'
        sep_html = '<hr style="border:none; border-top:1px solid #FDE68A; margin:6px 0;">' if i < len(qa_pairs) - 1 else ''
        items_html.append(f'{q_html}{a_html}{notes_html}{md_html}{sep_html}')

    content = ''.join(items_html)
    separator = '─' * 80

    return f'''<div class="message user-msg ask-result-msg nav-always">
<div class="ask-inner">
<div class="msg-header">
<span class="bullet" style="color:#D97706; font-size:14px;">&#10067;</span> <span class="label" style="color:#D97706;">[USER RESPONSE]</span> <span class="metadata">Tool ID: {escape(tool_use_id[-12:]) if tool_use_id else 'N/A'}</span>
</div>
<div style="padding:4px 12px; color:#1E1E1E; white-space:normal; margin-left:15px;">{content}</div>
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator">{separator}</div>
</div>
'''


def render_user_rejection_block(rejection: dict, tool_use_id: str, uuid: str) -> str:
    """Render a tool_use rejection with optional user feedback.

    Shows a coral/red indicator for the rejection, and if the user provided
    feedback, displays it prominently as a user message.
    """
    separator = '─' * 80
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
<div class="separator">{separator}</div>
</div>
'''
    else:
        return f'''<div class="message user-msg nav-skip"><div class="msg-content" style="color:#DC2626; background:#FFF1F2; border-left:3px solid #F87171; padding:6px 12px; margin-left:15px; font-size:12px; border-radius:4px;"><span style="font-weight:700;">&#10060;</span> <span style="font-weight:600;">[REJECTED]</span> Tool use rejected by user</div><div class="separator">{separator}</div></div>
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
    separator = '─' * 80

    # Unique ID for toggle
    block_id = f'compact-{uuid[-8:]}' if uuid else f'compact-{id(compact_data)}'

    return f'''<div class="message compact-msg nav-always">
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
<div class="separator">{separator}</div>
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
    questions = tool_input.get('questions', [])
    if not questions:
        return None

    parts = []
    for q in questions:
        question_text = q.get('question', '')
        header_text = q.get('header', '')
        multi = q.get('multiSelect', False)
        options = q.get('options', [])

        q_html = f'<div style="font-weight:700; color:#E8E8E8; margin-bottom:4px;">{escape(question_text)}</div>'
        if header_text:
            q_html += f'<div style="color:#999; font-size:11px; margin-bottom:4px;">[{escape(header_text)}] {"Multi-select" if multi else "Single-select"}</div>'

        opts_html = []
        for opt in options:
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


def render_edit_tool_use(tool_id: str, tool_name: str, tool_input: dict) -> str:
    """Render Edit / MultiEdit tool_use with a two-column diff view (old vs new)."""
    file_path = tool_input.get('file_path', '')

    if tool_name == 'MultiEdit':
        edits = tool_input.get('edits', []) or []
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
        tool_input = item.get('input', {})

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

        input_lines = []
        for key, value in tool_input.items():
            input_lines.append(f'  {escape(key)}: {escape(str(value))}')

        input_str = '<br>'.join(input_lines) if input_lines else '  (no parameters)'

        return f'''<details class="tool-use"><summary>Tool: {escape(tool_name)}</summary><div class="tool-use-content">
   ID: {escape(tool_id[:16])}...
   Parameters:
{input_str}
</div></details>'''

    if item_type == 'tool_result':
        return ''

    return f'<div class="unknown-type">[Type: {item_type}]</div>'

def format_message_html(msg: Dict, index: int) -> str:
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
        message_id = msg.get('messageId', '')[:12]
        return f'<div class="snapshot">[Snapshot saved: {message_id}...]</div>\n'

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

                # Check if this is an AskUserQuestion result
                if result_text.startswith('User has answered your questions:'):
                    qa_pairs = parse_ask_result(result_text)
                    if qa_pairs:
                        tool_results_html.append(render_ask_result_block(
                            qa_pairs, item.get('tool_use_id', ''), uuid))
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
<span class="bullet">&#128228;</span> <span class="label">[TOOL RESULT]</span> <span class="metadata">Tool ID: {escape(tool_use_id[-12:])}</span>
</div>
<div class="msg-content">{result_content}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
</div>
<div class="separator">{'─' * 80}</div>
</div>''')

        # Render inline user comments as a visible user feedback block
        if user_comments:
            comment_text = escape_html_preserve_structure('<br>'.join(user_comments))
            separator = '─' * 80
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
<div class="separator">{separator}</div>
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
    metadata_parts = []
    if time_str:
        metadata_parts.append(time_str)
    if model:
        metadata_parts.append(model)
    if git_branch:
        metadata_parts.append(f'[{escape(git_branch)}]')

    metadata_str = '  '.join(metadata_parts) if metadata_parts else ''

    # Process content (excluding tool_result handled above)
    content_parts = []

    if isinstance(content, str):
        content_parts.append(escape_html_preserve_structure(content))
    elif isinstance(content, list):
        for item in content:
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

    separator = '─' * 80

    message_html = f'''<div class="message {msg_class}">
<div class="msg-header">
<span class="bullet">•</span> <span class="label">[{label}]:</span> <span class="metadata">{escape(metadata_str)}</span>
</div>
<div class="msg-content">{content_html}</div>
<div class="msg-footer">
<span class="uuid-small">ID: {escape(uuid[-12:]) if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {escape(cwd)}</span>' if cwd else ''}
</div>
<div class="separator">{separator}</div>
</div>
'''

    return message_html

def generate_html(messages: List[Dict], output_file: str, dashboard_url: str = None, chat_title: str = "", chat_uuid: str = ""):
    """Generate the complete HTML document in terminal style."""

    # Count statistics (distinguishing tool_results)
    total_lines = len(messages)
    real_user_msgs = 0
    tool_result_msgs = 0
    assistant_msgs = 0
    summaries = 0
    snapshots = sum(1 for m in messages if m.get('type') == 'file-history-snapshot')

    for m in messages:
        if m.get('type') == 'summary':
            summaries += 1
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

    # Pre-process: group compact-related messages
    processed_messages = group_compact_messages(messages)

    # Generate HTML for all messages
    messages_html = []
    for i, msg in enumerate(processed_messages):
        # Compact groups are rendered directly
        if isinstance(msg, dict) and msg.get('_compact_group'):
            msg_html = render_compact_block(msg)
        else:
            msg_html = format_message_html(msg, i)
        if msg_html:
            messages_html.append(msg_html)

    messages_content = '\n'.join(messages_html)

    # Extract chat date and time (converted to local timezone)
    chat_timestamp = get_chat_timestamp(messages)
    if chat_timestamp:
        try:
            dt = datetime.fromisoformat(chat_timestamp.replace('Z', '+00:00')).astimezone()
            chat_date = dt.strftime('%d/%m/%Y')
            chat_time = dt.strftime('%H:%M')
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
        '<a href="mailto:oscar@nucleoia.es?subject=Code%20Chat%20Viewer%20-%20Feedback" class="header-btn feedback" title="Send feedback">Feedback</a>'
    )
    header_actions_html = '\n                '.join(header_actions_parts)

    # Complete HTML template in terminal style
    html_template = f'''<!DOCTYPE html>
<!--
=============================================================================
Code Chat Viewer v2.2.0 - Professional Chat Log HTML Exporter
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
    <meta name="keywords" content="Claude Code, chat viewer, conversation export, JSONL to HTML, AI chat visualization, Claude Code logs, export claude code chats, chat log viewer, code assistant history, VS Code chat export, developer tools, Claude AI, AI conversation viewer, terminal UI, chat dashboard, coding assistant logs">

    <meta name="generator" content="Code Chat Viewer v2.2.0 - https://github.com/oskar-gm/code-chat-viewer">
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

        body {{
            font-family: 'Cascadia Code', 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #FFFFFF;
            color: #1E1E1E;
            line-height: 1.6;
            font-size: 14px;
            padding: 0;
            margin: 0;
        }}

        .container {{
            width: 100%;
            background: #FFFFFF;
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
            padding: 10px 15px;
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            background: #FFFFFF;
        }}

        .message {{
            margin-bottom: 8px;
            font-size: 13px;
            line-height: 1.5;
        }}

        .msg-header {{
            display: flex;
            align-items: baseline;
            margin-bottom: 4px;
            gap: 8px;
        }}

        .bullet {{
            font-weight: bold;
            font-size: 16px;
            margin-right: 4px;
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
            font-size: 15px;
        }}

        .user-msg .label,
        .assistant-msg .label {{
            font-size: 15px;
            letter-spacing: 0.5px;
        }}

        .metadata {{
            color: #666;
            font-size: 12px;
            margin-left: auto;
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
            padding: 6px 12px;
            color: #0066CC;
            background: #F8FBFF;
            border-left: 3px solid #0066CC;
            border-radius: 4px;
            margin-left: 15px;
            font-size: 14px;
            line-height: 1.5;
        }}

        .assistant-msg .msg-content {{
            padding: 6px 12px;
            color: #1E1E1E;
            background: #FAFFF8;
            border-left: 3px solid #10893E;
            border-radius: 4px;
            margin-left: 15px;
            font-size: 14px;
            line-height: 1.5;
        }}

        .tool-result-msg {{
            margin-bottom: 8px;
            background: #F8F8F8;
            border-left: 3px solid #FF6B00;
            padding: 8px 10px;
            border-radius: 4px;
        }}

        .tool-result-header {{
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: #FF6B00;
        }}

        .tool-result-header:hover {{
            opacity: 0.8;
        }}

        .tool-result-toggle {{
            font-size: 12px;
            transition: transform 0.2s;
        }}

        .tool-result-toggle.collapsed {{
            transform: rotate(-90deg);
        }}

        .tool-result-content {{
            margin-top: 6px;
            display: none;
        }}

        .tool-result-content.expanded {{
            display: block;
        }}

        .tool-result-msg .msg-content {{
            padding-left: 10px;
            color: #333;
            font-size: 12px;
        }}

        .thinking {{
            background: #FFFFFF;
            border-left: 3px solid #B8C8B8;
            margin: 5px 0;
            font-style: italic;
            color: #666;
            border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
            font-size: 13px;
            line-height: 1.5;
        }}
        .thinking summary {{
            padding: 6px 10px;
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
            padding: 0 10px 8px;
            border-top: 1px solid #E0E8E0;
        }}

        .tool-use {{
            background: #48484A;
            border-left: 3px solid #6A6A6C;
            margin: 5px 0;
            color: #E8E8E8;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            font-size: 13px;
            line-height: 1.5;
        }}
        .tool-use summary {{
            padding: 6px 10px;
            cursor: pointer;
            user-select: none;
        }}
        .tool-use-content {{
            padding: 0 10px 8px;
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

        .edit-ctrl-btn-theme {{
            border-left-width: 0 !important;
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

        .edit-ctrl-btn.is-light {{
            background: #FFF5E1;
            border-color: #E0B060;
            color: #7A4E00;
        }}

        /* ====== Chat UUID in header ====== */
        .chat-uuid {{
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 11px;
            color: #9AAFC4;
            user-select: all;
            padding: 3px 8px;
            background: rgba(255,255,255,0.04);
            border: 1px solid #444;
            border-radius: 3px;
            letter-spacing: 0.3px;
            white-space: nowrap;
        }}

        @media (max-width: 900px) {{
            .chat-uuid {{
                display: none;
            }}
        }}

        .msg-footer {{
            padding-left: 15px;
            margin-top: 3px;
            font-size: 11px;
            color: #999;
            display: flex;
            gap: 20px;
        }}

        .separator {{
            color: #E0E0E0;
            margin-top: 4px;
            font-size: 12px;
            letter-spacing: -1px;
        }}

        .summary-msg {{
            background: #F8F8F8;
            border: 1px solid #E0E0E0;
            padding: 10px;
            margin: 10px 0;
        }}

        .summary-header {{
            color: #666;
            font-size: 12px;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }}

        .summary-content {{
            color: #1E1E1E;
            padding-left: 10px;
        }}

        .snapshot {{
            color: #999;
            font-size: 12px;
            padding: 5px 0;
            border-left: 2px solid #E0E0E0;
            padding-left: 10px;
            margin: 5px 0;
        }}

        .uuid-small, .cwd-small {{
            font-family: 'Consolas', monospace;
            font-size: 10px;
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
            margin-bottom: 8px;
        }}
        .compact-inner {{
            background: #F5F3FF;
            border-left: 3px solid #8B5CF6;
            padding: 8px 10px;
            border-radius: 4px;
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
            margin-bottom: 8px;
        }}
        .ask-inner {{
            background: #FFFBEB;
            border-left: 3px solid #FCD34D;
            padding: 8px 10px;
            border-radius: 4px;
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
    <div class="container">
        <div class="terminal-header">
            <div class="terminal-title">
                <img src="data:image/png;base64,{ICON_BASE64}" alt="" style="height:16px;width:16px;vertical-align:middle;margin-right:6px;" onerror="this.style.display='none'">
                <span>Code Chat Viewer</span>
                {'<span class="chat-name-sep">|</span><span class="chat-name">' + escape(chat_title) + '</span>' if chat_title else ''}
            </div>
            <div class="header-actions">
                {('<span class="chat-uuid" title="Chat UUID (click to select)">' + escape(chat_uuid) + '</span>') if chat_uuid else ''}
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
                Snapshots: {snapshots}
            </div>
            <div>
                Date: {chat_date} | Time: {chat_time}
            </div>
        </div>

        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="Filter conversation...">
            <div class="edit-ctrl-group">
                <button class="edit-ctrl-btn" id="editToggleCollapse" title="Expand / collapse all Edit blocks">
                    <span class="edit-ctrl-icon" id="editToggleIcon">&#9654;</span>
                    <span id="editToggleLabel">Edits</span>
                </button>
                <button class="edit-ctrl-btn edit-ctrl-btn-theme" id="editToggleTheme" title="Toggle Edit diff theme (dark / light)">
                    <span id="editToggleThemeLabel">Light</span>
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
            <a href="https://nucleoia.es" target="_blank" style="color: #666; text-decoration: none;">nucleoia.es</a> |
            Processed {len(messages_html)} elements from {total_lines} total lines |
            <a href="mailto:oscar@nucleoia.es?subject=Code%20Chat%20Viewer%20-%20Feedback" style="color: #666; text-decoration: none;">Feedback</a>
        </div>
    </div>

    <script>
        // ====== MESSAGE NAVIGATION ======
        let navMessages = [];
        let currentNavIndex = -1;
        let navMode = 'all';
        let observerActive = true;
        let navObserver = null;

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

        function goToPrev() {{
            if (navMessages.length === 0) return;
            if (currentNavIndex <= 0) {{
                currentNavIndex = navMessages.length - 1;
            }} else {{
                currentNavIndex--;
            }}
            scrollToNavMessage(currentNavIndex);
        }}

        function goToNext() {{
            if (navMessages.length === 0) return;
            if (currentNavIndex >= navMessages.length - 1) {{
                currentNavIndex = 0;
            }} else {{
                currentNavIndex++;
            }}
            scrollToNavMessage(currentNavIndex);
        }}

        function setNavMode(mode) {{
            navMode = mode;
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
        }});

        // ====== SEARCH ======
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const searchTerm = e.target.value.toLowerCase();
            const messages = document.querySelectorAll('.message, .summary-msg, .tool-result-msg');

            let visibleCount = 0;
            messages.forEach(message => {{
                const text = message.textContent.toLowerCase();
                if (text.includes(searchTerm)) {{
                    message.style.display = 'block';
                    visibleCount++;
                }} else {{
                    message.style.display = 'none';
                }}
            }});

            console.log(`Showing ${{visibleCount}} of ${{messages.length}} messages`);
        }});

        // Toggle for collapsible tool results
        document.addEventListener('DOMContentLoaded', function() {{
            const toolResults = document.querySelectorAll('.tool-result-msg');

            toolResults.forEach(toolResult => {{
                const header = toolResult.querySelector('.msg-header');
                const content = toolResult.querySelector('.msg-content');

                if (header && content) {{
                    // Create collapsible structure
                    const toggle = document.createElement('span');
                    toggle.className = 'tool-result-toggle collapsed';
                    toggle.innerHTML = '▼';

                    const newHeader = document.createElement('div');
                    newHeader.className = 'tool-result-header';
                    newHeader.appendChild(toggle);
                    newHeader.appendChild(header.cloneNode(true));

                    const newContent = document.createElement('div');
                    newContent.className = 'tool-result-content';
                    newContent.appendChild(content.cloneNode(true));

                    // Clear and rebuild
                    toolResult.innerHTML = '';
                    toolResult.appendChild(newHeader);
                    toolResult.appendChild(newContent);

                    // Footer if present
                    const footer = toolResult.querySelector('.msg-footer');
                    if (footer) {{
                        newContent.appendChild(footer);
                    }}

                    // Click event
                    newHeader.addEventListener('click', function() {{
                        toggle.classList.toggle('collapsed');
                        newContent.classList.toggle('expanded');
                    }});
                }}
            }});
        }});

        // ====== Edit blocks: expand / collapse all ======
        (function() {{
            const btn = document.getElementById('editToggleCollapse');
            if (!btn) return;
            const icon = document.getElementById('editToggleIcon');
            const getEdits = () => document.querySelectorAll('details.tool-use-edit');
            const refresh = () => {{
                const edits = getEdits();
                const anyOpen = Array.from(edits).some(d => d.open);
                icon.innerHTML = anyOpen ? '&#9660;' : '&#9654;';
            }};
            btn.addEventListener('click', function() {{
                const edits = getEdits();
                if (!edits.length) return;
                const anyOpen = Array.from(edits).some(d => d.open);
                edits.forEach(d => {{ d.open = !anyOpen; }});
                refresh();
            }});
            document.addEventListener('toggle', function(e) {{
                if (e.target && e.target.classList && e.target.classList.contains('tool-use-edit')) {{
                    refresh();
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
                label.textContent = isLight ? 'Dark' : 'Light';
            }});
        }})();

        // Scroll to top on load
        window.addEventListener('load', function() {{
            const content = document.getElementById('terminalContent');
            content.scrollTop = 0;
        }});
    </script>
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
    print(f"   - Snapshots: {snapshots}")
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
    generate_html(messages, output_file, chat_uuid=chat_uuid)

    print(f"\nConversion completed!")
    print(f"Open file: {output_file}")
    _wait_if_interactive()

if __name__ == "__main__":
    main()
