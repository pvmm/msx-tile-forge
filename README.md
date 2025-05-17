# MSX Tile Forge

An integrated Palette, Tile, Supertile and Map Editor for MSX, built with Python and Tkinter.

## Introduction

MSX Tile Forge (v0.0.31) is a desktop application created to assist in the development of graphical assets for MSX2 computers and similar retro systems that utilize tile-based graphics and have specific palette limitations. It provides an integrated environment for designing 16-color palettes, creating 8x8 pixel tiles with row-specific colors, composing supertiles (meta-tiles) from these base tiles with **project-configurable dimensions**, and arranging them into larger game maps. The tool aims to streamline the asset creation workflow for retro game developers and hobbyists.

All project components (palette, tiles, supertiles, map) can be saved and loaded individually or as a complete project, using custom binary file formats designed for ease of use and integration into MSX development pipelines.

## Features

*   **Project Management:** New, Open, Save, Save As for complete projects (bundling palette, tiles, supertiles, and map). Tracks unsaved changes.
*   **Palette Editor:**
    *   Manage a 16-color active MSX2 palette.
    *   Select colors from a 512-color MSX2 visual picker or by direct RGB (0-7 per channel) input.
    *   Save/Load custom `.msxpal` palette files.
    *   Reset to the standard MSX2 default palette.
*   **Tile Editor (8x8 pixels):**
    *   Pixel-level drawing with selectable foreground/background colors.
    *   Assign unique foreground and background palette indices to each of the 8 rows within a tile.
    *   Tileset viewer (up to 256 tiles) with selection and drag-and-drop reordering.
    *   Operations: Add New, Insert, Delete tiles.
    *   Transformations: Flip Horizontal/Vertical, Rotate 90° CW (colors reset), Shift Up/Down/Left/Right.
    *   Copy/Paste functionality for tile patterns and row colors.
    *   "Mark Unused" feature to highlight tiles not referenced in any supertile.
    *   Save/Load tilesets as `.SC4Tiles` binary files.
    *   **ROM Importer:** Import 8x8 1bpp tile data directly from ROM files via a visual browser with fine offset control, live preview, and selection.
