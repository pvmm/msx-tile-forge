# MSX Tile Forge
v0.0.33

An integrated Palette, Tile, Supertile and Map Editor for MSX, built with Python and TkMyinter.

## Introduction

MSX Tile Forge is a desktop application created to assist in the development of graphical assets for MSX2 computers and similar retro systems that utilize tile-based graphics and have specific palette limitations. It provides an integrated environment for designing 16-color palettes, creating 8x8 pixel tiles with row-specific colors, composing 4x4 supertiles from these tiles, and arranging them into larger game maps. The tool aims to streamline the asset creation workflow for retro game developers and hobbyists.

All project components (palette, tiles, supertiles, map) can be saved and loaded individually or as a complete project, using custom binary file formats designed for ease of use and integration into MSX development pipelines.

## Features

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
    *   Transformations: Flip Horizontal/Vertical, Rotate 90° CW (colors reset for rows), Shift Up/Down/Left/Right.
    *   Copy/Paste functionality for tile patterns and row colors.
    *   "Mark Unused" feature to highlight tiles not referenced in any supertile.
    *   Save/Load tilesets as `.SC4Tiles` binary files.
    *   **ROM Importer:** Import 8x8 1bpp tile data directly from ROM files. Features a visual browser with fine offset control, live preview, advanced multi-selection (Click, Shift+Click, Ctrl+Click, Ctrl+Shift+Click), and per-selection configurable preview/import colors from the active palette.
      
*   **Supertile Editor (Project-Configurable Dimensions, e.g., 2x2, 4x4, 8x2 tiles):**
    *   Define supertiles by arranging existing tiles in a grid of **user-defined width and height** (1-32 tiles per dimension, set per project).
    *   Tileset viewer for selecting component tiles from the current tileset.
    *   Supertile selector (up to 256 supertiles) with selection and drag-and-drop reordering.
    *   Operations: Add New, Insert, Delete supertiles.
    *   Transformations: Flip Horizontal/Vertical, Rotate 90° CW (**enabled only for square supertiles**), Shift Up/Down/Left/Right for the supertile definition.
    *   Copy/Paste functionality for supertile definitions
    *   "Mark Unused" feature: Highlights unused supertiles (not used on the map) and also re-highlights unused base tiles (not used in any supertile definition) within this tab's context.
    *   Save/Load supertile definitions as `.SC4Super` binary files (these files store the supertile dimensions).
 
