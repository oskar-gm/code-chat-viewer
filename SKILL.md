---
name: cl-code-visualizer
description: Convert Claude Code, VS Code, and Visual Studio Code chat JSON files (JSONL format) into professional HTML visualizations. Use when users need to visualize, view, export, or convert Claude Code conversation logs (.claude/chats/, .claude/projects/) into readable HTML with terminal-style aesthetics, syntax highlighting, collapsible tool results, and search functionality. Handles chat exports, conversation logs, JSONL files, and Claude AI chat history.
license: Complete terms in LICENSE
metadata:
  author: Óscar González Martín
  repository: https://github.com/oskar-gm/cl-code-visualizer
  version: 1.0
  keywords: claude-code, vs-code, visual-studio-code, chat-visualization, jsonl-converter, html-export, conversation-logs, chat-export, terminal-ui, developer-tools
  tags: claude-ai, vscode, visual-studio, chat-logs, json-converter, ai-tools, conversation-export
---

# Claude Code Visualizer

Convert Claude Code chat JSON files into formatted HTML visualizations with professional terminal-style aesthetics.

## Quick Start

Convert a Claude Code chat JSON to HTML:

```bash
python3 scripts/visualizer.py <input.json> <output.html>
```

**Example (Windows):**
```bash
python3 scripts/visualizer.py %USERPROFILE%\.claude\chats\chat_12345.json conversation.html
```

**Example (Linux/Mac):**
```bash
python3 scripts/visualizer.py ~/.claude/chats/chat_12345.json conversation.html
```

## What This Skill Does

Transforms raw Claude Code conversation logs (JSONL format) into readable, styled HTML documents with:

- **Terminal aesthetics**: Professional monospace styling with VS Code-inspired colors
- **Message categorization**: User messages (blue), Assistant responses (green), Tool results (orange)
- **Collapsible tool results**: Click to expand/collapse detailed tool outputs
- **Syntax highlighting**: Code blocks with proper formatting
- **Thinking blocks**: Italicized, subtle styling for internal reasoning
- **Tool use blocks**: Dark-themed blocks for function calls
- **Search functionality**: Built-in search bar to filter messages
- **Responsive layout**: Adapts to different screen sizes

## File Locations

Claude Code stores chat logs in JSONL format at:

