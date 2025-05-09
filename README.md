# MSX Tile Forge

An integrated Palette, Tile, Supertile and Map Editor for MSX, built with Python and Tkinter.

## Introduction

MSX Tile Forge (v0.0.29) is a desktop application created to assist in the development of graphical assets for MSX2 computers and similar retro systems that utilize tile-based graphics and have specific palette limitations. It provides an integrated environment for designing 16-color palettes, creating 8x8 pixel tiles with row-specific colors, composing 4x4 supertiles from these tiles, and arranging them into larger game maps. The tool aims to streamline the asset creation workflow for retro game developers and hobbyists.

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
*   **Supertile Editor (4x4 tiles):**
    *   Define supertiles by arranging existing tiles in a 4x4 grid.
    *   Tileset viewer for selecting component tiles.
    *   Supertile selector (up to 256 supertiles) with selection and drag-and-drop reordering.
    *   Operations: Add New, Insert, Delete supertiles.
    *   Transformations: Flip Horizontal/Vertical, Rotate 90° CW, Shift Up/Down/Left/Right for the supertile definition.
    *   Copy/Paste functionality for supertile definitions.
    *   "Mark Unused" feature (highlights unused supertiles and unused tiles within this tab's context).
    *   Save/Load supertile definitions as `.SC4Super` binary files.
*   **Map Editor:**
    *   Construct maps by placing supertiles on a grid (default 32x24, configurable up to 1024x1024 supertiles).
    *   Supertile palette for selecting supertiles to paint.
    *   Zoomable and pannable map canvas.
    *   Optional supertile grid overlay with cyclable colors ('G' key when map tab is active).
    *   "Window View" overlay: Visualizes screen boundaries, configurable size (W:1-32, H:1-27 tiles), draggable and resizable via handles or keyboard (WASD when map tab is active).
    *   Resizable Minimap window displaying the entire map, current map viewport, and window view area.
    *   Map region selection (Shift+Drag) for Copy/Paste operations.
    *   Eyedropper functionality (right-click) to select tiles in the supertile definition or supertiles on the map/palettes.
    *   Save/Load maps as `.SC4Map` binary files.
*   **General UI & UX:**
    *   Tabbed interface for clear separation of editing modes.
    *   Comprehensive menu system with keyboard accelerators.
    *   Contextual cursors for different editor actions.
    *   Startup splash screen and application icon.
    *   Informative "About" dialog.
    *   Window title indicates project name and modification status.

## How to Run

### System Requirements
*   Python 3.x (Developed and tested with Python 3.12, but should be compatible with recent Python 3 versions).
*   Tkinter (typically included with standard Python installations). No other external libraries are required.

### Running the Application
1.  Ensure Python 3 is installed and accessible from your command line or terminal.
2.  Navigate to the directory containing the `msxtileforge.py` (or your script's name) file.
3.  Execute the script using the Python interpreter:
    ```
    python msxtileforge.py
    ```
    (On some systems, you might use `python3 msxtileforge.py`)

The application window should appear after a brief splash screen.

## Manual

The application is organized into four main tabs: Palette Editor, Tile Editor, Supertile Editor, and Map Editor.

### Global Operations (Menu Bar)

*   **File Menu:**
    *   **New Project (Ctrl+N):** Clears all current data (palette, tiles, supertiles, map) and starts a fresh, untitled project. Prompts to save if current project is modified.
    *   **Open Project... (Ctrl+O):** Opens a dialog to select any component file (`.msxpal`, `.SC4Tiles`, `.SC4Super`, `.SC4Map`) of a project. The application will then attempt to load all four associated files based on the selected file's base name. Prompts to save if current project is modified.
    *   **Save Project (Ctrl+S):** Saves all four components of the current project. If the project hasn't been saved before, it behaves like "Save Project As...".
    *   **Save Project As... (Ctrl+Shift+S):** Opens a dialog to specify a base name and location for saving all four project components.
    *   **Open/Save Palette (.msxpal)...:** Loads or saves only the 16-color active palette.
    *   **Open/Save Tileset (.SC4Tiles)...:** Loads or saves only the tile definitions (patterns and row colors).
    *   **Open/Save Supertiles (.SC4Super)...:** Loads or saves only the supertile definitions.
    *   **Open/Save Map (.SC4Map)...:** Loads or saves only the map data.
    *   **Exit (Ctrl+Q):** Closes the application. Prompts to save if current project is modified.
*   **Edit Menu:**
    *   **Copy (Ctrl+C):** Context-sensitive. Copies the currently selected Tile (Tile Editor), Supertile (Supertile Editor), or selected Map Region (Map Editor).
    *   **Paste (Ctrl+V):** Context-sensitive. Pastes the copied data onto the current Tile, Supertile, or at the mouse cursor position on the Map.
    *   **Clear Current Tile/Supertile/Map:** Resets the currently selected item or the entire map to a default (blank/zero) state.
    *   **Set Tileset Size...:** Allows changing the total number of tiles in the tileset (1-256).
    *   **Set Supertile Count...:** Allows changing the total number of supertiles (1-256).
    *   **Set Map Dimensions...:** Allows changing the width and height of the map in supertiles (1-1024 per dimension).
*   **View Menu:**
    *   **Show/Hide Minimap (Ctrl+M):** Toggles the visibility of the resizable Minimap window for the Map Editor.
*   **Help Menu:**
    *   **About...:** Displays application information, version, and author.

### 1. Palette Editor Tab

This tab allows you to define the 16-color active palette used throughout the application.

*   **Active Palette (16 colors):**
    *   A 4x4 grid displaying the 16 colors of the current active palette.
    *   Click on a color slot to select it for editing. The selected slot is highlighted with a red border.
*   **Selected Slot Info:**
    *   Displays the index of the selected palette slot.
    *   Shows a preview of the selected color.
    *   Displays the Hex RGB value and the MSX2 RGB (0-7 per channel) values.
*   **Set Color (RGB 0-7):**
    *   Input fields for Red, Green, and Blue values (each 0-7).
    *   Click "Set" to apply these RGB values to the currently selected palette slot.
*   **MSX2 512 Color Picker:**
    *   A large grid displaying all 512 possible MSX2 colors.
    *   Click on any color in this picker to apply it to the currently selected active palette slot.
*   **Reset to MSX2 Default:** Resets the 16 active palette colors to the standard MSX2 hardware default palette.

### 2. Tile Editor Tab

This tab is for creating and modifying individual 8x8 pixel tiles.

*   **Left Pane:**
    *   **Tile Editor Canvas:**
        *   An 8x8 grid where each cell represents a pixel.
        *   **Left-Click:** Draws a pixel using the currently selected color from the "Color Selector" palette (marks pixel as '1').
        *   **Right-Click:** Erases a pixel or draws with a "background" concept (marks pixel as '0').
        *   Click-and-drag to draw lines/multiple pixels.
    *   **Row Colors (FG/BG Buttons next to Editor Canvas):**
        *   For each of the 8 rows of the tile being edited, two small color swatches (FG and BG) are displayed.
        *   Click a swatch to set that row's foreground or background color to the color currently selected in the "Color Selector" palette.
    *   **Transform Controls:** Buttons to:
        *   **Flip H/V:** Flip the current tile horizontally or vertically.
        *   **Rotate:** Rotate the current tile 90 degrees clockwise (note: this resets row colors to default FG/BG).
        *   **Shift Up/Down/Left/Right:** Shift all pixels in the tile by one position, with wrapping.
    *   **Mark Unused Button:**
        *   Click once to highlight all tiles in the "Tileset" viewer (right pane) that are not used in any supertile definition with a bold blue border.
        *   Click again to clear this highlighting.
        *   Highlighting is automatically cleared on most editing actions or when switching tabs.
*   **Right Pane:**
    *   **Color Selector Palette:**
        *   A 4x4 grid showing the 16 active palette colors.
        *   Click a color here to make it the active drawing color for the Tile Editor canvas and for setting row FG/BG colors.
    *   **Tileset Viewer:**
        *   Displays all tiles in the current tileset (up to 256).
        *   **Click a tile:** Selects it for editing in the Tile Editor canvas and attribute editor. The selected tile has a red border.
        *   **Drag-and-Drop:** Click and drag a tile to a new position in the viewer to reorder tiles. A yellow line indicates the drop position. References to moved tiles in supertile definitions are updated.
    *   **Tile Management Buttons:**
        *   **Add New:** Adds a new blank tile at the end of the tileset and selects it.
        *   **Insert:** Inserts a new blank tile at the position of the currently selected tile, shifting subsequent tiles.
        *   **Delete:** Deletes the currently selected tile (cannot delete the last tile). Prompts for confirmation if the tile is used in supertiles.

### 3. Supertile Editor Tab

This tab is for creating 4x4 composite "supertiles" from the existing tiles.

*   **Left Pane:**
    *   **Supertile Definition Canvas:**
        *   A 4x4 grid representing the supertile being edited. Each cell shows a preview of a tile.
        *   **Left-Click a cell:** Places the tile currently selected in the "Tileset" viewer (right pane) into that cell of the supertile definition.
        *   **Right-Click a cell:** Selects the tile in that cell, making it the active tile in the "Tileset" viewer (eyedropper).
    *   **Info Labels:** Displays the index of the supertile being edited and the index of the tile selected for placing.
    *   **Transform Controls:** Buttons to:
        *   **Flip H/V:** Flip the current supertile definition horizontally or vertically.
        *   **Rotate:** Rotate the current supertile definition 90 degrees clockwise.
        *   **Shift Up/Down/Left/Right:** Shift all tiles within the supertile definition by one position, with wrapping.
    *   **Mark Unused Button:**
        *   Click once to highlight:
            *   Unused tiles (not in any supertile) in this tab's "Tileset" viewer (bold blue).
            *   Unused supertiles (not on the map) in this tab's "Supertile Selector" (bold blue).
        *   Click again to clear these highlights.
        *   Highlighting is automatically cleared on most editing actions or when switching tabs.
*   **Right Pane:**
    *   **Tileset Viewer:**
        *   Displays all tiles in the current tileset.
        *   **Click a tile:** Selects it for placing into the Supertile Definition canvas. The selected tile has a red border.
        *   **Drag-and-Drop:** Reorders tiles within the tileset (same functionality as in Tile Editor tab).
    *   **Supertile Selector:**
        *   Displays all supertiles in the project (up to 256).
        *   **Click a supertile:** Selects it for editing in the Supertile Definition canvas. The selected supertile has a red border.
        *   **Drag-and-Drop:** Click and drag a supertile to a new position to reorder supertiles. Map references are updated.
    *   **Supertile Management Buttons:**
        *   **Add New:** Adds a new blank supertile at the end and selects it.
        *   **Insert:** Inserts a new blank supertile at the position of the currently selected supertile.
        *   **Delete:** Deletes the currently selected supertile (cannot delete the last one). Prompts for confirmation if used on the map.

### 4. Map Editor Tab

This tab is for arranging supertiles to create a game map.

*   **Left Pane (Main Area):**
    *   **Controls Bar:**
        *   **Map Size:** Displays current map dimensions (Width x Height in supertiles).
        *   **Zoom Controls:** Buttons to Zoom In (+), Zoom Out (-), and Reset zoom to 100%. Displays current zoom percentage. Zooming is centered on the mouse cursor (Ctrl+MouseWheel) or canvas center (buttons).
        *   **Coords Label:** Displays the supertile coordinates (Col, Row) under the mouse cursor.
        *   **Show Window View Checkbox:** Toggles the visibility of the "Window View" overlay.
        *   **Window View Width/Height Entries:** Set the dimensions (in 8x8 tiles) of the Window View overlay. Press Enter or "Apply Size" to update.
        *   **Show Supertile Grid Checkbox:** Toggles the visibility of the supertile grid lines. Press 'G' (when map tab is active) to cycle grid line colors.
    *   **Map Canvas:**
        *   Displays the map.
        *   **Left-Click (No Modifiers):** Paints the currently selected supertile (from the "Supertile Palette" on the right) onto the map cell under the cursor. Click-and-drag to paint multiple cells.
        *   **Right-Click:** Selects the supertile under the cursor, making it the active supertile in the "Supertile Palette" (eyedropper).
        *   **Ctrl + Left-Click & Drag (or Middle Mouse Drag):** Pans the map view.
        *   **Shift + Left-Click & Drag:** Selects a rectangular region of supertiles on the map. The selection can be copied (Ctrl+C).
        *   **Ctrl + MouseWheel:** Zooms the map in/out, centered on the mouse cursor.
        *   **WASD Keys (when canvas has focus and Window View is active):** Nudges the Window View overlay one tile at a time.
        *   **Escape Key:** Clears the current map selection and any map clipboard/paste preview.
    *   **Window View Overlay (when active):**
        *   A rectangle showing a defined screen area in 8x8 tile units.
        *   Can be dragged by clicking inside it (when Ctrl is NOT pressed).
        *   Can be resized by dragging its corner/edge handles (when Ctrl is NOT pressed).
        *   If height is set to max (27 tiles), the bottom half-tile is shaded to indicate potential overscan.
    *   **Paste Preview (when map clipboard has data):**
        *   A semi-transparent blue rectangle showing where the map clipboard content will be pasted if Ctrl+V is pressed. Follows the mouse cursor.
*   **Right Pane:**
    *   **Supertile Palette:**
        *   Displays all supertiles.
        *   **Click a supertile:** Selects it for painting onto the Map Canvas. The selected supertile has a red border.
        *   **Drag-and-Drop:** Reorders supertiles (same functionality as in Supertile Editor tab).
    *   **Selected Supertile Label:** Displays "Selected Supertile for Painting: [index]".
*   **Minimap Window (View Menu -> Show/Hide Minimap or Ctrl+M):**
    *   A separate, resizable window.
    *   Shows a scaled-down preview of the entire map.
    *   A red rectangle indicates the current viewport of the main Map Canvas.
    *   A dashed blue rectangle (if Window View is active) indicates the position and size of the Window View overlay on the map.
    *   Automatically resizes to maintain the map's aspect ratio.

## Technical Description of Generated Files

All files are custom binary formats. Multi-byte integers are generally stored in Big-Endian format unless specified.

### 1. Palette File (`.msxpal`)

*   **Purpose:** Stores the 16 active palette colors.
*   **Format:**
    *   Total Size: 48 bytes.
    *   Structure: 16 entries, each 3 bytes.
    *   Each 3-byte entry represents one color:
        *   Byte 1: Red component (0-7)
        *   Byte 2: Green component (0-7)
        *   Byte 3: Blue component (0-7)
    *   The order of entries corresponds to palette index 0 through 15.

    Example: `R0 G0 B0 R1 G1 B1 ... R15 G15 B15`

### 2. Tileset File (`.SC4Tiles`)

*   **Purpose:** Stores tile pattern data and row color attributes.
*   **Format:**
    *   **Header:**
        *   `num_tiles_in_set` (1 byte): Number of tiles actually defined in the set (1-256. If 256, this byte is 0).
    *   **Tile Data (repeated `num_tiles_in_set` times):**
        *   Each tile consists of 16 bytes:
            *   **Pattern Data (8 bytes):**
                *   One byte per row (8 rows total).
                *   Each bit in a byte corresponds to a pixel in that row (MSB = leftmost pixel).
                *   Bit = 1 for foreground color, Bit = 0 for background color.
                *   Example for one row: `P0 P1 P2 P3 P4 P5 P6 P7` (where Px is a pixel bit)
            *   **Color Attribute Data (8 bytes):**
                *   One byte per row (8 rows total).
                *   Each byte combines the foreground and background palette indices for that row:
                    *   Bits 7-4 (High Nibble): Foreground palette index (0-15).
                    *   Bits 3-0 (Low Nibble): Background palette index (0-15).
                    *   Example byte: `FFFFBBBB` (F = Foreground index bit, B = Background index bit)

### 3. Supertile Definition File (`.SC4Super`)

*   **Purpose:** Stores the definitions of supertiles (which tiles make up each 4x4 supertile).
*   **Format:**
    *   **Header:**
        *   `num_supertiles` (1 byte): Number of supertiles defined (1-256. If 256, this byte is 0).
    *   **Supertile Definition Data (repeated `num_supertiles` times):**
        *   Each supertile definition consists of 16 bytes (for a 4x4 grid of tiles).
        *   Each byte is the index (0-255) of a tile from the tileset file (`.SC4Tiles`).
        *   Data is stored row by row for the 4x4 grid.
        *   Example for one supertile (16 bytes):
            `T00 T01 T02 T03` (Row 0 of supertile)
            `T10 T11 T12 T13` (Row 1 of supertile)
            `T20 T21 T22 T23` (Row 2 of supertile)
            `T30 T31 T32 T33` (Row 3 of supertile)
            (Where Txy is the tile index for cell at row x, column y within the supertile)

### 4. Map File (`.SC4Map`)

*   **Purpose:** Stores the map layout, referencing supertile indices.
*   **Format:**
    *   **Header:**
        *   `map_width` (2 bytes, Unsigned Short, Big-Endian): Width of the map in supertiles.
        *   `map_height` (2 bytes, Unsigned Short, Big-Endian): Height of the map in supertiles.
    *   **Map Data:**
        *   A sequence of `map_width * map_height` bytes.
        *   Each byte is the index (0-255) of a supertile from the supertile definition file (`.SC4Super`).
        *   Data is stored row by row. For a map of WxH supertiles:
            `ST(0,0) ST(0,1) ... ST(0,W-1)`
            `ST(1,0) ST(1,1) ... ST(1,W-1)`
            ...
            `ST(H-1,0) ... ST(H-1,W-1)`
            (Where ST(r,c) is the supertile index for map cell at row r, column c)

## Contributing

Contributions, bug reports, and feature suggestions are welcome! Please feel free to open an issue or submit a pull request on the GitHub repository.

## License

This project is licensed under the **GNU Affero General Public License v3.0**.

A copy of the license should be included with the software (e.g., in a `LICENSE` file). The full text can also be found at: [https://www.gnu.org/licenses/agpl-3.0.en.html](https://www.gnu.org/licenses/agpl-3.0.en.html)