*   **Map Editor:**
    *   Construct maps by placing supertiles on a grid (default 32x24 supertiles, dimensions configurable up to 1024x1024 supertiles per project).
    *   Supertile palette for selecting supertiles (from the current project's supertile set) to paint onto the map.
    *   Zoomable (Ctrl+MouseWheel or buttons) and pannable (Ctrl+LMB Drag or MMB Drag) map canvas.
    *   Optional supertile grid overlay with cyclable colors (toggled by 'Show Supertile Grid' checkbox; 'G' key cycles colors when map tab is active).
    *   "Window View" overlay:
        *   Visualizes a screen-like boundary on the map.
        *   Dimensions configurable in 8x8 base tiles (Width: 1-32, Height: 1-27). Max height of 27 accommodates MSX half-tile overscan concepts.
        *   Draggable on the map canvas (when not holding Ctrl).
        *   Resizable via its handles.
        *   Can be nudged one tile at a time using WASD keys when the Window View is active and the map canvas has focus.
    *   Resizable Minimap window (toggled via View menu or Ctrl+M):
        *   Displays a scaled-down overview of the entire map.
        *   Shows a red rectangle indicating the main Map Canvas's current viewport.
        *   Shows a dashed blue rectangle indicating the "Window View" overlay's position and size, if active.
        *   Maintains the map's aspect ratio when resized by the user.
    *   Map region selection using Shift+LMB Drag for Copy/Paste operations within the map.
    *   Eyedropper functionality (Right-Click on map) to select the supertile under the cursor and make it active in the Supertile Palette.
    *   "ST Coords" display the supertile coordinates under the mouse.
    *   Paste Preview: When map data is on the clipboard, a semi-transparent preview of the paste area follows the mouse cursor.
    *   Save/Load maps as `.SC4Map` binary files.

*   **Project Management:**
    *   Projects bundle all asset types: palettes, tilesets, supertiles and maps.
    *   Ability to save and load individual asset components (palette, tileset, supertiles, map) separately.
    *   Automatic tracking of unsaved changes within a project, with prompts to prevent data loss.

## Getting Started

This section explains how to set up your system and run MSX Tile Forge.

### System Requirements

*   **Python:** Version 3.x. The application has been developed and tested with Python 3.12, but it is expected to be compatible with other recent Python 3 releases.
*   **Tkinter:** This is Python's standard GUI (Graphical User Interface) package and is typically included with most Python installations across Windows, macOS, and Linux. No other external Python libraries are required.

### Running the Application

1.  **Ensure Python 3 is Installed:**
    Verify that Python 3 is installed on your system and that the `python` (or `python3` on some systems) command is accessible from your command line or terminal.

2.  **Obtain the Script:**
    Download or clone the `msxtileforge.py` script (or the directory containing it) to your computer.

3.  **Navigate to the Script's Directory:**
    Open your command line interface (Terminal, Command Prompt, PowerShell, etc.) and navigate to the directory where you saved the `msxtileforge.py` file.
    ```bash
    cd path/to/your/msx-tile-forge-directory
    ```

4.  **Execute the Script:**
    Run the application using the Python interpreter:
    ```bash
    python msxtileforge.py
    ```
    *   On some systems, particularly Linux or macOS where Python 2 might also be present, you may need to use `python3` explicitly:
        ```bash
        python3 msxtileforge.py
        ```

5.  **Optional Debug Mode:**
    To launch the application with detailed diagnostic messages printed to the console (useful for troubleshooting or development), use the `--debug` flag:
    ```bash
    python msxtileforge.py --debug
    ```
    or
    ```bash
    python3 msxtileforge.py --debug
    ```

Upon successful execution, the MSX Tile Forge application window should appear after a brief splash screen.

## Manual

This manual provides an overview of MSX Tile Forge's functionalities, organized by its main interface components.

### Global Operations (Menu Bar & General UX)

The main menu bar provides access to project-wide operations and settings.

*   **File Menu:**
    *   **Project Management:**
        *   `New Project (Ctrl+N)`: Starts a new project, prompting for supertile dimensions. Clears all current data (palette, tiles, supertiles, map).
        *   `Open Project... (Ctrl+O)`: Loads an existing project. Select any of its four component files (`.msxpal`, `.SC4Tiles`, `.SC4Super`, `.SC4Map`); the application loads all associated files. Supertile dimensions are restored from the `.SC4Super` file.
        *   `Save Project (Ctrl+S)`: Saves all four components of the current project. If unsaved, acts like "Save Project As...".
        *   `Save Project As... (Ctrl+Shift+S)`: Saves all four project components under a new base name and location chosen by the user.
    *   **Individual File Operations:** Allows loading or saving specific asset types independently:
        *   Palette (`.msxpal`)
        *   Tileset (`.SC4Tiles`)
        *   Supertiles (`.SC4Super`)
        *   Map (`.SC4Map`)
    *   **Import Tiles from ROM...:** Opens the ROM Importer dialog to extract tile data from external binary files (see detailed section below).
    *   **Exit (Ctrl+Q):** Closes the application. Prompts to save if there are unsaved changes to the current project.

*   **Edit Menu:**
    *   **Copy/Paste (Ctrl+C / Ctrl+V):** Context-sensitive actions.
        *   **Tile Editor:** Copies/pastes the current tile's pattern and row colors.
        *   **Supertile Editor:** Copies/pastes the current supertile's definition.
        *   **Map Editor:** Copies/pastes a selected rectangular region of supertiles on the map.
    *   **Clear Operations:**
        *   `Clear Current Tile`: Resets the selected tile's pattern and row colors to default.
        *   `Clear Current Supertile`: Resets the selected supertile's definition to all tile 0s.
        *   `Clear Map`: Resets all cells in the current map to supertile 0.
    *   **Set Data Counts/Dimensions:**
        *   `Set Tileset Size...`: Adjusts the total number of active tiles (1-256).
        *   `Set Supertile Count...`: Adjusts the total number of active supertiles (1-256).
        *   `Set Map Dimensions...`: Changes the map's width and height in supertile units (1-1024 per side).
        *   *Note: Reducing sizes may discard data and will prompt for confirmation if dependent items are affected.*

*   **View Menu:**
    *   `Show/Hide Minimap (Ctrl+M)`: Toggles the resizable Minimap window for the Map Editor.

*   **Help Menu:**
    *   `About...`: Displays application information (version, author).

*   **General User Experience:**
    *   **Unsaved Changes:** The window title is marked with an asterisk (*) if the project has unsaved modifications. Prompts to save are given before closing, opening, or creating new projects if changes are pending.
    *   **Drag-and-Drop Reordering:** In the Tileset Viewers (Tile and Supertile Editor tabs) and Supertile Selectors (Supertile and Map Editor tabs), items can be reordered by clicking and dragging them to a new position. References are updated accordingly.

### 1. Palette Editor Tab

This tab is dedicated to managing the 16-color active palette used for all graphics.

*   **Active Palette Display:** A 4x4 grid shows the 16 colors. Click a slot to select it for modification (highlighted red).
*   **Selected Slot Information:** Shows the selected slot's index, a color preview, its hexadecimal RGB value, and its MSX2-specific RGB values (0-7 per R, G, B channel).
*   **Color Modification:**
    *   **MSX2 512 Color Picker:** A large grid displaying all 512 possible MSX2 colors. Clicking a color here applies it to the selected active palette slot.
    *   **Set Color (RGB 0-7):** Input R, G, B values (0-7 each) and click "Set" to apply them to the selected slot.
*   **Reset Palette:** A button to revert the active 16-color palette to the standard MSX2 hardware default colors.

### 2. Tile Editor Tab

Used for creating and editing individual 8x8 pixel base tiles.

*   **Tile Editing Area (Left):**
    *   **Editor Canvas:** An 8x8 magnified grid for pixel drawing.
        *   Left-Click: Draws a foreground pixel (marks as '1').
        *   Right-Click: Draws a background pixel (marks as '0').
        *   Uses the color selected in the "Color Selector Palette" (Right Pane).
    *   **Row Colors Attributes:** Adjacent to the editor canvas, displays 8 pairs of FG (Foreground) and BG (Background) color swatches, one for each row of the tile.
        *   Click a swatch to assign the currently selected color (from "Color Selector Palette") as that row's FG or BG palette index.
    *   **Transformations:** Buttons for the currently edited tile:
        *   Flip Horizontal / Flip Vertical.
        *   Rotate 90° Clockwise (resets row colors to default for all rows).
        *   Shift (Up, Down, Left, Right) with pixel wrapping.
    *   **Mark Unused:** Highlights tiles in the "Tileset Viewer" not used in any supertile definition. Click again to clear.

*   **Tileset Management (Right):**
    *   **Color Selector Palette:** A 4x4 grid of the 16 active palette colors. Click to choose the active color for drawing pixels and setting row colors.
    *   **Tileset Viewer:** Displays all tiles in the project (up to 256).
        *   Click to select a tile for editing.
        *   Drag-and-drop to reorder tiles (supertile definitions update references).
    *   **Tile Operations:** Buttons for "Add New" (appends a blank tile), "Insert" (inserts a blank tile at selection), "Delete" (removes selected tile).
    *   **Info Label:** Shows current tile index and total tiles.

### 3. Supertile Editor Tab

For creating composite "supertiles" from base tiles. Supertile grid dimensions (e.g., 4x4, 2x8 tiles) are defined per-project.

*   **Supertile Definition Area (Left):**
    *   **Definition Canvas:** A grid matching the project's supertile dimensions (e.g., 4x4 cells, each showing a base tile).
        *   Left-Click a cell: Places the currently selected tile (from "Tileset Viewer" on the right) into that cell.
        *   Right-Click a cell (Eyedropper): Selects the tile within that cell, making it active in the "Tileset Viewer."
    *   **Information:** Labels display the index of the supertile being edited and the tile selected for placement.
    *   **Transformations:** Buttons for the current supertile definition:
        *   Flip Horizontal / Flip Vertical.
        *   Rotate 90° Clockwise (enabled only if the supertile grid is square).
        *   Shift (Up, Down, Left, Right) tiles within the definition, with wrapping.
    *   **Mark Unused:** Highlights unused supertiles (not on map) in the "Supertile Selector" and re-highlights unused base tiles in this tab's "Tileset Viewer." Click again to clear.

*   **Asset Selection (Right):**
    *   **Tileset Viewer:** Displays all base tiles. Click to select a tile for placing in the supertile definition. Drag-and-drop reorders tiles.
    *   **Supertile Selector:** Displays all supertiles in the project. Click to select a supertile for editing. Drag-and-drop reorders supertiles (map data updates references).
    *   **Supertile Operations:** Buttons for "Add New", "Insert", "Delete" supertiles.
    *   **Info Label:** Shows total number of supertiles.

### 4. Map Editor Tab

For arranging supertiles to construct game maps.

*   **Main Map Area (Left):**
    *   **Controls Bar (Top):**
        *   Displays current map dimensions (in supertiles) and zoom level.
        *   Zoom buttons (+, -, Reset).
        *   "ST Coords" label: Shows supertile coordinates under the mouse, respecting project-specific supertile dimensions.
        *   Checkboxes: "Show Supertile Grid" (press 'G' to cycle grid color), "Show Window View."
        *   "Window View" Width/Height entries (in 8x8 base tiles).
    *   **Map Canvas:** The main drawing area for the map.
        *   **Painting (LMB):** Places the currently selected supertile (from "Supertile Palette" on the right) onto the map.
        *   **Eyedropper (RMB):** Selects the supertile under the cursor, making it active in the "Supertile Palette."
        *   **Navigation:** Pan with Ctrl+LMB Drag (or MMB Drag); Zoom with Ctrl+MouseWheel.
        *   **Region Selection (Shift+LMB Drag):** Selects a rectangular area of supertiles for copy/paste.
        *   **Window View Nudge (WASD Keys):** Moves the "Window View" overlay if active and canvas has focus.
        *   **Paste Preview:** If map data is on the clipboard, a preview of the paste area follows the mouse.
        *   **Clear Selection/Clipboard (Escape Key):** Deselects map region and clears map clipboard/preview.
    *   **Window View Overlay (if active):** A draggable and resizable rectangle representing a screen area. Max height of 27 tiles allows for MSX overscan visualization (bottom half-tile shaded).

*   **Supertile Selection (Right):**
    *   **Supertile Palette:** Displays all supertiles in the project.
        *   Click to select a supertile for painting on the map.
        *   Drag-and-drop to reorder supertiles.
    *   **Info Label:** Shows the currently selected supertile for painting.

*   **Minimap Window (View Menu or Ctrl+M):**
    *   A separate, resizable window providing an overview of the entire map.
    *   Displays the main Map Canvas's current viewport (red rectangle) and the "Window View" overlay's position/size (dashed blue rectangle, if active).
    *   Maintains map aspect ratio when resized.

### 5. Importing Tiles from ROM

This feature (accessible via `File -> Import Tiles from ROM...`) allows loading an external binary file (e.g., a game ROM) to extract 8x8 pixel, 1-bit-per-pixel (1bpp) tile data and add it to the current project's tileset.

**Importer Dialog Features:**

*   **Layout:** The dialog is split into a left pane (controls and single tile preview) and a right pane (scrollable grid of tiles from the ROM).
*   **Live Preview (Left Pane):** Magnified view of the tile currently under the mouse cursor in the main ROM grid.
*   **Fine Offset Slider (Left Pane):** Adjusts the starting byte offset (0-7 bytes) within the ROM for tile decoding. The slider thumb snaps to integer values, with tick marks (0-7) displayed below.
*   **Preview/Import Colors (Left Pane):**
    *   Two clickable color swatches ("FG (1-bits)" and "BG (0-bits)") allow choosing two colors from the main application's 16-color active palette. These are the "current importer rendering colors."
*   **Status Information (Left Pane):** Displays "Grid Top-Left Byte" offset, hover information (ROM offset and grid index of tile under mouse), and "Tiles Selected" count.
*   **ROM Tile Grid (Right Pane):** Shows ROM data interpreted as a sequence of 8x8 1bpp tiles. Scrollable via scrollbars or keyboard.
*   **Rendering Colors in Previews:**
    *   **Unselected Tiles** in the grid and the live preview (when hovering an unselected tile) use the "current importer rendering colors."
    *   **Selected Tiles** in the grid and the live preview (when hovering a selected tile) use the FG/BG colors that were active in the "Preview/Import Colors" swatches *at the moment they were selected*. These colors are "locked-in" for each selected tile's preview.
    *   Changing the "Preview/Import Colors" swatches immediately updates unselected tiles; selected tiles retain their locked-in preview colors.
*   **Multi-Selection in Grid:**
    *   **Click (LMB):** Clears previous selection; selects the clicked tile; sets it as the "anchor"; associates current importer FG/BG colors.
    *   **Shift + Click (LMB):** Clears previous selection; selects a range from the anchor to the clicked tile; associates current importer FG/BG colors with this new range.
    *   **Ctrl + Click (LMB):** Toggles selection of the clicked tile without clearing others; associates current importer FG/BG colors if adding; updates the "anchor."
    *   **Ctrl + Shift + Click (LMB):** Adds a range (from anchor to clicked tile) to the existing selection; newly added tiles use colors associated with the anchor (or current importer colors if anchor wasn't specifically colored).
    *   **Right-Click / Escape Key:** Clears current selection.
    *   Selected tiles are highlighted with a yellow border.
*   **Importing:**
    *   The "Import" button (active when tiles are selected) appends selected tiles to the project's tileset.
    *   Each imported tile's default row colors are set using the FG/BG palette indices stored with it at its time of selection in the importer.
    *   Import stops if the tileset limit (256 tiles) is reached.
*   **Cancel:** Closes the dialog without importing.

## Technical Description of Generated Files

All project assets are saved in custom binary file formats. Multi-byte numerical values (like map dimensions) are stored in Big-Endian format unless specified otherwise.

### 1. Palette File (`.msxpal`)

*   **Purpose:** Stores the 16-color active MSX2 palette.
*   **Structure:**
    *   A sequence of 16 color entries, totaling 48 bytes.
    *   Each entry is 3 bytes, representing one palette color (index 0 to 15):
        *   Byte 1: Red component (value 0-7)
        *   Byte 2: Green component (value 0-7)
        *   Byte 3: Blue component (value 0-7)

### 2. Tileset File (`.SC4Tiles`)

*   **Purpose:** Stores definitions for 8x8 pixel tiles, including their pixel patterns and per-row color attributes.
*   **Structure:**
    *   **Header (1 byte):**
        *   `num_tiles_in_set`: The number of tiles defined in this file (value 1-255. A value of 0 represents 256 tiles).
    *   **Tile Data Blocks (repeated `num_tiles_in_set` times):**
        *   Each tile block is 16 bytes:
            *   **Pattern Data (8 bytes):** One byte per row of the 8x8 tile.
                *   Each bit within a byte represents a pixel (MSB = leftmost pixel).
                *   `1` = foreground pixel, `0` = background pixel.
            *   **Color Attribute Data (8 bytes):** One byte per row of the 8x8 tile.
                *   Each byte defines the foreground and background palette indices for that row:
                    *   High Nibble (bits 7-4): Foreground palette index (0-15).
                    *   Low Nibble (bits 3-0): Background palette index (0-15).

### 3. Supertile Definition File (`.SC4Super`)

*   **Purpose:** Stores the definitions of supertiles, specifying which base tiles compose them and the supertile grid dimensions.
*   **Structure:**
    *   **Header (3 bytes):**
        *   `num_supertiles` (1 byte): Number of supertiles defined (value 1-255. A value of 0 represents 256 supertiles).
        *   `supertile_grid_width` (1 byte): The width of each supertile in base tiles (value 1-32).
        *   `supertile_grid_height` (1 byte): The height of each supertile in base tiles (value 1-32).
    *   **Supertile Definition Blocks (repeated `num_supertiles` times):**
        *   Each block defines one supertile and consists of `supertile_grid_width * supertile_grid_height` bytes.
        *   Each byte within a block is a tile index (0-255) from a `.SC4Tiles` file, specifying the base tile for that position within the supertile's grid.
        *   Tile indices are stored row by row (top-to-bottom, left-to-right within each row).

### 4. Map File (`.SC4Map`)

*   **Purpose:** Stores the overall map layout, referencing supertile indices.
*   **Structure:**
    *   **Header (4 bytes):**
        *   `map_width` (2 bytes, Unsigned Short, Big-Endian): Width of the map in supertile units.
        *   `map_height` (2 bytes, Unsigned Short, Big-Endian): Height of the map in supertile units.
    *   **Map Data:**
        *   A sequence of `map_width * map_height` bytes.
        *   Each byte is a supertile index (0-255) from a `.SC4Super` file, specifying the supertile for that map cell.
        *   Supertile indices are stored row by row (top-to-bottom, left-to-right within each row).
     
## Contributing

Contributions to MSX Tile Forge are welcome! If you have bug reports, feature suggestions, or would like to contribute code:

1.  **Issues:** Please feel free to open an issue on the project's GitHub repository to discuss bugs or propose new features.
2.  **Pull Requests:** For code contributions, please fork the repository, make your changes in a separate branch, and then submit a pull request for review.

Clear descriptions and, where applicable, steps to reproduce issues are greatly appreciated.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

The full text of the license should be included with the software (typically in a `LICENSE` or `COPYING` file). It can also be found online at:
[https://www.gnu.org/licenses/agpl-3.0.en.html](https://www.gnu.org/licenses/agpl-3.0.en.html)
