#!/usr/bin/env python3
"""
Code Chat Viewer v2.0

Converts Claude Code chat JSON files (JSONL format) into formatted HTML
visualizations with terminal-style aesthetics, syntax highlighting, and
interactive features.

Copyright (c) 2025 Óscar González Martín
Licensed under the MIT License - see LICENSE for details

Author: Óscar González Martín
Version: 2.0
Contact: oscar@nucleoia.es
Website: https://nucleoia.es
Repository: https://github.com/oskar-gm/code-chat-viewer
LinkedIn: https://linkedin.com/in/oscar-gonz

This script transforms raw Claude Code conversation logs (JSONL format) into
readable, styled HTML documents with:
- Terminal aesthetics with VS Code-inspired colors
- Collapsible tool results with interactive toggles
- Real-time search functionality
- Syntax highlighting for code blocks
- Responsive fullscreen layout
- User message navigation with position counter
- Security-safe HTML rendering
- Proper attribution in HTML output

For usage instructions, see README.md or visit the repository.

Changes from v1.0:
- Fullscreen layout: edge-to-edge rendering without borders or shadows
- User message navigation: prev/next buttons to jump between user messages
- Position counter with automatic scroll synchronization
- Highlight animation when navigating to a user message
- CSS specificity fix: user messages correctly display blue styling
- Blue-themed styling for unknown content types inside user messages
- Instant scroll navigation for responsiveness
- Fast IntersectionObserver reactivation (100ms)
- Timestamps converted to local timezone
- Stats bar displays chat date/time instead of generation time
- Smart output filename generation (Chat YYYY-MM-DD HH-MM hash.html)
- Security fix: HTML-escaped tool_use parameters to prevent DOM injection
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from html import escape

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
    except:
        return ""

def format_model_name(model: str) -> str:
    """Format model name to short display form."""
    if not model:
        return ""
    return model

def escape_html_preserve_structure(text: str) -> str:
    """Escape HTML while preserving text structure (newlines, spaces)."""
    if not text:
        return ""

    text = escape(text)
    text = text.replace('\n', '<br>')
    text = re.sub(r'  +', lambda m: '&nbsp;' * len(m.group()), text)

    return text

def is_tool_result_message(content) -> bool:
    """Determine if a message is a tool_result (not a real user message)."""
    if isinstance(content, list):
        return any(isinstance(item, dict) and item.get('type') == 'tool_result' for item in content)
    return False

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
        return f'<div class="thinking">☉ Thinking...<br><br>{escape_html_preserve_structure(thinking_text)}</div>'

    if item_type == 'tool_use':
        tool_name = item.get('name', 'unknown')
        tool_id = item.get('id', '')
        tool_input = item.get('input', {})

        input_lines = []
        for key, value in tool_input.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + '...'
            input_lines.append(f'  {escape(key)}: {escape(str(value))}')

        input_str = '<br>'.join(input_lines) if input_lines else '  (no parameters)'

        return f'''<div class="tool-use">
Tool: {escape(tool_name)}
   ID: {escape(tool_id[:16])}...
   Parameters:
{input_str}
</div>'''

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

    # ====== DETECT TOOL_RESULT (NOT A REAL USER MESSAGE) ======
    if role == 'user' and is_tool_result_message(content):
        tool_results_html = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'tool_result':
                result_content = format_tool_result_content(item)
                tool_use_id = item.get('tool_use_id', 'N/A')

                tool_results_html.append(f'''<div class="tool-result-msg">
<div class="msg-header">
<span class="bullet">📤</span> <span class="label">[TOOL RESULT]</span> <span class="metadata">Tool ID: {tool_use_id[-12:]}</span>
</div>
<div class="msg-content">
{result_content}
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {uuid[-12:] if uuid else 'N/A'}</span>
</div>
<div class="separator">{'─' * 80}</div>
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
    model_str = format_model_name(model)

    metadata_parts = []
    if time_str:
        metadata_parts.append(time_str)
    if model_str:
        metadata_parts.append(model_str)
    if git_branch:
        metadata_parts.append(f'[{git_branch}]')

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

    content_html = '<br><br>'.join(content_parts)

    if not content_html.strip():
        return ''

    separator = '─' * 80

    message_html = f'''<div class="message {msg_class}">
<div class="msg-header">
<span class="bullet">•</span> <span class="label">[{label}]:</span> <span class="metadata">{metadata_str}</span>
</div>
<div class="msg-content">
{content_html}
</div>
<div class="msg-footer">
<span class="uuid-small">ID: {uuid[-12:] if uuid else 'N/A'}</span>
{f'<span class="cwd-small">CWD: {cwd}</span>' if cwd else ''}
</div>
<div class="separator">{separator}</div>
</div>
'''

    return message_html

def generate_html(messages: List[Dict], output_file: str, dashboard_url: str = None):
    """Generate the complete HTML document in terminal style."""

    # Count statistics (distinguishing tool_results)
    total_lines = len(messages)
    real_user_msgs = 0
    tool_result_msgs = 0
    assistant_msgs = 0
    summaries = sum(1 for m in messages if m.get('type') == 'summary')
    snapshots = sum(1 for m in messages if m.get('type') == 'file-history-snapshot')

    for m in messages:
        if m.get('message', {}).get('role') == 'user':
            content = m.get('message', {}).get('content', [])
            if is_tool_result_message(content):
                tool_result_msgs += 1
            else:
                real_user_msgs += 1
        elif m.get('message', {}).get('role') == 'assistant':
            assistant_msgs += 1

    # Generate HTML for all messages
    messages_html = []
    for i, msg in enumerate(messages):
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
        except:
            chat_date = "N/A"
            chat_time = "N/A"
    else:
        chat_date = "N/A"
        chat_time = "N/A"

    # Build header action buttons
    header_actions_parts = []
    if dashboard_url:
        header_actions_parts.append(
            f'<a href="{dashboard_url}" class="header-btn" title="Back to Dashboard">&#9664; Dashboard</a>'
        )
    header_actions_parts.append(
        '<a href="mailto:oscar@nucleoia.es?subject=Code%20Chat%20Viewer%20-%20Feedback" class="header-btn feedback" title="Send feedback">Feedback</a>'
    )
    header_actions_html = '\n                '.join(header_actions_parts)

    # Complete HTML template in terminal style
    html_template = f'''<!DOCTYPE html>
<!--
=============================================================================
Code Chat Viewer v2.0 - Professional Chat Log HTML Exporter
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

    <meta name="generator" content="Code Chat Viewer v2.0 - https://github.com/oskar-gm/code-chat-viewer">
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
    <title>Code Chat Viewer - Conversation</title>
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
            padding: 12px 20px;
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
            padding: 10px 20px;
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
        }}

        .search-bar {{
            background: #FAFAFA;
            border-bottom: 1px solid #E0E0E0;
            padding: 12px 20px;
        }}

        .search-input {{
            width: 100%;
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
        .search-bar {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .search-input {{
            flex: 1;
        }}

        .user-nav {{
            display: flex;
            align-items: center;
            gap: 6px;
            background: #FFFFFF;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 4px 10px;
        }}

        .user-nav-label {{
            font-size: 14px;
            user-select: none;
        }}

        .user-nav-btn {{
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

        .user-nav-btn:hover {{
            background: #0066CC;
            border-color: #0066CC;
            color: white;
        }}

        .user-nav-btn:active {{
            transform: scale(0.95);
        }}

        .user-nav-counter {{
            font-size: 11px;
            color: #666;
            min-width: 35px;
            text-align: center;
            font-family: 'Consolas', monospace;
        }}

        /* Active user message highlight during navigation */
        .message.user-msg.user-highlight {{
            animation: userPulse 1.5s ease-out;
        }}

        @keyframes userPulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(0, 102, 204, 0.5); }}
            50% {{ box-shadow: 0 0 0 8px rgba(0, 102, 204, 0.2); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0, 102, 204, 0); }}
        }}

        .terminal-content {{
            padding: 20px;
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            background: #FFFFFF;
        }}

        .message {{
            margin-bottom: 20px;
            font-size: 13px;
            line-height: 1.8;
        }}

        .msg-header {{
            display: flex;
            align-items: baseline;
            margin-bottom: 10px;
            gap: 8px;
        }}

        .bullet {{
            font-weight: bold;
            font-size: 20px;
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
            font-size: 17px;
            letter-spacing: 0.5px;
        }}

        .metadata {{
            color: #666;
            font-size: 12px;
            margin-left: auto;
        }}

        .msg-content {{
            padding-left: 20px;
            color: #1E1E1E;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .tool-result-msg .msg-content {{
            padding-left: 10px;
        }}

        /* Higher specificity to prevent CSS cascade conflicts */
        .message.user-msg .msg-content {{
            padding: 12px 20px;
            padding-left: 20px;
            color: #0066CC;
            background: #F8FBFF;
            border-left: 3px solid #0066CC;
            border-radius: 4px;
            margin-left: 20px;
            font-size: 14px;
            line-height: 1.7;
        }}

        .assistant-msg .msg-content {{
            padding: 12px 20px;
            padding-left: 20px;
            color: #1E1E1E;
            background: #FAFFF8;
            border-left: 3px solid #10893E;
            border-radius: 4px;
            margin-left: 20px;
            font-size: 14px;
            line-height: 1.7;
        }}

        .tool-result-msg {{
            margin-bottom: 20px;
            background: #F8F8F8;
            border-left: 3px solid #FF6B00;
            padding: 15px;
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
            margin-top: 10px;
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
            padding: 12px;
            margin: 10px 0;
            font-style: italic;
            color: #666;
            border-radius: 4px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
            font-size: 13px;
            line-height: 1.6;
        }}

        .tool-use {{
            background: #48484A;
            border-left: 3px solid #6A6A6C;
            padding: 12px;
            margin: 10px 0;
            color: #E8E8E8;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            font-size: 13px;
            line-height: 1.6;
        }}

        .msg-footer {{
            padding-left: 20px;
            margin-top: 8px;
            font-size: 11px;
            color: #999;
            display: flex;
            gap: 20px;
        }}

        .separator {{
            color: #E0E0E0;
            margin-top: 10px;
            font-size: 12px;
            letter-spacing: -1px;
        }}

        .summary-msg {{
            background: #F8F8F8;
            border: 1px solid #E0E0E0;
            padding: 15px;
            margin: 20px 0;
        }}

        .summary-header {{
            color: #666;
            font-size: 12px;
            margin-bottom: 10px;
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
            padding: 15px 20px;
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
            </div>
            <div class="header-actions">
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
            <div class="user-nav">
                <span class="user-nav-label">👤</span>
                <button class="user-nav-btn" id="prevUser" title="Previous user message">▲</button>
                <button class="user-nav-btn" id="nextUser" title="Next user message">▼</button>
                <span class="user-nav-counter" id="userCounter">0/0</span>
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
        // ====== USER MESSAGE NAVIGATION ======
        let userMessages = [];
        let currentUserIndex = -1;
        let observerActive = true;

        function initUserNavigation() {{
            // Get all user messages (not tool results)
            userMessages = Array.from(document.querySelectorAll('.message.user-msg'));
            updateUserCounter();
        }}

        function updateUserCounter() {{
            const counter = document.getElementById('userCounter');
            if (userMessages.length === 0) {{
                counter.textContent = '0/0';
            }} else {{
                counter.textContent = `${{currentUserIndex + 1}}/${{userMessages.length}}`;
            }}
        }}

        function scrollToUserMessage(index) {{
            if (userMessages.length === 0) return;

            // Pause observer during programmatic scroll
            observerActive = false;

            // Remove previous highlight
            userMessages.forEach(msg => msg.classList.remove('user-highlight'));

            // Apply new index
            currentUserIndex = index;

            // Scroll to message
            const targetMsg = userMessages[currentUserIndex];
            targetMsg.scrollIntoView({{ behavior: 'auto', block: 'center' }});

            // Temporary highlight
            targetMsg.classList.add('user-highlight');

            updateUserCounter();

            // Reactivate observer after scroll
            setTimeout(() => {{ observerActive = true; }}, 100);
        }}

        function goToPrevUser() {{
            if (userMessages.length === 0) return;

            if (currentUserIndex <= 0) {{
                currentUserIndex = userMessages.length - 1;
            }} else {{
                currentUserIndex--;
            }}
            scrollToUserMessage(currentUserIndex);
        }}

        function goToNextUser() {{
            if (userMessages.length === 0) return;

            if (currentUserIndex >= userMessages.length - 1) {{
                currentUserIndex = 0;
            }} else {{
                currentUserIndex++;
            }}
            scrollToUserMessage(currentUserIndex);
        }}

        // Event listeners for navigation buttons
        document.getElementById('prevUser').addEventListener('click', goToPrevUser);
        document.getElementById('nextUser').addEventListener('click', goToNextUser);

        // Intersection Observer to detect manual scrolling
        function setupScrollObserver() {{
            const container = document.getElementById('terminalContent');

            const observer = new IntersectionObserver((entries) => {{
                if (!observerActive) return;

                entries.forEach(entry => {{
                    if (entry.isIntersecting && entry.intersectionRatio > 0.5) {{
                        const visibleIndex = userMessages.indexOf(entry.target);
                        if (visibleIndex !== -1 && visibleIndex !== currentUserIndex) {{
                            currentUserIndex = visibleIndex;
                            updateUserCounter();
                        }}
                    }}
                }});
            }}, {{
                root: container,
                threshold: 0.5
            }});

            // Observe all user messages
            userMessages.forEach(msg => observer.observe(msg));
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            initUserNavigation();
            setupScrollObserver();
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
        except:
            pass

    return f"Chat {hash_short}.html"

def _wait_if_interactive():
    """Pause before closing if running in an interactive console (e.g. double-click on Windows).

    When called from Claude Code or another process, stdout is piped
    so isatty() returns False and this does nothing.
    """
    import os
    if sys.stdout.isatty() and os.name == 'nt':
        input("\nPress Enter to close...")


def main():
    """Main entry point."""
    import sys

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
    generate_html(messages, output_file)

    print(f"\nConversion completed!")
    print(f"Open file: {output_file}")
    _wait_if_interactive()

if __name__ == "__main__":
    main()