*   **Supertile Editor (Project-Configurable Dimensions, e.g., 2x2, 4x4, 8x2 tiles):**
    *   Define supertiles by arranging existing tiles in a grid of **user-defined width and height** (1-32 tiles per dimension, set per project).
    *   Tileset viewer for selecting component tiles.
    *   Supertile selector (up to 256 supertiles) with selection and drag-and-drop reordering.
    *   Operations: Add New, Insert, Delete supertiles.
    *   Transformations: Flip Horizontal/Vertical, Rotate 90° CW (**enabled only for square supertiles**), Shift Up/Down/Left/Right for the supertile definition.
    *   Copy/Paste functionality for supertile definitions (assumes matching dimensions).
    *   "Mark Unused" feature (highlights unused supertiles and unused tiles within this tab's context).
    *   Save/Load supertile definitions as `.SC4Super` binary files (includes supertile dimensions).
*   **Map Editor:**
    *   Construct maps by placing supertiles on a grid (default 32x24, configurable up to 1024x1024 supertiles).
    *   Supertile palette for selecting supertiles to paint.
    *   Zoomable and pannable map canvas.
    *   Optional supertile grid overlay with cyclable colors ('G' key when map tab is active).
    *   "Window View" overlay: Visualizes screen boundaries, configurable size (W:1-32, H:1-27 tiles), draggable and resizable via handles or keyboard (WASD when map tab is active).
    *   Resizable Minimap window displaying the entire map, current map viewport, and window view area. Automatically maintains map aspect ratio.
    *   Map region selection (Shift+Drag) for Copy/Paste operations.
    *   Eyedropper functionality (right-click) to select tiles in the supertile definition or supertiles on the map/palettes.
    *   "ST Coords" display now accurately reflects the current project's supertile dimensions.
    *   Save/Load maps as `.SC4Map` binary files.
*   **General UI & UX:**
    *   Tabbed interface for clear separation of editing modes.
    *   Comprehensive menu system with keyboard accelerators.
    *   Contextual cursors for different editor actions.
    *   Startup splash screen and application icon.
    *   Informative "About" dialog.
    *   Window title indicates project name and modification status.
    *   Improved stability for ROM Importer dialog during resize and scrolling operations.

## How to Run

### System Requirements
*   Python 3.x (Developed and tested with Python 3.12, but should be compatible with recent Python 3 versions).
*   Tkinter (typically included with standard Python installations). No other external libraries are required.

### Running the Application
1.  Ensure Python 3 is installed and accessible from your command line or terminal.
2.  Navigate to the directory containing the `msxtileforge.py` (or your script's name) file.
3.  Execute the script using the Python interpreter:
    ```bash
    python msxtileforge.py
    ```
    (On some systems, you might use `python3 msxtileforge.py`)
4.  **Optional Debug Mode:** To enable detailed console output for troubleshooting:
    ```bash
    python msxtileforge.py --debug
    ```

The application window should appear after a brief splash screen.

## Manual

The application is organized into four main tabs: Palette Editor, Tile Editor, Supertile Editor, and Map Editor.

### Global Operations (Menu Bar)

*   **File Menu:**
    *   **New Project (Ctrl+N):** Clears all current data. Prompts for **new supertile grid dimensions (width/height)**. Then starts a fresh, untitled project. Prompts to save if current project is modified.
    *   **Open Project... (Ctrl+O):** Opens a dialog to select any component file (`.msxpal`, `.SC4Tiles`, `.SC4Super`, `.SC4Map`) of a project. The application will then attempt to load all four associated files based on the selected file's base name (supertile dimensions are loaded from `.SC4Super`). Prompts to save if current project is modified.
    *   **Save Project (Ctrl+S):** Saves all four components of the current project. If the project hasn't been saved before, it behaves like "Save Project As...".
    *   **Save Project As... (Ctrl+Shift+S):** Opens a dialog to specify a base name and location for saving all four project components.
    *   **Open/Save Palette (.msxpal)...:** Loads or saves only the 16-color active palette.
    *   **Open/Save Tileset (.SC4Tiles)...:** Loads or saves only the tile definitions.
    *   **Import Tiles from ROM...:** Opens a dialog to select a ROM file and import 8x8 1bpp tile data from it into the current tileset.
    *   **Open/Save Supertiles (.SC4Super)...:** Loads or saves only the supertile definitions (including their grid dimensions).
    *   **Open/Save Map (.SC4Map)...:** Loads or saves only the map data.
    *   **Exit (Ctrl+Q):** Closes the application. Prompts to save if current project is modified.
*   **Edit Menu:**
    *   **Copy (Ctrl+C):** Context-sensitive. Copies the currently selected Tile, Supertile, or selected Map Region.
    *   **Paste (Ctrl+V):** Context-sensitive. Pastes the copied data onto the current Tile, Supertile, or at the mouse cursor position on the Map.
    *   **Clear Current Tile/Supertile/Map:** Resets the currently selected item or the entire map to a default state.
    *   **Set Tileset Size...:** Allows changing the total number of tiles in the tileset (1-256).
    *   **Set Supertile Count...:** Allows changing the total number of supertiles (1-256).
    *   **Set Map Dimensions...:** Allows changing the width and height of the map in supertiles (1-1024 per dimension).
*   **View Menu:**
    *   **Show/Hide Minimap (Ctrl+M):** Toggles the visibility of the resizable Minimap window.
*   **Help Menu:**
    *   **About...:** Displays application information, version, and author.

### 1. Palette Editor Tab

(Content mostly unchanged, assumed correct)
This tab allows you to define the 16-color active palette used throughout the application.
*   **Active Palette (16 colors):** Click a slot to select it.
*   **Selected Slot Info:** Displays index, color preview, Hex RGB, and MSX2 RGB (0-7).
*   **Set Color (RGB 0-7):** Input fields to apply RGB values to the selected slot.
*   **MSX2 512 Color Picker:** Click a color to apply it to the selected active palette slot.
*   **Reset to MSX2 Default:** Resets to the standard MSX2 palette.

### 2. Tile Editor Tab

(Content mostly unchanged, added ROM Importer context)
This tab is for creating and modifying individual 8x8 pixel tiles.
*   **Left Pane:**
    *   **Tile Editor Canvas:** Draw (LMB) / Erase (RMB) pixels.
    *   **Row Colors (FG/BG Buttons):** Set row-specific foreground/background colors.
    *   **Transform Controls:** Flip H/V, Rotate (resets row colors), Shift Up/Down/Left/Right.
    *   **Mark Unused Button:** Highlights tiles not used in any supertile.
*   **Right Pane:**
    *   **Color Selector Palette:** Select active drawing color from the 16-color active palette.
    *   **Tileset Viewer:** Displays all tiles. Click to select for editing. Drag-and-drop to reorder.
    *   **Tile Management Buttons:** Add New, Insert, Delete tiles.
*   See `File -> Import Tiles from ROM...` to add tiles from external binary files.

### 3. Supertile Editor Tab

This tab is for creating composite "supertiles" from the existing base tiles. The **dimensions of the supertile grid (e.g., 4x4, 2x8, etc.) are defined per project**.
*   **Left Pane:**
    *   **Supertile Definition Canvas:**
        *   A grid of `Width x Height` (defined by project settings) representing the supertile.
        *   **Left-Click a cell:** Places the tile currently selected in the "Tileset" viewer (right pane) into that cell.
        *   **Right-Click a cell:** Selects the tile in that cell, making it active in the "Tileset" viewer.
    *   **Info Labels:** Displays editing supertile index and selected tile for placing.
    *   **Transform Controls:**
        *   **Flip H/V:** Flip the supertile definition.
        *   **Rotate:** Rotate 90° CW (**only enabled if the supertile grid is square**).
        *   **Shift Up/Down/Left/Right:** Shift tiles within the definition.
    *   **Mark Unused Button:** Highlights unused tiles (in this tab's viewer) and unused supertiles (not on map).
*   **Right Pane:**
    *   **Tileset Viewer:** Selects tiles for placing. Drag-and-drop reorders tileset.
    *   **Supertile Selector:** Selects supertile for editing. Drag-and-drop reorders supertiles.
    *   **Supertile Management Buttons:** Add New, Insert, Delete supertiles.

### 4. Map Editor Tab

(Content mostly unchanged, noted ST Coords fix)
This tab is for arranging supertiles to create a game map.
*   **Left Pane (Main Area):**
    *   **Controls Bar:** Map Size, Zoom, **ST Coords (now respects project supertile dimensions)**, Window View toggle and size, Supertile Grid toggle.
    *   **Map Canvas:**
        *   Paint with selected supertile (LMB).
        *   Eyedrop supertile (RMB).
        *   Pan (Ctrl+LMB Drag or MMB Drag).
        *   Select Region (Shift+LMB Drag).
        *   Zoom (Ctrl+MouseWheel).
        *   Nudge Window View (WASD with Window View active).
        *   Clear Selection/Clipboard (Escape).
    *   **Window View Overlay:** Draggable/resizable screen representation.
    *   **Paste Preview:** Shows where map clipboard data will paste.
*   **Right Pane:**
    *   **Supertile Palette:** Selects supertile for painting. Drag-and-drop reorders supertiles.
    *   **Selected Supertile Label.**
*   **Minimap Window (Ctrl+M):** Overview of map, viewport, and window view.

## Technical Description of Generated Files

All files are custom binary formats. Multi-byte integers are generally stored in Big-Endian format unless specified.

### 1. Palette File (`.msxpal`)
(Content unchanged)
*   **Purpose:** Stores the 16 active palette colors.
*   **Format:** Total Size: 48 bytes. 16 entries, each 3 bytes (R,G,B as 0-7).

### 2. Tileset File (`.SC4Tiles`)
(Content unchanged)
*   **Purpose:** Stores 8x8 tile pattern data and row color attributes.
*   **Format:**
    *   Header: `num_tiles_in_set` (1 byte).
    *   Tile Data (repeated): 8 bytes for pattern (1 bit/pixel per row), 8 bytes for color attributes (4 bits FG index, 4 bits BG index per row).

### 3. Supertile Definition File (`.SC4Super`)
*   **Purpose:** Stores the definitions of supertiles (which base tiles make up each supertile) **and their dimensions**.
*   **Format:**
    *   **Header:**
        *   `num_supertiles` (1 byte): Number of supertiles defined (0-255; if 256, this byte is 0, but practically max is 255 if 0 means 256).
        *   `supertile_grid_width` (1 byte): Number of base tiles horizontally in each supertile definition (1-32).
        *   `supertile_grid_height` (1 byte): Number of base tiles vertically in each supertile definition (1-32).
    *   **Supertile Definition Data (repeated `num_supertiles` times):**
        *   Each supertile definition consists of `supertile_grid_width * supertile_grid_height` bytes.
        *   Each byte is the index (0-255) of a tile from the `.SC4Tiles` file.
        *   Data is stored row by row for the `width x height` grid of tiles within the supertile.

### 4. Map File (`.SC4Map`)
(Content unchanged)
*   **Purpose:** Stores the map layout, referencing supertile indices.
*   **Format:**
    *   Header: `map_width` (2 bytes, Unsigned Short, Big-Endian), `map_height` (2 bytes, Unsigned Short, Big-Endian).
    *   Map Data: Sequence of `map_width * map_height` bytes, each being a supertile index (0-255). Stored row by row.

## Contributing

Contributions, bug reports, and feature suggestions are welcome! Please feel free to open an issue or submit a pull request on the GitHub repository.

## License

This project is licensed under the **GNU Affero General Public License v3.0**.

A copy of the license should be included with the software (e.g., in a `LICENSE` file). The full text can also be found at: [https://www.gnu.org/licenses/agpl-3.0.en.html](https://www.gnu.org/licenses/agpl-3.0.en.html)