---
name: code-chat-viewer
description: Claude Code skill for converting chat JSONL files into professional HTML visualizations with an interactive dashboard. Handles setup, configuration, batch generation, and organization of Claude Code conversation logs. Fully automated — Claude Code configures, generates, and manages everything.
license: Complete terms in LICENSE
metadata:
  author: Óscar González Martín
  repository: https://github.com/oskar-gm/code-chat-viewer
  version: 2.1.1
  keywords: claude-code, chat-visualization, jsonl-converter, html-export, conversation-logs, terminal-ui, developer-tools
  tags: claude-code, chat-logs, json-converter, ai-tools, conversation-export, skill
---

# Code Chat Viewer — Skill Instructions

This file contains operational instructions for Claude Code. When this skill is loaded, follow the workflows below to help the user configure, generate, and manage their Claude Code chat visualizations.

## Overview

This skill provides two scripts:

| Script | Purpose |
|--------|---------|
| `scripts/visualizer.py` | Core converter: single JSONL file to single HTML |
| `scripts/manager.py` | Orchestrator: batch scan, generate, organize, and create dashboard |

The manager reads `config.json` for all paths and settings. If it does not exist, guide the user through interactive setup.

## Workflow: First-Time Setup

When the user wants to use this skill and `config.json` does not exist:

### Step 1: Detect source path

Look for Claude Code chat files automatically:

- **Windows**: `%USERPROFILE%\.claude\projects\`
- **Linux/Mac**: `~/.claude/projects/`

Verify the path exists and contains project subdirectories with `.jsonl` files. If not found, ask the user for the correct path.

### Step 2: Ask configuration questions

Ask these questions interactively (suggest defaults in parentheses):

1. **Output folder**: "Where should the generated HTML files be saved?"
   - Default: `~/Code Chat Viewer`
   - Dashboard is saved at the root; chats go into a `Chats/` subfolder

2. **Dashboard filename**: "What name for the dashboard file?"
   - Default: `CCV-Dashboard.html`

3. **Agent chats**: "Include agent sub-chats? (yes/no)"
   - Default: yes
   - If yes: "Minimum agent file size in KB?" (default: 3)

4. **Inactive days**: "Days of inactivity before organizing?"
   - Default: 5

5. **Shorts management**: "Automatically separate small inactive chats into a subfolder? (yes/no)"
   - Default: yes
   - If yes: "Maximum size in KB to classify as short?" (default: 40)

6. **Archive management**: "Automatically archive large inactive chats? (yes/no)"
   - Default: yes

### Step 3: Create config.json

Generate `config.json` from the user's answers. Use the structure in `config.example.json` as template. Place it in the skill's root folder.

### Step 4: Run first generation

Execute: `python scripts/manager.py`

Report the results to the user.

## Workflow: Regular Usage

When `config.json` already exists:

1. Execute: `python scripts/manager.py`
2. Report results (new, updated, unchanged, organized, dashboard stats)
3. Inform the user where the dashboard file is located

## Workflow: Update Configuration

When the user wants to change settings:

1. Read current `config.json`
2. Show current configuration
3. Ask what they want to change
4. Update `config.json`
5. Re-run the manager if needed

## Workflow: Single Chat Conversion

When the user wants to convert a single JSONL file:

```bash
python scripts/visualizer.py <input.jsonl> [output.html]
```

If no output filename is provided, the script generates one automatically with format `Chat YYYY-MM-DD HH-MM hash.html`.

## File Locations

Claude Code stores chat logs at:

- **Windows**: `%USERPROFILE%\.claude\projects\` and `%USERPROFILE%\.claude\chats\`
- **Linux/Mac**: `~/.claude/projects/` and `~/.claude/chats/`

Each project subdirectory contains:
- `*.jsonl` — Main chat files (UUID-named)
- `agent-*.jsonl` — Agent sub-chat files
- `sessions-index.json` — Rich metadata (name, summary, message count, git branch)

## Configuration Reference

`config.json` fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source.projects_path` | string | `~/.claude/projects` | Directory with Claude Code JSONL files |
| `output.folder` | string | `~/Code Chat Viewer` | Root folder for output (dashboard + Chats/ subfolder) |
| `output.index_filename` | string | `CCV-Dashboard.html` | Dashboard filename |
| `agents.include` | bool | `true` | Include agent sub-chat files |
| `agents.min_size_kb` | int | `3` | Minimum agent file size to include (KB) |
| `inactive_days` | int | `5` | Days without activity before organizing |
| `shorts.enabled` | bool | `true` | Separate small inactive chats |
| `shorts.folder` | string | `Shorts` | Subfolder name for short chats |
| `shorts.max_size_kb` | int | `40` | Max HTML size to classify as short (KB) |
| `archive.enabled` | bool | `true` | Separate old inactive chats |
| `archive.folder` | string | `Archived` | Subfolder name for archived chats |

