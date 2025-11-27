# Theme Toggle Implementation

## Overview
Add dark/light theme toggle to existing glass/acrylic UI design.

## Current State
- ✅ Dark theme already implemented in `applyGlassTheme()`
- Located in: `gui/main_gui.py` lines ~165-400
- Modern glass/acrylic/liquid design

## Implementation

### 1. Add Light Theme Method

```python
def applyLightTheme(self):
    """Apply light theme - modern glass/acrylic design"""
    self.setStyleSheet("""
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #f5f5f5, stop:0.5 #ffffff, stop:1 #e8e8e8);
        }
        QGroupBox, QTabWidget::pane {
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 12px;
        }
        
        QGroupBox {
            font-weight: bold;
            color: #2c3e50;
            margin-top: 12px;
            padding-top: 8px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 10px;
            background-color: rgba(100, 181, 246, 0.15);
            border-radius: 6px;
            color: #1976d2;
        }
        
        /* Buttons - Glass effect */
        QPushButton {
            background-color: rgba(100, 181, 246, 0.15);
            border: 1px solid rgba(100, 181, 246, 0.3);
            border-radius: 8px;
            color: #2c3e50;
            padding: 6px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: rgba(100, 181, 246, 0.25);
            border: 1px solid rgba(100, 181, 246, 0.5);
        }
        
        QPushButton:pressed {
            background-color: rgba(100, 181, 246, 0.4);
        }
        
        QPushButton:disabled {
            background-color: rgba(128, 128, 128, 0.1);
            border: 1px solid rgba(128, 128, 128, 0.2);
            color: #999999;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid rgba(0, 0, 0, 0.15);
            border-radius: 10px;
            background-color: rgba(255, 255, 255, 0.5);
        }
        
        QTabBar::tab {
            background-color: rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(0, 0, 0, 0.15);
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 20px;
            color: #555555;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: rgba(100, 181, 246, 0.2);
            border: 1px solid rgba(100, 181, 246, 0.4);
            color: #1976d2;
            font-weight: bold;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: rgba(0, 0, 0, 0.08);
        }
        
        /* Input fields */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            padding: 4px 8px;
            color: #2c3e50;
        }
        
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
        QDoubleSpinBox:focus, QComboBox:focus {
            border: 1px solid rgba(100, 181, 246, 0.6);
            background-color: rgba(255, 255, 255, 0.95);
        }
        
        QComboBox::drop-down {
            border: none;
            background-color: rgba(100, 181, 246, 0.15);
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #1976d2;
            margin-right: 6px;
        }
        
        QComboBox QAbstractItemView {
            background-color: rgba(255, 255, 255, 0.98);
            border: 1px solid rgba(100, 181, 246, 0.4);
            border-radius: 6px;
            selection-background-color: rgba(100, 181, 246, 0.3);
            color: #2c3e50;
        }
        
        /* Sliders */
        QSlider::groove:horizontal {
            height: 6px;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #64b5f6, stop:1 #42a5f5);
            border: 1px solid rgba(0, 0, 0, 0.2);
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #81c784, stop:1 #66bb6a);
        }
        
        /* Checkboxes */
        QCheckBox {
            color: #2c3e50;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(100, 181, 246, 0.5);
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.8);
        }
        
        QCheckBox::indicator:checked {
            background-color: rgba(100, 181, 246, 0.3);
            border: 2px solid rgba(100, 181, 246, 0.8);
        }
        
        QCheckBox::indicator:hover {
            border: 2px solid rgba(100, 181, 246, 0.7);
            background-color: rgba(255, 255, 255, 0.95);
        }
        
        /* Labels */
        QLabel {
            color: #2c3e50;
        }
        
        /* ScrollBars */
        QScrollBar:vertical {
            background: rgba(0, 0, 0, 0.05);
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: rgba(100, 181, 246, 0.4);
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: rgba(100, 181, 246, 0.6);
        }
        
        QScrollBar:horizontal {
            background: rgba(0, 0, 0, 0.05);
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background: rgba(100, 181, 246, 0.4);
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background: rgba(100, 181, 246, 0.6);
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: rgba(255, 255, 255, 0.7);
            color: #2c3e50;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        QMenuBar::item:selected {
            background-color: rgba(100, 181, 246, 0.2);
            border-radius: 4px;
        }
        
        QMenu {
            background-color: rgba(255, 255, 255, 0.98);
            border: 1px solid rgba(100, 181, 246, 0.3);
            border-radius: 8px;
            color: #2c3e50;
        }
        
        QMenu::item:selected {
            background-color: rgba(100, 181, 246, 0.3);
            border-radius: 4px;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: rgba(255, 255, 255, 0.7);
            color: #555555;
            border-top: 1px solid rgba(0, 0, 0, 0.1);
        }
        
        /* Splitter */
        QSplitter::handle {
            background-color: rgba(100, 181, 246, 0.2);
            border-radius: 2px;
        }
        
        QSplitter::handle:hover {
            background-color: rgba(100, 181, 246, 0.4);
        }
    """)
```

### 2. Add Theme Toggle Menu

In `createMenuBar()` method, add to View menu:

