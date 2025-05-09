# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
import struct
import os
import math
import copy

# --- Constants ---
TILE_WIDTH = 8
TILE_HEIGHT = 8
EDITOR_PIXEL_SIZE = 30
VIEWER_TILE_SIZE = TILE_WIDTH * 2 # 16
PALETTE_SQUARE_SIZE = 20
NUM_TILES_ACROSS = 16
MAX_TILES = 256
SUPERTILE_GRID_DIM = 4
SUPERTILE_DEF_TILE_SIZE = TILE_WIDTH * 4 # 32
SUPERTILE_SELECTOR_PREVIEW_SIZE = TILE_WIDTH * 4 # 32
NUM_SUPERTILES_ACROSS = 8
MAX_SUPERTILES = 256
# MAP_CELL_PREVIEW_SIZE removed, base size is now TILE_WIDTH/HEIGHT
DEFAULT_MAP_WIDTH = 32 # In supertiles
DEFAULT_MAP_HEIGHT = 24 # In supertiles
DEFAULT_WIN_VIEW_WIDTH_TILES = 32 # Default screen size
DEFAULT_WIN_VIEW_HEIGHT_TILES = 24 # Default screen size
MAX_WIN_VIEW_HEIGHT_TILES = 27 # Allow up to 27 for half-tile logic

MINIMAP_INITIAL_WIDTH = 256  # Default desired width of minimap window in pixels
MINIMAP_INITIAL_HEIGHT = 212 # Default desired height of minimap window in pixels

# --- Palette Editor Constants ---
MSX2_PICKER_COLS = 32
MSX2_PICKER_ROWS = 16
MSX2_PICKER_SQUARE_SIZE = 15
CURRENT_PALETTE_SLOT_SIZE = 30

# --- MSX2 Default Palette (Indices & Colors) ---
MSX2_RGB7_VALUES = [
    (0, 0, 0), (0, 0, 0), (1, 6, 1), (3, 7, 3), (1, 1, 7), (2, 3, 7),
    (5, 1, 1), (2, 6, 7), (7, 1, 1), (7, 3, 3), (6, 6, 1), (6, 6, 4),
    (1, 4, 1), (6, 2, 5), (5, 5, 5), (7, 7, 7),
]
BLACK_IDX = 1
MED_GREEN_IDX = 2
WHITE_IDX = 15

# --- Placeholder Colors ---
INVALID_TILE_COLOR = "#FF00FF"
INVALID_SUPERTILE_COLOR = "#00FFFF"

# --- Grid & Overlay Constants ---
GRID_COLOR_CYCLE = ["#FFFFFF", "#000000", "#FF00FF", "#00FFFF", "#FFFF00"] # White, Black, Magenta, Cyan, Yellow
GRID_DASH_PATTERN = (5, 3) # 5 pixels on, 3 pixels off
WIN_VIEW_HANDLE_SIZE = 8 # Pixel size of resize handles
WIN_VIEW_HALF_ROW_COLOR = "#80808080" # Semi-transparent grey for overscan area (adjust alpha if needed, format depends on tk version)

# --- MSX2 Color Generation ---
msx2_512_colors_hex = []
msx2_512_colors_rgb7 = []
for r in range(8):
    for g in range(8):
        for b in range(8):
            r_255 = min(255, r * 36)
            g_255 = min(255, g * 36)
            b_255 = min(255, b * 36)
            hex_color = f"#{r_255:02x}{g_255:02x}{b_255:02x}"
            msx2_512_colors_hex.append(hex_color)
            msx2_512_colors_rgb7.append((r, g, b))

