#!/usr/bin/env python3
"""
Claude Code Visualizer v1.0

Converts Claude Code chat JSON files (JSONL format) into formatted HTML
visualizations with terminal-style aesthetics, syntax highlighting, and
interactive features.

Copyright (c) 2025 Óscar González Martín
Licensed under the MIT License - see LICENSE for details

Author: Óscar González Martín
Version: 1.0
Contact: oscar@nucleoia.es
Website: https://nucleoia.es
Repository: https://github.com/oskar-gm/cl-code-visualizer
LinkedIn: https://linkedin.com/in/oscar-gonz

This script transforms raw Claude Code conversation logs (JSONL format) into
readable, styled HTML documents with:
- Terminal aesthetics with VS Code-inspired colors
- Collapsible tool results with interactive toggles
- Real-time search functionality
- Syntax highlighting for code blocks
- Responsive design for all screen sizes
- Proper attribution in HTML output

For usage instructions, see README.md or visit the repository.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from html import escape

def parse_chat_json(json_file: str) -> List[Dict]:
    """Lee y parsea el archivo JSON línea por línea (JSONL format)"""
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
                    print(f"⚠️  Error parseando línea {line_num}: {e}")
                    continue
    return messages

def format_timestamp(timestamp_str: str) -> str:
    """Formatea timestamp ISO a formato HH:MM AM/PM"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%I:%M %p').lstrip('0')
    except:
        return ""

def format_model_name(model: str) -> str:
    """Formatea el nombre del modelo de forma corta"""
    if not model:
        return ""
    return model

def escape_html_preserve_structure(text: str) -> str:
    """Escapa HTML pero preserva la estructura del texto"""
    if not text:
        return ""
    
    text = escape(text)
    text = text.replace('\n', '<br>')
    text = re.sub(r'  +', lambda m: '&nbsp;' * len(m.group()), text)
    
    return text

def is_tool_result_message(content) -> bool:
    """Determina si un mensaje es un tool_result (no un mensaje real del usuario)"""
    if isinstance(content, list):
        return any(isinstance(item, dict) and item.get('type') == 'tool_result' for item in content)
    return False

def format_tool_result_content(tool_result_data: Dict) -> str:
    """Formatea el contenido de un tool_result - MUESTRA TODO SIN TRUNCAR"""
    content = tool_result_data.get('content', '')
    tool_use_id = tool_result_data.get('tool_use_id', '')
    
    if isinstance(content, str):
        # String directo - MOSTRAR TODO
        return escape_html_preserve_structure(content)
    elif isinstance(content, list):
        # Lista de items (generalmente [{type: 'text', text: '...'}])
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    # MOSTRAR TODO EL TEXTO SIN TRUNCAR
                    parts.append(escape_html_preserve_structure(text))
                else:
                    parts.append(f"[{item.get('type')}]")
        return '<br>'.join(parts)
    else:
        return escape(str(content))

def format_content_item(item) -> str:
    """Formatea un item de contenido individual"""
    if isinstance(item, str):
        return escape_html_preserve_structure(item)
    
    if not isinstance(item, dict):
        return str(item)
    
    item_type = item.get('type', '')
    
    if item_type == 'text':
        return escape_html_preserve_structure(item.get('text', ''))
    
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
            input_lines.append(f'  {key}: {value}')
        
        input_str = '<br>'.join(input_lines) if input_lines else '  (sin parámetros)'
        
        return f'''<div class="tool-use">
🔧 Tool: {escape(tool_name)}
   ID: {escape(tool_id[:16])}...
   Parámetros:
{input_str}
</div>'''
    
    # Si es tool_result, NO procesarlo aquí (se maneja en otro lugar)
    if item_type == 'tool_result':
        return ''
    
    return f'<div class="unknown-type">[Tipo: {item_type}]</div>'

