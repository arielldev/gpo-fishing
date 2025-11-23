# GPO Autofish - Source Code Structure

This directory contains the refactored source code for GPO Autofish, organized into modular components.

## File Structure

- `main.py` - Entry point for the application
- `gui.py` - Main GUI class and UI components
- `fishing.py` - Fishing bot logic and auto-purchase system
- `overlay.py` - Overlay window management
- `webhook.py` - Discord webhook notifications
- `updater.py` - Auto-update functionality
- `settings.py` - Settings management (save/load/presets)
- `utils.py` - Utility classes (ToolTip, CollapsibleFrame)

## Running the Application

From the project root directory:

**Development mode (with console):**
```
python src/main.py
```
or use the batch file:
```
run_dev.bat
```

**Silent mode (no console):**
```
pythonw src/main.py
```
or use the batch file:
```
run.bat
```

## Building Executable

Use the provided batch file:
```
CompileCommand.bat
```

This will create a standalone executable in the `dist/` folder.