**Windows:**
- `%USERPROFILE%\.claude\chats\`
- `%USERPROFILE%\.claude\projects\`

**Linux/Mac:**
- `~/.claude/chats/`
- `~/.claude/projects/`

Each chat file is named with a UUID (e.g., `c5f2a3e1-1234-5678-9abc-def012345678.json`)

## Input Format

The script expects **JSONL (JSON Lines)** format where each line is a valid JSON object representing a message or event in the conversation. This is the standard format for Claude Code chat logs.

Example JSONL structure:
```json
{"role":"user","content":"Hello","created_at":"2025-11-08T10:00:00Z","uuid":"abc123"}
{"role":"assistant","content":"Hi!","created_at":"2025-11-08T10:00:01Z","uuid":"def456"}
```

## Output Format

The generated HTML includes:

1. **Header section**: Chat title, timestamp, and metadata
2. **Search bar**: Real-time message filtering
3. **Message stream**: Chronologically ordered conversation
4. **Statistics footer**: Message counts and processing info
5. **Author signature**: Attribution comment in HTML source

### Message Types Handled

- **User messages**: Questions and commands from the user
- **Assistant messages**: AI responses with formatting
- **Tool uses**: Function calls with parameters
- **Tool results**: Command outputs (collapsible by default)
- **Thinking blocks**: Internal reasoning process
- **Summaries**: Conversation context summaries
- **Snapshots**: Conversation state markers

## Usage Patterns

### Basic Conversion

```bash
python3 scripts/visualizer.py chat.json output.html
```

### With Full Paths (Windows)

```bash
python3 scripts/visualizer.py %USERPROFILE%\.claude\chats\c5f2a3e1-1234-5678.json %USERPROFILE%\Documents\chat.html
```

### With Full Paths (Linux/Mac)

```bash
python3 scripts/visualizer.py ~/.claude/chats/c5f2a3e1-1234-5678.json ~/Documents/chat.html
```

### Batch Processing Multiple Chats (Windows PowerShell)

```powershell
Get-ChildItem "$env:USERPROFILE\.claude\chats\*.json" | ForEach-Object {
    python3 scripts/visualizer.py $_.FullName "$($_.BaseName).html"
}
```

### Batch Processing Multiple Chats (Linux/Mac)

```bash
for chat in ~/.claude/chats/*.json; do
    python3 scripts/visualizer.py "$chat" "$(basename "$chat" .json).html"
done
```

## Visual Styling Details

### Color Scheme

- **User messages**: Blue (`#0066CC`) with light blue background (`#F8FBFF`)
- **Assistant messages**: Green (`#10893E`) with light green background (`#FAFFF8`)
- **Tool results**: Orange (`#FF6B00`) with gray background (`#F8F8F8`)
- **Thinking blocks**: White background with subtle gray border and shadow (`#B8C8B8`)
- **Tool use blocks**: Dark gray (`#48484A`) with light text (`#E8E8E8`)

### Interactive Features

- **Collapsible tool results**: Click the header to expand/collapse
- **Search highlighting**: Matching messages shown, others hidden
- **Responsive bullets**: Size 20px with color-coded by message type
- **Smooth scrolling**: Auto-scroll to top on page load

### Typography

- **Font family**: Cascadia Code, Consolas, Monaco, monospace
- **Bullet size**: 20px
- **Label size**: 17px (user/assistant), 15px (general)
- **Content size**: 14px with line-height 1.7

## Technical Notes

### Processing Statistics

After conversion, the script displays:
- Total lines processed
- Count by message type (user, assistant, tool results, etc.)
- HTML elements generated
- Output file location

### Error Handling

- **Invalid JSON lines**: Logged with line number, processing continues
- **Missing fields**: Uses sensible defaults (e.g., "N/A" for missing IDs)
- **Empty content**: Displays "(empty)" placeholder

### Attribution in Output

All generated HTML files include an invisible comment with:
- Author information (Óscar González Martín)
- Repository link (https://github.com/oskar-gm/cl-code-visualizer)
- License information (MIT License)
- Generation timestamp

This ensures proper attribution while not affecting the visual output.

## When to Use This Skill

Trigger this skill when users want to:
- **Visualize** Claude Code conversations as HTML
- **Convert** chat.json or JSONL files to HTML format
- **Export** Claude Code conversation logs for sharing or archiving
- **View** chat history from VS Code Claude Code in a readable format
- **Transform** .claude/chats/ or .claude/projects/ files into HTML visualizations

**Example user requests:**
- "Convert my Claude Code chat to HTML"
- "Visualize this chat.json file"
- "Export my VS Code Claude conversation"
- "Make this JSONL conversation readable"

## Script Output

Upon successful conversion, the script prints:
```
📖 Reading <input-file>...
✅ X lines parsed
🔄 Generating HTML in terminal style...
✅ HTML generated successfully: <output-file>
📊 Statistics:
   - Total lines processed: X
   - User messages: X
   - Assistant messages: X
   - Tool Results: X
   - Summaries: X
   - Snapshots: X
   - HTML elements generated: X

🎉 Conversion completed!
📁 Open file: <output-file>
```

## Requirements

- **Python**: 3.6 or higher
- **Dependencies**: None (uses only Python standard library)
- **Operating System**: Windows, Linux, macOS
- **Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

## Best Practices

1. **Keep original JSON**: Always maintain the source .json file
2. **Descriptive names**: Use meaningful output filenames (e.g., `project_x_chat_2025-11-08.html`)
3. **Regular exports**: Convert important conversations for archival
4. **Browser viewing**: Open HTML files in any modern browser for best experience
5. **Sharing conversations**: HTML format is ideal for sharing with non-technical stakeholders

## Limitations

- Processes one chat file at a time
- Output is static HTML (no server-side processing)
- Requires local file access (cannot process remote URLs directly)
- Large conversations (1000+ messages) may take a few seconds to render

## Troubleshooting

### Issue: "File not found"
**Solution**: Check the path to your JSON file. Use full paths with `%USERPROFILE%` (Windows) or `~` (Linux/Mac).

### Issue: "Invalid JSON"
**Solution**: Ensure the file is in JSONL format (one JSON object per line). Check for corrupted lines.

### Issue: "Tool results not collapsing"
**Solution**: Ensure JavaScript is enabled in your browser. Try opening in a different browser.

### Issue: "Search not working"
**Solution**: The search function requires JavaScript. Make sure it's not blocked by browser extensions.

## Support

For questions, issues, or contributions:
- **Repository**: https://github.com/oskar-gm/cl-code-visualizer
- **Issues**: https://github.com/oskar-gm/cl-code-visualizer/issues
- **Email**: oscar@nucleoia.es
- **Website**: https://nucleoia.es

## License

This project is licensed under the MIT License. See LICENSE file for details.

**Author**: Óscar González Martín
**Version**: 1.0
**Last Updated**: November 2025