def format_message_html(msg: Dict, index: int) -> str:
    """Convierte un mensaje completo a HTML en formato terminal"""
    
    msg_type = msg.get('type', '')
    
    # ====== MANEJAR RESÚMENES ======
    if msg_type == 'summary':
        summary_text = msg.get('summary', '')
        leaf_uuid = msg.get('leafUuid', '')
        return f'''<div class="message summary-msg">
<div class="summary-header">
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 RESUMEN DE CONVERSACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</div>
<div class="summary-content">
{escape(summary_text)}
<br><br>
<span class="uuid-small">Leaf UUID: {leaf_uuid[-12:]}</span>
</div>
</div>
'''
    
    # ====== MANEJAR SNAPSHOTS ======
    if msg_type == 'file-history-snapshot':
        message_id = msg.get('messageId', '')[:12]
        return f'<div class="snapshot">💾 [Snapshot guardado: {message_id}...]</div>\n'
    
    # ====== MANEJAR MENSAJES ======
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
    
    # ====== DETECTAR SI ES TOOL_RESULT (NO ES MENSAJE REAL DEL USUARIO) ======
    if role == 'user' and is_tool_result_message(content):
        # Este es un resultado de herramienta, NO un mensaje del usuario
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
    
    # ====== MENSAJES REALES (USUARIO O ASISTENTE) ======
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
    
    # Procesar contenido (excluyendo tool_result que ya se manejó arriba)
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