# --- Data Structures ---
tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
tileset_colors = [[(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
current_tile_index = 0
num_tiles_in_set = 1
selected_color_index = WHITE_IDX
last_drawn_pixel = None
supertiles_data = [[[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
current_supertile_index = 0
num_supertiles = 1
selected_tile_for_supertile = 0
map_width = DEFAULT_MAP_WIDTH # In supertiles
map_height = DEFAULT_MAP_HEIGHT # In supertiles
map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
selected_supertile_for_map = 0
last_painted_map_cell = None
tile_clipboard_pattern = None
tile_clipboard_colors = None
supertile_clipboard_data = None

# --- Utility Functions ---
def get_contrast_color(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except:
        return "#000000"

# --- Application Class ---
class TileEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MSX2 Tile/Map/Palette Editor - Untitled")
        self.root.state('zoomed')

        self.current_project_base_path = None

        # --- Dynamic Palette ---
        self.active_msx_palette = []
        for r, g, b in MSX2_RGB7_VALUES:
            canonical_hex = self._rgb7_to_hex(r, g, b)
            self.active_msx_palette.append(canonical_hex)
        self.selected_palette_slot = 0

        # --- Image Caches ---
        self.tile_image_cache = {}
        self.supertile_image_cache = {}

        # --- Map Editor State ---
        self.map_zoom_level = 1.0
        self.show_supertile_grid = tk.BooleanVar(value=False)
        self.show_window_view = tk.BooleanVar(value=False)
        self.grid_color_index = 1
        self.window_view_tile_x = 0
        self.window_view_tile_y = 0
        self.window_view_tile_w = tk.IntVar(value=DEFAULT_WIN_VIEW_WIDTH_TILES)
        self.window_view_tile_h = tk.IntVar(value=DEFAULT_WIN_VIEW_HEIGHT_TILES)
        self.window_view_resize_handle = None # Keep for resize type
        self.drag_start_x = 0 # Keep for window move/resize calcs
        self.drag_start_y = 0
        self.drag_start_win_tx = 0 # Keep for window move/resize calcs
        self.drag_start_win_ty = 0
        self.drag_start_win_tw = 0 # Keep for window move/resize calcs
        self.drag_start_win_th = 0

        # --- Minimap State ---
        self.minimap_window = None
        self.minimap_canvas = None
        self.MINIMAP_WIDTH = 256
        self.MINIMAP_HEIGHT = 212
        self.MINIMAP_VIEWPORT_COLOR = "#FF0000"
        self.MINIMAP_WIN_VIEW_COLOR = "#0000FF"
        self.minimap_background_cache = None
        self.minimap_bg_rendered_width = 0
        self.minimap_bg_rendered_height = 0
        self.minimap_resize_timer = None
        self._minimap_resizing_internally = False

        # --- Interaction State ---
        self.is_ctrl_pressed = False       # Track if Control key is held down
        self.current_mouse_action = None   # None, 'panning', 'painting', 'window_dragging', 'window_resizing'
        self.pan_start_x = 0               # Deprecated by scan_mark/dragto, can remove if desired
        self.pan_start_y = 0               # Deprecated by scan_mark/dragto, can remove if desired

        # --- UI Setup ---
        self.create_menu()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # <<< ---vvv ENSURE THESE LINES ARE PRESENT vvv--- >>>
        self.tab_palette_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_tile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_supertile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_map_editor = ttk.Frame(self.notebook, padding="10") # THIS LINE WAS LIKELY MISSING
        # <<< ---^^^ ENSURE THESE LINES ARE PRESENT ^^^--- >>>

        self.notebook.add(self.tab_palette_editor, text='Palette Editor')
        self.notebook.add(self.tab_tile_editor, text='Tile Editor')
        self.notebook.add(self.tab_supertile_editor, text='Supertile Editor')
        self.notebook.add(self.tab_map_editor, text='Map Editor')

        # Call widget creation AFTER defining the tab frames
        self.create_palette_editor_widgets(self.tab_palette_editor)
        self.create_tile_editor_widgets(self.tab_tile_editor)
        self.create_supertile_editor_widgets(self.tab_supertile_editor)
        self.create_map_editor_widgets(self.tab_map_editor) # This call needs self.tab_map_editor

        self.update_all_displays(changed_level="all")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.root.bind("<c>", self.handle_global_keypress) # Bind lowercase 'c' globally
        self.root.bind("<C>", self.handle_global_keypress)

        # --- Extra Bindings for Map Canvas ---
        self._setup_map_canvas_bindings()

        self._update_window_title()


    # --- Palette Conversion Helpers ---
    def _hex_to_rgb7(self, hex_color):
        try:
            if not isinstance(hex_color, str):
                raise TypeError("Input must be a string.")
            if not hex_color.startswith('#') or len(hex_color) != 7:
                raise ValueError(f"Input '{hex_color}' is not a valid #RRGGBB format.")
            lookup_hex = hex_color.lower()
            idx512 = msx2_512_colors_hex.index(lookup_hex)
            return msx2_512_colors_rgb7[idx512]
        except ValueError:
            print(f"Warning: Could not find exact MSX2 RGB7 mapping for hex '{hex_color}'. Returning (0,0,0).")
            return (0, 0, 0)
        except TypeError as e:
            print(f"Error in _hex_to_rgb7: Input type error for '{hex_color}'. {e}")
            return (0, 0, 0)
        except Exception as e:
            print(f"Unexpected error in _hex_to_rgb7 for '{hex_color}': {e}")
            return (0, 0, 0)

    def _rgb7_to_hex(self, r, g, b):
        try:
            safe_r = max(0, min(7, int(r)))
            safe_g = max(0, min(7, int(g)))
            safe_b = max(0, min(7, int(b)))
            r_255 = min(255, safe_r * 36)
            g_255 = min(255, safe_g * 36)
            b_255 = min(255, safe_b * 36)
            hex_color = f"#{r_255:02x}{g_255:02x}{b_255:02x}"
            return hex_color
        except (ValueError, TypeError) as e:
            print(f"Error in _rgb7_to_hex converting input ({r},{g},{b}): {e}")
            return "#000000"
        except Exception as e:
            print(f"Unexpected error in _rgb7_to_hex for ({r},{g},{b}): {e}")
            return "#000000"

    # --- Cache Management ---
    def invalidate_tile_cache(self, tile_index):
        keys_to_remove = [k for k in self.tile_image_cache if k[0] == tile_index]
        for key in keys_to_remove:
            self.tile_image_cache.pop(key, None)
        for st_index in range(num_supertiles):
            definition = supertiles_data[st_index]
            used = False
            for r in range(SUPERTILE_GRID_DIM):
                for c in range(SUPERTILE_GRID_DIM):
                    if definition[r][c] == tile_index:
                        used = True
                        break
                if used:
                    break
            if used:
                self.invalidate_supertile_cache(st_index)

    def invalidate_supertile_cache(self, supertile_index):
        keys_to_remove = [k for k in self.supertile_image_cache if k[0] == supertile_index]
        for key in keys_to_remove:
            self.supertile_image_cache.pop(key, None)

    def clear_all_caches(self):
        self.tile_image_cache.clear()
        self.supertile_image_cache.clear()

    # --- Image Generation ---
    def create_tile_image(self, tile_index, size):
        cache_key = (tile_index, size)
        if cache_key in self.tile_image_cache:
            return self.tile_image_cache[cache_key]
        render_size = max(1, int(size))
        img = tk.PhotoImage(width=render_size, height=render_size)
        if not (0 <= tile_index < num_tiles_in_set):
            img.put(INVALID_TILE_COLOR, to=(0, 0, render_size, render_size))
            self.tile_image_cache[cache_key] = img
            return img
        pattern = tileset_patterns[tile_index]
        colors = tileset_colors[tile_index]
        pixel_w_ratio = TILE_WIDTH / render_size
        pixel_h_ratio = TILE_HEIGHT / render_size
        for y in range(render_size):
            tile_r = min(TILE_HEIGHT - 1, int(y * pixel_h_ratio))
            try:
                fg_idx, bg_idx = colors[tile_r]
                fg_color = self.active_msx_palette[fg_idx]
                bg_color = self.active_msx_palette[bg_idx]
            except IndexError:
                fg_color, bg_color = INVALID_TILE_COLOR, INVALID_TILE_COLOR
            row_colors_hex = []
            for x in range(render_size):
                tile_c = min(TILE_WIDTH - 1, int(x * pixel_w_ratio))
                try:
                    pixel_val = pattern[tile_r][tile_c]
                except IndexError:
                    pixel_val = 0
                color_hex = fg_color if pixel_val == 1 else bg_color
                row_colors_hex.append(color_hex)
            try:
                img.put("{" + " ".join(row_colors_hex) + "}", to=(0, y))
            except tk.TclError as e:
                print(f"Warning [create_tile_image]: TclError tile {tile_index} size {size} row {y}: {e}")
                if row_colors_hex:
                     img.put(row_colors_hex[0], to=(0, y, render_size, y+1))
        self.tile_image_cache[cache_key] = img
        return img

    def create_supertile_image(self, supertile_index, total_size):
        cache_key = (supertile_index, total_size)
        if cache_key in self.supertile_image_cache:
            return self.supertile_image_cache[cache_key]
        render_size = max(1, int(total_size))
        img = tk.PhotoImage(width=render_size, height=render_size)
        if not (0 <= supertile_index < num_supertiles):
            img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, render_size, render_size))
            self.supertile_image_cache[cache_key] = img
            return img
        definition = supertiles_data[supertile_index]
        mini_tile_size_float = render_size / SUPERTILE_GRID_DIM
        if mini_tile_size_float < 1:
            print(f"Warning [create_supertile_image]: ST {supertile_index} size {total_size} -> mini-tiles too small.")
            img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, render_size, render_size))
            self.supertile_image_cache[cache_key] = img
            return img
        mini_tile_pixel_h_ratio = TILE_HEIGHT / mini_tile_size_float
        mini_tile_pixel_w_ratio = TILE_WIDTH / mini_tile_size_float
        for y in range(render_size):
            mini_tile_r = min(SUPERTILE_GRID_DIM - 1, int(y / mini_tile_size_float))
            y_in_mini_render = y % mini_tile_size_float
            row_colors_hex = []
            for x in range(render_size):
                mini_tile_c = min(SUPERTILE_GRID_DIM - 1, int(x / mini_tile_size_float))
                x_in_mini_render = x % mini_tile_size_float
                tile_idx = definition[mini_tile_r][mini_tile_c]
                pixel_color_hex = INVALID_TILE_COLOR # Default
                if 0 <= tile_idx < num_tiles_in_set:
                    tile_r = min(TILE_HEIGHT - 1, int(y_in_mini_render * mini_tile_pixel_h_ratio))
                    tile_c = min(TILE_WIDTH - 1, int(x_in_mini_render * mini_tile_pixel_w_ratio))
                    try:
                        pattern_row = tileset_patterns[tile_idx][tile_r]
                        colors_row = tileset_colors[tile_idx][tile_r]
                        fg_idx = colors_row[0]
                        bg_idx = colors_row[1]
                        fg_color = self.active_msx_palette[fg_idx]
                        bg_color = self.active_msx_palette[bg_idx]
                        pixel_val = pattern_row[tile_c]
                        pixel_color_hex = fg_color if pixel_val == 1 else bg_color
                    except IndexError:
                         print(f"Warning [create_supertile_image]: IndexError T:{tile_idx} P:[{tile_r},{tile_c}] PaletteIdx:[{fg_idx},{bg_idx}]")
                         pixel_color_hex = INVALID_TILE_COLOR
                row_colors_hex.append(pixel_color_hex)
            try:
                img.put("{" + " ".join(row_colors_hex) + "}", to=(0, y))
            except tk.TclError as e:
                print(f"Warning [create_supertile_image]: TclError ST {supertile_index} size {total_size} row {y}: {e}")
                if row_colors_hex:
                    img.put(row_colors_hex[0], to=(0, y, render_size, y+1))
        self.supertile_image_cache[cache_key] = img
        return img

    # --- Menu Creation ---
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project (All)", command=self.new_project)
        file_menu.add_separator()
        file_menu.add_command(label="Open Project...", command=self.open_project)
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_command(label="Save Project As...", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Open Palette (.msxpal)...", command=self.open_palette)
        file_menu.add_command(label="Save Palette (.msxpal)...", command=self.save_palette)
        file_menu.add_separator()
        file_menu.add_command(label="Open Tileset (.SC4Tiles)...", command=self.open_tileset)
        file_menu.add_command(label="Save Tileset (.SC4Tiles)...", command=self.save_tileset)
        file_menu.add_separator()
        file_menu.add_command(label="Open Supertiles (.SC4Super)...", command=self.open_supertiles)
        file_menu.add_command(label="Save Supertiles (.SC4Super)...", command=self.save_supertiles)
        file_menu.add_separator()
        file_menu.add_command(label="Open Map (.SC4Map)...", command=self.open_map)
        file_menu.add_command(label="Save Map (.SC4Map)...", command=self.save_map)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Tile", command=self.copy_current_tile)
        edit_menu.add_command(label="Paste Tile", command=self.paste_tile)
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy Supertile", command=self.copy_current_supertile)
        edit_menu.add_command(label="Paste Supertile", command=self.paste_supertile)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile)
        edit_menu.add_command(label="Clear Current Supertile", command=self.clear_current_supertile)
        edit_menu.add_command(label="Clear Map", command=self.clear_map)
        edit_menu.add_separator()
        edit_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size)
        edit_menu.add_command(label="Set Supertile Count...", command=self.set_supertile_count)
        edit_menu.add_command(label="Set Map Dimensions...", command=self.set_map_dimensions)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show/Hide Minimap", command=self.toggle_minimap)

    # --- Widget Creation ---
    def create_palette_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame, padding=5)
        left_frame.grid(row=0, column=0, sticky="ns")
        right_frame = ttk.Frame(main_frame, padding=5)
        right_frame.grid(row=0, column=1, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=0)
        main_frame.grid_columnconfigure(1, weight=1)
        # Left Frame Contents
        current_palette_frame = ttk.LabelFrame(left_frame, text="Active Palette (16 colors)")
        current_palette_frame.pack(pady=(0, 10), fill="x")
        cp_canvas_width = 4 * (CURRENT_PALETTE_SLOT_SIZE + 2) + 2
        cp_canvas_height = 4 * (CURRENT_PALETTE_SLOT_SIZE + 2) + 2
        self.current_palette_canvas = tk.Canvas(current_palette_frame, width=cp_canvas_width, height=cp_canvas_height, borderwidth=0, highlightthickness=0)
        self.current_palette_canvas.pack()
        self.current_palette_canvas.bind("<Button-1>", self.handle_current_palette_click)
        info_frame = ttk.LabelFrame(left_frame, text="Selected Slot Info")
        info_frame.pack(pady=(0, 10), fill="x")
        self.selected_slot_label = ttk.Label(info_frame, text="Slot: 0")
        self.selected_slot_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=2)
        self.selected_slot_color_label = tk.Label(info_frame, text="      ", bg="#000000", relief="sunken", width=6)
        self.selected_slot_color_label.grid(row=1, column=0, padx=5, pady=2)
        self.selected_slot_rgb_label = ttk.Label(info_frame, text="RGB: #000000")
        self.selected_slot_rgb_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)
        rgb_frame = ttk.LabelFrame(left_frame, text="Set Color (RGB 0-7)")
        rgb_frame.pack(pady=(0, 10), fill="x")
        r_label = ttk.Label(rgb_frame, text="R:")
        r_label.grid(row=0, column=0, padx=(5,0))
        self.rgb_r_var = tk.StringVar(value="0")
        self.rgb_r_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_r_var, width=2)
        self.rgb_r_entry.grid(row=0, column=1)
        g_label = ttk.Label(rgb_frame, text="G:")
        g_label.grid(row=0, column=2, padx=(5,0))
        self.rgb_g_var = tk.StringVar(value="0")
        self.rgb_g_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_g_var, width=2)
        self.rgb_g_entry.grid(row=0, column=3)
        b_label = ttk.Label(rgb_frame, text="B:")
        b_label.grid(row=0, column=4, padx=(5,0))
        self.rgb_b_var = tk.StringVar(value="0")
        self.rgb_b_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_b_var, width=2)
        self.rgb_b_entry.grid(row=0, column=5)
        apply_rgb_button = ttk.Button(rgb_frame, text="Set", command=self.handle_rgb_apply)
        apply_rgb_button.grid(row=0, column=6, padx=5, pady=5)
        reset_palette_button = ttk.Button(left_frame, text="Reset to MSX2 Default", command=self.reset_palette_to_default)
        reset_palette_button.pack(pady=(0, 5), fill="x")
        # Right Frame Contents
        picker_frame = ttk.LabelFrame(right_frame, text="MSX2 512 Color Picker")
        picker_frame.pack(expand=True, fill="both")
        picker_canvas_width = MSX2_PICKER_COLS * (MSX2_PICKER_SQUARE_SIZE + 1) + 1
        picker_canvas_height = MSX2_PICKER_ROWS * (MSX2_PICKER_SQUARE_SIZE + 1) + 1
        picker_hbar = ttk.Scrollbar(picker_frame, orient=tk.HORIZONTAL)
        picker_vbar = ttk.Scrollbar(picker_frame, orient=tk.VERTICAL)
        self.msx2_picker_canvas = tk.Canvas(picker_frame, bg="lightgrey", scrollregion=(0, 0, picker_canvas_width, picker_canvas_height), xscrollcommand=picker_hbar.set, yscrollcommand=picker_vbar.set)
        picker_hbar.config(command=self.msx2_picker_canvas.xview)
        picker_vbar.config(command=self.msx2_picker_canvas.yview)
        self.msx2_picker_canvas.grid(row=0, column=0, sticky="nsew")
        picker_vbar.grid(row=0, column=1, sticky="ns")
        picker_hbar.grid(row=1, column=0, sticky="ew")
        picker_frame.grid_rowconfigure(0, weight=1)
        picker_frame.grid_columnconfigure(0, weight=1)
        self.msx2_picker_canvas.bind("<Button-1>", self.handle_512_picker_click)
        self.draw_512_picker()

    def create_tile_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)")
        editor_frame.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        self.editor_canvas = tk.Canvas( editor_frame, width=TILE_WIDTH * EDITOR_PIXEL_SIZE, height=TILE_HEIGHT * EDITOR_PIXEL_SIZE, bg="grey")
        self.editor_canvas.grid(row=0, column=0)
        self.editor_canvas.bind("<Button-1>", self.handle_editor_click)
        self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag)
        self.editor_canvas.bind("<Button-3>", self.handle_editor_click)
        self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag)
        attr_frame = ttk.LabelFrame(left_frame, text="Row Colors (Click to set FG/BG)")
        attr_frame.grid(row=1, column=0, pady=(0,10), sticky="ew")
        self.attr_row_frames = []
        self.attr_fg_labels = []
        self.attr_bg_labels = []
        for r in range(TILE_HEIGHT):
            row_f = ttk.Frame(attr_frame)
            row_f.grid(row=r, column=0, sticky=tk.W, pady=1)
            row_label = ttk.Label(row_f, text=f"{r}:")
            row_label.grid(row=0, column=0, padx=(0, 5))
            fg_label = tk.Label(row_f, text=" FG ", width=3, relief="raised", borderwidth=2)
            fg_label.grid(row=0, column=1, padx=(0, 2))
            fg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'fg'))
            self.attr_fg_labels.append(fg_label)
            bg_label = tk.Label(row_f, text=" BG ", width=3, relief="raised", borderwidth=2)
            bg_label.grid(row=0, column=2)
            bg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'bg'))
            self.attr_bg_labels.append(bg_label)
            self.attr_row_frames.append(row_f)
        transform_frame = ttk.LabelFrame(left_frame, text="Transform")
        transform_frame.grid(row=2, column=0, pady=(0, 10), sticky="ew")
        flip_h_button = ttk.Button(transform_frame, text="Flip H", command=self.flip_tile_horizontal)
        flip_h_button.grid(row=0, column=0, padx=3, pady=3)
        flip_v_button = ttk.Button(transform_frame, text="Flip V", command=self.flip_tile_vertical)
        flip_v_button.grid(row=0, column=1, padx=3, pady=3)
        rotate_button = ttk.Button(transform_frame, text="Rotate", command=self.rotate_tile_90cw)
        rotate_button.grid(row=0, column=2, padx=3, pady=3)
        shift_up_button = ttk.Button(transform_frame, text="Shift Up", command=self.shift_tile_up)
        shift_up_button.grid(row=1, column=0, padx=3, pady=3)
        shift_down_button = ttk.Button(transform_frame, text="Shift Down", command=self.shift_tile_down)
        shift_down_button.grid(row=1, column=1, padx=3, pady=3)
        shift_left_button = ttk.Button(transform_frame, text="Shift Left", command=self.shift_tile_left)
        shift_left_button.grid(row=1, column=2, padx=3, pady=3)
        shift_right_button = ttk.Button(transform_frame, text="Shift Right", command=self.shift_tile_right)
        shift_right_button.grid(row=1, column=3, padx=3, pady=3)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        main_frame.grid_rowconfigure(0, weight=1)
        palette_frame = ttk.LabelFrame(right_frame, text="Color Selector (Click to draw)")
        palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.N, tk.W, tk.E))
        self.tile_editor_palette_canvas = tk.Canvas(palette_frame, width=4 * (PALETTE_SQUARE_SIZE + 2), height=4 * (PALETTE_SQUARE_SIZE + 2), borderwidth=0, highlightthickness=0)
        self.tile_editor_palette_canvas.grid(row=0, column=0)
        self.tile_editor_palette_canvas.bind("<Button-1>", self.handle_tile_editor_palette_click)
        viewer_frame = ttk.LabelFrame(right_frame, text="Tileset")
        viewer_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        right_frame.grid_rowconfigure(1, weight=1)
        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1
        num_rows_in_viewer = math.ceil(MAX_TILES / NUM_TILES_ACROSS)
        viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1
        viewer_hbar = ttk.Scrollbar(viewer_frame, orient=tk.HORIZONTAL)
        viewer_vbar = ttk.Scrollbar(viewer_frame, orient=tk.VERTICAL)
        self.tileset_canvas = tk.Canvas( viewer_frame, bg="lightgrey", scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height), xscrollcommand=viewer_hbar.set, yscrollcommand=viewer_vbar.set)
        viewer_hbar.config(command=self.tileset_canvas.xview)
        viewer_vbar.config(command=self.tileset_canvas.yview)
        self.tileset_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        viewer_frame.grid_rowconfigure(0, weight=1)
        viewer_frame.grid_columnconfigure(0, weight=1)
        self.tileset_canvas.bind("<Button-1>", self.handle_tileset_click)
        add_tile_button = ttk.Button(right_frame, text="Add New Tile", command=self.add_new_tile)
        add_tile_button.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.tile_info_label = ttk.Label(right_frame, text="Tile: 0/0")
        self.tile_info_label.grid(row=3, column=0, sticky=tk.W, pady=(2,0))

    def create_supertile_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        def_frame = ttk.LabelFrame(left_frame, text="Supertile Definition (Click to place selected tile)")
        def_frame.grid(row=0, column=0, pady=(0, 10))
        def_canvas_size = SUPERTILE_GRID_DIM * SUPERTILE_DEF_TILE_SIZE
        self.supertile_def_canvas = tk.Canvas(def_frame, width=def_canvas_size, height=def_canvas_size, bg="darkgrey")
        self.supertile_def_canvas.grid(row=0, column=0)
        self.supertile_def_canvas.bind("<Button-1>", self.handle_supertile_def_click)
        self.supertile_def_info_label = ttk.Label(left_frame, text=f"Editing Supertile: {current_supertile_index}")
        self.supertile_def_info_label.grid(row=1, column=0, sticky=tk.W)
        self.supertile_tile_select_label = ttk.Label(left_frame, text=f"Selected Tile for Placing: {selected_tile_for_supertile}")
        self.supertile_tile_select_label.grid(row=2, column=0, sticky=tk.W)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W, tk.E))
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        tileset_viewer_frame = ttk.LabelFrame(right_frame, text="Tileset (Click to select tile for definition)")
        tileset_viewer_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), pady=(0, 10))
        right_frame.grid_rowconfigure(0, weight=1)
        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1
        num_rows_in_viewer = math.ceil(MAX_TILES / NUM_TILES_ACROSS)
        viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1
        st_viewer_hbar = ttk.Scrollbar(tileset_viewer_frame, orient=tk.HORIZONTAL)
        st_viewer_vbar = ttk.Scrollbar(tileset_viewer_frame, orient=tk.VERTICAL)
        self.st_tileset_canvas = tk.Canvas( tileset_viewer_frame, bg="lightgrey", scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height), xscrollcommand=st_viewer_hbar.set, yscrollcommand=st_viewer_vbar.set)
        st_viewer_hbar.config(command=self.st_tileset_canvas.xview)
        st_viewer_vbar.config(command=self.st_tileset_canvas.yview)
        self.st_tileset_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        st_viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        st_viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        tileset_viewer_frame.grid_rowconfigure(0, weight=1)
        tileset_viewer_frame.grid_columnconfigure(0, weight=1)
        self.st_tileset_canvas.bind("<Button-1>", self.handle_st_tileset_click)
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Selector (Click to edit)")
        st_selector_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        right_frame.grid_rowconfigure(1, weight=1)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS)
        st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL)
        st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=st_sel_hbar.set, yscrollcommand=st_sel_vbar.set)
        st_sel_hbar.config(command=self.supertile_selector_canvas.xview)
        st_sel_vbar.config(command=self.supertile_selector_canvas.yview)
        self.supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        st_selector_frame.grid_rowconfigure(0, weight=1)
        st_selector_frame.grid_columnconfigure(0, weight=1)
        self.supertile_selector_canvas.bind("<Button-1>", self.handle_supertile_selector_click)
        add_supertile_button = ttk.Button(right_frame, text="Add New Supertile", command=self.add_new_supertile)
        add_supertile_button.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.supertile_sel_info_label = ttk.Label(right_frame, text=f"Supertiles: {num_supertiles}")
        self.supertile_sel_info_label.grid(row=3, column=0, sticky=tk.W, pady=(2,0))

    def create_map_editor_widgets(self, parent_frame):
        # Create the main container frame for this tab
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")

        # --- Create Left and Right Columns ---
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10))
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # --- Configure Main Frame Grid Weights ---
        # Column 0 (left_frame) expands horizontally
        main_frame.grid_columnconfigure(0, weight=1)
        # Column 1 (right_frame) has fixed width
        main_frame.grid_columnconfigure(1, weight=0)
        # Row 0 expands vertically
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Configure Left Frame Contents ---

        # Row 0: Map Size and Zoom Controls
        controls_frame = ttk.Frame(left_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        # Map Size
        size_label = ttk.Label(controls_frame, text="Map Size:")
        size_label.grid(row=0, column=0, padx=(0,5), pady=2)
        self.map_size_label = ttk.Label(controls_frame, text=f"{map_width} x {map_height}")
        self.map_size_label.grid(row=0, column=1, padx=(0, 10), pady=2)
        # Zoom
        zoom_frame = ttk.Frame(controls_frame)
        zoom_frame.grid(row=0, column=2, padx=(10, 0), pady=2)
        zoom_out_button = ttk.Button(zoom_frame, text="-", width=2, command=lambda: self.change_map_zoom_mult(1/1.25))
        zoom_out_button.pack(side=tk.LEFT)
        self.map_zoom_label = ttk.Label(zoom_frame, text="100%", width=5, anchor=tk.CENTER)
        self.map_zoom_label.pack(side=tk.LEFT, padx=2)
        zoom_in_button = ttk.Button(zoom_frame, text="+", width=2, command=lambda: self.change_map_zoom_mult(1.25))
        zoom_in_button.pack(side=tk.LEFT)
        zoom_reset_button = ttk.Button(zoom_frame, text="Reset", width=5, command=lambda: self.set_map_zoom(1.0))
        zoom_reset_button.pack(side=tk.LEFT, padx=(5,0))

        # Row 1: Grid / Window View Controls
        grid_controls_frame = ttk.Frame(left_frame)
        grid_controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        st_grid_check = ttk.Checkbutton(
            grid_controls_frame,
            text="Show Supertile Grid",
            variable=self.show_supertile_grid,
            command=self.toggle_supertile_grid
        )
        st_grid_check.grid(row=0, column=0, padx=5, sticky='w')
        win_view_check = ttk.Checkbutton(
            grid_controls_frame,
            text="Show Window View",
            variable=self.show_window_view,
            command=self.toggle_window_view
        )
        win_view_check.grid(row=0, column=1, padx=5, sticky='w')
        grid_color_label = ttk.Label(grid_controls_frame, text="Grid Color (Press 'C' to Cycle)")
        grid_color_label.grid(row=0, column=2, padx=15, sticky='w')

        # Row 2: Window View Size Inputs
        win_size_frame = ttk.Frame(left_frame)
        win_size_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        win_w_label = ttk.Label(win_size_frame, text="Win W:")
        win_w_label.grid(row=0, column=0, padx=(5,0))
        self.win_view_w_entry = ttk.Entry(win_size_frame, textvariable=self.window_view_tile_w, width=4)
        self.win_view_w_entry.grid(row=0, column=1)
        win_h_label = ttk.Label(win_size_frame, text="H:")
        win_h_label.grid(row=0, column=2, padx=(5,0))
        self.win_view_h_entry = ttk.Entry(win_size_frame, textvariable=self.window_view_tile_h, width=4)
        self.win_view_h_entry.grid(row=0, column=3)
        win_apply_button = ttk.Button(win_size_frame, text="Apply Size", command=self.apply_window_size_from_entries)
        win_apply_button.grid(row=0, column=4, padx=5)
        self.win_view_w_entry.bind("<Return>", lambda e: self.apply_window_size_from_entries())
        self.win_view_h_entry.bind("<Return>", lambda e: self.apply_window_size_from_entries())

        # Row 3: Map Canvas Frame
        map_canvas_frame = ttk.LabelFrame(left_frame, text="Map")
        map_canvas_frame.grid(row=3, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        # --- Configure Left Frame Grid Weights ---
        left_frame.grid_rowconfigure(0, weight=0) # Controls row fixed height
        left_frame.grid_rowconfigure(1, weight=0) # Grid controls fixed height
        left_frame.grid_rowconfigure(2, weight=0) # Win Size controls fixed height
        left_frame.grid_rowconfigure(3, weight=1) # Canvas frame expands vertically
        left_frame.grid_columnconfigure(0, weight=1)# The single column expands horizontally

        # --- Create Map Canvas and Scrollbars ---
        # Create scrollbars and store as instance variables
        self.map_hbar = ttk.Scrollbar(map_canvas_frame, orient=tk.HORIZONTAL)
        self.map_vbar = ttk.Scrollbar(map_canvas_frame, orient=tk.VERTICAL)

        # Create canvas, linking scroll commands to the instance scrollbars
        self.map_canvas = tk.Canvas(
            map_canvas_frame,
            bg="black",
            xscrollcommand=self.map_hbar.set,
            yscrollcommand=self.map_vbar.set
        )

        # Configure scrollbars to control the canvas view
        self.map_hbar.config(command=self.map_canvas.xview)
        self.map_vbar.config(command=self.map_canvas.yview)

        # Place canvas and scrollbars using grid within map_canvas_frame
        self.map_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.map_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.map_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # --- Configure Map Canvas Frame Grid Weights ---
        map_canvas_frame.grid_rowconfigure(0, weight=1)    # Canvas row expands
        map_canvas_frame.grid_columnconfigure(0, weight=1) # Canvas column expands
        map_canvas_frame.grid_rowconfigure(1, weight=0)    # Horizontal scrollbar fixed height
        map_canvas_frame.grid_columnconfigure(1, weight=0) # Vertical scrollbar fixed width

        # Bindings are handled in _setup_map_canvas_bindings() called from __init__


        # --- Configure Right Frame Contents ---
        # Supertile Palette
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Palette (Click to select for map)")
        st_selector_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        # Right frame row weights
        right_frame.grid_rowconfigure(0, weight=1) # Palette expands vertically
        right_frame.grid_rowconfigure(1, weight=0) # Info label fixed height
        # Right frame column weights
        right_frame.grid_columnconfigure(0, weight=1) # Allow content width

        # Supertile Palette Canvas Setup
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS)
        st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        map_st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL)
        map_st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.map_supertile_selector_canvas = tk.Canvas(
            st_selector_frame,
            bg="lightgrey",
            scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height),
            xscrollcommand=map_st_sel_hbar.set,
            yscrollcommand=map_st_sel_vbar.set
        )
        map_st_sel_hbar.config(command=self.map_supertile_selector_canvas.xview)
        map_st_sel_vbar.config(command=self.map_supertile_selector_canvas.yview)
        # Place palette canvas and scrollbars
        self.map_supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        map_st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        map_st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        # Configure grid weights within the palette frame
        st_selector_frame.grid_rowconfigure(0, weight=1)    # Canvas row expands
        st_selector_frame.grid_columnconfigure(0, weight=1) # Canvas column expands
        st_selector_frame.grid_rowconfigure(1, weight=0)    # Scrollbar fixed height
        st_selector_frame.grid_columnconfigure(1, weight=0) # Scrollbar fixed width
        # Bind palette click
        self.map_supertile_selector_canvas.bind("<Button-1>", self.handle_map_supertile_selector_click)

        # Selected Supertile Label
        self.map_supertile_select_label = ttk.Label(right_frame, text=f"Selected Supertile for Painting: {selected_supertile_for_map}")
        self.map_supertile_select_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))

    def _setup_map_canvas_bindings(self):
        """Sets up additional event bindings for the map canvas."""
        # Basic painting/window ops (NO Ctrl)
        self.map_canvas.bind("<Button-1>", self.handle_map_click_or_drag_start) # Handles non-Ctrl clicks
        self.map_canvas.bind("<B1-Motion>", self.handle_map_drag) # Handles non-Ctrl drags
        self.map_canvas.bind("<ButtonRelease-1>", self.handle_map_drag_release) # Handles ALL button releases

        # Zooming (Ctrl + Wheel)
        self.map_canvas.bind("<Control-MouseWheel>", self.handle_map_zoom_scroll) # Windows/macOS
        self.map_canvas.bind("<Control-Button-4>", self.handle_map_zoom_scroll) # Linux scroll up
        self.map_canvas.bind("<Control-Button-5>", self.handle_map_zoom_scroll) # Linux scroll down

        # Ctrl Key Press/Release (Bound to root window)
        self.root.bind("<KeyPress-Control_L>", self.handle_ctrl_press)
        self.root.bind("<KeyPress-Control_R>", self.handle_ctrl_press)
        self.root.bind("<KeyRelease-Control_L>", self.handle_ctrl_release) # Crucial
        self.root.bind("<KeyRelease-Control_R>", self.handle_ctrl_release) # Crucial

        # Panning Bindings (Ctrl + Click/Drag)
        # These specifically trigger the pan start/motion handlers
        self.map_canvas.bind("<Control-ButtonPress-1>", self.handle_pan_start) # <<< Uses handle_pan_start
        self.map_canvas.bind("<Control-B1-Motion>", self.handle_pan_motion)   # <<< Uses handle_pan_motion

        # Enter/Leave Bindings (for cursor changes)
        self.map_canvas.bind("<Enter>", self.handle_canvas_enter)
        self.map_canvas.bind("<Leave>", self.handle_canvas_leave)

        # Keyboard (requires focus on canvas)
        self.map_canvas.bind("<FocusIn>", lambda e: self.map_canvas.focus_set())
        self.map_canvas.bind("<Key>", self.handle_map_keypress)

        # Scrollbar bindings (remain the same)
        if hasattr(self, 'map_hbar') and self.map_hbar:
             self.map_hbar.bind("<B1-Motion>", lambda e: self.draw_minimap())
             self.map_hbar.bind("<ButtonRelease-1>", lambda e: self.draw_minimap())
        if hasattr(self, 'map_vbar') and self.map_vbar:
             self.map_vbar.bind("<B1-Motion>", lambda e: self.draw_minimap())
             self.map_vbar.bind("<ButtonRelease-1>", lambda e: self.draw_minimap())

    # --- Drawing Functions ---
    def update_all_displays(self, changed_level="all"):
        # Palette Editor parts
        if changed_level in ["all", "palette"]:
            self.draw_current_palette()
            self.update_palette_info_labels()
        # Tile Editor parts
        if changed_level in ["all", "palette", "tile"]:
            self.draw_editor_canvas()
            self.draw_attribute_editor()
            self.draw_palette()
            self.draw_tileset_viewer(self.tileset_canvas, current_tile_index)
            self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
            self.update_tile_info_label()
        # Supertile Editor parts
        if changed_level in ["all", "palette", "tile", "supertile"]:
            self.draw_supertile_definition_canvas()
            self.draw_supertile_selector(self.supertile_selector_canvas, current_supertile_index)
            self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
            self.update_supertile_info_labels()
        # Map Editor parts (Now includes grid/window updates)
        if changed_level in ["all", "palette", "tile", "supertile", "map"]:
             self.draw_map_canvas() # This now handles drawing overlays
             self.update_map_info_labels() # Updates size/zoom/window size entries

    # ... (draw_editor_canvas, draw_attribute_editor, draw_palette unchanged) ...
    def draw_editor_canvas(self):
        self.editor_canvas.delete("all")
        if not (0 <= current_tile_index < num_tiles_in_set): return
        pattern = tileset_patterns[current_tile_index]; colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            try: fg_idx, bg_idx = colors[r]; fg_color = self.active_msx_palette[fg_idx]; bg_color = self.active_msx_palette[bg_idx]
            except IndexError: fg_color, bg_color = INVALID_TILE_COLOR, INVALID_TILE_COLOR
            for c in range(TILE_WIDTH):
                try: pixel_val = pattern[r][c]
                except IndexError: pixel_val = 0
                color = fg_color if pixel_val == 1 else bg_color; x1=c*EDITOR_PIXEL_SIZE; y1=r*EDITOR_PIXEL_SIZE; x2=x1+EDITOR_PIXEL_SIZE; y2=y1+EDITOR_PIXEL_SIZE
                self.editor_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="darkgrey", width=1)
    def draw_attribute_editor(self):
        if not (0 <= current_tile_index < num_tiles_in_set): return
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            try: fg_idx, bg_idx = colors[r]; fg_color_hex = self.active_msx_palette[fg_idx]; bg_color_hex = self.active_msx_palette[bg_idx]
            except IndexError: fg_color_hex, bg_color_hex = INVALID_TILE_COLOR, INVALID_TILE_COLOR
            self.attr_fg_labels[r].config(bg=fg_color_hex, fg=get_contrast_color(fg_color_hex)); self.attr_bg_labels[r].config(bg=bg_color_hex, fg=get_contrast_color(bg_color_hex))
    def draw_palette(self): # Renamed draw_palette to this for clarity
        """Draws the 16-color selector palette in the Tile Editor tab."""
        canvas = self.tile_editor_palette_canvas
        canvas.delete("all"); size = PALETTE_SQUARE_SIZE; padding = 2
        for i in range(16):
            row, col = divmod(i, 4); x1 = col * (size + padding) + padding; y1 = row * (size + padding) + padding; x2 = x1 + size; y2 = y1 + size
            color = self.active_msx_palette[i] # Use active palette
            outline_color = "red" if i == selected_color_index else "grey"; outline_width = 2 if i == selected_color_index else 1
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline_color, width=outline_width, tags=f"pal_sel_{i}")

    # --- vvv Palette Editor Drawing vvv ---
    def draw_current_palette(self):
        canvas = self.current_palette_canvas; canvas.delete("all")
        size = CURRENT_PALETTE_SLOT_SIZE; padding = 2
        for i in range(16):
            row, col = divmod(i, 4); x1 = col * (size + padding) + padding; y1 = row * (size + padding) + padding; x2 = x1 + size; y2 = y1 + size
            color = self.active_msx_palette[i]; outline_color = "red" if i == self.selected_palette_slot else "grey"; outline_width = 3 if i == self.selected_palette_slot else 1
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline_color, width=outline_width, tags=f"pal_slot_{i}")
    def draw_512_picker(self):
        canvas = self.msx2_picker_canvas; canvas.delete("all")
        size = MSX2_PICKER_SQUARE_SIZE; padding = 1; cols = MSX2_PICKER_COLS
        for i in range(512):
            row, col = divmod(i, cols); x1 = col * (size + padding) + padding; y1 = row * (size + padding) + padding; x2 = x1 + size; y2 = y1 + size
            hex_color = msx2_512_colors_hex[i]; r, g, b = msx2_512_colors_rgb7[i]
            canvas.create_rectangle(x1, y1, x2, y2, fill=hex_color, outline="grey", width=1, tags=(f"msx2_picker_{i}", f"msx2_rgb_{r}_{g}_{b}"))
    def update_palette_info_labels(self):
        slot = self.selected_palette_slot
        if 0 <= slot < 16:
            color_hex = self.active_msx_palette[slot]; rgb7 = (-1,-1,-1)
            try: idx512 = msx2_512_colors_hex.index(color_hex); rgb7 = msx2_512_colors_rgb7[idx512]
            except ValueError: pass
            self.selected_slot_label.config(text=f"Slot: {slot}"); self.selected_slot_color_label.config(bg=color_hex)
            self.selected_slot_rgb_label.config(text=f"RGB: {color_hex} ({rgb7[0]},{rgb7[1]},{rgb7[2]})")
            self.rgb_r_var.set(str(rgb7[0]) if rgb7[0] != -1 else "?"); self.rgb_g_var.set(str(rgb7[1]) if rgb7[1] != -1 else "?"); self.rgb_b_var.set(str(rgb7[2]) if rgb7[2] != -1 else "?")
        else:
            self.selected_slot_label.config(text="Slot: -"); self.selected_slot_color_label.config(bg="grey"); self.selected_slot_rgb_label.config(text="RGB: -"); self.rgb_r_var.set(""); self.rgb_g_var.set(""); self.rgb_b_var.set("")
    # --- ^^^ Palette Editor Drawing ^^^ ---

    # ... (draw_tileset_viewer, update_tile_info_label unchanged) ...
    def draw_tileset_viewer(self, canvas, highlighted_tile_index):
        canvas.delete("all"); padding = 1; size = VIEWER_TILE_SIZE; max_rows = math.ceil(num_tiles_in_set / NUM_TILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding; canvas_width = NUM_TILES_ACROSS * (size + padding) + padding; str_scroll = f"0 0 {float(canvas_width)} {float(canvas_height)}"
        current_scroll = canvas.cget("scrollregion");
        if isinstance(current_scroll, tuple): current_scroll = " ".join(map(str, current_scroll))
        if current_scroll != str_scroll: canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        for i in range(num_tiles_in_set):
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS); base_x = tile_c * (size + padding) + padding; base_y = tile_r * (size + padding) + padding
            img = self.create_tile_image(i, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(f"tile_img_{i}", "tile_image"))
            outline_color = "red" if i == highlighted_tile_index else "grey"; outline_width = 2 if i == highlighted_tile_index else 1
            canvas.create_rectangle( base_x - padding/2, base_y - padding/2, base_x + size + padding/2, base_y + size + padding/2, outline=outline_color, width=outline_width, tags=f"tile_border_{i}")
    def update_tile_info_label(self): self.tile_info_label.config(text=f"Tile: {current_tile_index}/{max(0, num_tiles_in_set-1)}")
    # ... (draw_supertile_definition_canvas, draw_supertile_selector, update_supertile_info_labels unchanged) ...
    def draw_supertile_definition_canvas(self):
        canvas = self.supertile_def_canvas; canvas.delete("all")
        if not (0 <= current_supertile_index < num_supertiles): return
        definition = supertiles_data[current_supertile_index]; size = SUPERTILE_DEF_TILE_SIZE
        for r in range(SUPERTILE_GRID_DIM):
            for c in range(SUPERTILE_GRID_DIM):
                tile_idx = definition[r][c]; base_x = c * size; base_y = r * size
                img = self.create_tile_image(tile_idx, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"def_tile_{r}_{c}")
                canvas.create_rectangle(base_x, base_y, base_x + size, base_y + size, outline="grey")
    def draw_supertile_selector(self, canvas, highlighted_supertile_index):
        canvas.delete("all"); padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; max_rows = math.ceil(num_supertiles / NUM_SUPERTILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding; canvas_width = NUM_SUPERTILES_ACROSS * (size + padding) + padding; str_scroll = f"0 0 {float(canvas_width)} {float(canvas_height)}"
        current_scroll = canvas.cget("scrollregion");
        if isinstance(current_scroll, tuple): current_scroll = " ".join(map(str, current_scroll))
        if current_scroll != str_scroll: canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        for i in range(num_supertiles):
            st_r, st_c = divmod(i, NUM_SUPERTILES_ACROSS); base_x = st_c * (size + padding) + padding; base_y = st_r * (size + padding) + padding
            img = self.create_supertile_image(i, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(f"st_img_{i}", "st_image"))
            outline_color = "red" if i == highlighted_supertile_index else "grey"; outline_width = 2 if i == highlighted_supertile_index else 1
            canvas.create_rectangle(base_x - padding/2, base_y - padding/2, base_x + size + padding/2, base_y + size + padding/2, outline=outline_color, width=outline_width, tags=f"st_border_{i}")
    def update_supertile_info_labels(self): self.supertile_def_info_label.config(text=f"Editing Supertile: {current_supertile_index}/{max(0, num_supertiles-1)}"); self.supertile_tile_select_label.config(text=f"Selected Tile for Placing: {selected_tile_for_supertile}"); self.supertile_sel_info_label.config(text=f"Supertiles: {num_supertiles}")

    # --- vvv MODIFIED Map Drawing vvv ---
    def draw_map_canvas(self):
        """Draws map, supertile grid, window view, and handles based on state."""
        canvas = self.map_canvas
        canvas.delete("all") # Clear everything first

        # --- 1. Calculate Sizes ---
        zoomed_tile_size = self.get_zoomed_tile_size()
        zoomed_supertile_size = SUPERTILE_GRID_DIM * zoomed_tile_size

        # --- 2. Update Scroll Region ---
        map_pixel_width = map_width * zoomed_supertile_size
        map_pixel_height = map_height * zoomed_supertile_size
        str_scroll = f"0 0 {float(map_pixel_width)} {float(map_pixel_height)}"
        current_scroll = canvas.cget("scrollregion")
        if isinstance(current_scroll, tuple): current_scroll = " ".join(map(str, current_scroll))
        if current_scroll != str_scroll:
            canvas.config(scrollregion=(0, 0, map_pixel_width, map_pixel_height))

        # --- 3. Draw Supertile Images ---
        # Determine visible area (optional optimization, simpler to draw all)
        # For simplicity, draw all supertiles; Tkinter clips what's off-screen
        for r in range(map_height):
            for c in range(map_width):
                 supertile_idx = map_data[r][c]
                 # Calculate top-left corner in canvas pixels
                 base_x = c * zoomed_supertile_size
                 base_y = r * zoomed_supertile_size
                 # Get/create image at the required zoomed size
                 img = self.create_supertile_image(supertile_idx, zoomed_supertile_size)
                 # Draw image
                 canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=("map_supertile_image")) # Use common tag

        # --- 4. Draw Supertile Grid (if enabled) ---
        if self.show_supertile_grid.get():
            grid_color = GRID_COLOR_CYCLE[self.grid_color_index]
            # Draw vertical lines
            for c in range(map_width + 1):
                x = c * zoomed_supertile_size
                canvas.create_line(x, 0, x, map_pixel_height, fill=grid_color, dash=GRID_DASH_PATTERN, tags="supertile_grid")
            # Draw horizontal lines
            for r in range(map_height + 1):
                y = r * zoomed_supertile_size
                canvas.create_line(0, y, map_pixel_width, y, fill=grid_color, dash=GRID_DASH_PATTERN, tags="supertile_grid")

        # --- 5. Draw Window View Overlay (if enabled) ---
        if self.show_window_view.get():
            grid_color = GRID_COLOR_CYCLE[self.grid_color_index]
            # Get current window view state (in TILE units)
            win_tx = self.window_view_tile_x
            win_ty = self.window_view_tile_y
            win_tw = self.window_view_tile_w.get()
            win_th = self.window_view_tile_h.get()

            # Calculate pixel coordinates and dimensions
            win_px = win_tx * zoomed_tile_size
            win_py = win_ty * zoomed_tile_size
            win_pw = win_tw * zoomed_tile_size
            win_ph = win_th * zoomed_tile_size

            # Draw the main rectangle border
            canvas.create_rectangle(
                win_px, win_py, win_px + win_pw, win_py + win_ph,
                outline=grid_color, width=1, dash=GRID_DASH_PATTERN, tags=("window_view_rect", "window_view_item")
            )

            # Draw darkening for the bottom half of the 27th row if applicable
            if win_th == MAX_WIN_VIEW_HEIGHT_TILES:
                half_tile_h_px = zoomed_tile_size / 2
                dark_y1 = win_py + win_ph - half_tile_h_px
                dark_y2 = win_py + win_ph
                # Create a semi-transparent rectangle (stipple might be more compatible)
                canvas.create_rectangle(
                    win_px, dark_y1, win_px + win_pw, dark_y2,
                    fill="gray50", # Use a standard gray
                    stipple="gray50", # Apply stipple pattern for transparency effect
                    outline="", # No outline for the overlay itself
                    tags=("window_view_overscan", "window_view_item")
                )


            # --- 6. Draw Resize Handles (if window view enabled) ---
            handle_size = WIN_VIEW_HANDLE_SIZE
            hs2 = handle_size // 2 # half size for centering
            handle_fill = grid_color
            handle_outline = "black" if grid_color != "#000000" else "white"

            # Define handle positions (center coordinates)
            handles = {
                'nw': (win_px, win_py),
                'n':  (win_px + win_pw / 2, win_py),
                'ne': (win_px + win_pw, win_py),
                'w':  (win_px, win_py + win_ph / 2),
                'e':  (win_px + win_pw, win_py + win_ph / 2),
                'sw': (win_px, win_py + win_ph),
                's':  (win_px + win_pw / 2, win_py + win_ph),
                'se': (win_px + win_pw, win_py + win_ph),
            }
            # Draw each handle
            for tag, (cx, cy) in handles.items():
                x1 = cx - hs2
                y1 = cy - hs2
                x2 = cx + hs2
                y2 = cy + hs2
                canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=handle_fill, outline=handle_outline, width=1,
                    tags=("window_view_handle", f"handle_{tag}", "window_view_item")
                )

        # --- 7. Update Zoom Label ---
        self.map_zoom_label.config(text=f"{int(self.map_zoom_level * 100)}%")

    def update_map_info_labels(self):
         self.map_size_label.config(text=f"{map_width} x {map_height}")
         self.map_supertile_select_label.config(text=f"Selected Supertile for Painting: {selected_supertile_for_map}")
         # Update window size entries from state variables
         self.window_view_tile_w.set(self.window_view_tile_w.get()) # Ensure IntVar reflects internal state if needed
         self.window_view_tile_h.set(self.window_view_tile_h.get())
         # Zoom label updated in draw_map_canvas

    # --- Event Handlers ---
    def on_tab_change(self, event): # Unchanged
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: self.update_all_displays(changed_level="palette")
        elif selected_tab == 1: self.update_all_displays(changed_level="tile")
        elif selected_tab == 2: self.update_all_displays(changed_level="supertile")
        elif selected_tab == 3: self.update_all_displays(changed_level="map")

    # --- Palette Editor Handlers ---
    def handle_current_palette_click(self, event):
        canvas = self.current_palette_canvas; size = CURRENT_PALETTE_SLOT_SIZE; padding = 2
        col = event.x // (size + padding); row = event.y // (size + padding)
        clicked_slot = row * 4 + col
        if 0 <= clicked_slot < 16:
            if self.selected_palette_slot != clicked_slot:
                self.selected_palette_slot = clicked_slot
                self.draw_current_palette() # Redraw highlight
                self.update_palette_info_labels() # Update info display

    def handle_512_picker_click(self, event):
        if not (0 <= self.selected_palette_slot < 16): return
        canvas = self.msx2_picker_canvas; size = MSX2_PICKER_SQUARE_SIZE; padding = 1; cols = MSX2_PICKER_COLS
        canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y)
        col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding))
        clicked_index = row * cols + col
        if 0 <= clicked_index < 512:
            new_color_hex = msx2_512_colors_hex[clicked_index]
            target_slot = self.selected_palette_slot
            if self.active_msx_palette[target_slot] != new_color_hex:
                self.active_msx_palette[target_slot] = new_color_hex
                print(f"Set Palette Slot {target_slot} to {new_color_hex}")
                self.clear_all_caches()
                self.update_all_displays(changed_level="all")
        else: print("Clicked outside valid color range in picker.")

    def handle_rgb_apply(self):
        if not (0 <= self.selected_palette_slot < 16): return
        try:
            r = int(self.rgb_r_var.get()); g = int(self.rgb_g_var.get()); b = int(self.rgb_b_var.get())
            if not (0 <= r <= 7 and 0 <= g <= 7 and 0 <= b <= 7): raise ValueError("RGB values must be 0-7.")
            new_color_hex = self._rgb7_to_hex(r, g, b); target_slot = self.selected_palette_slot
            if self.active_msx_palette[target_slot] != new_color_hex:
                 self.active_msx_palette[target_slot] = new_color_hex
                 print(f"Set Palette Slot {target_slot} to {new_color_hex} via RGB")
                 self.clear_all_caches(); self.update_all_displays(changed_level="all")
        except ValueError as e: messagebox.showerror("Invalid RGB", f"Invalid RGB input: {e}")

    def reset_palette_to_default(self):
        confirm = messagebox.askokcancel("Reset Palette", "Reset the active palette to the MSX2 default colors?\nThis will affect the appearance of all tiles and supertiles.")
        if confirm:
            new_default_palette = [];
            for r, g, b in MSX2_RGB7_VALUES: new_default_palette.append(self._rgb7_to_hex(r, g, b))
            if self.active_msx_palette != new_default_palette:
                self.active_msx_palette = new_default_palette; self.selected_palette_slot = 0
                global selected_color_index; selected_color_index = 0
                self.clear_all_caches(); self.update_all_displays(changed_level="all")
                print("Palette reset to MSX2 defaults.")
            else: print("Palette is already set to MSX2 defaults.")

    # --- Tile Editor Handlers ---
    def handle_editor_click(self, event):
        global last_drawn_pixel, current_tile_index, tileset_patterns
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE; r = event.y // EDITOR_PIXEL_SIZE
        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            pixel_value = 1 if event.num == 1 else 0
            if tileset_patterns[current_tile_index][r][c] != pixel_value:
                tileset_patterns[current_tile_index][r][c] = pixel_value
                self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
            last_drawn_pixel = (r, c)
    def handle_editor_drag(self, event):
        global last_drawn_pixel, current_tile_index, tileset_patterns
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE; r = event.y // EDITOR_PIXEL_SIZE
        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            if (r, c) != last_drawn_pixel:
                pixel_value = 1 if event.state & 0x100 else (0 if event.state & 0x400 else -1)
                if pixel_value != -1 and tileset_patterns[current_tile_index][r][c] != pixel_value:
                    tileset_patterns[current_tile_index][r][c] = pixel_value
                    self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
                last_drawn_pixel = (r, c)
    def handle_tile_editor_palette_click(self, event):
        global selected_color_index
        canvas = self.tile_editor_palette_canvas; size = PALETTE_SQUARE_SIZE; padding = 2
        col = event.x // (size + padding); row = event.y // (size + padding)
        clicked_index = row * 4 + col
        if 0 <= clicked_index < 16:
            if selected_color_index != clicked_index:
                selected_color_index = clicked_index
                self.draw_palette() # Redraw this palette only
    def set_row_color(self, row, fg_or_bg):
        global tileset_colors, current_tile_index, selected_color_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if not (0 <= selected_color_index < 16): return
        if 0 <= row < TILE_HEIGHT:
            current_fg_idx, current_bg_idx = tileset_colors[current_tile_index][row]; changed = False
            if fg_or_bg == 'fg' and current_fg_idx != selected_color_index: tileset_colors[current_tile_index][row] = (selected_color_index, current_bg_idx); changed = True
            elif fg_or_bg == 'bg' and current_bg_idx != selected_color_index: tileset_colors[current_tile_index][row] = (current_fg_idx, selected_color_index); changed = True
            if changed: self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
    def handle_tileset_click(self, event):
        global current_tile_index
        canvas = event.widget; padding = 1; size = VIEWER_TILE_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and current_tile_index != clicked_index: current_tile_index = clicked_index; self.update_all_displays(changed_level="tile")
    def flip_tile_horizontal(self):
        global tileset_patterns, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; new_pattern = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
        for r in range(TILE_HEIGHT): new_pattern[r] = current_pattern[r][::-1]
        tileset_patterns[current_tile_index] = new_pattern
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} flipped horizontally.")
    def flip_tile_vertical(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        tileset_patterns[current_tile_index].reverse()
        tileset_colors[current_tile_index].reverse()
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} flipped vertically.")
    def rotate_tile_90cw(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, WHITE_IDX, BLACK_IDX
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; new_pattern = [[0 for _ in range(TILE_WIDTH)] for _ in range(TILE_HEIGHT)]
        for r in range(TILE_HEIGHT):
            for c in range(TILE_WIDTH): new_pattern[c][(TILE_HEIGHT - 1) - r] = current_pattern[r][c]
        tileset_patterns[current_tile_index] = new_pattern
        tileset_colors[current_tile_index] = [(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] # Reset colors
        messagebox.showinfo("Rotation Complete", "Tile rotated.\nRow colors have been reset to default."); self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} rotated 90 CW (colors reset).")
    def shift_tile_up(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; current_colors = tileset_colors[current_tile_index]
        first_pattern_row = current_pattern[0]; first_color_row = current_colors[0]
        for i in range(TILE_HEIGHT - 1): current_pattern[i] = current_pattern[i + 1]; current_colors[i] = current_colors[i + 1]
        current_pattern[TILE_HEIGHT - 1] = first_pattern_row; current_colors[TILE_HEIGHT - 1] = first_color_row
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted up.")
    def shift_tile_down(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; current_colors = tileset_colors[current_tile_index]
        last_pattern_row = current_pattern[TILE_HEIGHT - 1]; last_color_row = current_colors[TILE_HEIGHT - 1]
        for i in range(TILE_HEIGHT - 1, 0, -1): current_pattern[i] = current_pattern[i - 1]; current_colors[i] = current_colors[i - 1]
        current_pattern[0] = last_pattern_row; current_colors[0] = last_color_row
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted down.")
    def shift_tile_left(self):
        global tileset_patterns, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]
        for r in range(TILE_HEIGHT):
            row_data = current_pattern[r]
            if TILE_WIDTH > 0: first_pixel = row_data[0];
            for c in range(TILE_WIDTH - 1): row_data[c] = row_data[c + 1]
            row_data[TILE_WIDTH - 1] = first_pixel
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted left.")
    def shift_tile_right(self):
        global tileset_patterns, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]
        for r in range(TILE_HEIGHT):
            row_data = current_pattern[r]
            if TILE_WIDTH > 0: last_pixel = row_data[TILE_WIDTH - 1]
            for c in range(TILE_WIDTH - 1, 0, -1): row_data[c] = row_data[c - 1]
            row_data[0] = last_pixel
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted right.")

    # --- Supertile Editor Handlers ---
    def handle_st_tileset_click(self, event):
        global selected_tile_for_supertile
        canvas = event.widget; padding = 1; size = VIEWER_TILE_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and selected_tile_for_supertile != clicked_index: selected_tile_for_supertile = clicked_index; self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile); self.update_supertile_info_labels()
    def handle_supertile_def_click(self, event):
        global current_supertile_index, supertiles_data
        if not (0 <= current_supertile_index < num_supertiles): return
        if not (0 <= selected_tile_for_supertile < num_tiles_in_set): messagebox.showwarning("Place Tile", "Please select a tile first."); return
        canvas = self.supertile_def_canvas; size = SUPERTILE_DEF_TILE_SIZE; col = event.x // size; row = event.y // size
        if 0 <= row < SUPERTILE_GRID_DIM and 0 <= col < SUPERTILE_GRID_DIM:
            if supertiles_data[current_supertile_index][row][col] != selected_tile_for_supertile:
                supertiles_data[current_supertile_index][row][col] = selected_tile_for_supertile
                self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")
    def handle_supertile_selector_click(self, event):
        global current_supertile_index
        canvas = event.widget; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and current_supertile_index != clicked_index: current_supertile_index = clicked_index; self.update_all_displays(changed_level="supertile")

    # --- Map Editor Handlers ---
    def handle_map_supertile_selector_click(self, event):
        global selected_supertile_for_map
        canvas = event.widget; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and selected_supertile_for_map != clicked_index: selected_supertile_for_map = clicked_index; self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map); self.update_map_info_labels()

    def _paint_map_cell(self, canvas_x, canvas_y):
        """Paints a supertile on the map at the given CANVAS coordinates."""
        global map_data, last_painted_map_cell
        canvas = self.map_canvas
        zoomed_supertile_size = SUPERTILE_GRID_DIM * self.get_zoomed_tile_size()
        if zoomed_supertile_size <= 0: return

        # Convert scrolled canvas coords to map cell coords (supertile grid)
        c = int(canvas_x // zoomed_supertile_size)
        r = int(canvas_y // zoomed_supertile_size)

        # Check bounds
        if 0 <= r < map_height and 0 <= c < map_width:
            current_cell_id = (r, c)
            # Only paint if different cell OR different supertile selected
            if current_cell_id != last_painted_map_cell:
                if map_data[r][c] != selected_supertile_for_map:
                    map_data[r][c] = selected_supertile_for_map
                    self.invalidate_minimap_background_cache()
                    self.draw_minimap() # Redraw minimap immediately after invalidation
                    # Redraw only this specific cell image
                    base_x = c * zoomed_supertile_size
                    base_y = r * zoomed_supertile_size
                    img = self.create_supertile_image(selected_supertile_for_map, zoomed_supertile_size)
                    tag = f"map_cell_{r}_{c}"
                    # Find existing image items with this specific tag (should be 0 or 1)
                    items = canvas.find_withtag(tag)
                    if items:
                        canvas.itemconfig(items[0], image=img) # Update existing image
                    else:
                        # Should not happen if map drawn correctly, but draw new as fallback
                        canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(tag, "map_supertile_image"))

                last_painted_map_cell = current_cell_id # Update last painted cell

    def handle_map_click_or_drag_start(self, event):
        """Handles initial NON-CTRL click: determines action (paint/window drag/resize)."""
        # Ignore if Ctrl is pressed (handled by pan_start) or an action is already in progress
        if self.is_ctrl_pressed or self.current_mouse_action is not None:
            return "break"

        global last_painted_map_cell
        canvas = self.map_canvas
        canvas.focus_set()
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)

        # Determine action based on click location
        action_determined = None
        handle = self._get_handle_at(canvas_x, canvas_y)

        if handle and self.show_window_view.get():
            action_determined = 'window_resizing'
            self.window_view_resize_handle = handle
            self.drag_start_x = canvas_x
            self.drag_start_y = canvas_y
            self.drag_start_win_tx = self.window_view_tile_x
            self.drag_start_win_ty = self.window_view_tile_y
            self.drag_start_win_tw = self.window_view_tile_w.get()
            self.drag_start_win_th = self.window_view_tile_h.get()
            print(f"Start Resize from handle: {handle}")

        elif self._is_inside_window_view(canvas_x, canvas_y):
            action_determined = 'window_dragging'
            self.drag_start_x = canvas_x
            self.drag_start_y = canvas_y
            self.drag_start_win_tx = self.window_view_tile_x
            self.drag_start_win_ty = self.window_view_tile_y
            print("Start Window Drag")

        else:
            action_determined = 'painting'
            last_painted_map_cell = None # Reset for single click paint
            self._paint_map_cell(canvas_x, canvas_y) # Paint immediately

        # Set the determined action
        self.current_mouse_action = action_determined
        self._update_map_cursor() # Update cursor for the new action (though paint doesn't have one)

    def handle_map_drag_release(self, event):
        """Handles mouse button release: stops paint/drag/resize/pan."""
        global last_painted_map_cell
        last_painted_map_cell = None # Stop continuous paint

        panning_was_active = self.is_panning

        if panning_was_active:
            self.is_panning = False
            # Cursor update happens below after flag reset

        # Always reset the ignore flag when the mouse button comes up,
        # regardless of whether panning was active or ctrl was released.
        self._ignore_current_drag_after_pan = False
        self._update_map_cursor() # Update cursor state AFTER flags are reset

        # Only run window finalization if we WEREN'T panning when Button-1 was released
        if not panning_was_active:
            if self.window_view_dragging:
                print("End Window Drag")
                self.window_view_dragging = False
                # Position is already snapped during drag

            if self.window_view_resizing:
                print(f"End Resize from handle: {self.window_view_resize_handle}")
                # Clamp final position and update entries
                self._clamp_window_view_position()
                self._update_window_size_vars_from_state() # Sync IntVars
                self.window_view_resizing = False
                self.window_view_resize_handle = None
                # Redraw needed to finalize visual state and ensure entries match
                self.draw_map_canvas()

            # Reset general window drag/resize states (might be redundant?)
            self.window_view_dragging = False
            self.window_view_resizing = False
            self.window_view_resize_handle = None

            # Ensure minimap is up-to-date at the end of any non-pan operation
            self.draw_minimap()

    # --- Map Grid/Window Event Handlers ---
    def toggle_supertile_grid(self):
        """Callback for the supertile grid checkbutton."""
        self.draw_map_canvas() # Redraw map to show/hide grid

    def toggle_window_view(self):
        """Callback for the window view checkbutton."""
        print(f"*** toggle_window_view: START. State BEFORE get() is potentially {self.show_window_view.get()}") # Debug before draw

        # Redraw map to show/hide window view on the main canvas
        self.draw_map_canvas()

        # Force the main window to process drawing/state updates related to the main map
        self.root.update_idletasks()
        print(f"*** toggle_window_view: after update_idletasks. State is {self.show_window_view.get()}") # Debug after update

        # Now, redraw the minimap using the updated state
        print(f"*** toggle_window_view: Calling draw_minimap...") # Debug before call
        self.draw_minimap()
        print(f"*** toggle_window_view: draw_minimap finished.") # Debug after call

    def cycle_grid_color(self):
        """Cycles through the available grid colors."""
        self.grid_color_index = (self.grid_color_index + 1) % len(GRID_COLOR_CYCLE)
        # Redraw map if grids are visible
        if self.show_supertile_grid.get() or self.show_window_view.get():
            self.draw_map_canvas()
        print(f"Grid color set to: {GRID_COLOR_CYCLE[self.grid_color_index]}")

    def apply_window_size_from_entries(self):
        """Applies the W/H values from the Entry widgets."""
        try:
            new_w = self.window_view_tile_w.get() # Get value from IntVar
            new_h = self.window_view_tile_h.get()

            # Validate range
            min_w, max_w = 1, 32
            min_h, max_h = 1, MAX_WIN_VIEW_HEIGHT_TILES # Use constant
            if not (min_w <= new_w <= max_w and min_h <= new_h <= max_h):
                messagebox.showerror("Invalid Size", f"Window width must be {min_w}-{max_w}, height {min_h}-{max_h}.")
                # Reset entries to current state if invalid
                self.update_window_size_entries()
                return

            # If size changed, redraw the map
            # (IntVar should already hold the value, no need to set self.window_view_tile_w/h directly)
            self.draw_map_canvas()
            print(f"Window view size set to {new_w}x{new_h} tiles via input.")

        except tk.TclError:
             messagebox.showerror("Invalid Input", "Please enter valid integer numbers for width and height.")
             self.update_window_size_entries() # Reset on error
        except Exception as e:
             messagebox.showerror("Error", f"Could not apply size: {e}")
             self.update_window_size_entries()

    def update_window_size_entries(self):
        """Updates the W/H entry boxes to match the current state."""
        # This ensures IntVars linked to entries have the correct value
        self.window_view_tile_w.set(self.window_view_tile_w.get())
        self.window_view_tile_h.set(self.window_view_tile_h.get())

    def _do_window_move_drag(self, current_canvas_x, current_canvas_y):
        """Helper function to handle window view movement during drag."""
        zoomed_tile_size = self.get_zoomed_tile_size()
        if zoomed_tile_size <= 0: return

        # Calculate drag distance in canvas pixels
        delta_x = current_canvas_x - self.drag_start_x
        delta_y = current_canvas_y - self.drag_start_y

        # Calculate drag distance in TILES (integer steps)
        delta_tile_x = round(delta_x / zoomed_tile_size)
        delta_tile_y = round(delta_y / zoomed_tile_size)

        # Calculate new top-left TILE coordinate
        new_tx = self.drag_start_win_tx + delta_tile_x
        new_ty = self.drag_start_win_ty + delta_tile_y

        # Clamp position within map bounds (in tile units)
        max_tile_x = (map_width * SUPERTILE_GRID_DIM) - self.window_view_tile_w.get()
        max_tile_y = (map_height * SUPERTILE_GRID_DIM) - self.window_view_tile_h.get()
        clamped_tx = max(0, min(new_tx, max_tile_x))
        clamped_ty = max(0, min(new_ty, max_tile_y))

        # Update state only if position changed
        if self.window_view_tile_x != clamped_tx or self.window_view_tile_y != clamped_ty:
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.draw_map_canvas() # Redraw to show moved window

    def _do_window_resize_drag(self, current_canvas_x, current_canvas_y):
        """Helper function to handle window view resizing during drag."""
        zoomed_tile_size = self.get_zoomed_tile_size()
        if zoomed_tile_size <= 0: return

        # Get starting dimensions and position in TILE units
        start_tx = self.drag_start_win_tx
        start_ty = self.drag_start_win_ty
        start_tw = self.drag_start_win_tw
        start_th = self.drag_start_win_th

        # Calculate current mouse position in TILE units (relative to map 0,0)
        current_tile_x = round(current_canvas_x / zoomed_tile_size)
        current_tile_y = round(current_canvas_y / zoomed_tile_size)

        # Calculate new dimensions based on handle and mouse position
        new_tx = start_tx
        new_ty = start_ty
        new_tw = start_tw
        new_th = start_th
        handle = self.window_view_resize_handle

        # Adjust X and Width based on handle
        if 'w' in handle: # West handles affect left edge (tx) and width
            new_tx = min(current_tile_x, start_tx + start_tw - 1) # Don't allow negative width
            new_tw = start_tw + (start_tx - new_tx)
        elif 'e' in handle: # East handles affect width only
            new_tw = max(1, current_tile_x - start_tx + 1) # Ensure at least 1 width

        # Adjust Y and Height based on handle
        if 'n' in handle: # North handles affect top edge (ty) and height
            new_ty = min(current_tile_y, start_ty + start_th - 1)
            new_th = start_th + (start_ty - new_ty)
        elif 's' in handle: # South handles affect height only
            new_th = max(1, current_tile_y - start_ty + 1)

        # Clamp dimensions to valid range (1x1 to 32xMaxH)
        min_w, max_w = 1, 32
        min_h, max_h = 1, MAX_WIN_VIEW_HEIGHT_TILES
        clamped_tw = max(min_w, min(new_tw, max_w))
        clamped_th = max(min_h, min(new_th, max_h))

        # If width/height changed due to clamping, adjust position if necessary
        # (e.g., if dragging 'w' handle and clamped_tw < new_tw)
        if 'w' in handle and clamped_tw != new_tw:
            new_tx = start_tx + start_tw - clamped_tw
        if 'n' in handle and clamped_th != new_th:
            new_ty = start_ty + start_th - clamped_th

        # Clamp position within map bounds (0,0 to max_map_tile - current_size)
        max_map_tile_x = map_width * SUPERTILE_GRID_DIM
        max_map_tile_y = map_height * SUPERTILE_GRID_DIM
        clamped_tx = max(0, min(new_tx, max_map_tile_x - clamped_tw))
        clamped_ty = max(0, min(new_ty, max_map_tile_y - clamped_th))

        # Update state only if position or size changed
        if (self.window_view_tile_x != clamped_tx or
            self.window_view_tile_y != clamped_ty or
            self.window_view_tile_w.get() != clamped_tw or
            self.window_view_tile_h.get() != clamped_th):
            #
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.window_view_tile_w.set(clamped_tw) # Update IntVars
            self.window_view_tile_h.set(clamped_th)
            # self.update_window_size_entries() # Update entries visually
            self.draw_map_canvas() # Redraw to show resize

    def move_window_view_keyboard(self, dx, dy):
        """Moves the window view by dx, dy TILE steps."""
        if not self.show_window_view.get():
            return # Only move if visible

        # Calculate new target position
        new_tx = self.window_view_tile_x + dx
        new_ty = self.window_view_tile_y + dy

        # Clamp within map bounds
        current_w = self.window_view_tile_w.get()
        current_h = self.window_view_tile_h.get()
        max_tile_x = (map_width * SUPERTILE_GRID_DIM) - current_w
        max_tile_y = (map_height * SUPERTILE_GRID_DIM) - current_h
        clamped_tx = max(0, min(new_tx, max_tile_x))
        clamped_ty = max(0, min(new_ty, max_tile_y))

        # Update if position changed
        if self.window_view_tile_x != clamped_tx or self.window_view_tile_y != clamped_ty:
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.draw_map_canvas() # Redraw

    def handle_map_keypress(self, event):
        """Handles key presses when the map canvas has focus."""
        key = event.keysym.lower() # Get lowercase keysym

        if key == 'w':
            self.move_window_view_keyboard(0, -1) # Move up
        elif key == 'a':
            self.move_window_view_keyboard(-1, 0) # Move left
        elif key == 's':
            self.move_window_view_keyboard(0, 1)  # Move down
        elif key == 'd':
            self.move_window_view_keyboard(1, 0)  # Move right
        # else:
            # Optional: handle other keys if needed
            # print(f"Map KeyPress: {key}")


    # --- Map Zoom Handlers ---
    def handle_map_zoom_scroll(self, event):
        """Handles Ctrl+MouseWheel zooming."""
        # Determine zoom direction
        zoom_in = False
        if event.num == 4 or event.delta > 0: # Button 4 (Linux scroll up) or positive delta
            zoom_in = True
        elif event.num == 5 or event.delta < 0: # Button 5 (Linux scroll down) or negative delta
            zoom_in = False
        else:
            return # Unknown scroll event

        # Calculate zoom factor (multiplicative)
        factor = 1.1 if zoom_in else (1 / 1.1)

        # Get mouse position relative to canvas for zoom point
        canvas_x = self.map_canvas.canvasx(event.x)
        canvas_y = self.map_canvas.canvasy(event.y)

        # Perform zoom centered on the cursor
        self.zoom_map_at_point(factor, canvas_x, canvas_y)

    def change_map_zoom_mult(self, factor):
        """Applies multiplicative zoom, centered on the current canvas center."""
        canvas = self.map_canvas
        # Get current canvas view center
        cx = canvas.canvasx(canvas.winfo_width() / 2)
        cy = canvas.canvasy(canvas.winfo_height() / 2)
        # Zoom towards the center
        self.zoom_map_at_point(factor, cx, cy)

    def set_map_zoom(self, new_zoom_level):
        """Sets absolute zoom level, centered on current canvas center."""
        safe_zoom = max(0.1, min(6.0, float(new_zoom_level))) # Clamp to new limits
        current_zoom = self.map_zoom_level
        if current_zoom != safe_zoom:
            factor = safe_zoom / current_zoom
            # Calculate center point to zoom around
            canvas = self.map_canvas
            cx = canvas.canvasx(canvas.winfo_width() / 2)
            cy = canvas.canvasy(canvas.winfo_height() / 2)
            # Apply zoom using the calculated factor
            self.zoom_map_at_point(factor, cx, cy) # zoom_map_at_point handles redraw

    def get_zoomed_tile_size(self):
        """Calculates the current TILE size (base 8x8) based on zoom."""
        # Base size for 100% zoom is 8 pixels per tile edge
        zoomed_size = 8 * self.map_zoom_level
        # Ensure minimum size of 1 pixel
        return max(1, int(zoomed_size))

    def zoom_map_at_point(self, factor, zoom_x_canvas, zoom_y_canvas):
        """Zooms the map by 'factor', keeping the point (zoom_x/y_canvas) stationary,
           and clamps scroll to prevent top/left gaps when map is smaller than canvas."""
        canvas = self.map_canvas
        current_zoom = self.map_zoom_level
        min_zoom, max_zoom = 0.1, 6.0 # Use defined limits
        new_zoom = max(min_zoom, min(max_zoom, current_zoom * factor))

        # Only proceed if zoom actually changes significantly
        if abs(new_zoom - current_zoom) < 1e-9:
            return

        # --- Calculate scaling and update zoom level ---
        scale_change = new_zoom / current_zoom
        self.map_zoom_level = new_zoom # Update zoom level state FIRST

        # --- Initial Scroll Adjustment (Zoom to Cursor) ---
        # Calculate where the map point under the cursor *would* move to
        new_x = zoom_x_canvas * scale_change
        new_y = zoom_y_canvas * scale_change

        # Calculate how much the view needs to shift to counteract this movement
        delta_x = new_x - zoom_x_canvas
        delta_y = new_y - zoom_y_canvas

        # Apply the initial scroll adjustment based on cursor position
        canvas.xview_scroll(int(round(delta_x)), "units")
        canvas.yview_scroll(int(round(delta_y)), "units")

        # --- vvv NEW: Clamping Scroll Position vvv ---
        # Calculate the total pixel dimensions of the map content at the NEW zoom level
        # Note: get_zoomed_tile_size() now uses the updated self.map_zoom_level
        zoomed_tile_size_after_zoom = self.get_zoomed_tile_size() # Base tile size * new_zoom
        map_total_pixel_width_new = map_width * SUPERTILE_GRID_DIM * zoomed_tile_size_after_zoom
        map_total_pixel_height_new = map_height * SUPERTILE_GRID_DIM * zoomed_tile_size_after_zoom

        # Get the actual pixel dimensions of the canvas widget itself
        canvas_widget_width = canvas.winfo_width()
        canvas_widget_height = canvas.winfo_height()

        # Get the current scroll position *after* the initial adjustment
        current_xview = canvas.xview()
        current_yview = canvas.yview()

        # Check and clamp horizontal scroll if map is narrower than canvas
        needs_x_clamp = False
        if map_total_pixel_width_new < canvas_widget_width:
             # If map is smaller, top-left must be at 0. Check if it isn't (allow small float error).
             if current_xview[0] > 1e-6:
                 needs_x_clamp = True

        # Check and clamp vertical scroll if map is shorter than canvas
        needs_y_clamp = False
        if map_total_pixel_height_new < canvas_widget_height:
             # If map is smaller, top-left must be at 0.
             if current_yview[0] > 1e-6:
                 needs_y_clamp = True

        # Apply clamping if needed
        if needs_x_clamp:
            # print(f"Clamping X scroll: MapW={map_total_pixel_width_new:.1f} < CanvasW={canvas_widget_width}, xview={current_xview[0]:.3f}") # Debug
            canvas.xview_moveto(0.0)
        if needs_y_clamp:
            # print(f"Clamping Y scroll: MapH={map_total_pixel_height_new:.1f} < CanvasH={canvas_widget_height}, yview={current_yview[0]:.3f}") # Debug
            canvas.yview_moveto(0.0)
        # --- ^^^ END: Clamping Scroll Position ^^^ ---

        # --- Final Redraw ---
        # Redraw the entire map. This will use the final (potentially clamped) scroll position
        # and update the scrollregion based on the new map_total_pixel dimensions.
        self.draw_map_canvas()

        # Update the minimap viewport
        self.draw_minimap()

    # --- File Menu Commands ---
    # ... (new_project, save/load tileset/supertile/map remain mostly unchanged,
    #      ensure new_project resets new state like grid toggles, window view) ...
    def new_project(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        global supertiles_data, current_supertile_index, num_supertiles, selected_tile_for_supertile
        global map_data, map_width, map_height, selected_supertile_for_map, last_painted_map_cell
        global tile_clipboard_pattern, tile_clipboard_colors, supertile_clipboard_data
        confirm = messagebox.askokcancel("New Project", "Discard all current data (Tiles, Supertiles, Map, Palette, Clipboards) and start new?")
        if confirm:
            tileset_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; tileset_colors = [[(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; current_tile_index = 0; num_tiles_in_set = 1
            supertiles_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]; current_supertile_index = 0; num_supertiles = 1; selected_tile_for_supertile = 0
            map_width = DEFAULT_MAP_WIDTH; map_height = DEFAULT_MAP_HEIGHT; map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]; selected_supertile_for_map = 0; last_painted_map_cell = None
            tile_clipboard_pattern = None; tile_clipboard_colors = None; supertile_clipboard_data = None
            self.active_msx_palette = []; [ self.active_msx_palette.append(self._rgb7_to_hex(r, g, b)) for r, g, b in MSX2_RGB7_VALUES ]; self.selected_palette_slot = 0
            # --- Reset new state ---
            self.map_zoom_level = 1.0
            self.show_supertile_grid.set(False)
            self.show_window_view.set(False)
            self.grid_color_index = 0
            self.window_view_tile_x = 0
            self.window_view_tile_y = 0
            self.window_view_tile_w.set(DEFAULT_WIN_VIEW_WIDTH_TILES)
            self.window_view_tile_h.set(DEFAULT_WIN_VIEW_HEIGHT_TILES)
            self.window_view_dragging = False
            self.window_view_resizing = False
            self.window_view_resize_handle = None
            self.invalidate_minimap_background_cache() # Map reset in new project
            self._trigger_minimap_reconfigure() # Check/fix minimap aspect AFTER map update
            # --- End Reset ---
            self.root.title("MSX2 Tile/Map/Palette Editor - Untitled")
            self.current_project_base_path = None
            self._update_window_title()
            self.clear_all_caches()
            self.update_all_displays(changed_level="all")

    # --- Individual File Save/Load Methods (Modified for Project Handling) ---

    def save_palette(self, filepath=None):
        """Saves the current 16 active palette colors to a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        save_path = filepath
        # Prompt user if no path provided
        if not save_path:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".msxpal",
                filetypes=[("MSX Palette File", "*.msxpal"), ("All Files", "*.*")],
                title="Save MSX Palette As..."
            )
        # Return False if user cancelled dialog
        if not save_path:
            return False

        try:
            # Open file in binary write mode
            with open(save_path, 'wb') as f:
                # Sanity check palette length
                if len(self.active_msx_palette) != 16:
                    # Use internal print for non-interactive error
                    print("ERROR: Active palette length is not 16 during save!")
                    # Show message box only if called directly by user
                    if filepath is None:
                        messagebox.showerror("Palette Error", "Internal Error: Active palette does not contain 16 colors.")
                    return False # Indicate failure

                # Write each color as 3 bytes (R,G,B 0-7)
                for i in range(16):
                    hex_color = self.active_msx_palette[i]
                    r, g, b = self._hex_to_rgb7(hex_color) # Convert hex to 0-7 range
                    packed_bytes = struct.pack('BBB', r, g, b) # Pack as 3 bytes
                    f.write(packed_bytes)

            # Show success message ONLY if called directly by user
            if filepath is None:
                 messagebox.showinfo("Save Successful", f"Palette saved successfully to {os.path.basename(save_path)}")
            return True # Indicate success

        except Exception as e:
            # Always show error message on failure
            messagebox.showerror("Save Palette Error", f"Failed to save palette file '{os.path.basename(save_path)}':\n{e}")
            return False # Indicate failure

    def open_palette(self, filepath=None):
        """Loads a 16-color palette from a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        load_path = filepath
        # Prompt user if no path provided
        if not load_path:
            load_path = filedialog.askopenfilename(
                filetypes=[("MSX Palette File", "*.msxpal"), ("All Files", "*.*")],
                title="Open MSX Palette"
            )
        # Return False if user cancelled dialog
        if not load_path:
            return False

        try:
            expected_size = 16 * 3 # 16 colors * 3 bytes/color
            new_palette_hex = [] # Temp list for loaded colors

            # Open file in binary read mode
            with open(load_path, 'rb') as f:
                # Read expected bytes (+1 to check size)
                palette_data = f.read(expected_size + 1)

                # Validate file size
                if len(palette_data) < expected_size:
                    raise ValueError(f"Invalid file size. Expected {expected_size} bytes, got {len(palette_data)}.")
                if len(palette_data) > expected_size:
                    # Warn but proceed if file is larger
                    print(f"Warning: File '{os.path.basename(load_path)}' is larger than expected ({expected_size} bytes). Extra data ignored.")

                # Process the 16 colors (48 bytes)
                for i in range(16):
                    offset = i * 3
                    # Unpack 3 bytes for R, G, B (0-7)
                    r, g, b = struct.unpack_from('BBB', palette_data, offset)

                    # Validate RGB range (0-7)
                    if not (0 <= r <= 7 and 0 <= g <= 7 and 0 <= b <= 7):
                        print(f"Warning: Invalid RGB ({r},{g},{b}) at slot {i} in '{os.path.basename(load_path)}'. Clamping.")
                        r = max(0, min(7, r))
                        g = max(0, min(7, g))
                        b = max(0, min(7, b))

                    # Convert valid/clamped RGB(0-7) to hex string
                    hex_color = self._rgb7_to_hex(r, g, b)
                    new_palette_hex.append(hex_color)

            # --- Confirmation and Update ---
            confirm = True # Assume confirmed if called internally
            if filepath is None: # Ask only if user initiated this specific load
                confirm = messagebox.askokcancel(
                    "Load Palette",
                    "Replace the current active palette with data from this file?"
                )

            if confirm:
                # Commit the loaded palette
                self.active_msx_palette = new_palette_hex
                # Reset palette editor selection
                self.selected_palette_slot = 0
                # Reset tile editor color selection
                global selected_color_index
                selected_color_index = 0
                # Palette change invalidates everything visual
                self.clear_all_caches()
                self.invalidate_minimap_background_cache() # Also invalidate minimap
                self.update_all_displays(changed_level="all")
                # Switch tab only if loading individually
                if filepath is None:
                    self.notebook.select(self.tab_palette_editor)
                    messagebox.showinfo("Load Successful", f"Loaded palette from {os.path.basename(load_path)}")
                return True # Indicate success
            else:
                # User cancelled confirmation
                return False

        # --- Exception Handling ---
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{load_path}")
             return False
        except (struct.error, ValueError, EOFError) as e: # Catch struct, validation, and read errors
             messagebox.showerror("Open Palette Error", f"Invalid data, size, or format in palette file '{os.path.basename(load_path)}':\n{e}")
             return False
        except Exception as e:
             messagebox.showerror("Open Palette Error", f"Failed to open or parse palette file '{os.path.basename(load_path)}':\n{e}")
             return False

    def save_tileset(self, filepath=None):
        """Saves the current tileset data to a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global num_tiles_in_set, tileset_patterns, tileset_colors
        save_path = filepath
        if not save_path:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".SC4Tiles",
                filetypes=[("MSX Tileset", "*.SC4Tiles"), ("All Files", "*.*")],
                title="Save Tileset As..."
            )
        if not save_path:
            return False

        try:
             with open(save_path, 'wb') as f:
                # Write number of tiles
                num_byte = struct.pack('B', num_tiles_in_set)
                f.write(num_byte)
                # Write data for each tile
                for i in range(num_tiles_in_set):
                    # Write pattern data (8 bytes)
                    pattern = tileset_patterns[i]
                    for r in range(TILE_HEIGHT):
                        byte_val = 0
                        row_pattern = pattern[r]
                        for c in range(TILE_WIDTH):
                            if row_pattern[c] == 1:
                                byte_val = byte_val | (1 << (7 - c))
                        pattern_byte = struct.pack('B', byte_val)
                        f.write(pattern_byte)
                    # Write color data (8 bytes)
                    colors = tileset_colors[i]
                    for r in range(TILE_HEIGHT):
                        fg_idx, bg_idx = colors[r]
                        color_byte_val = ((fg_idx & 0x0F) << 4) | (bg_idx & 0x0F)
                        color_byte = struct.pack('B', color_byte_val)
                        f.write(color_byte)
             # Show success message ONLY if called directly by user
             if filepath is None:
                 messagebox.showinfo("Save Successful", f"Tileset saved successfully to {os.path.basename(save_path)}")
             return True # Indicate success
        except Exception as e:
             messagebox.showerror("Save Tileset Error", f"Failed to save tileset file '{os.path.basename(save_path)}':\n{e}")
             return False # Indicate failure

    def open_tileset(self, filepath=None):
        """Loads tileset data from a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, selected_tile_for_supertile
        load_path = filepath
        if not load_path:
            load_path = filedialog.askopenfilename(
                filetypes=[("MSX Tileset", "*.SC4Tiles"), ("All Files", "*.*")],
                title="Open Tileset"
            )
        if not load_path:
            return False

        try:
            with open(load_path, 'rb') as f:
                 # Read count
                 num_tiles_byte = f.read(1)
                 if not num_tiles_byte: raise ValueError("File empty or missing tile count byte.")
                 loaded_num_tiles = struct.unpack('B', num_tiles_byte)[0]
                 if not (1 <= loaded_num_tiles <= MAX_TILES): raise ValueError(f"Invalid tile count: {loaded_num_tiles}")

                 # Prepare temp storage
                 new_patterns = [[[0]*TILE_WIDTH for _r in range(TILE_HEIGHT)] for _i in range(MAX_TILES)]
                 new_colors = [[(WHITE_IDX, BLACK_IDX) for _r in range(TILE_HEIGHT)] for _i in range(MAX_TILES)]

                 # Read data
                 for i in range(loaded_num_tiles):
                     # Pattern
                     for r in range(TILE_HEIGHT):
                         pattern_byte = f.read(1);
                         if not pattern_byte: raise EOFError(f"EOF pattern T:{i} R:{r}")
                         byte_val = struct.unpack('B', pattern_byte)[0]
                         for c in range(TILE_WIDTH):
                             pixel_bit = (byte_val >> (7 - c)) & 1
                             new_patterns[i][r][c] = pixel_bit
                     # Color
                     for r in range(TILE_HEIGHT):
                         color_byte = f.read(1);
                         if not color_byte: raise EOFError(f"EOF color T:{i} R:{r}")
                         byte_val = struct.unpack('B', color_byte)[0]
                         fg_idx = (byte_val >> 4) & 0x0F
                         bg_idx = byte_val & 0x0F
                         new_colors[i][r] = (fg_idx, bg_idx)

            # --- Confirmation and Update ---
            confirm = True
            if filepath is None:
                confirm = messagebox.askokcancel("Load Tileset", "Replace current tileset?")

            if confirm:
                # Commit changes
                tileset_patterns = new_patterns
                tileset_colors = new_colors
                num_tiles_in_set = loaded_num_tiles
                current_tile_index = 0
                selected_tile_for_supertile = 0
                # Clear relevant caches and update UI
                self.clear_all_caches() # Tile changes affect supertiles and map
                self.invalidate_minimap_background_cache()
                self.update_all_displays(changed_level="all")
                # Switch tab only if loading individually
                if filepath is None:
                    self.notebook.select(self.tab_tile_editor)
                    messagebox.showinfo("Load Successful", f"Loaded {num_tiles_in_set} tiles from {os.path.basename(load_path)}")
                return True # Indicate success
            else:
                return False # User cancelled confirmation

        # --- Exception Handling ---
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{load_path}")
             return False
        except (EOFError, ValueError, struct.error) as e:
             messagebox.showerror("Open Tileset Error", f"Invalid data, size, or format in tileset file '{os.path.basename(load_path)}':\n{e}")
             return False
        except Exception as e:
             messagebox.showerror("Open Tileset Error", f"Failed to open or parse tileset file '{os.path.basename(load_path)}':\n{e}")
             return False

    def save_supertiles(self, filepath=None):
        """Saves the current supertile definitions to a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global num_supertiles, supertiles_data
        save_path = filepath
        if not save_path:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".SC4Super",
                filetypes=[("MSX Supertiles", "*.SC4Super"), ("All Files", "*.*")],
                title="Save Supertiles As..."
            )
        if not save_path:
            return False

        try:
            with open(save_path, 'wb') as f:
                # Write count
                num_byte = struct.pack('B', num_supertiles)
                f.write(num_byte)
                # Write data
                for i in range(num_supertiles):
                    definition = supertiles_data[i]
                    for r in range(SUPERTILE_GRID_DIM):
                        row_data = definition[r]
                        for c in range(SUPERTILE_GRID_DIM):
                            tile_index = row_data[c]
                            index_byte = struct.pack('B', tile_index)
                            f.write(index_byte)
            # Show success message ONLY if called directly
            if filepath is None:
                messagebox.showinfo("Save Successful", f"Supertiles saved successfully to {os.path.basename(save_path)}")
            return True # Indicate success
        except Exception as e:
             messagebox.showerror("Save Supertile Error", f"Failed to save supertiles file '{os.path.basename(save_path)}':\n{e}")
             return False # Indicate failure

    def open_supertiles(self, filepath=None):
        """Loads supertile definitions from a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global supertiles_data, num_supertiles, current_supertile_index, selected_supertile_for_map
        load_path = filepath
        if not load_path:
            load_path = filedialog.askopenfilename(
                filetypes=[("MSX Supertiles", "*.SC4Super"), ("All Files", "*.*")],
                title="Open Supertiles"
            )
        if not load_path:
            return False

        try:
            with open(load_path, 'rb') as f:
                # Read count
                num_st_byte = f.read(1)
                if not num_st_byte: raise ValueError("File empty or missing supertile count.")
                loaded_num_st = struct.unpack('B', num_st_byte)[0]
                if not (1 <= loaded_num_st <= MAX_SUPERTILES): raise ValueError(f"Invalid supertile count: {loaded_num_st}")

                # Prepare temp storage
                new_st_data = [[[0]*SUPERTILE_GRID_DIM for _r in range(SUPERTILE_GRID_DIM)] for _i in range(MAX_SUPERTILES)]

                # Read data
                for i in range(loaded_num_st):
                    for r in range(SUPERTILE_GRID_DIM):
                        for c in range(SUPERTILE_GRID_DIM):
                            idx_byte = f.read(1)
                            if not idx_byte: raise EOFError(f"EOF supertile {i} at [{r},{c}]")
                            tile_index = struct.unpack('B', idx_byte)[0]
                            new_st_data[i][r][c] = tile_index

            # --- Confirmation and Update ---
            confirm = True
            if filepath is None:
                confirm = messagebox.askokcancel("Load Supertiles", "Replace current supertiles?")

            if confirm:
                # Commit changes
                supertiles_data = new_st_data
                num_supertiles = loaded_num_st
                current_supertile_index = 0
                selected_supertile_for_map = 0
                # Clear caches and update UI
                self.supertile_image_cache.clear()
                self.invalidate_minimap_background_cache() # Map appearance might change
                self.update_all_displays(changed_level="supertile")
                # Switch tab only if loading individually
                if filepath is None:
                    self.notebook.select(self.tab_supertile_editor)
                    messagebox.showinfo("Load Successful", f"Loaded {num_supertiles} supertiles from {os.path.basename(load_path)}")
                return True # Indicate success
            else:
                return False # User cancelled confirmation

        # --- Exception Handling ---
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{load_path}")
             return False
        except (EOFError, ValueError, struct.error) as e:
             messagebox.showerror("Open Supertile Error", f"Invalid data, size, or format in supertile file '{os.path.basename(load_path)}':\n{e}")
             return False
        except Exception as e:
             messagebox.showerror("Open Supertile Error", f"Failed to open or parse supertiles file '{os.path.basename(load_path)}':\n{e}")
             return False

    def save_map(self, filepath=None):
        """Saves the current map data to a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global map_width, map_height, map_data
        save_path = filepath
        if not save_path:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".SC4Map",
                filetypes=[("MSX Map", "*.SC4Map"), ("All Files", "*.*")],
                title="Save Map As..."
            )
        if not save_path:
            return False

        try:
            with open(save_path, 'wb') as f:
                # Write dimensions (Big-endian)
                dim_bytes = struct.pack('>HH', map_width, map_height)
                f.write(dim_bytes)
                # Write map data
                for r in range(map_height):
                    row_data = map_data[r]
                    for c in range(map_width):
                        supertile_index = row_data[c]
                        index_byte = struct.pack('B', supertile_index)
                        f.write(index_byte)
            # Show success message ONLY if called directly
            if filepath is None:
                messagebox.showinfo("Save Successful", f"Map saved successfully to {os.path.basename(save_path)}")
            return True # Indicate success
        except Exception as e:
            messagebox.showerror("Save Map Error", f"Failed to save map file '{os.path.basename(save_path)}':\n{e}")
            return False # Indicate failure

    def open_map(self, filepath=None):
        """Loads map data from a binary file.
           Returns True on success, False on failure/cancel.
           If filepath is None, prompts the user.
        """
        global map_data, map_width, map_height
        load_path = filepath
        if not load_path:
            load_path = filedialog.askopenfilename(
                filetypes=[("MSX Map", "*.SC4Map"), ("All Files", "*.*")],
                title="Open Map"
            )
        if not load_path:
            return False

        try:
            with open(load_path, 'rb') as f:
                # Read header
                dim_bytes = f.read(4)
                if len(dim_bytes) < 4: raise ValueError("Invalid map header")
                # Unpack dimensions
                loaded_w, loaded_h = struct.unpack('>HH', dim_bytes)
                # Validate dimensions
                min_dim, max_dim = 1, 1024
                if not (min_dim <= loaded_w <= max_dim and min_dim <= loaded_h <= max_dim):
                     raise ValueError(f"Invalid dimensions: {loaded_w}x{loaded_h}")

                # Prepare temp storage
                new_map_data = [[0 for _c in range(loaded_w)] for _r in range(loaded_h)]

                # Read data
                for r in range(loaded_h):
                    for c in range(loaded_w):
                        st_idx_byte = f.read(1)
                        if not st_idx_byte: raise EOFError(f"EOF map at row {r}, col {c}")
                        supertile_index = struct.unpack('B', st_idx_byte)[0]
                        new_map_data[r][c] = supertile_index

            # --- Confirmation and Update ---
            confirm = True
            if filepath is None:
                confirm = messagebox.askokcancel("Load Map", "Replace current map?")

            if confirm:
                # Commit changes
                map_width = loaded_w
                map_height = loaded_h
                map_data = new_map_data
                # Invalidate minimap cache and update UI
                self.invalidate_minimap_background_cache()
                self.update_all_displays(changed_level="map")
                self._trigger_minimap_reconfigure() # Check/fix minimap aspect AFTER map update
                # Switch tab only if loading individually
                if filepath is None:
                    self.notebook.select(self.tab_map_editor)
                    messagebox.showinfo("Load Successful", f"Loaded {map_width}x{map_height} map from {os.path.basename(load_path)}")
                return True # Indicate success
            else:
                return False # User cancelled confirmation

        # --- Exception Handling ---
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{load_path}")
             return False
        except (EOFError, ValueError, struct.error) as e:
             messagebox.showerror("Open Map Error", f"Invalid data, size, or format in map file '{os.path.basename(load_path)}':\n{e}")
             return False
        except Exception as e:
             messagebox.showerror("Open Map Error", f"Failed to open or parse map file '{os.path.basename(load_path)}':\n{e}")
             return False

    # --- Project Save/Load Methods ---

    def save_project_as(self):
        """Prompts user for a base project name and saves all four component files."""
        # Ask for base path (user types name, selects directory)
        base_path = filedialog.asksaveasfilename(
            filetypes=[("MSX Project (Enter Base Name)", "*.*")], # Filter description
            title="Save Project As (Enter Base Name)"
        )
        # Exit if cancelled
        if not base_path:
            return

        # Construct full paths for each component file
        pal_path = base_path + ".msxpal"
        til_path = base_path + ".SC4Tiles"
        sup_path = base_path + ".SC4Super"
        map_path = base_path + ".SC4Map"

        # Attempt to save all components sequentially
        # Use the modified save methods which return True/False
        # Stop saving if any component fails
        success = True
        if success:
            print(f"Saving palette to: {pal_path}") # Debug
            success = self.save_palette(pal_path)
        if success:
            print(f"Saving tileset to: {til_path}") # Debug
            success = self.save_tileset(til_path)
        if success:
            print(f"Saving supertiles to: {sup_path}") # Debug
            success = self.save_supertiles(sup_path)
        if success:
            print(f"Saving map to: {map_path}") # Debug
            success = self.save_map(map_path)

        # Update state and UI if all saves were successful
        if success:
            self.current_project_base_path = base_path # Store the base path
            self._update_window_title() # Update title bar
            messagebox.showinfo("Project Saved", f"Project saved successfully as:\n{os.path.basename(base_path)}")
        else:
            # Individual error messages should have been shown by the failing save_* method
            messagebox.showerror("Project Save Error", "One or more project components failed to save.")

    def save_project(self):
        """Saves the project using the current base path, or calls Save As if none."""
        # Check if a project path is already known
        if self.current_project_base_path:
            base_path = self.current_project_base_path
            # Construct component paths
            pal_path = base_path + ".msxpal"
            til_path = base_path + ".SC4Tiles"
            sup_path = base_path + ".SC4Super"
            map_path = base_path + ".SC4Map"

            # Attempt to save all components
            success = True
            if success: success = self.save_palette(pal_path)
            if success: success = self.save_tileset(til_path)
            if success: success = self.save_supertiles(sup_path)
            if success: success = self.save_map(map_path)

            # Show appropriate message
            if success:
                # Note: No need to update title, path is already set
                messagebox.showinfo("Project Saved", f"Project saved successfully:\n{os.path.basename(base_path)}")
            else:
                messagebox.showerror("Project Save Error", "One or more project components failed to save.")
        else:
            # If no project path is known, act like "Save As..."
            self.save_project_as()

    def open_project(self):
        """Prompts user to select ONE project file, then loads all four components."""
        # Ask user to select any component file
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("MSX Tileset File (*.SC4Tiles)", "*.SC4Tiles"), # Suggest tileset first
                ("MSX Palette File (*.msxpal)", "*.msxpal"),
                ("MSX Supertile File (*.SC4Super)", "*.SC4Super"),
                ("MSX Map File (*.SC4Map)", "*.SC4Map"),
                ("All Files", "*.*")
            ],
            title="Open Project (Select Any Component File)"
        )
        # Exit if cancelled
        if not filepath:
            return

        # --- Determine Base Path ---
        directory = os.path.dirname(filepath)
        base_name_with_ext = os.path.basename(filepath)
        base_name, _ = os.path.splitext(base_name_with_ext)
        base_path = os.path.join(directory, base_name)

        # --- Construct Expected Paths ---
        pal_path = base_path + ".msxpal"
        til_path = base_path + ".SC4Tiles"
        sup_path = base_path + ".SC4Super"
        map_path = base_path + ".SC4Map"

        # --- Check Existence ---
        missing_files = []
        if not os.path.exists(pal_path): missing_files.append(os.path.basename(pal_path))
        if not os.path.exists(til_path): missing_files.append(os.path.basename(til_path))
        if not os.path.exists(sup_path): missing_files.append(os.path.basename(sup_path))
        if not os.path.exists(map_path): missing_files.append(os.path.basename(map_path))

        # Abort if files are missing
        if missing_files:
            messagebox.showerror("Open Project Error",
                                 f"Cannot open project '{base_name}'.\n"
                                 f"Missing component file(s):\n" + "\n".join(missing_files))
            return

        # --- Confirmation ---
        confirm = messagebox.askokcancel(
            "Open Project",
            f"Open project '{base_name}'?\nThis will replace your current work."
        )
        if not confirm:
            return

        # --- Attempt to Load All Components ---
        # Load methods now return True/False
        success = True
        print(f"Loading project '{base_name}'...")

        # Clear caches BEFORE loading new data
        self.clear_all_caches()
        self.invalidate_minimap_background_cache()

        # Load sequentially, checking success
        if success:
            print(f"  Loading palette: {pal_path}")
            success = self.open_palette(pal_path) # Call internal load
        if success:
            print(f"  Loading tileset: {til_path}")
            success = self.open_tileset(til_path) # Call internal load
        if success:
            print(f"  Loading supertiles: {sup_path}")
            success = self.open_supertiles(sup_path) # Call internal load
        if success:
            print(f"  Loading map: {map_path}")
            success = self.open_map(map_path) # Call internal load

        # --- Final Actions ---
        if success:
            # Store the new project path
            self.current_project_base_path = base_path
            # Update title
            self._update_window_title()
            # Update ALL displays (already done by individual loads, but ensure consistency)
            # self.update_all_displays("all") # Probably redundant now
            # Select a default tab
            self.notebook.select(self.tab_map_editor)
            messagebox.showinfo("Project Opened", f"Project '{base_name}' loaded successfully.")
        else:
            # Error messages were shown by the failing open_* method
            messagebox.showerror("Project Open Error", f"Failed to load one or more components for project '{base_name}'. The application state might be inconsistent.")
            # Optionally reset to prevent inconsistent state
            # self.new_project() # Call new_project without confirmation?
            # Update title to show inconsistency or reset
            self._update_window_title() # Reflects base_path might be set even on failure

    # --- Edit Menu Commands ---

    def set_tileset_size(self):
        global num_tiles_in_set, current_tile_index, selected_tile_for_supertile

        prompt = f"Enter number of tiles (1-{MAX_TILES}):"
        new_size_str = simpledialog.askstring(
            "Set Tileset Size",
            prompt,
            initialvalue=str(num_tiles_in_set)
        )

        if new_size_str:
            try:
                new_size = int(new_size_str)

                # Validate range first
                if not (1 <= new_size <= MAX_TILES):
                    messagebox.showerror("Invalid Size", f"Size must be between 1 and {MAX_TILES}.")
                    return # Exit if invalid

                reduced = new_size < num_tiles_in_set
                # Assume confirmed unless reducing
                confirmed = True
                if reduced:
                    confirm_prompt = f"Reducing size to {new_size} will discard tiles {new_size} to {num_tiles_in_set-1}. Proceed?"
                    confirmed = messagebox.askokcancel("Reduce Size", confirm_prompt)

                # Proceed if confirmed (or not reducing)
                if confirmed:
                    # Invalidate cache if reducing size
                    if reduced:
                        # Use a proper loop instead of list comprehension for side effects
                        for i in range(new_size, num_tiles_in_set):
                            self.invalidate_tile_cache(i)

                    # Update global count
                    num_tiles_in_set = new_size

                    # Clamp indices to the new valid range
                    current_tile_index = max(0, min(current_tile_index, num_tiles_in_set - 1))
                    # Handle potential num_tiles_in_set = 0 case (although prevented by validation)
                    max_valid_select_index = num_tiles_in_set - 1
                    if max_valid_select_index < 0:
                         selected_tile_for_supertile = 0
                    else:
                         selected_tile_for_supertile = max(0, min(selected_tile_for_supertile, max_valid_select_index))

                    # Update displays
                    self.update_all_displays(changed_level="all")

            except ValueError:
                # Handle error during int() conversion
                messagebox.showerror("Invalid Input", "Please enter a valid whole number.")

    def set_supertile_count(self):
        global num_supertiles, current_supertile_index, selected_supertile_for_map

        prompt = f"Enter number of supertiles (1-{MAX_SUPERTILES}):"
        new_count_str = simpledialog.askstring(
            "Set Supertile Count",
            prompt,
            initialvalue=str(num_supertiles)
        )

        if new_count_str:
            try:
                new_count = int(new_count_str)

                # Validate range first
                if not (1 <= new_count <= MAX_SUPERTILES):
                    messagebox.showerror("Invalid Count", f"Count must be between 1 and {MAX_SUPERTILES}.")
                    return # Exit if invalid

                reduced = new_count < num_supertiles
                # Assume confirmed unless reducing
                confirmed = True
                if reduced:
                    confirm_prompt = f"Reducing count to {new_count} will discard supertiles {new_count} to {num_supertiles-1}. Proceed?"
                    confirmed = messagebox.askokcancel("Reduce Count", confirm_prompt)

                # Proceed if confirmed (or not reducing)
                if confirmed:
                    # Invalidate cache if reducing size
                    if reduced:
                        # Use a proper loop
                        for i in range(new_count, num_supertiles):
                            self.invalidate_supertile_cache(i)

                    # Update global count
                    num_supertiles = new_count

                    # Clamp indices to the new valid range
                    current_supertile_index = max(0, min(current_supertile_index, num_supertiles - 1))
                    # Handle potential num_supertiles = 0 case
                    max_valid_select_index = num_supertiles - 1
                    if max_valid_select_index < 0:
                        selected_supertile_for_map = 0
                    else:
                        selected_supertile_for_map = max(0, min(selected_supertile_for_map, max_valid_select_index))

                    # Update displays
                    self.update_all_displays(changed_level="supertile")

            except ValueError:
                # Handle error during int() conversion
                messagebox.showerror("Invalid Input", "Please enter a valid whole number.")

    def set_map_dimensions(self):
        global map_width, map_height, map_data

        prompt = "Enter new dimensions (Width x Height):"
        dims_str = simpledialog.askstring(
            "Set Map Dimensions",
            prompt,
            initialvalue=f"{map_width}x{map_height}"
        )

        if dims_str:
            try:
                parts = dims_str.lower().split('x')
                if len(parts) != 2:
                    # Raise error for incorrect format
                    raise ValueError("Format must be WidthxHeight")

                # Parse dimensions
                new_w_str = parts[0].strip()
                new_h_str = parts[1].strip()
                new_w = int(new_w_str)
                new_h = int(new_h_str)

                # Define and check limits
                min_dim, max_dim = 1, 1024
                if not (min_dim <= new_w <= max_dim):
                     raise ValueError(f"Width must be between {min_dim} and {max_dim}")
                if not (min_dim <= new_h <= max_dim):
                     raise ValueError(f"Height must be between {min_dim} and {max_dim}")

                # Check if dimensions actually changed
                if new_w == map_width and new_h == map_height:
                    return # No change needed

                # Ask for confirmation only if reducing size
                reducing = (new_w < map_width or new_h < map_height)
                confirmed = True # Assume confirmed unless reducing
                if reducing:
                    confirm_prompt = "Reducing map size will discard data outside boundaries. Proceed?"
                    confirmed = messagebox.askokcancel("Resize Map", confirm_prompt)

                # Proceed if confirmed
                if confirmed:
                    # Create new empty map structure
                    new_map_data = [[0 for _ in range(new_w)] for _ in range(new_h)]
                    # Determine copy boundaries
                    rows_to_copy = min(map_height, new_h)
                    cols_to_copy = min(map_width, new_w)
                    # Copy existing data
                    for r in range(rows_to_copy):
                        for c in range(cols_to_copy):
                            new_map_data[r][c] = map_data[r][c]

                    # Update global variables
                    map_width = new_w
                    map_height = new_h
                    map_data = new_map_data

                    # Redraw map display
                    self.update_all_displays(changed_level="map")
                    self._trigger_minimap_reconfigure() # Check/fix minimap aspect AFTER map update

            except ValueError as e:
                # Handle parsing errors or validation errors
                messagebox.showerror("Invalid Input", f"Error setting dimensions: {e}")
            except Exception as e:
                # Catch other potential errors during resize/copy
                messagebox.showerror("Error", f"An unexpected error occurred during resize: {e}")

    
    # ... (clear_current_tile, clear_current_supertile, clear_map unchanged) ...
    def clear_current_tile(self):
        global tileset_patterns, tileset_colors, current_tile_index, WHITE_IDX, BLACK_IDX
        if not (0 <= current_tile_index < num_tiles_in_set): return
        prompt = f"Clear pattern and reset colors for tile {current_tile_index}?";
        if messagebox.askokcancel("Clear Tile", prompt): tileset_patterns[current_tile_index] = [[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)]; tileset_colors[current_tile_index] = [(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)]; self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
    def clear_current_supertile(self):
        global supertiles_data, current_supertile_index
        if not (0 <= current_supertile_index < num_supertiles): return
        prompt = f"Clear definition (set all to tile 0) for supertile {current_supertile_index}?";
        if messagebox.askokcancel("Clear Supertile", prompt): supertiles_data[current_supertile_index] = [[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)]; self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")
    def clear_map(self):
        global map_data, map_width, map_height
        prompt = "Clear entire map (set all to supertile 0)?";
        if messagebox.askokcancel("Clear Map", prompt):
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            self.invalidate_minimap_background_cache()
            self.update_all_displays(changed_level="map")

    # ... (copy/paste tile/supertile unchanged) ...
    def copy_current_tile(self):
        global tile_clipboard_pattern, tile_clipboard_colors, current_tile_index, num_tiles_in_set, tileset_patterns, tileset_colors
        if not (0 <= current_tile_index < num_tiles_in_set): messagebox.showwarning("Copy Tile", "No valid tile selected."); return
        tile_clipboard_pattern = copy.deepcopy(tileset_patterns[current_tile_index]); tile_clipboard_colors = copy.deepcopy(tileset_colors[current_tile_index]); print(f"Tile {current_tile_index} copied.")
    def paste_tile(self):
        global tile_clipboard_pattern, tile_clipboard_colors, current_tile_index, num_tiles_in_set, tileset_patterns, tileset_colors
        if tile_clipboard_pattern is None or tile_clipboard_colors is None: messagebox.showinfo("Paste Tile", "Tile clipboard is empty."); return
        if not (0 <= current_tile_index < num_tiles_in_set): messagebox.showwarning("Paste Tile", "No valid tile selected."); return
        if messagebox.askokcancel("Paste Tile", f"Overwrite Tile {current_tile_index}?"): tileset_patterns[current_tile_index] = copy.deepcopy(tile_clipboard_pattern); tileset_colors[current_tile_index] = copy.deepcopy(tile_clipboard_colors); self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Pasted onto Tile {current_tile_index}.")
    def copy_current_supertile(self):
        global supertile_clipboard_data, current_supertile_index, num_supertiles, supertiles_data
        if not (0 <= current_supertile_index < num_supertiles): messagebox.showwarning("Copy Supertile", "No valid supertile selected."); return
        supertile_clipboard_data = copy.deepcopy(supertiles_data[current_supertile_index]); print(f"Supertile {current_supertile_index} copied.")
    def paste_supertile(self):
        global supertile_clipboard_data, current_supertile_index, num_supertiles, supertiles_data
        if supertile_clipboard_data is None: messagebox.showinfo("Paste Supertile", "Supertile clipboard is empty."); return
        if not (0 <= current_supertile_index < num_supertiles): messagebox.showwarning("Paste Supertile", "No valid supertile selected."); return
        if messagebox.askokcancel("Paste Supertile", f"Overwrite Supertile {current_supertile_index}?"):
            supertiles_data[current_supertile_index] = copy.deepcopy(supertile_clipboard_data)
            self.invalidate_supertile_cache(current_supertile_index)
            self.invalidate_minimap_background_cache() # Appearance of map cells using this ST changed
            self.update_all_displays(changed_level="supertile")
            print(f"Pasted onto Supertile {current_supertile_index}.")
    # ... (add_new_tile, add_new_supertile unchanged) ...
    def add_new_tile(self):
        global num_tiles_in_set, current_tile_index, WHITE_IDX, BLACK_IDX
        if num_tiles_in_set >= MAX_TILES: messagebox.showwarning("Maximum Tiles", f"Max {MAX_TILES} tiles reached."); return
        num_tiles_in_set += 1; new_tile_idx = num_tiles_in_set - 1
        tileset_patterns[new_tile_idx] = [[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)]; tileset_colors[new_tile_idx] = [(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)]
        current_tile_index = new_tile_idx; self.update_all_displays(changed_level="tile"); self.scroll_viewers_to_tile(current_tile_index)
    def add_new_supertile(self):
        global num_supertiles, current_supertile_index
        if num_supertiles >= MAX_SUPERTILES: messagebox.showwarning("Maximum Supertiles", f"Max {MAX_SUPERTILES} supertiles reached."); return
        num_supertiles += 1; new_st_idx = num_supertiles - 1
        supertiles_data[new_st_idx] = [[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)]
        current_supertile_index = new_st_idx; self.update_all_displays(changed_level="supertile"); self.scroll_selectors_to_supertile(current_supertile_index)
    # ... (shift methods unchanged) ...
    def shift_tile_up(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; current_colors = tileset_colors[current_tile_index]
        first_pattern_row = current_pattern[0]; first_color_row = current_colors[0]
        for i in range(TILE_HEIGHT - 1): current_pattern[i] = current_pattern[i + 1]; current_colors[i] = current_colors[i + 1]
        current_pattern[TILE_HEIGHT - 1] = first_pattern_row; current_colors[TILE_HEIGHT - 1] = first_color_row
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted up.")
    def shift_tile_down(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]; current_colors = tileset_colors[current_tile_index]
        last_pattern_row = current_pattern[TILE_HEIGHT - 1]; last_color_row = current_colors[TILE_HEIGHT - 1]
        for i in range(TILE_HEIGHT - 1, 0, -1): current_pattern[i] = current_pattern[i - 1]; current_colors[i] = current_colors[i - 1]
        current_pattern[0] = last_pattern_row; current_colors[0] = last_color_row
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted down.")
    def shift_tile_left(self):
        global tileset_patterns, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]
        for r in range(TILE_HEIGHT):
            row_data = current_pattern[r]
            if TILE_WIDTH > 0: first_pixel = row_data[0];
            for c in range(TILE_WIDTH - 1): row_data[c] = row_data[c + 1]
            row_data[TILE_WIDTH - 1] = first_pixel
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted left.")
    def shift_tile_right(self):
        global tileset_patterns, current_tile_index, num_tiles_in_set
        if not (0 <= current_tile_index < num_tiles_in_set): return
        current_pattern = tileset_patterns[current_tile_index]
        for r in range(TILE_HEIGHT):
            row_data = current_pattern[r]
            if TILE_WIDTH > 0: last_pixel = row_data[TILE_WIDTH - 1]
            for c in range(TILE_WIDTH - 1, 0, -1): row_data[c] = row_data[c - 1]
            row_data[0] = last_pixel
        self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile"); print(f"Tile {current_tile_index} shifted right.")

    # --- Zoom Methods ---
    def change_map_zoom_mult(self, factor): # Renamed from change_map_zoom
        """Applies multiplicative zoom, centered on the current canvas center."""
        canvas = self.map_canvas
        view_x1, view_y1, view_x2, view_y2 = canvas.xview()[0], canvas.yview()[0], canvas.xview()[1], canvas.yview()[1]
        center_x_canvas = canvas.canvasx( (canvas.winfo_width() / 2) ) # Approximation of center
        center_y_canvas = canvas.canvasy( (canvas.winfo_height() / 2) )
        self.zoom_map_at_point(factor, center_x_canvas, center_y_canvas)

    def set_map_zoom(self, new_zoom_level):
        """Sets absolute zoom level, centered on current canvas center."""
        min_zoom, max_zoom = 0.1, 6.0 # New limits
        safe_zoom = max(min_zoom, min(max_zoom, float(new_zoom_level)))
        current_zoom = self.map_zoom_level
        if abs(current_zoom - safe_zoom) > 1e-9: # Avoid floating point noise
            factor = safe_zoom / current_zoom if current_zoom > 1e-9 else 1.0
            canvas = self.map_canvas
            center_x_canvas = canvas.canvasx(canvas.winfo_width() / 2)
            center_y_canvas = canvas.canvasy(canvas.winfo_height() / 2)
            self.zoom_map_at_point(factor, center_x_canvas, center_y_canvas)

    def get_zoomed_tile_size(self):
        """Calculates the current TILE size based on 8x8 base and zoom."""
        base_tile_size = 8 # 100% zoom = 8 pixels
        zoomed_size = base_tile_size * self.map_zoom_level
        return max(1, int(zoomed_size)) # Ensure at least 1 pixel

    def zoom_map_at_point(self, factor, zoom_x_canvas, zoom_y_canvas):
        """Zooms the map by 'factor', keeping the point (zoom_x/y_canvas) stationary,
           and clamps scroll to prevent top/left gaps when map is smaller than canvas."""
        canvas = self.map_canvas
        current_zoom = self.map_zoom_level
        min_zoom, max_zoom = 0.1, 6.0
        new_zoom = max(min_zoom, min(max_zoom, current_zoom * factor))

        # Only proceed if zoom actually changes significantly
        if abs(new_zoom - current_zoom) < 1e-9:
            return

        # --- 1. Get map coordinates under cursor BEFORE zoom ---
        # canvas.canvasx/y gives coordinates relative to the canvas's virtual (0,0)
        # including the current scroll offset.
        map_coord_x_at_cursor = canvas.canvasx(zoom_x_canvas)
        map_coord_y_at_cursor = canvas.canvasy(zoom_y_canvas)

        # --- 2. Update zoom level ---
        scale_change = new_zoom / current_zoom
        self.map_zoom_level = new_zoom # Update state

        # --- 3. Calculate target scroll position for zoom-to-cursor ---
        # The map point map_coord_x_at_cursor should end up at the screen
        # position zoom_x_canvas after zooming.
        # The new position of that map point in the scaled coordinate system is:
        new_map_coord_x = map_coord_x_at_cursor * scale_change
        new_map_coord_y = map_coord_y_at_cursor * scale_change

        # The target absolute coordinate for the viewport's top-left (scroll position)
        # should be such that: target_scroll_x + zoom_x_canvas = new_map_coord_x
        target_scroll_x_abs = new_map_coord_x - zoom_x_canvas
        target_scroll_y_abs = new_map_coord_y - zoom_y_canvas

        # --- 4. Calculate new total map dimensions and widget size ---
        zoomed_tile_size_new = self.get_zoomed_tile_size() # Uses updated self.map_zoom_level
        map_total_pixel_width_new = map_width * SUPERTILE_GRID_DIM * zoomed_tile_size_new
        map_total_pixel_height_new = map_height * SUPERTILE_GRID_DIM * zoomed_tile_size_new

        # Ensure dimensions are at least 1 to avoid division by zero
        safe_map_width = max(1.0, map_total_pixel_width_new)
        safe_map_height = max(1.0, map_total_pixel_height_new)

        canvas_widget_width = canvas.winfo_width()
        canvas_widget_height = canvas.winfo_height()

        # --- 5. Convert target scroll position to fractions ---
        target_x_fraction = target_scroll_x_abs / safe_map_width
        target_y_fraction = target_scroll_y_abs / safe_map_height

        # --- 6. Clamp fractions to valid scroll range [0.0, max_scroll] ---
        # Calculate the maximum fraction allowed to prevent scrolling past the content edge
        max_scroll_x = max(0.0, safe_map_width - canvas_widget_width)
        max_scroll_y = max(0.0, safe_map_height - canvas_widget_height)
        max_x_fraction = max_scroll_x / safe_map_width
        max_y_fraction = max_scroll_y / safe_map_height

        clamped_x_fraction = max(0.0, min(target_x_fraction, max_x_fraction))
        clamped_y_fraction = max(0.0, min(target_y_fraction, max_y_fraction))

        # --- 7. Apply override clamping if map is smaller than canvas ---
        final_x_fraction = clamped_x_fraction
        final_y_fraction = clamped_y_fraction

        if map_total_pixel_width_new <= canvas_widget_width:
            final_x_fraction = 0.0 # Force to left edge

        if map_total_pixel_height_new <= canvas_widget_height:
            final_y_fraction = 0.0 # Force to top edge

        # --- 8. Apply the FINAL definite scroll position using moveto ---
        canvas.xview_moveto(final_x_fraction)
        canvas.yview_moveto(final_y_fraction)

        # --- 9. Final Redraw ---
        # Redraw the map. This uses the final scroll position set by moveto
        # and updates the scrollregion based on the new total map dimensions.
        self.draw_map_canvas()

        # Update the minimap viewport
        self.draw_minimap()

    def handle_map_zoom_scroll(self, event):
        """Handles Ctrl+MouseWheel zooming, centered on cursor."""
        factor = 0.0
        # Determine zoom direction and set multiplicative factor
        if event.num == 4 or event.delta > 0: # Zoom In
            factor = 1.1 # Smaller steps often feel better for scroll wheel
        elif event.num == 5 or event.delta < 0: # Zoom Out
            factor = 1 / 1.1
        else:
            return # Ignore other wheel events

        # Get mouse position relative to canvas content (scrolled coords)
        canvas = self.map_canvas
        zoom_x_canvas = canvas.canvasx(event.x)
        zoom_y_canvas = canvas.canvasy(event.y)

        # Perform zoom centered on the cursor
        self.zoom_map_at_point(factor, zoom_x_canvas, zoom_y_canvas)

    # --- Scrolling Methods ---

    def scroll_viewers_to_tile(self, tile_index):
        """Scrolls the tileset viewers to make the specified tile index visible."""
        # Basic input validation
        if tile_index < 0:
            return

        # Define layout parameters
        padding = 1
        tile_size = VIEWER_TILE_SIZE
        items_per_row = NUM_TILES_ACROSS

        # Calculate target row and y-coordinate
        row, _ = divmod(tile_index, items_per_row)
        target_y = row * (tile_size + padding)

        # --- Scroll main viewer ---
        canvas_main = self.tileset_canvas
        try:
            # Get scroll region info (might be tuple or string)
            scroll_info_tuple = canvas_main.cget("scrollregion")
            # Convert to string and split for consistent parsing
            scroll_info = str(scroll_info_tuple).split()

            # Check if format is valid ("0 0 width height")
            if len(scroll_info) == 4:
                # Extract total height
                total_height = float(scroll_info[3])

                # Avoid division by zero
                if total_height > 0:
                    # Calculate scroll fraction
                    fraction = target_y / total_height
                    # Clamp fraction to valid range [0.0, 1.0]
                    clamped_fraction = min(1.0, max(0.0, fraction))
                    # Perform the scroll
                    canvas_main.yview_moveto(clamped_fraction)
            # else: (Optional: handle invalid scrollregion format if needed)
            #     print(f"Warning: Invalid scrollregion format for main tileset viewer: {scroll_info}")

        except Exception as e:
            # Catch any error during scrolling
            print(f"Error scrolling main tileset viewer: {e}")

        # --- Scroll Supertile tab's viewer ---
        canvas_st = self.st_tileset_canvas
        try:
            scroll_info_st_tuple = canvas_st.cget("scrollregion")
            scroll_info_st = str(scroll_info_st_tuple).split()

            if len(scroll_info_st) == 4:
                total_height_st = float(scroll_info_st[3])

                if total_height_st > 0:
                    fraction_st = target_y / total_height_st
                    clamped_fraction_st = min(1.0, max(0.0, fraction_st))
                    canvas_st.yview_moveto(clamped_fraction_st)
            # else:
            #     print(f"Warning: Invalid scrollregion format for ST tileset viewer: {scroll_info_st}")

        except Exception as e:
            print(f"Error scrolling ST tileset viewer: {e}")

    def scroll_selectors_to_supertile(self, supertile_index):
        """Scrolls the supertile selectors to make the specified index visible."""
        # Basic input validation
        if supertile_index < 0:
             return

        # Define layout parameters
        padding = 1
        item_size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        items_per_row = NUM_SUPERTILES_ACROSS

        # Calculate target row and y-coordinate
        row, _ = divmod(supertile_index, items_per_row)
        target_y = row * (item_size + padding)

        # --- Scroll Supertile tab's selector ---
        canvas_st = self.supertile_selector_canvas
        try:
            scroll_info_tuple = canvas_st.cget("scrollregion")
            scroll_info = str(scroll_info_tuple).split()

            if len(scroll_info) == 4:
                total_height = float(scroll_info[3])

                if total_height > 0:
                    fraction = target_y / total_height
                    clamped_fraction = min(1.0, max(0.0, fraction))
                    canvas_st.yview_moveto(clamped_fraction)
            # else:
            #     print(f"Warning: Invalid scrollregion format for ST selector: {scroll_info}")

        except Exception as e:
            print(f"Error scrolling ST selector: {e}")

        # --- Scroll Map tab's selector ---
        canvas_map = self.map_supertile_selector_canvas
        try:
            scroll_info_map_tuple = canvas_map.cget("scrollregion")
            scroll_info_map = str(scroll_info_map_tuple).split()

            if len(scroll_info_map) == 4:
                total_height_map = float(scroll_info_map[3])

                if total_height_map > 0:
                    fraction_map = target_y / total_height_map
                    clamped_fraction_map = min(1.0, max(0.0, fraction_map))
                    canvas_map.yview_moveto(clamped_fraction_map)
            # else:
            #     print(f"Warning: Invalid scrollregion format for Map selector: {scroll_info_map}")

        except Exception as e:
             print(f"Error scrolling Map selector: {e}")

    # --- vvv NEW Grid/Window Handlers vvv ---
    def toggle_supertile_grid(self):
        """Callback for the supertile grid checkbutton."""
        self.draw_map_canvas() # Redraw map to show/hide grid

    def toggle_window_view(self):
        """Callback for the window view checkbutton."""
        self.draw_map_canvas() # Redraw map to show/hide window view
        self.draw_minimap()

    def cycle_grid_color(self):
        """Cycles through the available grid colors."""
        self.grid_color_index = (self.grid_color_index + 1) % len(GRID_COLOR_CYCLE)
        # Redraw map if grids are visible
        if self.show_supertile_grid.get() or self.show_window_view.get():
            self.draw_map_canvas()
        print(f"Grid color set to: {GRID_COLOR_CYCLE[self.grid_color_index]}")

    def apply_window_size_from_entries(self):
        """Applies the W/H values from the Entry widgets."""
        try:
            new_w = self.window_view_tile_w.get() # Get value from IntVar
            new_h = self.window_view_tile_h.get()

            # Validate range
            min_w, max_w = 1, 32
            min_h, max_h = 1, MAX_WIN_VIEW_HEIGHT_TILES
            valid = True
            if not (min_w <= new_w <= max_w):
                messagebox.showerror("Invalid Width", f"Window width must be {min_w}-{max_w}.")
                valid = False
            if not (min_h <= new_h <= max_h):
                messagebox.showerror("Invalid Height", f"Window height must be {min_h}-{max_h}.")
                valid = False

            if not valid:
                # Reset entries to current state if invalid
                self._update_window_size_vars_from_state() # Use internal helper
                return

            # If size changed (or even if not, just redraw for simplicity)
            self._clamp_window_view_position() # Ensure position is valid for new size
            self.draw_map_canvas()
            self.draw_minimap()
            print(f"Window view size set to {new_w}x{new_h} tiles via input.")

        except tk.TclError: # Handles non-integer input in IntVars
             messagebox.showerror("Invalid Input", "Please enter valid integer numbers for width and height.")
             self._update_window_size_vars_from_state() # Reset on error
        except Exception as e:
             messagebox.showerror("Error", f"Could not apply size: {e}")
             self._update_window_size_vars_from_state()

    def _update_window_size_vars_from_state(self):
        """Internal helper to set IntVars from the state variables."""
        # Needed because the IntVars are bound to entries, direct setting is best
        self.window_view_tile_w.set(self.window_view_tile_w.get()) # Trigger update if needed
        self.window_view_tile_h.set(self.window_view_tile_h.get())

    def _clamp_window_view_position(self):
        """Ensures the window view's top-left position is valid for its current size."""
        current_w = self.window_view_tile_w.get()
        current_h = self.window_view_tile_h.get()
        # Calculate max valid top-left tile coord
        max_tile_x = max(0, (map_width * SUPERTILE_GRID_DIM) - current_w)
        max_tile_y = max(0, (map_height * SUPERTILE_GRID_DIM) - current_h)
        # Clamp current position
        self.window_view_tile_x = max(0, min(self.window_view_tile_x, max_tile_x))
        self.window_view_tile_y = max(0, min(self.window_view_tile_y, max_tile_y))

    def move_window_view_keyboard(self, dx_tile, dy_tile):
        """Moves the window view by dx, dy TILE steps."""
        if not self.show_window_view.get():
            return # Only move if visible

        # Calculate new target position
        new_tx = self.window_view_tile_x + dx_tile
        new_ty = self.window_view_tile_y + dy_tile

        # Clamp within map bounds (recalculate max based on current size)
        current_w = self.window_view_tile_w.get()
        current_h = self.window_view_tile_h.get()
        max_tile_x = max(0, (map_width * SUPERTILE_GRID_DIM) - current_w)
        max_tile_y = max(0, (map_height * SUPERTILE_GRID_DIM) - current_h)
        clamped_tx = max(0, min(new_tx, max_tile_x))
        clamped_ty = max(0, min(new_ty, max_tile_y))

        # Update if position changed
        if self.window_view_tile_x != clamped_tx or self.window_view_tile_y != clamped_ty:
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.draw_map_canvas() # Redraw to show moved window
            self.draw_minimap()

    def handle_map_keypress(self, event):
        """Handles key presses when the map canvas has focus."""
        key = event.keysym.lower() # Get lowercase keysym

        if key == 'c':
            self.cycle_grid_color()
        elif self.show_window_view.get(): # Only move window if visible
            if key == 'w':
                self.move_window_view_keyboard(0, -1) # Move up
            elif key == 'a':
                self.move_window_view_keyboard(-1, 0) # Move left
            elif key == 's':
                self.move_window_view_keyboard(0, 1)  # Move down
            elif key == 'd':
                self.move_window_view_keyboard(1, 0)  # Move right

    # --- Window View Drag/Resize Handlers ---
    def _get_handle_at(self, canvas_x, canvas_y):
        """Checks if the click is on a resize handle, returns handle tag ('nw', 'n', etc.) or None."""
        if not self.show_window_view.get():
            return None
        # Find items tagged 'window_view_handle' near the click
        search_radius = WIN_VIEW_HANDLE_SIZE # Search slightly larger than handle
        items = self.map_canvas.find_overlapping(
            canvas_x - search_radius, canvas_y - search_radius,
            canvas_x + search_radius, canvas_y + search_radius
        )
        for item_id in items:
            tags = self.map_canvas.gettags(item_id)
            if "window_view_handle" in tags:
                for t in tags:
                    if t.startswith("handle_"):
                        return t.split("_")[1] # Return 'nw', 'n', etc.
        return None # No handle found

    def _is_inside_window_view(self, canvas_x, canvas_y):
        """Checks if the click is inside the window view rectangle bounds."""
        if not self.show_window_view.get():
            return False
        zoomed_tile_size = self.get_zoomed_tile_size()
        win_px = self.window_view_tile_x * zoomed_tile_size
        win_py = self.window_view_tile_y * zoomed_tile_size
        win_pw = self.window_view_tile_w.get() * zoomed_tile_size
        win_ph = self.window_view_tile_h.get() * zoomed_tile_size
        return (win_px <= canvas_x < win_px + win_pw and
                win_py <= canvas_y < win_py + win_ph)

    def handle_map_click_or_drag_start(self, event):
        """Handles initial click on map: starts paint, window drag, or resize."""
        global last_painted_map_cell
        canvas = self.map_canvas
        canvas.focus_set() # Ensure keyboard events go to the map
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)

        # Reset drag states
        self.window_view_dragging = False
        self.window_view_resizing = False
        self.window_view_resize_handle = None

        # Check for handle click first (priority)
        handle = self._get_handle_at(canvas_x, canvas_y)
        if handle and self.show_window_view.get():
            self.window_view_resizing = True
            self.window_view_resize_handle = handle
            self.drag_start_x = canvas_x
            self.drag_start_y = canvas_y
            self.drag_start_win_tx = self.window_view_tile_x
            self.drag_start_win_ty = self.window_view_tile_y
            self.drag_start_win_tw = self.window_view_tile_w.get()
            self.drag_start_win_th = self.window_view_tile_h.get()
            print(f"Start Resize from handle: {handle}")
        # Check for click inside window view (if not on handle)
        elif self._is_inside_window_view(canvas_x, canvas_y):
            self.window_view_dragging = True
            self.drag_start_x = canvas_x
            self.drag_start_y = canvas_y
            self.drag_start_win_tx = self.window_view_tile_x
            self.drag_start_win_ty = self.window_view_tile_y
            print("Start Window Drag")
        # Otherwise, treat as map painting
        else:
            last_painted_map_cell = None
            self._paint_map_cell(canvas_x, canvas_y)

    def handle_map_drag(self, event):
        """Handles motion for non-panning actions (paint, window drag/resize)."""
        # Ignore if panning or no action is set
        if self.current_mouse_action == 'panning' or self.current_mouse_action is None:
            return "break"

        canvas = self.map_canvas
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)

        # Perform action based on the current state
        if self.current_mouse_action == 'painting':
            self._paint_map_cell(canvas_x, canvas_y)
        elif self.current_mouse_action == 'window_dragging':
            self._do_window_move_drag(canvas_x, canvas_y)
        elif self.current_mouse_action == 'window_resizing':
            self._do_window_resize_drag(canvas_x, canvas_y)

        # Prevent other bindings? Usually not needed here if structure is correct.
        # return "break"

    def handle_map_drag_release(self, event):
        """Handles mouse button release: ends the current action."""
        global last_painted_map_cell
        last_painted_map_cell = None # Stop continuous paint

        action_at_release = self.current_mouse_action

        # Reset the current action state FIRST
        self.current_mouse_action = None

        # Perform any finalization based on the action that just finished
        if action_at_release == 'panning':
            # print("End Pan") # Debug
            pass # scan_dragto handles the state automatically

        elif action_at_release == 'window_dragging':
            print("End Window Drag")
            # Position is already snapped during drag

        elif action_at_release == 'window_resizing':
            print(f"End Resize from handle: {self.window_view_resize_handle}")
            # Clamp final position and update entries/IntVar state
            self._clamp_window_view_position()
            self._update_window_size_vars_from_state() # Sync IntVars post-resize
            self.window_view_resize_handle = None
            # Redraw needed to finalize visual state and ensure entries match
            self.draw_map_canvas()

        elif action_at_release == 'painting':
            # print("End Painting Drag") # Debug
            pass # No specific finalization needed

        # Update cursor AFTER action is None, based on current Ctrl state
        self._update_map_cursor()
        # Always update minimap at the end of any operation
        self.draw_minimap()

    def _do_window_move_drag(self, current_canvas_x, current_canvas_y):
        """Helper: Calculates and applies window movement during drag."""
        zoomed_tile_size = self.get_zoomed_tile_size()
        if zoomed_tile_size <= 0: return

        delta_x_pixels = current_canvas_x - self.drag_start_x
        delta_y_pixels = current_canvas_y - self.drag_start_y

        # Calculate movement in TILE units, snapping to grid
        # Use floor for consistent snapping direction
        delta_tile_x = math.floor(delta_x_pixels / zoomed_tile_size)
        delta_tile_y = math.floor(delta_y_pixels / zoomed_tile_size)

        # Calculate potential new top-left TILE coordinate
        new_tx = self.drag_start_win_tx + delta_tile_x
        new_ty = self.drag_start_win_ty + delta_tile_y

        # Clamp position within map bounds (using current W/H)
        current_w = self.window_view_tile_w.get()
        current_h = self.window_view_tile_h.get()
        max_tile_x = max(0, (map_width * SUPERTILE_GRID_DIM) - current_w)
        max_tile_y = max(0, (map_height * SUPERTILE_GRID_DIM) - current_h)
        clamped_tx = max(0, min(new_tx, max_tile_x))
        clamped_ty = max(0, min(new_ty, max_tile_y))

        # Update state and redraw ONLY if position actually changes
        if self.window_view_tile_x != clamped_tx or self.window_view_tile_y != clamped_ty:
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.draw_map_canvas() # Redraw to show moved window
            self.draw_minimap()

    def _do_window_resize_drag(self, current_canvas_x, current_canvas_y):
        """Helper: Calculates and applies window resize during drag."""
        zoomed_tile_size = self.get_zoomed_tile_size()
        if zoomed_tile_size <= 0: return

        # Starting state in TILE units
        start_tx = self.drag_start_win_tx
        start_ty = self.drag_start_win_ty
        start_tw = self.drag_start_win_tw
        start_th = self.drag_start_win_th
        start_br_tx = start_tx + start_tw # Bottom-right tile X (exclusive)
        start_br_ty = start_ty + start_th # Bottom-right tile Y (exclusive)

        # Current mouse position snapped to TILE grid
        current_tile_x = math.floor(current_canvas_x / zoomed_tile_size)
        current_tile_y = math.floor(current_canvas_y / zoomed_tile_size)

        # Calculate new potential corners based on handle
        new_tx = start_tx
        new_ty = start_ty
        new_br_tx = start_br_tx
        new_br_ty = start_br_ty
        handle = self.window_view_resize_handle

        # Adjust based on handle dragged
        if 'n' in handle: new_ty = current_tile_y
        if 's' in handle: new_br_ty = current_tile_y + 1 # +1 because BR is exclusive
        if 'w' in handle: new_tx = current_tile_x
        if 'e' in handle: new_br_tx = current_tile_x + 1

        # Ensure top-left is never beyond bottom-right
        new_tx = min(new_tx, new_br_tx - 1) # Ensure width >= 1
        new_ty = min(new_ty, new_br_ty - 1) # Ensure height >= 1
        new_br_tx = max(new_br_tx, new_tx + 1)
        new_br_ty = max(new_br_ty, new_ty + 1)

        # Calculate new width and height in tiles
        new_tw = new_br_tx - new_tx
        new_th = new_br_ty - new_ty

        # Clamp dimensions to allowed limits
        min_w, max_w = 1, 32
        min_h, max_h = 1, MAX_WIN_VIEW_HEIGHT_TILES
        clamped_tw = max(min_w, min(new_tw, max_w))
        clamped_th = max(min_h, min(new_th, max_h))

        # Adjust position if clamping changed dimensions, preserving the fixed corner/edge
        if 'n' in handle and clamped_th != new_th: new_ty = new_br_ty - clamped_th
        if 'w' in handle and clamped_tw != new_tw: new_tx = new_br_tx - clamped_tw
        if 's' in handle: new_br_ty = new_ty + clamped_th # Recalculate needed? No, height is clamped.
        if 'e' in handle: new_br_tx = new_tx + clamped_tw

        # Clamp position to stay within map boundaries
        max_map_tile_x = map_width * SUPERTILE_GRID_DIM
        max_map_tile_y = map_height * SUPERTILE_GRID_DIM
        clamped_tx = max(0, min(new_tx, max_map_tile_x - clamped_tw))
        clamped_ty = max(0, min(new_ty, max_map_tile_y - clamped_th))

        # Final check if clamping position changed dimensions again (shouldn't drastically)
        final_tw = min(clamped_tw, max_map_tile_x - clamped_tx)
        final_th = min(clamped_th, max_map_tile_y - clamped_ty)

        # Update state only if position or size changed
        if (self.window_view_tile_x != clamped_tx or
            self.window_view_tile_y != clamped_ty or
            self.window_view_tile_w.get() != final_tw or
            self.window_view_tile_h.get() != final_th):
            #
            self.window_view_tile_x = clamped_tx
            self.window_view_tile_y = clamped_ty
            self.window_view_tile_w.set(final_tw) # Update IntVars
            self.window_view_tile_h.set(final_th)
            # self._update_window_size_vars_from_state() # Update entries
            self.draw_map_canvas() # Redraw to show resize
            self.draw_minimap()

    # --- Minimap Methods ---

    def toggle_minimap(self):
        """Opens/raises the resizable minimap window."""
        if self.minimap_window is None or not tk.Toplevel.winfo_exists(self.minimap_window):
            self.minimap_window = tk.Toplevel(self.root)
            self.minimap_window.title("Minimap")
            # Set initial size, but allow resizing
            self.minimap_window.geometry(f"{MINIMAP_INITIAL_WIDTH}x{MINIMAP_INITIAL_HEIGHT}")
            # self.minimap_window.resizable(False, False) # REMOVE or set True

            self.minimap_canvas = tk.Canvas(
                self.minimap_window,
                bg="dark slate gray",
                highlightthickness=0
            )
            # Make canvas fill the resizable window
            self.minimap_canvas.pack(fill=tk.BOTH, expand=True) # MODIFIED pack options
            self.minimap_window.protocol("WM_DELETE_WINDOW", self._on_minimap_close)
            self.minimap_window.bind("<Configure>", self._on_minimap_configure)

            # Initial draw (will use initial geometry)
            # Need to ensure canvas has dimensions before first draw
            self.minimap_window.update_idletasks() # Process geometry requests
            self.draw_minimap()
        else:
            self.minimap_window.lift()
            self.minimap_window.focus_set()

    def _on_minimap_close(self):
        """Handles the closing of the minimap window."""
        if self.minimap_window:
            self.minimap_window.destroy() # Destroy the window
        self.minimap_window = None # Reset state variable
        self.minimap_canvas = None

    def draw_minimap(self):
        """Draws the minimap content: rendered background, viewport, window view."""
        if self.minimap_window is None or self.minimap_canvas is None: return
        if not tk.Toplevel.winfo_exists(self.minimap_window): self._on_minimap_close(); return

        canvas = self.minimap_canvas
        canvas.delete("all")

        # --- 1. Get Current Minimap Canvas Dimensions ---
        current_minimap_w = canvas.winfo_width()
        current_minimap_h = canvas.winfo_height()
        # If dimensions are 1, window hasn't been drawn properly yet, skip draw
        if current_minimap_w <= 1 or current_minimap_h <= 1:
            return

        # --- 2. Draw Rendered Map Background ---
        # Check cache first, also check if rendered size matches current canvas size
        if (self.minimap_background_cache is None or
            self.minimap_bg_rendered_width != current_minimap_w or
            self.minimap_bg_rendered_height != current_minimap_h):
            # Regenerate if cache is invalid or size changed
            self.minimap_background_cache = self._create_minimap_background_image(
                current_minimap_w, current_minimap_h
            )

        # Draw the cached background image (if successfully created)
        if self.minimap_background_cache:
            canvas.create_image(0, 0, image=self.minimap_background_cache, anchor=tk.NW, tags="minimap_bg_image")
        else:
            # Fallback: draw simple background if image creation failed
            canvas.create_rectangle(0, 0, current_minimap_w, current_minimap_h, fill="gray10")


        # --- 3. Calculate Scaling for Overlays ---
        map_total_pixel_w = map_width * SUPERTILE_GRID_DIM * TILE_WIDTH
        map_total_pixel_h = map_height * SUPERTILE_GRID_DIM * TILE_HEIGHT
        if map_total_pixel_w <= 0 or map_total_pixel_h <= 0: return

        # Calculate scale factors based on CURRENT minimap size
        scale_x = current_minimap_w / map_total_pixel_w
        scale_y = current_minimap_h / map_total_pixel_h
        scale = min(scale_x, scale_y) # Fit entirely, maintain aspect ratio

        # Calculate centering offsets based on CURRENT minimap size
        scaled_map_w = map_total_pixel_w * scale
        scaled_map_h = map_total_pixel_h * scale
        offset_x = (current_minimap_w - scaled_map_w) / 2
        offset_y = (current_minimap_h - scaled_map_h) / 2

        # --- 4. Draw Main Map Viewport Rectangle (Bolder) ---
        try:
            main_canvas = self.map_canvas
            scroll_x_frac = main_canvas.xview()
            scroll_y_frac = main_canvas.yview()

            # Calculate total BASE map pixel dimensions (at 100% zoom)
            map_total_base_w = map_width * SUPERTILE_GRID_DIM * TILE_WIDTH
            map_total_base_h = map_height * SUPERTILE_GRID_DIM * TILE_HEIGHT

            # Check if base dimensions are valid
            if map_total_base_w > 0 and map_total_base_h > 0:
                # Calculate visible area in BASE map pixel coordinates directly from scroll fractions
                map_base_px_x1 = scroll_x_frac[0] * map_total_base_w
                map_base_px_y1 = scroll_y_frac[0] * map_total_base_h
                map_base_px_x2 = scroll_x_frac[1] * map_total_base_w
                map_base_px_y2 = scroll_y_frac[1] * map_total_base_h

                # Scale these correct base map pixel coordinates to minimap coordinates
                vp_x1 = offset_x + map_base_px_x1 * scale
                vp_y1 = offset_y + map_base_px_y1 * scale
                vp_x2 = offset_x + map_base_px_x2 * scale
                vp_y2 = offset_y + map_base_px_y2 * scale

                canvas.create_rectangle(
                    vp_x1, vp_y1, vp_x2, vp_y2,
                    outline=self.MINIMAP_VIEWPORT_COLOR,
                    width=2, # <-- Bolder line
                    tags="minimap_viewport"
                )
        except Exception as e:
            print(f"Error drawing minimap viewport: {e}")

        # --- 5. Draw Window View Rectangle (Bolder, if enabled) ---
        current_state = self.show_window_view.get()
        print(f"--- draw_minimap: Value of self.show_window_view.get() is {current_state}")
        if current_state:
            try:
                win_tx = self.window_view_tile_x
                win_ty = self.window_view_tile_y
                win_tw = self.window_view_tile_w.get()
                win_th = self.window_view_tile_h.get()

                win_map_px1 = win_tx * TILE_WIDTH
                win_map_py1 = win_ty * TILE_HEIGHT
                win_map_px2 = win_map_px1 + (win_tw * TILE_WIDTH)
                win_map_py2 = win_map_py1 + (win_th * TILE_HEIGHT)

                wv_x1 = offset_x + win_map_px1 * scale
                wv_y1 = offset_y + win_map_py1 * scale
                wv_x2 = offset_x + win_map_px2 * scale
                wv_y2 = offset_y + win_map_py2 * scale

                canvas.create_rectangle(
                    wv_x1, wv_y1, wv_x2, wv_y2,
                    outline=self.MINIMAP_WIN_VIEW_COLOR,
                    width=2, # <-- Bolder line
                    dash=(4,4), # Keep dashed to differentiate
                    tags="minimap_window_view"
                )
                print("--- draw_minimap: Drawing window view overlay.") # Debug confirm draw
            except Exception as e:
                print(f"Error drawing minimap window view: {e}")
        else: #(optional print if skipped)
           print("--- draw_minimap: Skipping window view overlay.") # Debug confirm skip

    def _on_minimap_configure(self, event):
        """Callback when the minimap window is resized/moved."""
        # We only care about size changes for redrawing
        # Basic debouncing: wait a short time after the last configure event
        # before redrawing to avoid excessive calls during drag-resizing.
        debounce_ms = 150 # Adjust as needed (milliseconds)

        # Cancel any pending redraw timer
        if self.minimap_resize_timer is not None:
            self.root.after_cancel(self.minimap_resize_timer)

        # Schedule a new redraw after the debounce period
        self.minimap_resize_timer = self.root.after(debounce_ms, self._redraw_minimap_after_resize)

    def _redraw_minimap_after_resize(self):
        """Handles aspect ratio enforcement and redraws after resize debounce."""
        self.minimap_resize_timer = None # Reset timer ID

        if not self.minimap_window or not tk.Toplevel.winfo_exists(self.minimap_window):
            return # Exit if window is gone

        if self._minimap_resizing_internally:
             # If we are already in the process of resizing programmatically, bail out
             # to prevent potential infinite loops from the geometry() call triggering Configure.
            return

        # --- Aspect Ratio Enforcement ---
        try:
            current_width = self.minimap_window.winfo_width()
            current_height = self.minimap_window.winfo_height()

            # Check for valid map dimensions and window size
            if map_height <= 0 or map_width <= 0 or current_width <= 1 or current_height <= 1:
                # Cannot calculate aspect ratio, just draw content
                self.invalidate_minimap_background_cache()
                self.draw_minimap()
                return # Exit aspect ratio logic

            map_aspect = map_width / map_height
            ideal_height = int(round(current_width / map_aspect))

            # Check if height needs adjustment (allow 1-pixel tolerance)
            if abs(current_height - ideal_height) > 1:
                self._minimap_resizing_internally = True # Set flag BEFORE resizing
                new_geometry = f"{current_width}x{ideal_height}"
                print(f"Minimap Configure: Forcing aspect ratio. New geometry: {new_geometry}")
                self.minimap_window.geometry(new_geometry)
                # After setting geometry, the configure event will likely fire again.
                # The flag _minimap_resizing_internally prevents immediate recursion.
                # We schedule the flag reset. Redraw will happen on the *next* configure event.
                self.root.after(50, setattr, self, '_minimap_resizing_internally', False)
                # Don't redraw immediately here, let the next configure event handle it after resize.
                return # Exit, wait for next configure event

        except Exception as e:
            print(f"Error during minimap aspect ratio enforcement: {e}")
            # Ensure flag is reset even on error
            self._minimap_resizing_internally = False

        # --- If no resize was needed, proceed with drawing ---
        print(f"Minimap Configure: Aspect ratio OK ({current_width}x{current_height}). Redrawing.")
        self.invalidate_minimap_background_cache() # Invalidate on any size change
        self.draw_minimap()

    def _trigger_minimap_reconfigure(self):
        """Forces the minimap to re-evaluate its size and aspect ratio if it exists."""
        if self.minimap_window and tk.Toplevel.winfo_exists(self.minimap_window):
            # A simple way to trigger <Configure> is to slightly change the size
            # We can just call the resize logic directly though.
            print("Map dimensions changed, triggering minimap aspect check/redraw.")
            # Reset the resize timer to avoid duplicate calls if configure is also pending
            if self.minimap_resize_timer is not None:
                self.root.after_cancel(self.minimap_resize_timer)
                self.minimap_resize_timer = None
            # Directly call the logic that handles resizing and drawing
            self._redraw_minimap_after_resize()

    def invalidate_minimap_background_cache(self):
        """Clears the cached minimap background image."""
        self.minimap_background_cache = None
        # Reset rendered size trackers too
        self.minimap_bg_rendered_width = 0
        self.minimap_bg_rendered_height = 0
        print("Minimap background cache invalidated.") # Debug message

    def _create_minimap_background_image(self, target_width, target_height):
        """Generates a single PhotoImage of the entire map scaled to fit, preserving aspect ratio."""
        if target_width <= 0 or target_height <= 0:
            return None

        print(f"Generating minimap background ({target_width}x{target_height}) with aspect preservation...") # Debug

        minimap_img = tk.PhotoImage(width=target_width, height=target_height)
        map_pixel_w = map_width * SUPERTILE_GRID_DIM * TILE_WIDTH
        map_pixel_h = map_height * SUPERTILE_GRID_DIM * TILE_HEIGHT

        if map_pixel_w <= 0 or map_pixel_h <= 0:
            print("Warning: Invalid base map pixel dimensions for minimap.")
            minimap_img.put("black", to=(0, 0, target_width, target_height))
            return minimap_img

        # --- Calculate aspect-preserving scale and offset (same logic as draw_minimap) ---
        scale_x = target_width / map_pixel_w
        scale_y = target_height / map_pixel_h
        scale = min(scale_x, scale_y)
        scaled_map_w = map_pixel_w * scale
        scaled_map_h = map_pixel_h * scale
        offset_x = (target_width - scaled_map_w) / 2
        offset_y = (target_height - scaled_map_h) / 2
        # --- End scale/offset calculation ---

        # Define background color for areas outside the scaled map (letter/pillarboxing)
        # Match the canvas background for seamless look if possible, else use black/grey
        # Using canvas bg might be tricky if it changes, black is safe.
        bg_fill_color_hex = "#000000"

        # --- Iterate through target minimap pixels ---
        for y_pix in range(target_height):
            row_hex_colors = []
            for x_pix in range(target_width):
                pixel_color_hex = bg_fill_color_hex # Default to background/fill color

                # Check if this minimap pixel falls within the centered, scaled map area
                if (offset_x <= x_pix < offset_x + scaled_map_w and
                    offset_y <= y_pix < offset_y + scaled_map_h):

                    # Map this minimap pixel back to the corresponding base map pixel coordinate
                    # Use max(1, ...) to prevent division by zero if scale is tiny
                    map_base_x = (x_pix - offset_x) / max(1e-9, scale)
                    map_base_y = (y_pix - offset_y) / max(1e-9, scale)

                    # Clamp coordinates to be within the valid base map pixel range
                    map_base_x = max(0, min(map_pixel_w - 1, map_base_x))
                    map_base_y = max(0, min(map_pixel_h - 1, map_base_y))

                    # Determine the source supertile, tile, and pixel within tile
                    map_pixel_col = int(map_base_x)
                    map_pixel_row = int(map_base_y)

                    st_col = map_pixel_col // (SUPERTILE_GRID_DIM * TILE_WIDTH)
                    st_row = map_pixel_row // (SUPERTILE_GRID_DIM * TILE_HEIGHT)

                    tile_col_in_st = (map_pixel_col % (SUPERTILE_GRID_DIM * TILE_WIDTH)) // TILE_WIDTH
                    tile_row_in_st = (map_pixel_row % (SUPERTILE_GRID_DIM * TILE_HEIGHT)) // TILE_HEIGHT

                    pixel_col_in_tile = map_pixel_col % TILE_WIDTH
                    pixel_row_in_tile = map_pixel_row % TILE_HEIGHT

                    # Get color using the indices (similar to original logic but using calculated coords)
                    try:
                        supertile_idx = map_data[st_row][st_col]
                        if 0 <= supertile_idx < num_supertiles:
                            tile_idx = supertiles_data[supertile_idx][tile_row_in_st][tile_col_in_st]
                            if 0 <= tile_idx < num_tiles_in_set:
                                pattern_val = tileset_patterns[tile_idx][pixel_row_in_tile][pixel_col_in_tile]
                                fg_idx, bg_idx = tileset_colors[tile_idx][pixel_row_in_tile]
                                fg_color = self.active_msx_palette[fg_idx]
                                bg_color = self.active_msx_palette[bg_idx]
                                pixel_color_hex = fg_color if pattern_val == 1 else bg_color
                            else:
                                pixel_color_hex = INVALID_TILE_COLOR # Invalid tile index
                        else:
                            pixel_color_hex = INVALID_SUPERTILE_COLOR # Invalid supertile index
                    except IndexError:
                        # Error case (e.g., map coords out of bounds, though clamping should prevent most)
                        pixel_color_hex = "#FF0000" # Bright Red Error

                # Append the determined color (either map color or background fill)
                row_hex_colors.append(pixel_color_hex)

            # Put the row data onto the PhotoImage
            try:
                minimap_img.put("{" + " ".join(row_hex_colors) + "}", to=(0, y_pix))
            except tk.TclError as e:
                print(f"Warning [Minimap BG]: TclError put row {y_pix}: {e}")
                if row_hex_colors: minimap_img.put(row_hex_colors[0], to=(0, y_pix, target_width, y_pix + 1))

        print("Minimap background generated.")
        # Store generated size along with image for cache validation
        self.minimap_bg_rendered_width = target_width
        self.minimap_bg_rendered_height = target_height
        self.minimap_background_cache = minimap_img # Store in cache
        return minimap_img

    def _update_window_title(self):
        """Updates the main window title based on the current project path."""
        base_title = "MSX2 Tile/Map/Palette Editor"
        if self.current_project_base_path:
            # Extract just the filename part
            project_name = os.path.basename(self.current_project_base_path)
            self.root.title(f"{base_title} - {project_name}")
        else:
            self.root.title(f"{base_title} - Untitled")

    def _update_map_cursor(self):
        """Sets the map canvas cursor based on current action and Ctrl state."""
        new_cursor = "" # Default cursor
        if self.current_mouse_action == 'panning':
            new_cursor = "fleur" # Grabbing hand cursor
        # Add cursors for window dragging/resizing if desired
        # elif self.current_mouse_action == 'window_dragging':
        #     new_cursor = "fleur" # Or maybe "move"
        # elif self.current_mouse_action == 'window_resizing':
        #     # Could set specific resize cursors based on self.window_view_resize_handle
        #     new_cursor = "sizing" # Generic resize cursor
        elif self.is_ctrl_pressed:
            new_cursor = "hand2" # Open hand cursor when Ctrl is pressed but no action active
        # else: use default ""

        self.map_canvas.config(cursor=new_cursor)

    def handle_ctrl_press(self, event):
        """Handles Control key press."""
        if "Control" in event.keysym:
            # Only update state if Ctrl wasn't already pressed
            if not self.is_ctrl_pressed:
                self.is_ctrl_pressed = True
                # Update cursor only if no mouse action is currently happening
                if self.current_mouse_action is None:
                    self._update_map_cursor()

    def handle_ctrl_release(self, event):
            """Handles Control key release. Stops panning if active."""
            if "Control" in event.keysym:
                # Only update state if Ctrl was actually pressed
                if self.is_ctrl_pressed:
                    self.is_ctrl_pressed = False
                    # If panning was the current action, stop it.
                    if self.current_mouse_action == 'panning':
                        self.current_mouse_action = None
                        # print("Panning action stopped by Ctrl release.") # Debug
                    # Update cursor regardless, reflects Ctrl state change
                    self._update_map_cursor()

    def handle_pan_start(self, event):
        """Handles the start of panning (Ctrl + Left Click) using scan_mark."""
        # Only start panning if Ctrl is pressed AND no other action is happening
        if self.is_ctrl_pressed and self.current_mouse_action is None:
            self.current_mouse_action = 'panning'
            self.map_canvas.scan_mark(event.x, event.y)
            self._update_map_cursor() # Set grabbing cursor
            # print("Panning started.") # Debug
            return "break" # Prevent other <Button-1> handlers
        # If Ctrl not pressed or already doing something, ignore.

    def handle_pan_motion(self, event):
            """Handles mouse motion during panning using scan_dragto."""
            # Only process if the current action is panning
            if self.current_mouse_action == 'panning':
                # Drag the canvas view based on mouse movement since scan_mark
                self.map_canvas.scan_dragto(event.x, event.y, gain=1)
                # Update the minimap to reflect the scroll
                self.draw_minimap()
                # Prevent other <B1-Motion> handlers
                return "break"
            # If not panning, do nothing here.

    def handle_canvas_enter(self, event):
        """Handles mouse entering the canvas area."""
        # Set cursor based on whether Ctrl is pressed when entering
        self._update_map_cursor()

    def handle_canvas_leave(self, event):
        """Handles mouse leaving the canvas area."""
        # Reset cursor to default when leaving
        self.map_canvas.config(cursor="")

    def handle_global_keypress(self, event):
        """Handles specific key presses globally for the root window."""
        key = event.keysym.lower()
        # Add checks for other global keys here if needed in the future

        if key == 'c':
            print("--- Global Key: 'c' pressed. Cycling grid color.") # Debug
            self.cycle_grid_color()
            return "break"

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TileEditorApp(root)
    root.mainloop()
