# Copilot Instructions for 3D_Part_01

## Project Overview
This codebase is a Python-based 3D simulation/game engine. It is organized as a set of modules handling rendering, input, game logic, and data management. The architecture is modular, with each file typically representing a major subsystem.

## Key Components
- **main.py**: Entry point; initializes the game loop and orchestrates subsystems.
- **ogl_render.py**: Handles OpenGL-based rendering. Central for all visual output.
- **input.py**: Manages user input (keyboard, mouse, etc.).
- **object.py**: Defines in-game objects/entities and their properties.
- **game_events.py**: Manages game event logic and triggers.
- **market.py, system_data.py, status.py**: Handle game state, economy, and system data.
- **docking_views/**, **wireframes.py**: Specialized rendering and UI components.
- **saves/**: Stores user save files (JSON format).

## Developer Workflows
- **Run the game**: Execute `main.py` directly (e.g., `python main.py`).
- **Debugging**: Use VS Code's Python debugger. The project is structured for step-through debugging.
- **No formal test suite**: Testing is manual via gameplay.

## Project Conventions
- Each major system is a separate Python file; cross-module imports are common.
- Game state is often passed as dictionaries or custom classes.
- Rendering logic is centralized in `ogl_render.py` and `ogl_cockpit.py`.
- Data files (e.g., saves, fonts) are stored in dedicated folders.
- Sound assets are in `sound/` and referenced by `sounds.py`.

## Integration & Dependencies
- Relies on OpenGL (likely via PyOpenGL) for rendering.
- No external build system or requirements.txt detected; dependencies may need to be installed manually.
- Save/load uses JSON files in `saves/`.

## Patterns & Examples
- To add a new game object: extend `object.py` and update relevant logic in `main.py` and `ogl_render.py`.
- To add a new screen/UI: create a new module or update `info_screens.py` and link it in `main.py`.
- For new input handling: update `input.py` and ensure integration in the main loop.

## References
- See `main.py` for the game loop and subsystem initialization.
- See `ogl_render.py` for rendering pipeline and OpenGL setup.
- See `object.py` for entity definitions and game object logic.

---

**Edit this file to update project-specific AI agent instructions.**