def generate_html(messages: List[Dict], output_file: str):
    """Genera el documento HTML completo en estilo terminal"""
    
    # Contar estadísticas (distinguiendo tool_results)
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
    
    # Generar HTML de todos los mensajes
    messages_html = []
    for i, msg in enumerate(messages):
        msg_html = format_message_html(msg, i)
        if msg_html:
            messages_html.append(msg_html)
    
    messages_content = '\n'.join(messages_html)
    
    generation_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # Plantilla HTML completa estilo terminal
    html_template = f'''<!DOCTYPE html>
<!--
=============================================================================
Claude Code Visualizer v1.0 - Professional Chat Log HTML Exporter
Generated HTML Visualization
=============================================================================

Created with: Claude Code Visualizer
Repository: https://github.com/oskar-gm/cl-code-visualizer
Website: https://nucleoia.es
License: MIT License

This HTML file was generated by Claude Code Visualizer, an open-source tool
for converting Claude Code, VS Code, and Visual Studio Code chat logs (JSONL)
into readable, professional HTML visualizations with terminal-style aesthetics.

Learn more: https://github.com/oskar-gm/cl-code-visualizer
Developer: https://nucleoia.es

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=============================================================================
-->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- SEO Meta Tags -->
    <meta name="description" content="Claude Code conversation visualization - Professional HTML export from JSONL chat logs. Terminal-style UI with collapsible tool results, real-time search, and responsive design. VS Code integration.">
    <meta name="keywords" content="Claude Code, VS Code, Visual Studio Code, chat visualization, conversation export, JSONL converter, HTML visualizer, terminal style, AI chat logs, conversation logs, chat export, developer tools, Claude AI, code assistant, AI tools, conversación Claude, visualización chat, exportar conversación, logs de chat, herramientas desarrollador, asistente código">
    
    <meta name="generator" content="Claude Code Visualizer v1.0 - https://github.com/oskar-gm/cl-code-visualizer">
    <meta name="robots" content="index, follow">
    <meta name="language" content="English, Spanish">

    <!-- Open Graph / Social Media Meta Tags -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="Claude Code Conversation - Professional Terminal Visualization">
    <meta property="og:description" content="Professional visualization of Claude Code chat logs. Convert JSONL to HTML with terminal-style aesthetics. Created with Claude Code Visualizer.">
    <meta property="og:url" content="https://github.com/oskar-gm/cl-code-visualizer">
    <meta property="og:site_name" content="Claude Code Visualizer">
    <meta property="og:locale" content="en_US">
    <meta property="og:locale:alternate" content="es_ES">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Claude Code Conversation Visualization">
    <meta name="twitter:description" content="Professional HTML export from Claude Code JSONL chat logs">

    <!-- Author & Publisher -->
    <link rel="author" href="https://nucleoia.es">
    <link rel="canonical" href="https://github.com/oskar-gm/cl-code-visualizer">
    <meta name="publisher" content="nucleoia.es">

    <title>Claude Code Conversation - Terminal View</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            background: #F5F5F5;
            color: #1E1E1E;
            line-height: 1.6;
            font-size: 14px;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: #FFFFFF;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .terminal-header {{
            background: #2D2D30;
            color: #CCCCCC;
            padding: 12px 20px;
            font-size: 13px;
            border-bottom: 1px solid #1E1E1E;
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
        
        .user-msg .bullet {{
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
        
        .user-msg .msg-content {{
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
        
        /* Restablecer tamaño de thinking y tool-use a 14px */
        
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
        
        .unknown-type {{
            color: #999;
            font-style: italic;
            padding: 5px 0;
        }}
        
        /* Scrollbar personalizado */
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
                <span>▶</span>
                <span>Claude Code Chat Viewer</span>
            </div>
            <div class="terminal-controls">
                <span class="terminal-btn btn-close"></span>
                <span class="terminal-btn btn-minimize"></span>
                <span class="terminal-btn btn-maximize"></span>
            </div>
        </div>
        
        <div class="stats-bar">
            <div>
                📊 Total: {total_lines} líneas | 
                👤 Usuario: {real_user_msgs} | 
                🤖 Asistente: {assistant_msgs} | 
                📤 Tool Results: {tool_result_msgs} | 
                📋 Resúmenes: {summaries} | 
                💾 Snapshots: {snapshots}
            </div>
            <div>
                🕒 Generado: {generation_time}
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="🔍 Buscar en la conversación...">
        </div>
        
        <div class="terminal-content" id="terminalContent">
{messages_content}
        </div>
        
        <div class="footer">
            <a href="https://github.com/oskar-gm/cl-code-visualizer" target="_blank" style="color: #666; text-decoration: none;">Claude Code Visualizer</a> | 
            <a href="https://nucleoia.es" target="_blank" style="color: #666; text-decoration: none;">nucleoia.es</a> | 
            Procesados {len(messages_html)} elementos de {total_lines} líneas totales
        </div>
    </div>
    
    <script>
        // Búsqueda
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
            
            console.log(`Mostrando ${{visibleCount}} de ${{messages.length}} mensajes`);
        }});
        
        // Toggle para tool results
        document.addEventListener('DOMContentLoaded', function() {{
            // Convertir todos los tool-result-msg en colapsables
            const toolResults = document.querySelectorAll('.tool-result-msg');
            
            toolResults.forEach(toolResult => {{
                const header = toolResult.querySelector('.msg-header');
                const content = toolResult.querySelector('.msg-content');
                
                if (header && content) {{
                    // Crear estructura colapsable
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
                    
                    // Limpiar y reconstruir
                    toolResult.innerHTML = '';
                    toolResult.appendChild(newHeader);
                    toolResult.appendChild(newContent);
                    
                    // Footer si existe
                    const footer = toolResult.querySelector('.msg-footer');
                    if (footer) {{
                        newContent.appendChild(footer);
                    }}
                    
                    // Evento click
                    newHeader.addEventListener('click', function() {{
                        toggle.classList.toggle('collapsed');
                        newContent.classList.toggle('expanded');
                    }});
                }}
            }});
        }});
        
        // Scroll al inicio
        window.addEventListener('load', function() {{
            const content = document.getElementById('terminalContent');
            content.scrollTop = 0;
        }});
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"✅ HTML generado exitosamente: {output_file}")
    print(f"📊 Estadísticas:")
    print(f"   - Total líneas procesadas: {total_lines}")
    print(f"   - Mensajes REALES de usuario: {real_user_msgs}")
    print(f"   - Mensajes del asistente: {assistant_msgs}")
    print(f"   - Tool Results (separados): {tool_result_msgs}")
    print(f"   - Resúmenes: {summaries}")
    print(f"   - Snapshots: {snapshots}")
    print(f"   - Elementos HTML generados: {len(messages_html)}")

def main():
    """Función principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python visualizer.py <archivo_json> [archivo_salida.html]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_terminal_v3.html')
    
    if not Path(input_file).exists():
        print(f"❌ Error: El archivo {input_file} no existe")
        sys.exit(1)
    
    print(f"📖 Leyendo {input_file}...")
    messages = parse_chat_json(input_file)
    print(f"✅ {len(messages)} líneas parseadas")
    
    print(f"🔄 Generando HTML en estilo terminal...")
    generate_html(messages, output_file)
    
    print(f"\n🎉 ¡Conversión completada!")
    print(f"📁 Abre el archivo: {output_file}")

if __name__ == "__main__":
    main()