## Dashboard Features

The generated dashboard (`CCV-Dashboard.html` by default) is a self-contained HTML file with:

- **Sortable table**: Click column headers to sort (default: last used, descending)
- **Filter**: Filter by text across all columns
- **Category filters**: Checkboxes for Active/Shorts/Archived (only shown if enabled)
- **Optional columns**: UUID, Branch, Size, First Prompt (toggle with checkboxes)
- **Direct links**: Icon to open each chat HTML file
- **Enriched data**: Uses `sessions-index.json` and direct JSONL parsing for name, summary, message count, git branch
- **State persistence**: Remembers sort order, filters, search text, and visible columns via localStorage (5h TTL)
- **Snapshot filtering**: Automatically excludes file-history-snapshot entries (Claude Code's undo system)
- **Feedback button**: Highlighted in header, also in footer

## Chat Page Features

Each generated chat HTML includes:

- **Dashboard link**: "Back to Dashboard" button in header (links adjust automatically for subfolder location)
- **Conversation filter**: Filter messages by text content
- **Multi-mode message navigation**: All/User/Assistant modes with prev/next buttons, position counter, and keyboard shortcuts (N/P)
- **Collapsible thinking blocks**: Collapsed by default with first-line preview; expand for full content
- **Collapsible tool-use blocks**: Collapsed by default; expand for full untruncated content
- **Color-coded highlights**: Blue for user messages, green for assistant messages
- **Smart scroll**: Centers short messages; pins long messages to top for readability
- **Feedback button**: In header (highlighted) and footer
- **Collapsible tool results**: Click to expand/collapse

## Chat Categories

| Category | Criteria | Location |
|----------|----------|----------|
| **Active** | Used within `inactive_days` | `Chats/` folder |
| **Short** | HTML < `shorts.max_size_kb` + inactive | `Chats/Shorts/` subfolder |
| **Archived** | Inactive for `inactive_days`+ | `Chats/Archived/` subfolder |

## Troubleshooting

### "config.json not found"
Run the setup workflow (Step 1-4 above) to create the configuration.

### "Source path does not exist"
The configured `source.projects_path` is wrong. Update it in `config.json` or re-run setup.

### Empty dashboard
The source directory may not contain any JSONL files, or the output folder has no generated HTMLs yet. Run the manager first.

### Missing enriched data (? icon in Msgs column)
Some chats lack metadata in `sessions-index.json`. This is normal for old chats, agent chats, or recently active sessions not yet indexed by Claude Code.

## Requirements

- **Python**: 3.6 or higher
- **Dependencies**: None (Python standard library only)
- **OS**: Windows, Linux, macOS

## Technical Notes

- The manager imports functions from `visualizer.py` (same directory): `parse_chat_json`, `generate_html`, `get_chat_timestamp`, `generate_output_filename`, `ICON_BASE64`, `ICON_FAVICON_BASE64`
- HTML generation is deterministic: same JSONL input produces same HTML output
- The manager only regenerates an HTML if the source JSONL is newer than the existing HTML
- Timestamps are always verified against JSONL file mtime (sessions-index.json can be stale)
- Message counts and metadata are extracted directly from JSONL files for accuracy
- File-history-snapshot entries (Claude Code's undo system) are automatically filtered out
- Organization (shorts/archive) uses the JSONL modification time as "last used" indicator, not the HTML generation time
- Dashboard links in chat pages are automatically adjusted for subfolder depth (`../` or `../../`)
- Favicon uses a dark icon (visible on white browser tabs); header uses a light icon (visible on dark header)
- Both icons are embedded as base64 — no external files needed
- The manager auto-opens the dashboard in the browser after generation (interactive mode only)
- "(no content)" placeholder messages from Claude Code internals are automatically filtered out
- Scripts can be run manually without Claude Code — they pause before closing on Windows (double-click compatible)

## Attribution

Author: Óscar González Martín
Repository: https://github.com/oskar-gm/code-chat-viewer
License: MIT
Version: 2.1