```python
# View Menu (existing)
view_menu = menubar.addMenu('&View')

# ... existing view menu items ...

view_menu.addSeparator()

# Theme submenu
theme_menu = view_menu.addMenu('&Theme')

self.theme_group = QActionGroup(self)

self.dark_theme_action = QAction('&Dark Theme', self)
self.dark_theme_action.setCheckable(True)
self.dark_theme_action.setChecked(True)  # Default
self.dark_theme_action.triggered.connect(self.setDarkTheme)
self.theme_group.addAction(self.dark_theme_action)
theme_menu.addAction(self.dark_theme_action)

self.light_theme_action = QAction('&Light Theme', self)
self.light_theme_action.setCheckable(True)
self.light_theme_action.triggered.connect(self.setLightTheme)
self.theme_group.addAction(self.light_theme_action)
theme_menu.addAction(self.light_theme_action)
```

### 3. Add Theme Switch Methods

```python
@Slot()
def setDarkTheme(self):
    """Switch to dark theme"""
    self.applyGlassTheme()  # Existing dark theme method
    self.current_theme = 'dark'
    self.saveThemePreference()
    self.log("✓ Switched to dark theme")
    self.status_bar.showMessage("Dark theme applied")

@Slot()
def setLightTheme(self):
    """Switch to light theme"""
    self.applyLightTheme()  # New light theme method
    self.current_theme = 'light'
    self.saveThemePreference()
    self.log("✓ Switched to light theme")
    self.status_bar.showMessage("Light theme applied")
```

### 4. Save/Load Theme Preference

```python
def saveThemePreference(self):
    """Save theme choice to config file"""
    config_path = Path("config/ui_preferences.yaml")
    config_path.parent.mkdir(exist_ok=True)
    
    prefs = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            prefs = yaml.safe_load(f) or {}
    
    prefs['theme'] = self.current_theme
    
    with open(config_path, 'w') as f:
        yaml.dump(prefs, f)

def loadThemePreference(self):
    """Load saved theme preference"""
    config_path = Path("config/ui_preferences.yaml")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            prefs = yaml.safe_load(f) or {}
        
        theme = prefs.get('theme', 'dark')
        self.current_theme = theme
        
        if theme == 'light':
            self.applyLightTheme()
            self.light_theme_action.setChecked(True)
        else:
            self.applyGlassTheme()
            self.dark_theme_action.setChecked(True)
    else:
        # Default to dark theme
        self.current_theme = 'dark'
        self.applyGlassTheme()
```

### 5. Initialize Theme on Startup

In `__init__()` method, add after `self.initUI()`:

```python
def __init__(self):
    super().__init__()
    
    # ... existing init code ...
    
    self.initUI()
    
    # Load theme preference AFTER UI is created
    self.loadThemePreference()
    
    self.loadConfig()
    # ... rest of init ...
```

## Canvas Background Adjustment

The canvas widget also needs theme awareness:

**In `gui/widgets/canvas_widget.py`:**

```python
def setTheme(self, theme='dark'):
    """Set canvas background color based on theme"""
    if theme == 'dark':
        self.canvas_color = QColor(64, 64, 64)  # Dark gray
    else:
        self.canvas_color = QColor(200, 200, 200)  # Light gray
    
    self.update()
```

**Connect from main window:**

```python
@Slot()
def setDarkTheme(self):
    self.applyGlassTheme()
    self.current_theme = 'dark'
    
    # Update canvas background
    if hasattr(self, 'layer_canvas') and hasattr(self.layer_canvas, 'canvas'):
        self.layer_canvas.canvas.setTheme('dark')
    
    self.saveThemePreference()
    # ...

@Slot()
def setLightTheme(self):
    self.applyLightTheme()
    self.current_theme = 'light'
    
    # Update canvas background
    if hasattr(self, 'layer_canvas') and hasattr(self.layer_canvas, 'canvas'):
        self.layer_canvas.canvas.setTheme('light')
    
    self.saveThemePreference()
    # ...
```

## Testing

Test theme toggle with:
1. Switch dark → light → dark
2. Restart app (should remember last choice)
3. Check all UI elements render correctly
4. Verify canvas background changes
5. Test with different layer opacities

## File Changes Summary

- `gui/main_gui.py`:
  - Add `applyLightTheme()` method (~150 lines)
  - Modify `createMenuBar()` to add theme menu (~20 lines)
  - Add `setDarkTheme()` / `setLightTheme()` methods (~20 lines)
  - Add `saveThemePreference()` / `loadThemePreference()` (~40 lines)
  - Call `loadThemePreference()` in `__init__()` (~1 line)

- `gui/widgets/canvas_widget.py`:
  - Add `setTheme()` method (~10 lines)

- `config/ui_preferences.yaml`:
  - New file (auto-created)

**Total: ~240 lines of code**

## Estimated Time

**1-2 hours** for complete implementation and testing.

## Preview

**Dark Theme (Current):**
- Background: Dark blue gradient (#1a1a2e → #0f3460)
- Text: Light gray (#e0e0e0)
- Accents: Blue (#64b5f6)
- Canvas: Dark gray (#404040)

**Light Theme (New):**
- Background: White gradient (#f5f5f5 → #e8e8e8)
- Text: Dark blue-gray (#2c3e50)
- Accents: Blue (#1976d2)
- Canvas: Light gray (#c8c8c8)

Both maintain the modern glass/acrylic aesthetic! ✨
