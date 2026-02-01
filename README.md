# Code Chat Viewer

> Convert Claude Code chat logs (JSONL) to professional, browsable HTML visualizations. Export AI conversations, build interactive dashboards, and organize your coding assistant history — with or without Claude Code.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0-green.svg)](https://github.com/oskar-gm/code-chat-viewer/releases/tag/v2.0)
[![Claude Code](https://img.shields.io/badge/Claude_Code_CLI-compatible-blueviolet.svg)](https://github.com/anthropics/claude-code)

### Chat View
![Chat View](https://github.com/oskar-gm/code-chat-viewer/releases/download/v2.0/ccv-2.0-screenshot-1.jpeg)

### Dashboard
![Dashboard](https://github.com/oskar-gm/code-chat-viewer/releases/download/v2.0/ccv-2.0-screenshot-3.jpeg)

## Quick Download

**Latest version:** [Download latest](https://github.com/oskar-gm/code-chat-viewer/releases/latest) - Always up-to-date

**Version 2.0:** [Download v2.0.zip](https://github.com/oskar-gm/code-chat-viewer/archive/refs/tags/v2.0.zip) - Stable release

Or browse all [Releases](https://github.com/oskar-gm/code-chat-viewer/releases)

---

**[English](#english)** | **[Español](#español)**

---

<a name="english"></a>
## English

### Direct Claude Code CLI Compatibility

**Claude Code does everything for you.** This skill is designed to work directly with [Claude Code CLI](https://github.com/anthropics/claude-code) (Anthropic's command-line tool for developers, not the web interface). Once installed, Claude Code will:

- **Detect** your Claude Code chat files automatically
- **Ask** your preferences through interactive setup
- **Create** the configuration file for you
- **Generate** HTML visualizations for all your chats
- **Build** an interactive dashboard to browse them
- **Organize** chats by activity (active, short, archived) — if you want

No manual configuration needed. Just install the skill and ask Claude Code to visualize your chats.

### Installation in Claude Code

**Option A: Per-project** (affects only one project)

Copy the skill folder into your project's `.claude/skills/` directory:

```bash
# From your project root
mkdir -p .claude/skills
cd .claude/skills
git clone https://github.com/oskar-gm/code-chat-viewer.git
```

**Option B: Global** (affects all your Claude Code projects)

Copy the skill folder into your user-level `.claude/skills/` directory:

```bash
# Global installation
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/oskar-gm/code-chat-viewer.git
```

Then ask Claude Code: *"Visualize my Claude Code chats"* or *"Set up the chat visualizer"*.

### How It Works

1. **First time**: Claude Code reads `SKILL.md`, detects your chat files, asks your preferences, creates `config.json`
2. **Next times**: Claude Code reads `config.json` and runs the manager — no questions asked
3. **To update settings**: Ask Claude Code *"Update visualizer config"*

### Configuration

The skill uses two files:

| File | Purpose |
|------|---------|
| `config.example.json` | Template with defaults (always present, shareable) |
| `config.json` | Your personalized settings (gitignored, created by Claude Code) |

Configurable options:

| Setting | Default | Description |
|---------|---------|-------------|
| Source path | `~/.claude/projects` | Where your JSONL chat files are |
| Output folder | `~/Code Chat Viewer` | Where HTML files and dashboard are saved |
| Dashboard filename | `CCV-Dashboard.html` | Name of the interactive index |
| Agent chats | Included (>3KB) | Include sub-agent conversations |
| Agent min size | 3 KB | Minimum agent file size to include |
| Shorts | Enabled | Separate small inactive chats into subfolder |
| Shorts max size | 40 KB | Maximum HTML size to classify as short |
| Archive | Enabled | Separate old inactive chats into subfolder |
| Inactive days | 5 | Days without activity before organizing |

### Features

- Terminal-style aesthetics inspired by VS Code
- User messages with light blue background
- Assistant responses with light green background
- Collapsible tool results (click to expand)
- Real-time conversation filter
- Responsive fullscreen layout
- User message navigation (prev/next buttons with position counter)
- Highlight animation when navigating
- Security-safe HTML rendering (escaped tool parameters)
- Interactive dashboard with sortable table, search, and category filters
- Batch generation with incremental updates (only regenerates changed chats)
- Configurable chat organization (active, shorts, archived)
- Dashboard link in every chat for easy navigation back
- Embedded favicon and header icon (self-contained, no external files needed)
- Auto-opens dashboard in browser after generation
- Full interactive setup with all options configurable
- Scan progress indicator with summary
- Built-in feedback button
- Windows-friendly: scripts pause on double-click (no instant close)

### What's New in v2.0

**Features:**
- Fullscreen edge-to-edge layout (no borders or shadows)
- User message navigation with prev/next buttons and position counter
- Scroll synchronization for navigation counter
- Highlight animation when navigating to a message
- Local timezone conversion for timestamps
- Smart output filename generation (Chat YYYY-MM-DD HH-MM hash.html)
- Stats bar shows chat date instead of generation time
- Chat Manager: batch generation, organization, and interactive dashboard
- Full interactive setup: all options configurable with sensible defaults
- Organized output: Chats/ subfolder with Shorts/ and Archived/ subfolders
- Embedded favicon (dark, visible on browser tabs) and header icon (light)
- Auto-opens dashboard in browser after generation
- Scan progress indicator with file count summary
- Dashboard navigation: every chat includes a "Back to Dashboard" link
- Built-in feedback button in header and footer
- Conversation filter (replaces generic search)
- Windows double-click support: scripts pause before closing
- Rebranded from "Claude Code Visualizer" to "Code Chat Viewer"

**Fixes:**
- Security: HTML-escaped tool_use parameters to prevent DOM injection
- Filtered out "(no content)" ghost messages from Claude Code internals
- CSS specificity: User messages correctly display with blue styling
- Unknown type elements styled correctly within user messages
- Instant scroll navigation (replaced smooth scrolling)
- Reduced IntersectionObserver reactivation delay to 100ms
- Consistent header sizing between chat pages and dashboard

### Manual Usage (without Claude Code)

You do **not** need Claude Code to use this tool. Both scripts work standalone with Python 3.6+.

**Convert a single chat:**

```bash
python scripts/visualizer.py path/to/chat.jsonl output.html
```

**Batch generation with dashboard** (requires config.json):

```bash
# 1. Create your config from the template
cp config.example.json config.json
# 2. Edit config.json — set projects_path to your Claude Code projects folder
# 3. Run the manager
python scripts/manager.py
```

On Windows, you can also **double-click** the `.py` files directly. The console window will stay open until you press Enter.

### File Structure

```
code-chat-viewer/
├── scripts/
│   ├── visualizer.py        # Core: JSONL to HTML converter
│   └── manager.py           # Orchestrator: batch generation + dashboard
├── icon.png                 # Project icon (embedded as base64 in output)
├── config.example.json      # Configuration template
├── config.json              # Your settings (gitignored, created by setup)
├── SKILL.md                 # Claude Code skill instructions
├── README.md                # This file
├── CONTRIBUTING.md          # Contribution guidelines
├── CODE_OF_CONDUCT.md       # Code of conduct
└── LICENSE                  # MIT License
```

### Output Structure

```
~/Code Chat Viewer/              # Output root (configurable)
├── CCV-Dashboard.html           # Interactive dashboard
└── Chats/                       # Generated HTML files
    ├── Chat 2026-01-30 ...html  # Active chats
    ├── Shorts/                  # Small inactive chats (if enabled)
    └── Archived/                # Old inactive chats (if enabled)
```

### Claude Code File Locations

Claude Code stores chat logs in JSONL format at:

- **Windows:** `%USERPROFILE%\.claude\projects\` or `%USERPROFILE%\.claude\chats\`
- **Linux/Mac:** `~/.claude/projects/` or `~/.claude/chats/`

Each chat file is named with a UUID (e.g., `c5f2a3e1-1234-5678-9abc-def012345678.jsonl`)

### Visual Styling

- **User messages**: Blue (`#0066CC`) with light blue background (`#F8FBFF`)
- **Assistant messages**: Green (`#10893E`) with light green background (`#FAFFF8`)
- **Tool results**: Orange (`#FF6B00`) with gray background (`#F8F8F8`)
- **Thinking blocks**: White background with subtle gray border and shadow
- **Tool use blocks**: Dark gray (`#48484A`) with light text (`#E8E8E8`)

### Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Attribution Requirements:**
- Keep the LICENSE file intact
- Credit the original author: Óscar González Martín
- Link to the original repository: https://github.com/oskar-gm/code-chat-viewer
- State any modifications made

### Author

**Óscar González Martín**
- Website: [nucleoia.es](https://nucleoia.es)
- Email: oscar@nucleoia.es
- GitHub: [@oskar-gm](https://github.com/oskar-gm)
- LinkedIn: [oscar-gonz](https://linkedin.com/in/oscar-gonz)

### Support

If you find this project useful, please:
- Star the repository
- Report bugs via [Issues](https://github.com/oskar-gm/code-chat-viewer/issues)
- Suggest improvements
- Share with others

### Contact

For questions, suggestions, or bug reports:
- **Email:** oscar@nucleoia.es
- **GitHub Issues:** [Report here](https://github.com/oskar-gm/code-chat-viewer/issues)

---

<a name="español"></a>
## Español

### Compatibilidad directa con Claude Code CLI

**Claude Code lo hace todo por ti.** Esta skill está diseñada para funcionar directamente con [Claude Code CLI](https://github.com/anthropics/claude-code) (la herramienta de línea de comandos de Anthropic para desarrolladores, no la interfaz web). Una vez instalada, Claude Code:

- **Detecta** tus archivos de chat de Claude Code automáticamente
- **Pregunta** tus preferencias mediante un setup interactivo
- **Crea** el archivo de configuración por ti
- **Genera** visualizaciones HTML de todos tus chats
- **Construye** un panel interactivo para navegarlos
- **Organiza** los chats por actividad (activos, cortos, archivados) — si quieres

Sin configuración manual. Solo instala la skill y pide a Claude Code que visualice tus chats.

### Instalación en Claude Code

**Opción A: Por proyecto** (afecta solo a un proyecto)

Copia la carpeta de la skill en el directorio `.claude/skills/` de tu proyecto:

```bash
# Desde la raíz de tu proyecto
mkdir -p .claude/skills
cd .claude/skills
git clone https://github.com/oskar-gm/code-chat-viewer.git
```

**Opción B: Global** (afecta a todos tus proyectos de Claude Code)

Copia la carpeta de la skill en tu directorio `.claude/skills/` a nivel de usuario:

```bash
# Instalación global
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/oskar-gm/code-chat-viewer.git
```

Luego pide a Claude Code: *"Visualiza mis chats de Claude Code"* o *"Configura el visualizador de chats"*.

### Cómo funciona

1. **Primera vez**: Claude Code lee `SKILL.md`, detecta tus archivos de chat, pregunta tus preferencias, crea `config.json`
2. **Siguientes veces**: Claude Code lee `config.json` y ejecuta el manager — sin preguntas
3. **Para cambiar ajustes**: Pide a Claude Code *"Actualiza la configuración del visualizador"*

### Configuración

La skill usa dos archivos:

| Archivo | Propósito |
|---------|-----------|
| `config.example.json` | Plantilla con valores por defecto (siempre presente, compartible) |
| `config.json` | Tu configuración personalizada (en gitignore, creada por Claude Code) |

Opciones configurables:

| Ajuste | Por defecto | Descripción |
|--------|-------------|-------------|
| Ruta origen | `~/.claude/projects` | Dónde están tus archivos JSONL |
| Carpeta de salida | `~/Code Chat Viewer` | Dónde se guardan los HTML y el panel |
| Nombre del panel | `CCV-Dashboard.html` | Nombre del archivo índice interactivo |
| Chats de agentes | Incluidos (>3KB) | Incluir conversaciones de sub-agentes |
| Tamaño mín. agente | 3 KB | Tamaño mínimo de agente para incluir |
| Shorts | Activado | Separar chats pequeños inactivos en subcarpeta |
| Tamaño máx. short | 40 KB | Tamaño máximo de HTML para clasificar como short |
| Archivo | Activado | Separar chats inactivos antiguos en subcarpeta |
| Días de inactividad | 5 | Días sin actividad antes de organizar |

### Características

- Estética estilo terminal inspirada en VS Code
- Mensajes de usuario con fondo azul claro
- Respuestas del asistente con fondo verde claro
- Resultados de herramientas colapsables (clic para expandir)
- Filtro de conversación en tiempo real
- Layout fullscreen responsive
- Navegación por mensajes de usuario (botones prev/next con contador)
- Animación de resaltado al navegar
- Renderizado HTML seguro (parámetros de herramientas escapados)
- Panel interactivo con tabla ordenable, búsqueda y filtros por categoría
- Generación por lotes con actualizaciones incrementales (solo regenera chats modificados)
- Organización configurable de chats (activos, cortos, archivados)
- Enlace al panel en cada chat para volver fácilmente
- Favicon e icono de cabecera embebidos (autocontenido, sin archivos externos)
- Apertura automática del panel en el navegador tras la generación
- Setup interactivo completo con todas las opciones configurables
- Indicador de progreso del escaneo con resumen
- Botón de feedback integrado
- Compatible con Windows: los scripts se pausan al hacer doble clic (sin cierre instantáneo)

### Novedades en v2.0

**Funcionalidades:**
- Layout fullscreen edge-to-edge sin bordes ni sombras
- Navegación por mensajes de usuario con botones prev/next y contador de posición
- Sincronización de scroll para el contador de navegación
- Animación de resaltado al navegar a un mensaje
- Conversión a zona horaria local para timestamps
- Generación inteligente de nombres de archivo (Chat YYYY-MM-DD HH-MM hash.html)
- La barra de estadísticas muestra fecha del chat en lugar de la de generación
- Chat Manager: generación por lotes, organización y panel interactivo
- Setup interactivo completo: todas las opciones configurables con defaults razonables
- Salida organizada: subcarpeta Chats/ con subcarpetas Shorts/ y Archived/
- Favicon embebido (oscuro, visible en pestañas del navegador) e icono de cabecera (claro)
- Apertura automática del panel en el navegador tras la generación
- Indicador de progreso del escaneo con resumen de archivos
- Navegación al panel: cada chat incluye un enlace "Volver al Dashboard"
- Botón de feedback integrado en encabezado y pie de página
- Filtro de conversación (reemplaza búsqueda genérica)
- Soporte para doble clic en Windows: los scripts se pausan antes de cerrarse
- Renombrado de "Claude Code Visualizer" a "Code Chat Viewer"

**Correcciones:**
- Seguridad: parámetros de tool_use escapados en HTML para prevenir inyección DOM
- Filtrado de mensajes fantasma "(no content)" de los internos de Claude Code
- Especificidad CSS: los mensajes de usuario se muestran correctamente en azul
- Estilos de tipos desconocidos corregidos dentro de mensajes de usuario
- Navegación instantánea (reemplazado smooth scrolling)
- Delay de reactivación de IntersectionObserver reducido a 100ms
- Tamaño de encabezado consistente entre las páginas de chat y el panel

### Uso manual (sin Claude Code)

**No** necesitas Claude Code para usar esta herramienta. Ambos scripts funcionan de forma independiente con Python 3.6+.

**Convertir un chat individual:**

```bash
python scripts/visualizer.py ruta/al/chat.jsonl salida.html
```

**Generación por lotes con panel** (requiere config.json):

```bash
# 1. Crear tu configuración desde la plantilla
cp config.example.json config.json
# 2. Editar config.json — configurar projects_path con la carpeta de proyectos de Claude Code
# 3. Ejecutar el manager
python scripts/manager.py
```

En Windows, también puedes hacer **doble clic** en los archivos `.py` directamente. La ventana de consola permanecerá abierta hasta que pulses Enter.

### Estructura de archivos

```
code-chat-viewer/
├── scripts/
│   ├── visualizer.py        # Core: conversor JSONL a HTML
│   └── manager.py           # Orquestador: generación por lotes + panel
├── icon.png                 # Icono del proyecto (embebido como base64 en la salida)
├── config.example.json      # Plantilla de configuración
├── config.json              # Tu configuración (en gitignore, creada por setup)
├── SKILL.md                 # Instrucciones de la skill para Claude Code
├── README.md                # Este archivo
├── CONTRIBUTING.md          # Guía de contribución
├── CODE_OF_CONDUCT.md       # Código de conducta
└── LICENSE                  # Licencia MIT
```

### Estructura de salida

```
~/Code Chat Viewer/              # Raíz de salida (configurable)
├── CCV-Dashboard.html           # Panel interactivo
└── Chats/                       # Archivos HTML generados
    ├── Chat 2026-01-30 ...html  # Chats activos
    ├── Shorts/                  # Chats pequeños inactivos (si está activado)
    └── Archived/                # Chats inactivos antiguos (si está activado)
```

### Ubicación de archivos de Claude Code

Claude Code almacena los logs de chat en formato JSONL en:

- **Windows:** `%USERPROFILE%\.claude\projects\` o `%USERPROFILE%\.claude\chats\`
- **Linux/Mac:** `~/.claude/projects/` o `~/.claude/chats/`

Cada archivo de chat tiene un nombre UUID (ej: `c5f2a3e1-1234-5678-9abc-def012345678.jsonl`)

### Estilo visual

- **Mensajes de usuario**: Azul (`#0066CC`) con fondo azul claro (`#F8FBFF`)
- **Mensajes del asistente**: Verde (`#10893E`) con fondo verde claro (`#FAFFF8`)
- **Resultados de herramientas**: Naranja (`#FF6B00`) con fondo gris (`#F8F8F8`)
- **Bloques de pensamiento**: Fondo blanco con borde gris sutil y sombra
- **Bloques tool use**: Gris oscuro (`#48484A`) con texto claro (`#E8E8E8`)

### Contribuir

Las contribuciones son bienvenidas. Por favor lee [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre nuestro código de conducta y el proceso para enviar pull requests.

### Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

**Requisitos de atribución:**
- Mantener el archivo LICENSE intacto
- Acreditar al autor original: Óscar González Martín
- Enlazar al repositorio original: https://github.com/oskar-gm/code-chat-viewer
- Indicar cualquier modificación realizada

### Autor

**Óscar González Martín**
- Sitio web: [nucleoia.es](https://nucleoia.es)
- Email: oscar@nucleoia.es
- GitHub: [@oskar-gm](https://github.com/oskar-gm)
- LinkedIn: [oscar-gonz](https://linkedin.com/in/oscar-gonz)

### Apoyo

Si este proyecto te resulta útil, por favor:
- Dale una estrella al repositorio
- Reporta bugs vía [Issues](https://github.com/oskar-gm/code-chat-viewer/issues)
- Sugiere mejoras
- Compártelo con otros

### Contacto

Para preguntas, sugerencias o reportar bugs:
- **Email:** oscar@nucleoia.es
- **GitHub Issues:** [Reportar aquí](https://github.com/oskar-gm/code-chat-viewer/issues)

---

**© 2025-2026 Óscar González Martín. All rights reserved under MIT License.**

<!-- SEO: keywords for discoverability -->
<!-- claude code chat viewer, claude code conversation export, JSONL to HTML converter, AI chat visualization, claude code log viewer, export claude code chats, claude code chat to HTML, AI conversation viewer, code assistant chat export, VS Code chat export, claude code skill, anthropic claude chat logs, AI coding assistant history, chat log visualizer, developer chat export tool -->
