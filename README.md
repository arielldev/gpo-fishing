[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/unPZxXAtfb)

# 🎣 GPO Autofish - GUIDE

**💬 Join our Discord server:** https://discord.gg/unPZxXAtfb

## What is this?

This is the **open-source version** of the GPO fishing macro that everyone uses. Unlike the closed-source version that gets flagged as a virus and isn't trustworthy, this version is:

- ✅ **Fully open source** - You can see and verify all the code
- ✅ **No viruses** - Clean, transparent, and safe
- ✅ **Improved** - Better features and reliability
- ✅ **Community-driven** - Open for contributions and review

The original closed-source macro is sketchy and often flagged by antivirus software because you can't verify what it's actually doing. This open-source version solves that problem.

**🛡️ Concerned about safety? Read [IS_IT_A_VIRUS.md](IS_IT_A_VIRUS.md) for more information.**

---

**Features:**

- Automatic fish detection and tracking
- PD controller for smooth, accurate bar control
- Configurable auto-purchase system for bait
- Draggable detection overlay
- Global hotkey support (F1/F2/F3)
- Tunable parameters for optimal performance
- **Modern UI** with CustomTkinter - Clean, professional interface
- **One-click installation** with `install.bat`
- **Silent mode** for long grinding sessions
- **Smart logging system** with performance optimization
- **Discord webhook integration** for progress tracking

## 🚀 Performance Features

### Silent Mode

- Use `run_silent.bat` for long grinding sessions (9+ hours)
- No console window = better performance
- Minimal logging to reduce memory usage

### Smart Logging

- **Verbose Logging**: Toggle detailed console output in GUI
- **Level-based System**: Important events vs debug info
- **Auto-detection**: Silent mode automatically reduces logging

### Long Session Optimization

- Reduced console spam during auto-purchase
- Memory-efficient logging system
- Clean interface without performance impact

## Installation

### 🚀 Easy Installation (Recommended)

1. **Download the repository** as ZIP and extract it
2. **Double-click `install.bat`** - This will:
   - Check if Python is installed
   - Install all required packages automatically
   - Set everything up for you
3. **Run the application:**
   - **With console:** Double-click `run.bat`
   - **Silent mode:** Double-click `run_silent.bat` (completely hidden)

### 🔧 Manual Installation

1. **Install Python** from https://python.org (check "Add to PATH")
2. **Clone or download this repository**
   ```bash
   git clone https://github.com/yourusername/gpo-autofish.git
   cd gpo-autofish
   ```
3. **Install packages**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**
   ```bash
   python src/main.py
   ```

## 🎮 Quick Start Guide

### First Time Setup

1. Run `install.bat` to set everything up
2. Launch with `run.bat` (shows console) or `run_silent.bat` (hidden)
3. Position the detection overlay over your fishing bar
4. Configure settings in the GUI (webhook, auto-purchase, etc.)

### For Long Sessions (9+ hours)

- Use `run_silent.bat` for best performance
- Disable "Verbose Console Logging" in settings
- Enable Discord webhook to track progress remotely

### Hotkeys

- **F1**: Start/Stop fishing
- **F2**: Toggle auto-purchase
- **F3**: Emergency stop
- **Note**: Hotkeys work without admin privileges

### Performance Tips

- Silent mode uses less CPU and memory
- Turn off verbose logging for smoother operation
- Use webhook notifications instead of watching console

---

## 🔧 Troubleshooting

### Installation Issues

- **"Python not found"**: Download from https://python.org and check "Add to PATH"
- **"pip not recognized"**: Reinstall Python with "Add to PATH" checked
- **Permission errors**: Right-click `install.bat` → "Run as administrator"

### Runtime Issues

- **Hotkeys not working**: Try running the macro with administrator
- **Detection not working**: Adjust overlay position and detection settings
- **High CPU usage**: Use silent mode (`run_silent.bat`) and disable verbose logging

### Performance Issues

- **Long sessions lagging**: Use `run_silent.bat` instead of `run.bat`
- **Console spam**: Uncheck "Verbose Console Logging" in GUI
- **Memory usage**: Silent mode automatically reduces memory footprint

---

## 📁 Project Structure

The codebase has been refactored into a clean, modular structure:

```
src/
├── main.py          # Application entry point
├── gui.py           # Main GUI and UI components
├── fishing.py       # Fishing bot logic
├── overlay.py       # Overlay window management
├── webhook.py       # Discord webhook integration
├── updater.py       # Auto-update system
├── settings.py      # Settings management
└── utils.py         # Utility classes
```

This modular structure makes the code:
- ✅ Easier to understand and maintain
- ✅ Better organized by functionality
- ✅ Simpler to extend with new features
- ✅ More testable and debuggable

### Modern UI with CustomTkinter

The application now uses **CustomTkinter** for a modern, professional look:
- Clean, modern interface with smooth animations
- Dark/Light theme support
- Better visual hierarchy and readability
- Professional-looking buttons and controls
- Improved user experience

## 🤝 Contributing

This is an open-source project! Feel free to:

- Report bugs and issues
- Suggest new features
- Submit pull requests
- Join our Discord community

**💬 Discord:** https://discord.gg/unPZxXAtfb
