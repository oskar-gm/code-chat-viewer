# Contributing to Claude Code Visualizer

**[English](#english)** | **[Español](#español)**

---

<a name="english"></a>
## 🇬🇧 English

First off, thank you for considering contributing to Claude Code Visualizer! It's people like you that make this tool better for everyone.

### Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Style Guidelines](#style-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

### Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/cl-code-visualizer.git
   cd cl-code-visualizer
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### How Can I Contribute?

#### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Sample JSON file** (if applicable)
- **Screenshots** of the HTML output (if applicable)
- **Python version** and **operating system**

**Example:**
```markdown
**Bug:** Tool results not collapsing

**Steps to reproduce:**
1. Run visualizer.py with sample.json
2. Open output.html in browser
3. Click on tool result header

**Expected:** Tool result content should collapse
**Actual:** Nothing happens

**Environment:**
- Python: 3.9.1
- OS: Windows 11
- Browser: Chrome 120
```

#### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** - why is this enhancement useful?
- **Expected behavior** - what should happen?
- **Alternative solutions** you've considered
- **Examples** from similar projects (if applicable)

#### Code Contributions

1. **Check existing issues** - someone might already be working on it
2. **Discuss major changes** - open an issue first for significant changes
3. **Write tests** - ensure your code works as expected
4. **Follow style guidelines** - maintain code consistency
5. **Update documentation** - keep README.md and comments current

### Style Guidelines

#### Python Code Style

- Follow **PEP 8** style guide
- Use **4 spaces** for indentation (no tabs)
- Maximum line length: **100 characters**
- Use **meaningful variable names**
- Add **docstrings** to functions and classes
- Include **type hints** where appropriate

**Example:**
```python
def format_timestamp(timestamp_str: str) -> str:
    """
    Format ISO timestamp to HH:MM AM/PM format.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        Formatted time string (e.g., "2:45 PM")
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%I:%M %p').lstrip('0')
    except Exception:
        return ""
```

#### HTML/CSS Style

- Use **semantic HTML** elements
- Keep CSS in the `<style>` section organized
- Comment complex CSS rules
- Maintain **responsive design** principles
- Test in multiple browsers

#### Documentation Style

- Use clear, concise language
- Include **code examples**
- Add **screenshots** when helpful
- Keep bilingual (English + Spanish)
- Update both languages simultaneously

### Commit Guidelines

Write clear, descriptive commit messages following this format:

```
type(scope): brief description

Detailed description (if needed)

- Additional details
- Related issues: #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(parser): add support for snapshot messages

- Parse conversation snapshot events
- Display snapshot metadata
- Update HTML template

Closes #42
```

```
fix(html): resolve tool result collapse issue

The toggle button was not triggering due to event
listener not being attached. Fixed by ensuring
DOMContentLoaded event fires before attaching.

Fixes #15
```

### Pull Request Process

1. **Update documentation** - reflect your changes in README.md if needed
2. **Test thoroughly** - ensure all functionality works
3. **Keep commits clean** - rebase/squash if needed
4. **Write clear PR description**:
   ```markdown
   ## Description
   Brief description of changes
   
   ## Motivation
   Why these changes are needed
   
   ## Changes
   - List of specific changes
   - Include any breaking changes
   
   ## Testing
   How you tested these changes
   
   ## Screenshots
   (if applicable)
   
   ## Related Issues
   Closes #123
   ```

5. **Wait for review** - maintainers will review your PR
6. **Address feedback** - make requested changes
7. **Merge** - once approved, your PR will be merged

### Testing

Before submitting your PR, please test:

1. **Basic functionality:**
   ```bash
   python3 scripts/visualizer.py test.json output.html
   ```

2. **Different message types:**
   - User messages
   - Assistant messages
   - Tool uses
   - Tool results
   - Thinking blocks

3. **Edge cases:**
   - Empty JSON files
   - Malformed JSON lines
   - Very long messages
   - Special characters

4. **Browser compatibility:**
   - Chrome
   - Firefox
   - Safari
   - Edge

### Questions?

Feel free to ask questions:
- Open an issue with the `question` label
- Email: oscar@nucleoia.es
- Check existing discussions

### Attribution

Contributors will be acknowledged in the project. Your contributions are appreciated!

### License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

<a name="español"></a>
## 🇪🇸 Español

Antes que nada, ¡gracias por considerar contribuir a Claude Code Visualizer! Son personas como tú las que hacen de esta herramienta algo mejor para todos.

### Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Primeros Pasos](#primeros-pasos)
- [¿Cómo Puedo Contribuir?](#cómo-puedo-contribuir)
- [Guías de Estilo](#guías-de-estilo)
- [Guías de Commits](#guías-de-commits)
- [Proceso de Pull Request](#proceso-de-pull-request)

### Código de Conducta

Este proyecto y todos los que participan en él se rigen por nuestro [Código de Conducta](CODE_OF_CONDUCT.md). Al participar, se espera que respetes este código.

### Primeros Pasos

1. **Haz fork del repositorio** en GitHub
2. **Clona tu fork** localmente:
   ```bash
   git clone https://github.com/TU-USUARIO/cl-code-visualizer.git
   cd cl-code-visualizer
   ```
3. **Crea una rama** para tus cambios:
   ```bash
   git checkout -b feature/nombre-de-tu-funcionalidad
   ```

### ¿Cómo Puedo Contribuir?

#### Reportar Bugs

Antes de crear un reporte de bug, revisa los issues existentes para evitar duplicados. Al crear un reporte de bug, incluye:

- **Título y descripción claros**
- **Pasos para reproducir** el problema
- **Comportamiento esperado** vs **comportamiento real**
- **Archivo JSON de ejemplo** (si aplica)
- **Capturas de pantalla** del HTML generado (si aplica)
- **Versión de Python** y **sistema operativo**

**Ejemplo:**
```markdown
**Bug:** Los resultados de herramientas no se colapsan

**Pasos para reproducir:**
1. Ejecutar visualizer.py con sample.json
2. Abrir output.html en navegador
3. Hacer click en header de tool result

**Esperado:** El contenido del tool result debería colapsarse
**Real:** No pasa nada

**Entorno:**
- Python: 3.9.1
- SO: Windows 11
- Navegador: Chrome 120
```

#### Sugerir Mejoras

Las sugerencias de mejoras se rastrean como issues de GitHub. Al crear una sugerencia de mejora, incluye:

- **Título y descripción claros**
- **Caso de uso** - ¿por qué es útil esta mejora?
- **Comportamiento esperado** - ¿qué debería pasar?
- **Soluciones alternativas** que hayas considerado
- **Ejemplos** de proyectos similares (si aplica)

#### Contribuciones de Código

1. **Revisa issues existentes** - alguien podría estar trabajando en ello
2. **Discute cambios importantes** - abre un issue primero para cambios significativos
3. **Escribe tests** - asegura que tu código funciona como se espera
4. **Sigue las guías de estilo** - mantén consistencia en el código
5. **Actualiza documentación** - mantén README.md y comentarios actualizados

### Guías de Estilo

#### Estilo de Código Python

- Sigue la guía de estilo **PEP 8**
- Usa **4 espacios** para indentación (sin tabs)
- Longitud máxima de línea: **100 caracteres**
- Usa **nombres de variables significativos**
- Añade **docstrings** a funciones y clases
- Incluye **type hints** donde sea apropiado

**Ejemplo:**
```python
def format_timestamp(timestamp_str: str) -> str:
    """
    Formatea timestamp ISO a formato HH:MM AM/PM.
    
    Args:
        timestamp_str: String de timestamp en formato ISO
        
    Returns:
        String de tiempo formateado (ej: "2:45 PM")
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%I:%M %p').lstrip('0')
    except Exception:
        return ""
```

#### Estilo HTML/CSS

- Usa elementos HTML **semánticos**
- Mantén el CSS en la sección `<style>` organizado
- Comenta reglas CSS complejas
- Mantén principios de **diseño responsive**
- Prueba en múltiples navegadores

#### Estilo de Documentación

- Usa lenguaje claro y conciso
- Incluye **ejemplos de código**
- Añade **capturas de pantalla** cuando sean útiles
- Mantén bilingüe (Inglés + Español)
- Actualiza ambos idiomas simultáneamente

### Guías de Commits

Escribe mensajes de commit claros y descriptivos siguiendo este formato:

```
tipo(alcance): descripción breve

Descripción detallada (si es necesario)

- Detalles adicionales
- Issues relacionados: #123
```

**Tipos:**
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Cambios de estilo de código (formato, etc.)
- `refactor`: Refactorización de código
- `test`: Añadir o actualizar tests
- `chore`: Tareas de mantenimiento

**Ejemplos:**
```
feat(parser): añadir soporte para mensajes snapshot

- Parsear eventos de snapshot de conversación
- Mostrar metadata de snapshot
- Actualizar plantilla HTML

Closes #42
```

```
fix(html): resolver problema de colapso de tool results

El botón de toggle no estaba activando debido a que
el event listener no se estaba adjuntando. Arreglado
asegurando que el evento DOMContentLoaded se dispare
antes de adjuntar.

Fixes #15
```

### Proceso de Pull Request

1. **Actualiza documentación** - refleja tus cambios en README.md si es necesario
2. **Prueba exhaustivamente** - asegura que toda la funcionalidad funciona
3. **Mantén commits limpios** - rebase/squash si es necesario
4. **Escribe descripción clara de PR**:
   ```markdown
   ## Descripción
   Breve descripción de los cambios
   
   ## Motivación
   Por qué estos cambios son necesarios
   
   ## Cambios
   - Lista de cambios específicos
   - Incluye cualquier cambio breaking
   
   ## Pruebas
   Cómo probaste estos cambios
   
   ## Capturas de Pantalla
   (si aplica)
   
   ## Issues Relacionados
   Closes #123
   ```

5. **Espera revisión** - los mantenedores revisarán tu PR
6. **Atiende feedback** - realiza los cambios solicitados
7. **Merge** - una vez aprobado, tu PR será fusionado

### Pruebas

Antes de enviar tu PR, por favor prueba:

1. **Funcionalidad básica:**
   ```bash
   python3 scripts/visualizer.py test.json output.html
   ```

2. **Diferentes tipos de mensajes:**
   - Mensajes de usuario
   - Mensajes del asistente
   - Tool uses
   - Tool results
   - Bloques de pensamiento

3. **Casos extremos:**
   - Archivos JSON vacíos
   - Líneas JSON malformadas
   - Mensajes muy largos
   - Caracteres especiales

4. **Compatibilidad de navegadores:**
   - Chrome
   - Firefox
   - Safari
   - Edge

### ¿Preguntas?

No dudes en hacer preguntas:
- Abre un issue con la etiqueta `question`
- Email: oscar@nucleoia.es
- Revisa discusiones existentes

### Atribución

Los contribuidores serán reconocidos en el proyecto. ¡Tus contribuciones son apreciadas!

### Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la Licencia MIT.

---

**© 2025 Óscar González Martín. Thank you for contributing!**
