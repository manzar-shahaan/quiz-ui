# Quiz UI Theme System Plan

## Overview
This document outlines a plan to implement a theme system for the quiz UI application. The themes will be configurable through the GUI launcher and will allow users to customize the appearance of quizzes without modifying core functionality.

## Current Architecture
- **Core Quiz Functionality**: Located in `app/` directory with Flask app, quiz parser, grading system
- **GUI Launcher**: `launcher.py` using customtkinter for file selection and launching
- **Web Interface**: Rendered via Flask templates in the core app

## Theme System Design

### 1. Theme Structure
```
themes/
├── default/
│   ├── css/
│   │   ├── theme-default.css
│   │   └── variables.css
│   ├── assets/
│   │   └── logo.png
│   └── config.json
├── dark/
│   ├── css/
│   │   ├── theme-dark.css
│   │   └── variables.css
│   ├── assets/
│   │   └── logo-dark.png
│   └── config.json
└── custom/
    ├── theme-custom.css
    └── config.json
```

### 2. Theme Configuration
Each theme will have a `config.json`:
```json
{
  "name": "Default Theme",
  "id": "default",
  "version": "1.0.0",
  "author": "Quiz UI Team",
  "description": "Standard light theme for quizzes",
  "variables": {
    "primary-color": "#3498db",
    "secondary-color": "#2ecc71",
    "background-color": "#ffffff",
    "text-color": "#333333"
  },
  "is-default": true
}
```

### 3. Core Functionality
- **Theme Loading**: Core app will load theme CSS dynamically
- **Theme Switching**: GUI launcher will store theme preference
- **Default Themes**: Two built-in themes (light and dark)
- **Custom Themes**: Support for downloading and installing themes

### 4. GUI Launcher Integration
- **Theme Selection Panel**: Add theme selection in launcher settings
- **Theme Preview**: Show preview of theme before applying
- **Theme Installation**: Support for downloading themes from a repository
- **Theme Management**: List installed themes and remove unused ones

### 5. Web Interface Integration
- **CSS Variables**: Use CSS variables for theme customization
- **Dynamic Loading**: Load theme CSS files at runtime
- **Theme Persistence**: Store theme preference in launcher settings
- **Fallback System**: Default theme if custom theme fails to load

### 6. Implementation Steps
1. **Phase 1**: Create theme directory structure and default themes
2. **Phase 2**: Implement theme loading in core Flask app
3. **Phase 3**: Add theme selection in GUI launcher
4. **Phase 4**: Add theme management (install, remove)
5. **Phase 5**: Theme repository integration

### 7. Benefits
- **Modularity**: Themes are separate from core functionality
- **Extensibility**: Easy to add new themes without modifying core code
- **User Experience**: Customizable appearance without changing the quiz experience
- **Maintenance**: Themes can be updated independently
- **Community**: Support for third-party theme contributions

### 8. Technical Considerations
- **Performance**: Theme CSS loading should be efficient
- **Compatibility**: Themes must be compatible with core UI structure
- **Fallback**: Default theme must always be available
- **Security**: Theme installation must be safe from malicious code
- **Versioning**: Themes should support version management

### 9. Default Themes
1. **Default Light Theme**: Standard light appearance
2. **Dark Theme**: Dark color scheme for low-light environments

### 10. Future Enhancements
- **Theme Repository**: Online repository for community themes
- **Theme Sharing**: Share themes with other users
- **Theme Creation Tools**: Tools for creating custom themes
- **Theme Preview**: Real-time preview in launcher