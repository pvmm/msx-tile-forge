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
# ... (Keep existing constants like TILE_WIDTH, etc.) ...
TILE_WIDTH = 8
TILE_HEIGHT = 8
EDITOR_PIXEL_SIZE = 30
VIEWER_TILE_SIZE = TILE_WIDTH * 2 # 16
PALETTE_SQUARE_SIZE = 20 # Size for Tile Editor palette chooser
NUM_TILES_ACROSS = 16
MAX_TILES = 256
SUPERTILE_GRID_DIM = 4
SUPERTILE_DEF_TILE_SIZE = TILE_WIDTH * 4 # 32
SUPERTILE_SELECTOR_PREVIEW_SIZE = TILE_WIDTH * 4 # 32
NUM_SUPERTILES_ACROSS = 8
MAX_SUPERTILES = 256
MAP_CELL_PREVIEW_SIZE = TILE_WIDTH * 2 # 16
DEFAULT_MAP_WIDTH = 32
DEFAULT_MAP_HEIGHT = 24

# --- Palette Editor Constants ---
MSX2_PICKER_COLS = 32 # How many colors across in the 512 picker
MSX2_PICKER_ROWS = 16 # 32 * 16 = 512
MSX2_PICKER_SQUARE_SIZE = 15 # Size of each color square in the 512 picker
CURRENT_PALETTE_SLOT_SIZE = 30 # Size of squares for the 16 selected colors

# --- MSX1 Default Palette (Indices & Colors) ---
# These are the INITIAL values for the active palette
# We'll store the active palette as hex strings for Tkinter drawing
DEFAULT_MSX1_COLORS_HEX = [
    "#000000", "#000000", "#3EB849", "#74D07D", "#5955E0", "#8076F1",
    "#B95E51", "#65DBEF", "#D96459", "#FF897D", "#CCC35E", "#DED087",
    "#3AA241", "#B766B5", "#CCCCCC", "#FFFFFF",
]
BLACK_IDX = 1
MED_GREEN_IDX = 2
WHITE_IDX = 15

# --- Placeholder Colors ---
INVALID_TILE_COLOR = "#FF00FF" # Bright Magenta
INVALID_SUPERTILE_COLOR = "#00FFFF" # Bright Cyan

# --- MSX2 Color Generation ---
msx2_512_colors_hex = []
msx2_512_colors_rgb7 = [] # Store the (r,g,b) 0-7 values too

for r in range(8): # 3 bits (0-7)
    for g in range(8): # 3 bits (0-7)
        for b in range(8): # 3 bits (0-7)
            # Approximate conversion to 0-255 range for display
            r_255 = min(255, r * 36) # Scale 0-7 -> 0-252
            g_255 = min(255, g * 36)
            b_255 = min(255, b * 36)
            hex_color = f"#{r_255:02x}{g_255:02x}{b_255:02x}"
            msx2_512_colors_hex.append(hex_color)
            msx2_512_colors_rgb7.append((r, g, b))

# --- Data Structures ---
# ... (Keep existing data structures: tileset_patterns, tileset_colors, etc.) ...
tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
# NOTE: tileset_colors stores (FG_INDEX, BG_INDEX) which now refer to the active_msx_palette
tileset_colors = [[(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
current_tile_index = 0
num_tiles_in_set = 1
selected_color_index = WHITE_IDX # Index (0-15) from the *active* palette for drawing
last_drawn_pixel = None

supertiles_data = [[[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
current_supertile_index = 0
num_supertiles = 1
selected_tile_for_supertile = 0

map_width = DEFAULT_MAP_WIDTH
map_height = DEFAULT_MAP_HEIGHT
map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
selected_supertile_for_map = 0
last_painted_map_cell = None

# Clipboards
tile_clipboard_pattern = None
tile_clipboard_colors = None
supertile_clipboard_data = None

# --- Utility Functions --- (get_contrast_color is the same)
def get_contrast_color(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except:
        return "#000000"

# --- Application Class ---
class TileEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MSX2 Tile/Map/Palette Editor - Untitled") # Updated title
        self.root.state('zoomed')

        # --- Dynamic Palette ---
        self.active_msx_palette = list(DEFAULT_MSX1_COLORS_HEX) # Start with MSX1 defaults
        self.selected_palette_slot = 0 # Which slot (0-15) is being edited

        # --- Image Caches ---
        self.tile_image_cache = {}
        self.supertile_image_cache = {}

        # --- Zoom State ---
        self.map_zoom_level = 1.0

        # --- UI Setup ---
        self.create_menu()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- Create Tabs (Palette Editor First) ---
        self.tab_palette_editor = ttk.Frame(self.notebook, padding="10") # New Tab
        self.tab_tile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_supertile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_map_editor = ttk.Frame(self.notebook, padding="10")

        # Add tabs in order
        self.notebook.add(self.tab_palette_editor, text='Palette Editor') # New Tab Added First
        self.notebook.add(self.tab_tile_editor, text='Tile Editor')
        self.notebook.add(self.tab_supertile_editor, text='Supertile Editor')
        self.notebook.add(self.tab_map_editor, text='Map Editor')

        # Populate tabs
        self.create_palette_editor_widgets(self.tab_palette_editor) # New Widgets
        self.create_tile_editor_widgets(self.tab_tile_editor)
        self.create_supertile_editor_widgets(self.tab_supertile_editor)
        self.create_map_editor_widgets(self.tab_map_editor)

        self.update_all_displays(changed_level="all")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    # --- Cache Management --- (invalidate_tile_cache needs slight change)
    def invalidate_tile_cache(self, tile_index):
        keys_to_remove = [k for k in self.tile_image_cache if k[0] == tile_index]
        for key in keys_to_remove:
            self.tile_image_cache.pop(key, None)
        # Invalidate dependent supertiles
        for st_index in range(num_supertiles):
            definition = supertiles_data[st_index] # Use global directly
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

    # --- Image Generation --- (Need to use self.active_msx_palette)
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
            # --- vvv Use active palette vvv ---
            try:
                fg_idx, bg_idx = colors[tile_r]
                fg_color = self.active_msx_palette[fg_idx] # Use dynamic palette
                bg_color = self.active_msx_palette[bg_idx] # Use dynamic palette
            except IndexError:
                # Handle case where indices might be invalid temporarily
                fg_color = INVALID_TILE_COLOR
                bg_color = INVALID_TILE_COLOR
            # --- ^^^ Use active palette ^^^ ---
            row_colors_hex = []
            for x in range(render_size):
                tile_c = min(TILE_WIDTH - 1, int(x * pixel_w_ratio))
                try:
                    pixel_val = pattern[tile_r][tile_c]
                except IndexError:
                    pixel_val = 0 # Default if pattern index is somehow wrong
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
                        # --- vvv Use active palette vvv ---
                        fg_color = self.active_msx_palette[fg_idx]
                        bg_color = self.active_msx_palette[bg_idx]
                        # --- ^^^ Use active palette ^^^ ---
                        pixel_val = pattern_row[tile_c]
                        pixel_color_hex = fg_color if pixel_val == 1 else bg_color
                    except IndexError:
                         print(f"Warning [create_supertile_image]: IndexError T:{tile_idx} P:[{tile_r},{tile_c}] PaletteIdx:[{fg_idx},{bg_idx}]")
                         pixel_color_hex = INVALID_TILE_COLOR # Use placeholder on error
                row_colors_hex.append(pixel_color_hex)
            try:
                img.put("{" + " ".join(row_colors_hex) + "}", to=(0, y))
            except tk.TclError as e:
                print(f"Warning [create_supertile_image]: TclError ST {supertile_index} size {total_size} row {y}: {e}")
                if row_colors_hex:
                    img.put(row_colors_hex[0], to=(0, y, render_size, y+1))
        self.supertile_image_cache[cache_key] = img
        return img

    # --- Menu Creation --- (Added Copy/Paste items)
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project (All)", command=self.new_project);
        file_menu.add_separator();

        file_menu.add_command(label="Open Tileset (.SC4Tiles)...", command=self.open_tileset);
        file_menu.add_command(label="Save Tileset (.SC4Tiles)...", command=self.save_tileset);
        file_menu.add_separator();

        file_menu.add_command(label="Open Supertiles (.SC4Super)...", command=self.open_supertiles);
        file_menu.add_command(label="Save Supertiles (.SC4Super)...", command=self.save_supertiles);
        file_menu.add_separator();

        file_menu.add_command(label="Open Map (.SC4Map)...", command=self.open_map);
        file_menu.add_command(label="Save Map (.SC4Map)...", command=self.save_map);
        file_menu.add_separator();
        

        file_menu.add_command(label="Load Palette (.msxpal)...", command=self.open_palette);
        file_menu.add_command(label="Save Palette (.msxpal)...", command=self.save_palette);
        file_menu.add_separator();

        file_menu.add_command(label="Exit", command=self.root.quit);

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Tile", command=self.copy_current_tile); edit_menu.add_command(label="Paste Tile", command=self.paste_tile); edit_menu.add_separator()
        edit_menu.add_command(label="Copy Supertile", command=self.copy_current_supertile); edit_menu.add_command(label="Paste Supertile", command=self.paste_supertile); edit_menu.add_separator()
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile); edit_menu.add_command(label="Clear Current Supertile", command=self.clear_current_supertile); edit_menu.add_command(label="Clear Map", command=self.clear_map); edit_menu.add_separator()
        edit_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size); edit_menu.add_command(label="Set Supertile Count...", command=self.set_supertile_count); edit_menu.add_command(label="Set Map Dimensions...", command=self.set_map_dimensions)

    # --- Widget Creation ---
    def create_palette_editor_widgets(self, parent_frame): # New Method
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")

        # Left: Current Palette + Controls
        left_frame = ttk.Frame(main_frame, padding=5)
        left_frame.grid(row=0, column=0, sticky="ns")

        # Right: 512 Color Picker
        right_frame = ttk.Frame(main_frame, padding=5)
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Configure main frame grid
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=0) # Left frame fixed width
        main_frame.grid_columnconfigure(1, weight=1) # Right frame expands H

        # --- Left Frame Contents ---
        current_palette_frame = ttk.LabelFrame(left_frame, text="Active Palette (16 colors)")
        current_palette_frame.pack(pady=(0, 10), fill="x")

        cp_canvas_width = 4 * (CURRENT_PALETTE_SLOT_SIZE + 2) + 2 # 4 columns
        cp_canvas_height = 4 * (CURRENT_PALETTE_SLOT_SIZE + 2) + 2 # 4 rows
        self.current_palette_canvas = tk.Canvas(
            current_palette_frame,
            width=cp_canvas_width,
            height=cp_canvas_height,
            borderwidth=0,
            highlightthickness=0
        )
        self.current_palette_canvas.pack()
        self.current_palette_canvas.bind("<Button-1>", self.handle_current_palette_click)

        # Selected Slot Info
        info_frame = ttk.LabelFrame(left_frame, text="Selected Slot Info")
        info_frame.pack(pady=(0, 10), fill="x")

        self.selected_slot_label = ttk.Label(info_frame, text="Slot: 0")
        self.selected_slot_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=2)

        self.selected_slot_color_label = tk.Label(info_frame, text="      ", bg="#000000", relief="sunken", width=6)
        self.selected_slot_color_label.grid(row=1, column=0, padx=5, pady=2)

        self.selected_slot_rgb_label = ttk.Label(info_frame, text="RGB: #000000")
        self.selected_slot_rgb_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=5)

        # RGB 0-7 Input (Optional)
        rgb_frame = ttk.LabelFrame(left_frame, text="Set Color (RGB 0-7)")
        rgb_frame.pack(pady=(0, 10), fill="x")

        ttk.Label(rgb_frame, text="R:").grid(row=0, column=0, padx=(5,0))
        self.rgb_r_var = tk.StringVar(value="0")
        self.rgb_r_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_r_var, width=2)
        self.rgb_r_entry.grid(row=0, column=1)

        ttk.Label(rgb_frame, text="G:").grid(row=0, column=2, padx=(5,0))
        self.rgb_g_var = tk.StringVar(value="0")
        self.rgb_g_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_g_var, width=2)
        self.rgb_g_entry.grid(row=0, column=3)

        ttk.Label(rgb_frame, text="B:").grid(row=0, column=4, padx=(5,0))
        self.rgb_b_var = tk.StringVar(value="0")
        self.rgb_b_entry = ttk.Entry(rgb_frame, textvariable=self.rgb_b_var, width=2)
        self.rgb_b_entry.grid(row=0, column=5)

        apply_rgb_button = ttk.Button(rgb_frame, text="Set", command=self.handle_rgb_apply)
        apply_rgb_button.grid(row=0, column=6, padx=5, pady=5)


        # --- Right Frame Contents ---
        picker_frame = ttk.LabelFrame(right_frame, text="MSX2 512 Color Picker")
        picker_frame.pack(expand=True, fill="both")

        picker_canvas_width = MSX2_PICKER_COLS * (MSX2_PICKER_SQUARE_SIZE + 1) + 1
        picker_canvas_height = MSX2_PICKER_ROWS * (MSX2_PICKER_SQUARE_SIZE + 1) + 1

        picker_hbar = ttk.Scrollbar(picker_frame, orient=tk.HORIZONTAL)
        picker_vbar = ttk.Scrollbar(picker_frame, orient=tk.VERTICAL)
        self.msx2_picker_canvas = tk.Canvas(
            picker_frame,
            bg="lightgrey",
            scrollregion=(0, 0, picker_canvas_width, picker_canvas_height),
            xscrollcommand=picker_hbar.set,
            yscrollcommand=picker_vbar.set
        )
        picker_hbar.config(command=self.msx2_picker_canvas.xview)
        picker_vbar.config(command=self.msx2_picker_canvas.yview)

        self.msx2_picker_canvas.grid(row=0, column=0, sticky="nsew")
        picker_vbar.grid(row=0, column=1, sticky="ns")
        picker_hbar.grid(row=1, column=0, sticky="ew")

        picker_frame.grid_rowconfigure(0, weight=1)
        picker_frame.grid_columnconfigure(0, weight=1)

        self.msx2_picker_canvas.bind("<Button-1>", self.handle_512_picker_click)

        # Draw the picker content initially
        self.draw_512_picker()

    def create_tile_editor_widgets(self, parent_frame):
        # ... (Identical structure, but palette canvas needs update in draw function) ...
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)"); editor_frame.grid(row=0, column=0, pady=(0, 10))
        self.editor_canvas = tk.Canvas( editor_frame, width=TILE_WIDTH * EDITOR_PIXEL_SIZE, height=TILE_HEIGHT * EDITOR_PIXEL_SIZE, bg="grey")
        self.editor_canvas.grid(row=0, column=0); self.editor_canvas.bind("<Button-1>", self.handle_editor_click); self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag); self.editor_canvas.bind("<Button-3>", self.handle_editor_click); self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag)
        attr_frame = ttk.LabelFrame(left_frame, text="Row Colors (Click to set FG/BG)"); attr_frame.grid(row=1, column=0, sticky=(tk.W, tk.E)); self.attr_row_frames = []; self.attr_fg_labels = []; self.attr_bg_labels = []
        for r in range(TILE_HEIGHT):
            row_f = ttk.Frame(attr_frame); row_f.grid(row=r, column=0, sticky=tk.W, pady=1); row_label = ttk.Label(row_f, text=f"{r}:"); row_label.grid(row=0, column=0, padx=(0, 5))
            fg_label = tk.Label(row_f, text=" FG ", width=3, relief="raised", borderwidth=2); fg_label.grid(row=0, column=1, padx=(0, 2)); fg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'fg')); self.attr_fg_labels.append(fg_label)
            bg_label = tk.Label(row_f, text=" BG ", width=3, relief="raised", borderwidth=2); bg_label.grid(row=0, column=2); bg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'bg')); self.attr_bg_labels.append(bg_label)
            self.attr_row_frames.append(row_f)
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S)); main_frame.grid_rowconfigure(0, weight=1)
        # --- vvv Palette Frame uses different canvas name now vvv ---
        palette_frame = ttk.LabelFrame(right_frame, text="Color Selector (Click to draw)") # Renamed label slightly
        palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.N, tk.W, tk.E))
        self.tile_editor_palette_canvas = tk.Canvas(palette_frame, width=4 * (PALETTE_SQUARE_SIZE + 2), height=4 * (PALETTE_SQUARE_SIZE + 2), borderwidth=0, highlightthickness=0)
        self.tile_editor_palette_canvas.grid(row=0, column=0)
        self.tile_editor_palette_canvas.bind("<Button-1>", self.handle_tile_editor_palette_click) # Renamed handler
        # --- ^^^ Palette Frame uses different canvas name now ^^^ ---
        viewer_frame = ttk.LabelFrame(right_frame, text="Tileset"); viewer_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(1, weight=1)
        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1; num_rows_in_viewer = math.ceil(MAX_TILES / NUM_TILES_ACROSS); viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1
        viewer_hbar = ttk.Scrollbar(viewer_frame, orient=tk.HORIZONTAL); viewer_vbar = ttk.Scrollbar(viewer_frame, orient=tk.VERTICAL)
        self.tileset_canvas = tk.Canvas( viewer_frame, bg="lightgrey", scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height), xscrollcommand=viewer_hbar.set, yscrollcommand=viewer_vbar.set)
        viewer_hbar.config(command=self.tileset_canvas.xview); viewer_vbar.config(command=self.tileset_canvas.yview)
        self.tileset_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        viewer_frame.grid_rowconfigure(0, weight=1); viewer_frame.grid_columnconfigure(0, weight=1); self.tileset_canvas.bind("<Button-1>", self.handle_tileset_click)
        add_tile_button = ttk.Button(right_frame, text="Add New Tile", command=self.add_new_tile)
        add_tile_button.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.tile_info_label = ttk.Label(right_frame, text="Tile: 0/0")
        self.tile_info_label.grid(row=3, column=0, sticky=tk.W, pady=(2,0))

    def create_supertile_editor_widgets(self, parent_frame):
        # ... (Identical to previous version) ...
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        def_frame = ttk.LabelFrame(left_frame, text="Supertile Definition (Click to place selected tile)"); def_frame.grid(row=0, column=0, pady=(0, 10))
        def_canvas_size = SUPERTILE_GRID_DIM * SUPERTILE_DEF_TILE_SIZE
        self.supertile_def_canvas = tk.Canvas(def_frame, width=def_canvas_size, height=def_canvas_size, bg="darkgrey")
        self.supertile_def_canvas.grid(row=0, column=0); self.supertile_def_canvas.bind("<Button-1>", self.handle_supertile_def_click)
        self.supertile_def_info_label = ttk.Label(left_frame, text=f"Editing Supertile: {current_supertile_index}"); self.supertile_def_info_label.grid(row=1, column=0, sticky=tk.W)
        self.supertile_tile_select_label = ttk.Label(left_frame, text=f"Selected Tile for Placing: {selected_tile_for_supertile}"); self.supertile_tile_select_label.grid(row=2, column=0, sticky=tk.W)
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W, tk.E)); main_frame.grid_columnconfigure(1, weight=1); main_frame.grid_rowconfigure(0, weight=1)
        tileset_viewer_frame = ttk.LabelFrame(right_frame, text="Tileset (Click to select tile for definition)"); tileset_viewer_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), pady=(0, 10)); right_frame.grid_rowconfigure(0, weight=1)
        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1; num_rows_in_viewer = math.ceil(MAX_TILES / NUM_TILES_ACROSS); viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1
        st_viewer_hbar = ttk.Scrollbar(tileset_viewer_frame, orient=tk.HORIZONTAL); st_viewer_vbar = ttk.Scrollbar(tileset_viewer_frame, orient=tk.VERTICAL)
        self.st_tileset_canvas = tk.Canvas( tileset_viewer_frame, bg="lightgrey", scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height), xscrollcommand=st_viewer_hbar.set, yscrollcommand=st_viewer_vbar.set)
        st_viewer_hbar.config(command=self.st_tileset_canvas.xview); st_viewer_vbar.config(command=self.st_tileset_canvas.yview)
        self.st_tileset_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); st_viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); st_viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        tileset_viewer_frame.grid_rowconfigure(0, weight=1); tileset_viewer_frame.grid_columnconfigure(0, weight=1); self.st_tileset_canvas.bind("<Button-1>", self.handle_st_tileset_click)
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Selector (Click to edit)"); st_selector_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(1, weight=1)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1; st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS); st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL); st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=st_sel_hbar.set, yscrollcommand=st_sel_vbar.set)
        st_sel_hbar.config(command=self.supertile_selector_canvas.xview); st_sel_vbar.config(command=self.supertile_selector_canvas.yview)
        self.supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        st_selector_frame.grid_rowconfigure(0, weight=1); st_selector_frame.grid_columnconfigure(0, weight=1); self.supertile_selector_canvas.bind("<Button-1>", self.handle_supertile_selector_click)
        add_supertile_button = ttk.Button(right_frame, text="Add New Supertile", command=self.add_new_supertile)
        add_supertile_button.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.supertile_sel_info_label = ttk.Label(right_frame, text=f"Supertiles: {num_supertiles}")
        self.supertile_sel_info_label.grid(row=3, column=0, sticky=tk.W, pady=(2,0))

    def create_map_editor_widgets(self, parent_frame):
        # ... (Identical to previous version with zoom) ...
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10))
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_columnconfigure(1, weight=0); main_frame.grid_rowconfigure(0, weight=1)
        map_controls_frame = ttk.Frame(left_frame); map_controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        size_label = ttk.Label(map_controls_frame, text="Map Size:"); size_label.grid(row=0, column=0, padx=(0,5))
        self.map_size_label = ttk.Label(map_controls_frame, text=f"{map_width} x {map_height}"); self.map_size_label.grid(row=0, column=1, padx=(0, 10))
        zoom_frame = ttk.Frame(map_controls_frame); zoom_frame.grid(row=0, column=2, padx=(10, 0))
        zoom_out_button = ttk.Button(zoom_frame, text="-", width=2, command=lambda: self.change_map_zoom(-0.25)); zoom_out_button.pack(side=tk.LEFT)
        self.map_zoom_label = ttk.Label(zoom_frame, text="100%", width=5, anchor=tk.CENTER); self.map_zoom_label.pack(side=tk.LEFT, padx=2)
        zoom_in_button = ttk.Button(zoom_frame, text="+", width=2, command=lambda: self.change_map_zoom(0.25)); zoom_in_button.pack(side=tk.LEFT)
        zoom_reset_button = ttk.Button(zoom_frame, text="Reset", width=5, command=lambda: self.set_map_zoom(1.0)); zoom_reset_button.pack(side=tk.LEFT, padx=(5,0))
        map_canvas_frame = ttk.LabelFrame(left_frame, text="Map (Click/Drag to place selected Supertile)"); map_canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        left_frame.grid_rowconfigure(0, weight=0); left_frame.grid_rowconfigure(1, weight=1); left_frame.grid_columnconfigure(0, weight=1)
        map_hbar = ttk.Scrollbar(map_canvas_frame, orient=tk.HORIZONTAL); map_vbar = ttk.Scrollbar(map_canvas_frame, orient=tk.VERTICAL)
        self.map_canvas = tk.Canvas(map_canvas_frame, bg="black", xscrollcommand=map_hbar.set, yscrollcommand=map_vbar.set)
        map_hbar.config(command=self.map_canvas.xview); map_vbar.config(command=self.map_canvas.yview)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        map_canvas_frame.grid_rowconfigure(0, weight=1); map_canvas_frame.grid_columnconfigure(0, weight=1); map_canvas_frame.grid_rowconfigure(1, weight=0); map_canvas_frame.grid_columnconfigure(1, weight=0)
        self.map_canvas.bind("<Button-1>", self.handle_map_click); self.map_canvas.bind("<B1-Motion>", self.handle_map_drag)
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Palette (Click to select for map)"); st_selector_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(0, weight=1); right_frame.grid_columnconfigure(0, weight=1); right_frame.grid_rowconfigure(1, weight=0)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1; st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS); st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        map_st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL); map_st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.map_supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=map_st_sel_hbar.set, yscrollcommand=map_st_sel_vbar.set)
        map_st_sel_hbar.config(command=self.map_supertile_selector_canvas.xview); map_st_sel_vbar.config(command=self.map_supertile_selector_canvas.yview); self.map_supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E)); st_selector_frame.grid_rowconfigure(0, weight=1); st_selector_frame.grid_columnconfigure(0, weight=1); st_selector_frame.grid_rowconfigure(1, weight=0); st_selector_frame.grid_columnconfigure(1, weight=0)
        self.map_supertile_selector_canvas.bind("<Button-1>", self.handle_map_supertile_selector_click)
        self.map_supertile_select_label = ttk.Label(right_frame, text=f"Selected Supertile for Painting: {selected_supertile_for_map}"); self.map_supertile_select_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))


    # --- Drawing Functions ---
    def update_all_displays(self, changed_level="all"):
        # Palette Editor parts (always redraw if palette changed)
        if changed_level in ["all", "palette"]:
            self.draw_current_palette() # Draws the 16 slots
            self.update_palette_info_labels() # Update info for selected slot
            # 512 picker only needs drawing once, unless colours change (they don't here)
            # self.draw_512_picker() # No need to redraw usually

        # Tile Editor parts
        if changed_level in ["all", "palette", "tile"]:
            self.draw_editor_canvas()
            self.draw_attribute_editor()
            self.draw_tile_editor_palette() # Draw the 16 color *selector* palette
            self.draw_tileset_viewer(self.tileset_canvas, current_tile_index)
            self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
            self.update_tile_info_label()

        # Supertile Editor parts
        if changed_level in ["all", "palette", "tile", "supertile"]:
            self.draw_supertile_definition_canvas()
            self.draw_supertile_selector(self.supertile_selector_canvas, current_supertile_index)
            self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
            self.update_supertile_info_labels()

        # Map Editor parts
        if changed_level in ["all", "palette", "tile", "supertile", "map"]:
             self.draw_map_canvas()
             self.update_map_info_labels()

    # --- vvv NEW Palette Drawing Methods vvv ---
    def draw_current_palette(self):
        """Draws the 16 active palette slots."""
        canvas = self.current_palette_canvas
        canvas.delete("all")
        size = CURRENT_PALETTE_SLOT_SIZE
        padding = 2

        for i in range(16):
            row, col = divmod(i, 4)
            x1 = col * (size + padding) + padding
            y1 = row * (size + padding) + padding
            x2 = x1 + size
            y2 = y1 + size
            color = self.active_msx_palette[i]
            outline_color = "red" if i == self.selected_palette_slot else "grey"
            outline_width = 3 if i == self.selected_palette_slot else 1

            canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline=outline_color,
                width=outline_width,
                tags=f"pal_slot_{i}"
            )

    def draw_512_picker(self):
        """Draws the full MSX2 512 color grid (usually only needs to be done once)."""
        canvas = self.msx2_picker_canvas
        canvas.delete("all")
        size = MSX2_PICKER_SQUARE_SIZE
        padding = 1
        cols = MSX2_PICKER_COLS

        for i in range(512):
            row, col = divmod(i, cols)
            x1 = col * (size + padding) + padding
            y1 = row * (size + padding) + padding
            x2 = x1 + size
            y2 = y1 + size
            hex_color = msx2_512_colors_hex[i]
            r, g, b = msx2_512_colors_rgb7[i]

            canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=hex_color,
                outline="grey",
                width=1,
                tags=(f"msx2_picker_{i}", f"msx2_rgb_{r}_{g}_{b}") # Add tags for lookup
            )

    def update_palette_info_labels(self):
        """Updates labels showing info about the selected palette slot."""
        slot = self.selected_palette_slot
        if 0 <= slot < 16:
            color_hex = self.active_msx_palette[slot]
            # Try to find the R G B (0-7) value by looking up the hex color
            # This is inefficient but works for display. A better way would be
            # to store the R G B (0-7) tuple alongside the hex string.
            rgb7 = (-1,-1,-1)
            try:
                idx512 = msx2_512_colors_hex.index(color_hex)
                rgb7 = msx2_512_colors_rgb7[idx512]
            except ValueError:
                pass # Color not found in the 512 list (shouldn't happen ideally)

            self.selected_slot_label.config(text=f"Slot: {slot}")
            self.selected_slot_color_label.config(bg=color_hex)
            self.selected_slot_rgb_label.config(text=f"RGB: {color_hex} ({rgb7[0]},{rgb7[1]},{rgb7[2]})")
            # Update RGB entry boxes as well
            self.rgb_r_var.set(str(rgb7[0]) if rgb7[0] != -1 else "?")
            self.rgb_g_var.set(str(rgb7[1]) if rgb7[1] != -1 else "?")
            self.rgb_b_var.set(str(rgb7[2]) if rgb7[2] != -1 else "?")
        else:
            # Clear labels if selection is somehow invalid
            self.selected_slot_label.config(text="Slot: -")
            self.selected_slot_color_label.config(bg="grey")
            self.selected_slot_rgb_label.config(text="RGB: -")
            self.rgb_r_var.set("")
            self.rgb_g_var.set("")
            self.rgb_b_var.set("")
    # --- ^^^ NEW Palette Drawing Methods ^^^ ---

    def draw_editor_canvas(self): # Uses active palette
        self.editor_canvas.delete("all")
        if not (0 <= current_tile_index < num_tiles_in_set):
            return
        pattern = tileset_patterns[current_tile_index]
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            try:
                fg_idx, bg_idx = colors[r]
                fg_color = self.active_msx_palette[fg_idx] # Use dynamic palette
                bg_color = self.active_msx_palette[bg_idx] # Use dynamic palette
            except IndexError:
                 fg_color, bg_color = INVALID_TILE_COLOR, INVALID_TILE_COLOR
            for c in range(TILE_WIDTH):
                try: pixel_val = pattern[r][c]
                except IndexError: pixel_val = 0
                color = fg_color if pixel_val == 1 else bg_color
                x1 = c * EDITOR_PIXEL_SIZE; y1 = r * EDITOR_PIXEL_SIZE
                x2 = x1 + EDITOR_PIXEL_SIZE; y2 = y1 + EDITOR_PIXEL_SIZE
                self.editor_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="darkgrey", width=1)

    def draw_attribute_editor(self): # Uses active palette
        if not (0 <= current_tile_index < num_tiles_in_set):
            return
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            try:
                fg_idx, bg_idx = colors[r]
                fg_color_hex = self.active_msx_palette[fg_idx]
                bg_color_hex = self.active_msx_palette[bg_idx]
            except IndexError:
                fg_color_hex, bg_color_hex = INVALID_TILE_COLOR, INVALID_TILE_COLOR
            self.attr_fg_labels[r].config(bg=fg_color_hex, fg=get_contrast_color(fg_color_hex))
            self.attr_bg_labels[r].config(bg=bg_color_hex, fg=get_contrast_color(bg_color_hex))

    def draw_tile_editor_palette(self): # Renamed method, draws the 16 color *selector*
        """Draws the 16-color selector palette in the Tile Editor tab."""
        canvas = self.tile_editor_palette_canvas
        canvas.delete("all")
        size = PALETTE_SQUARE_SIZE
        padding = 2
        for i in range(16):
            row, col = divmod(i, 4)
            x1 = col * (size + padding) + padding
            y1 = row * (size + padding) + padding
            x2 = x1 + size
            y2 = y1 + size
            color = self.active_msx_palette[i] # Use active palette
            outline_color = "red" if i == selected_color_index else "grey" # Use global selected_color_index
            outline_width = 2 if i == selected_color_index else 1
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline_color, width=outline_width, tags=f"pal_sel_{i}")

    def update_tile_info_label(self): # Unchanged
         self.tile_info_label.config(text=f"Tile: {current_tile_index}/{max(0, num_tiles_in_set-1)}")

    def draw_supertile_definition_canvas(self): # Uses active palette via create_tile_image
        # ... (Identical logic, relies on create_tile_image using active palette) ...
        canvas = self.supertile_def_canvas; canvas.delete("all")
        if not (0 <= current_supertile_index < num_supertiles): return
        definition = supertiles_data[current_supertile_index]; size = SUPERTILE_DEF_TILE_SIZE
        for r in range(SUPERTILE_GRID_DIM):
            for c in range(SUPERTILE_GRID_DIM):
                tile_idx = definition[r][c]; base_x = c * size; base_y = r * size
                img = self.create_tile_image(tile_idx, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"def_tile_{r}_{c}")
                canvas.create_rectangle(base_x, base_y, base_x + size, base_y + size, outline="grey")

    def draw_supertile_selector(self, canvas, highlighted_supertile_index): # Uses active palette via create_supertile_image
        # ... (Identical logic, relies on create_supertile_image using active palette) ...
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

    def update_supertile_info_labels(self): # Unchanged
         self.supertile_def_info_label.config(text=f"Editing Supertile: {current_supertile_index}/{max(0, num_supertiles-1)}")
         self.supertile_tile_select_label.config(text=f"Selected Tile for Placing: {selected_tile_for_supertile}")
         self.supertile_sel_info_label.config(text=f"Supertiles: {num_supertiles}")

    def draw_map_canvas(self): # Uses active palette via create_supertile_image
        # ... (Identical logic, relies on create_supertile_image using active palette) ...
        canvas = self.map_canvas; canvas.delete("all"); zoomed_cell_size = self.get_zoomed_map_cell_size()
        map_canvas_width = map_width * zoomed_cell_size; map_canvas_height = map_height * zoomed_cell_size; str_scroll = f"0 0 {float(map_canvas_width)} {float(map_canvas_height)}"
        current_scroll = canvas.cget("scrollregion");
        if isinstance(current_scroll, tuple): current_scroll = " ".join(map(str, current_scroll))
        if current_scroll != str_scroll: canvas.config(scrollregion=(0, 0, map_canvas_width, map_canvas_height))
        for r in range(map_height):
            for c in range(map_width):
                 supertile_idx = map_data[r][c]; base_x = c * zoomed_cell_size; base_y = r * zoomed_cell_size
                 img = self.create_supertile_image(supertile_idx, zoomed_cell_size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(f"map_cell_{r}_{c}", "map_image"))
        self.map_zoom_label.config(text=f"{int(self.map_zoom_level * 100)}%")

    def update_map_info_labels(self): # Unchanged
         self.map_size_label.config(text=f"{map_width} x {map_height}")
         self.map_supertile_select_label.config(text=f"Selected Supertile for Painting: {selected_supertile_for_map}")

    def draw_tileset_viewer(self, canvas, highlighted_tile_index):
        """Draws the tileset viewer using cached PhotoImages."""
        canvas.delete("all") # Clear previous contents
        padding = 1
        size = VIEWER_TILE_SIZE # Use the constant for tile size in viewers

        # Calculate needed canvas size based on number of tiles
        max_rows = math.ceil(num_tiles_in_set / NUM_TILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding
        canvas_width = NUM_TILES_ACROSS * (size + padding) + padding
        str_scroll = f"0 0 {float(canvas_width)} {float(canvas_height)}"

        # Update scrollregion if necessary
        current_scroll = canvas.cget("scrollregion")
        # Handle potential tuple return in newer Tk versions
        if isinstance(current_scroll, tuple):
            current_scroll = " ".join(map(str, current_scroll))
        if current_scroll != str_scroll:
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        # Draw each tile preview
        for i in range(num_tiles_in_set):
            # Calculate grid position
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS)
            base_x = tile_c * (size + padding) + padding
            base_y = tile_r * (size + padding) + padding

            # Get cached image for this tile
            img = self.create_tile_image(i, size)
            # Place image on canvas
            canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(f"tile_img_{i}", "tile_image")) # Added common tag

            # Draw selection border
            outline_color = "red" if i == highlighted_tile_index else "grey"
            outline_width = 2 if i == highlighted_tile_index else 1
            canvas.create_rectangle(
                base_x - padding / 2, base_y - padding / 2,
                base_x + size + padding / 2, base_y + size + padding / 2,
                outline=outline_color,
                width=outline_width,
                tags=f"tile_border_{i}"
            )
        
    # --- Event Handlers ---
    def on_tab_change(self, event): # Unchanged
        selected_tab = self.notebook.index(self.notebook.select())
        # Redraw based on the selected tab to ensure views are current
        if selected_tab == 0: self.update_all_displays(changed_level="palette")
        elif selected_tab == 1: self.update_all_displays(changed_level="tile")
        elif selected_tab == 2: self.update_all_displays(changed_level="supertile")
        elif selected_tab == 3: self.update_all_displays(changed_level="map")

    # --- vvv NEW Palette Editor Handlers vvv ---
    def handle_current_palette_click(self, event):
        """Selects a slot in the 16-color active palette display."""
        canvas = self.current_palette_canvas
        size = CURRENT_PALETTE_SLOT_SIZE
        padding = 2
        col = event.x // (size + padding)
        row = event.y // (size + padding)
        clicked_slot = row * 4 + col # Assuming 4 columns

        if 0 <= clicked_slot < 16:
            if self.selected_palette_slot != clicked_slot:
                self.selected_palette_slot = clicked_slot
                self.draw_current_palette() # Redraw to move highlight
                self.update_palette_info_labels() # Update info display

    def handle_512_picker_click(self, event):
        """Picks a color from the 512 grid and applies it to the selected slot."""
        if not (0 <= self.selected_palette_slot < 16):
             messagebox.showwarning("Select Slot", "Please select a slot (0-15) in the 'Active Palette' first.")
             return

        canvas = self.msx2_picker_canvas
        size = MSX2_PICKER_SQUARE_SIZE
        padding = 1
        cols = MSX2_PICKER_COLS
        # Account for scroll position
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)
        # Calculate column and row in the picker grid
        col = int(canvas_x // (size + padding))
        row = int(canvas_y // (size + padding))
        # Calculate the index (0-511) in the flat list
        clicked_index = row * cols + col

        if 0 <= clicked_index < 512:
            new_color_hex = msx2_512_colors_hex[clicked_index]
            target_slot = self.selected_palette_slot

            # Check if color actually changed
            if self.active_msx_palette[target_slot] != new_color_hex:
                self.active_msx_palette[target_slot] = new_color_hex
                print(f"Set Palette Slot {target_slot} to {new_color_hex}")

                # --- Crucial: Update everything as palette changed ---
                self.clear_all_caches() # Cache is now invalid
                self.update_all_displays(changed_level="all") # Redraw everything
                # --- Crucial ---

                # Explicitly update palette info labels after full redraw finishes
                # (update_all_displays calls this, but maybe do it again for safety)
                # self.update_palette_info_labels()
                # self.draw_current_palette() # Also redrawn by update_all_displays

        else:
            print("Clicked outside valid color range in picker.")

    def handle_rgb_apply(self):
        """Applies the R,G,B (0-7) values from entry boxes to the selected slot."""
        if not (0 <= self.selected_palette_slot < 16):
             messagebox.showwarning("Select Slot", "Please select a slot (0-15) in the 'Active Palette' first.")
             return

        try:
            r = int(self.rgb_r_var.get())
            g = int(self.rgb_g_var.get())
            b = int(self.rgb_b_var.get())

            if not (0 <= r <= 7 and 0 <= g <= 7 and 0 <= b <= 7):
                raise ValueError("RGB values must be between 0 and 7.")

            # Convert 0-7 RGB to hex
            r_255 = min(255, r * 36)
            g_255 = min(255, g * 36)
            b_255 = min(255, b * 36)
            new_color_hex = f"#{r_255:02x}{g_255:02x}{b_255:02x}"
            target_slot = self.selected_palette_slot

            # Check if color actually changed
            if self.active_msx_palette[target_slot] != new_color_hex:
                 self.active_msx_palette[target_slot] = new_color_hex
                 print(f"Set Palette Slot {target_slot} to {new_color_hex} via RGB")

                 # --- Crucial: Update everything as palette changed ---
                 self.clear_all_caches()
                 self.update_all_displays(changed_level="all")
                 # --- Crucial ---

        except ValueError as e:
            messagebox.showerror("Invalid RGB", f"Invalid RGB input: {e}")
    # --- ^^^ NEW Palette Editor Handlers ^^^ ---

    def handle_editor_click(self, event): # Unchanged logic
        global last_drawn_pixel, current_tile_index, tileset_patterns
        # ... (Identical logic) ...
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE; r = event.y // EDITOR_PIXEL_SIZE
        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            pixel_value = 1 if event.num == 1 else 0
            if tileset_patterns[current_tile_index][r][c] != pixel_value:
                tileset_patterns[current_tile_index][r][c] = pixel_value
                self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
            last_drawn_pixel = (r, c)

    def handle_editor_drag(self, event): # Unchanged logic
        global last_drawn_pixel, current_tile_index, tileset_patterns
        # ... (Identical logic) ...
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE; r = event.y // EDITOR_PIXEL_SIZE
        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            if (r, c) != last_drawn_pixel:
                pixel_value = 1 if event.state & 0x100 else (0 if event.state & 0x400 else -1)
                if pixel_value != -1 and tileset_patterns[current_tile_index][r][c] != pixel_value:
                    tileset_patterns[current_tile_index][r][c] = pixel_value
                    self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
                last_drawn_pixel = (r, c)

    def handle_tile_editor_palette_click(self, event): # Renamed, simpler logic
        """Selects a color index (0-15) from the Tile Editor's palette selector."""
        global selected_color_index # Use global for the drawing color index
        canvas = self.tile_editor_palette_canvas
        size = PALETTE_SQUARE_SIZE
        padding = 2
        col = event.x // (size + padding)
        row = event.y // (size + padding)
        clicked_index = row * 4 + col # Assuming 4 columns

        if 0 <= clicked_index < 16:
            if selected_color_index != clicked_index:
                selected_color_index = clicked_index
                self.draw_tile_editor_palette() # Redraw this palette only for highlight

    def set_row_color(self, row, fg_or_bg): # Uses global selected_color_index
        global tileset_colors, current_tile_index, selected_color_index
        # ... (Logic is identical, uses global selected_color_index) ...
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if not (0 <= selected_color_index < 16): return # Index must be valid for active palette
        if 0 <= row < TILE_HEIGHT:
            current_fg_idx, current_bg_idx = tileset_colors[current_tile_index][row]; changed = False
            if fg_or_bg == 'fg' and current_fg_idx != selected_color_index:
                tileset_colors[current_tile_index][row] = (selected_color_index, current_bg_idx); changed = True
            elif fg_or_bg == 'bg' and current_bg_idx != selected_color_index:
                tileset_colors[current_tile_index][row] = (current_fg_idx, selected_color_index); changed = True
            if changed:
                self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")

    def handle_tileset_click(self, event): # Unchanged logic
        global current_tile_index
        # ... (Identical logic) ...
        canvas = event.widget; padding = 1; size = VIEWER_TILE_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and current_tile_index != clicked_index: current_tile_index = clicked_index; self.update_all_displays(changed_level="tile")

    def handle_st_tileset_click(self, event): # Unchanged logic
        global selected_tile_for_supertile
        # ... (Identical logic) ...
        canvas = event.widget; padding = 1; size = VIEWER_TILE_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and selected_tile_for_supertile != clicked_index: selected_tile_for_supertile = clicked_index; self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile); self.update_supertile_info_labels()

    def handle_supertile_def_click(self, event): # Unchanged logic
        global current_supertile_index, supertiles_data
        # ... (Identical logic) ...
        if not (0 <= current_supertile_index < num_supertiles): return
        if not (0 <= selected_tile_for_supertile < num_tiles_in_set): return
        canvas = self.supertile_def_canvas; size = SUPERTILE_DEF_TILE_SIZE; col = event.x // size; row = event.y // size
        if 0 <= row < SUPERTILE_GRID_DIM and 0 <= col < SUPERTILE_GRID_DIM:
            if supertiles_data[current_supertile_index][row][col] != selected_tile_for_supertile:
                supertiles_data[current_supertile_index][row][col] = selected_tile_for_supertile
                self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")

    def handle_supertile_selector_click(self, event): # Unchanged logic
        global current_supertile_index
        # ... (Identical logic) ...
        canvas = event.widget; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and current_supertile_index != clicked_index: current_supertile_index = clicked_index; self.update_all_displays(changed_level="supertile")

    def handle_map_supertile_selector_click(self, event): # Unchanged logic
        global selected_supertile_for_map
        # ... (Identical logic) ...
        canvas = event.widget; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; canvas_x = canvas.canvasx(event.x); canvas_y = canvas.canvasy(event.y); col = int(canvas_x // (size + padding)); row = int(canvas_y // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and selected_supertile_for_map != clicked_index: selected_supertile_for_map = clicked_index; self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map); self.update_map_info_labels()

    def _paint_map_cell(self, event_x, event_y): # Unchanged logic
        global map_data, last_painted_map_cell
        # ... (Identical logic) ...
        canvas = self.map_canvas; zoomed_cell_size = self.get_zoomed_map_cell_size()
        if zoomed_cell_size <= 0: return
        canvas_x = canvas.canvasx(event_x); canvas_y = canvas.canvasy(event_y)
        c = int(canvas_x // zoomed_cell_size); r = int(canvas_y // zoomed_cell_size)
        if 0 <= r < map_height and 0 <= c < map_width:
            current_cell_id = (r, c)
            if current_cell_id != last_painted_map_cell:
                 if map_data[r][c] != selected_supertile_for_map:
                    map_data[r][c] = selected_supertile_for_map; base_x = c * zoomed_cell_size; base_y = r * zoomed_cell_size
                    img = self.create_supertile_image(selected_supertile_for_map, zoomed_cell_size); tag = f"map_cell_{r}_{c}"
                    canvas.delete(tag); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=(tag, "map_image"))
                 last_painted_map_cell = current_cell_id

    def handle_map_click(self, event): # Unchanged logic
        global last_painted_map_cell; last_painted_map_cell = None; self._paint_map_cell(event.x, event.y)

    def handle_map_drag(self, event): # Unchanged logic
        self._paint_map_cell(event.x, event.y)

    # --- File Menu Commands --- (Mostly unchanged, New Project clears palette)
    def new_project(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        global supertiles_data, current_supertile_index, num_supertiles, selected_tile_for_supertile
        global map_data, map_width, map_height, selected_supertile_for_map, last_painted_map_cell
        global tile_clipboard_pattern, tile_clipboard_colors, supertile_clipboard_data

        confirm = messagebox.askokcancel("New Project", "Discard all current data (Tiles, Supertiles, Map, Palette, Clipboards) and start new?")
        if confirm:
            # Reset Tile data
            tileset_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            tileset_colors = [[(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)] # Use default indices
            current_tile_index = 0; num_tiles_in_set = 1
            # Reset Supertile data
            supertiles_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
            current_supertile_index = 0; num_supertiles = 1; selected_tile_for_supertile = 0
            # Reset Map data
            map_width = DEFAULT_MAP_WIDTH; map_height = DEFAULT_MAP_HEIGHT
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            selected_supertile_for_map = 0; last_painted_map_cell = None
            # Reset Clipboards
            tile_clipboard_pattern = None; tile_clipboard_colors = None; supertile_clipboard_data = None
            # --- vvv Reset Palette vvv ---
            self.active_msx_palette = list(DEFAULT_MSX1_COLORS_HEX)
            self.selected_palette_slot = 0
            # --- ^^^ Reset Palette ^^^ ---
            # Update UI
            self.root.title("MSX2 Tile/Map/Palette Editor - Untitled")
            self.clear_all_caches()
            self.set_map_zoom(1.0) # Reset zoom
            self.update_all_displays(changed_level="all")

    def save_tileset(self): # Unchanged
        global num_tiles_in_set, tileset_patterns, tileset_colors
        # ... (Identical save logic) ...
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Tiles", filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Save Tileset As...")
        if not filepath: return
        try:
             with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_tiles_in_set))
                for i in range(num_tiles_in_set):
                    pattern = tileset_patterns[i]
                    for r in range(TILE_HEIGHT):
                        byte_val = 0; row_pattern = pattern[r]
                        for c in range(TILE_WIDTH):
                            if row_pattern[c] == 1: byte_val |= (1 << (7 - c))
                        f.write(struct.pack('B', byte_val))
                    colors = tileset_colors[i]
                    for r in range(TILE_HEIGHT):
                        fg, bg = colors[r]; color_byte_val = ((fg & 0x0F) << 4) | (bg & 0x0F)
                        f.write(struct.pack('B', color_byte_val))
             messagebox.showinfo("Save Successful", f"Tileset saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save tileset:\n{e}")

    def open_tileset(self): # Unchanged
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, selected_tile_for_supertile
        # ... (Identical load logic) ...
        filepath = filedialog.askopenfilename( filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Open Tileset")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 loaded_num_tiles = struct.unpack('B', f.read(1))[0]
                 if not (1 <= loaded_num_tiles <= MAX_TILES): raise ValueError(f"Invalid tile count: {loaded_num_tiles}")
                 new_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; new_colors = [[(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 for i in range(loaded_num_tiles):
                     for r in range(TILE_HEIGHT):
                         pattern_byte = f.read(1);
                         if not pattern_byte: raise EOFError(f"EOF pattern T:{i} R:{r}")
                         byte_val = struct.unpack('B', pattern_byte)[0]
                         for c in range(TILE_WIDTH): new_patterns[i][r][c] = (byte_val >> (7 - c)) & 1
                     for r in range(TILE_HEIGHT):
                         color_byte = f.read(1);
                         if not color_byte: raise EOFError(f"EOF color T:{i} R:{r}")
                         byte_val = struct.unpack('B', color_byte)[0]; fg = (byte_val >> 4) & 0x0F; bg = byte_val & 0x0F
                         new_colors[i][r] = (fg, bg)
            tileset_patterns = new_patterns; tileset_colors = new_colors; num_tiles_in_set = loaded_num_tiles; current_tile_index = 0; selected_tile_for_supertile = 0
            self.clear_all_caches(); self.update_all_displays(changed_level="all"); messagebox.showinfo("Open Successful", f"Loaded {num_tiles_in_set} tiles from {filepath}")
        except FileNotFoundError: messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except EOFError as e: messagebox.showerror("Open Error", f"File incomplete/corrupt:\n{e}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open/parse tileset:\n{e}")

    def save_supertiles(self): # Unchanged
        global num_supertiles, supertiles_data
        # ... (Identical save logic) ...
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Super", filetypes=[("MSX Supertiles", "*.SC4Super")], title="Save Supertiles As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_supertiles))
                for i in range(num_supertiles):
                    definition = supertiles_data[i]
                    for r in range(SUPERTILE_GRID_DIM):
                        row_data = definition[r]
                        for c in range(SUPERTILE_GRID_DIM): f.write(struct.pack('B', row_data[c]))
            messagebox.showinfo("Save Successful", f"Supertiles saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save supertiles:\n{e}")

    def open_supertiles(self): # Unchanged
        global supertiles_data, num_supertiles, current_supertile_index, selected_supertile_for_map
        # ... (Identical load logic) ...
        filepath = filedialog.askopenfilename( filetypes=[("MSX Supertiles", "*.SC4Super")], title="Open Supertiles")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 loaded_num_st = struct.unpack('B', f.read(1))[0]
                 if not (1 <= loaded_num_st <= MAX_SUPERTILES): raise ValueError(f"Invalid supertile count: {loaded_num_st}")
                 new_st_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
                 for i in range(loaded_num_st):
                     for r in range(SUPERTILE_GRID_DIM):
                         for c in range(SUPERTILE_GRID_DIM):
                              idx_byte = f.read(1);
                              if not idx_byte: raise EOFError(f"EOF supertile {i} at [{r},{c}]")
                              new_st_data[i][r][c] = struct.unpack('B', idx_byte)[0]
            supertiles_data = new_st_data; num_supertiles = loaded_num_st; current_supertile_index = 0; selected_supertile_for_map = 0
            self.supertile_image_cache.clear(); self.update_all_displays(changed_level="supertile"); messagebox.showinfo("Open Successful", f"Loaded {num_supertiles} supertiles from {filepath}")
        except FileNotFoundError: messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except EOFError as e: messagebox.showerror("Open Error", f"File incomplete/corrupt:\n{e}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open/parse supertiles:\n{e}")

    def save_map(self): # Unchanged
        global map_width, map_height, map_data
        # ... (Identical save logic) ...
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Map", filetypes=[("MSX Map", "*.SC4Map")], title="Save Map As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f:
                 f.write(struct.pack('>HH', map_width, map_height))
                 for r in range(map_height):
                     row_data = map_data[r]
                     for c in range(map_width): f.write(struct.pack('B', row_data[c]))
            messagebox.showinfo("Save Successful", f"Map saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save map:\n{e}")

    def open_map(self): # Unchanged
        global map_data, map_width, map_height
        # ... (Identical load logic) ...
        filepath = filedialog.askopenfilename( filetypes=[("MSX Map", "*.SC4Map")], title="Open Map")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 dim_bytes = f.read(4);
                 if len(dim_bytes) < 4: raise ValueError("Invalid map header")
                 loaded_w, loaded_h = struct.unpack('>HH', dim_bytes)
                 if not (1 <= loaded_w <= 1024 and 1 <= loaded_h <= 1024): raise ValueError(f"Invalid dimensions: {loaded_w}x{loaded_h}")
                 new_map_data = [[0]*loaded_w for _ in range(loaded_h)]
                 for r in range(loaded_h):
                     for c in range(loaded_w):
                          st_idx_byte = f.read(1);
                          if not st_idx_byte: raise EOFError(f"EOF map at row {r}, col {c}")
                          new_map_data[r][c] = struct.unpack('B', st_idx_byte)[0]
            map_width = loaded_w; map_height = loaded_h; map_data = new_map_data
            self.update_all_displays(changed_level="map"); messagebox.showinfo("Open Successful", f"Loaded {map_width}x{map_height} map from {filepath}")
        except FileNotFoundError: messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except EOFError as e: messagebox.showerror("Open Error", f"File incomplete/corrupt:\n{e}")
        except struct.error as e: messagebox.showerror("Open Error", f"Error unpacking data:\n{e}")
        except ValueError as e: messagebox.showerror("Open Error", f"Invalid data in file:\n{e}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open/parse map:\n{e}")


    # --- Edit Menu Commands --- (Unchanged logic, only formatting difference)
    def set_tileset_size(self):
        global num_tiles_in_set, current_tile_index, selected_tile_for_supertile
        prompt = f"Enter number of tiles (1-{MAX_TILES}):"
        new_size_str = simpledialog.askstring("Set Tileset Size", prompt, initialvalue=str(num_tiles_in_set))
        if new_size_str:
            try:
                new_size = int(new_size_str)
                if not (1 <= new_size <= MAX_TILES):
                    messagebox.showerror("Invalid Size", f"Size must be between 1 and {MAX_TILES}.")
                    return
                reduced = new_size < num_tiles_in_set
                confirmed = (not reduced) or messagebox.askokcancel("Reduce Size", f"Reducing size to {new_size} will discard tiles {new_size} to {num_tiles_in_set-1}. Proceed?")
                if confirmed:
                    if reduced:
                        for i in range(new_size, num_tiles_in_set): self.invalidate_tile_cache(i)
                    num_tiles_in_set = new_size
                    current_tile_index = max(0, min(current_tile_index, num_tiles_in_set - 1))
                    selected_tile_for_supertile = max(0, min(selected_tile_for_supertile, num_tiles_in_set - 1)) if num_tiles_in_set > 0 else 0
                    self.update_all_displays(changed_level="all")
            except ValueError: messagebox.showerror("Invalid Input", "Please enter a valid whole number.")

    def set_supertile_count(self):
        global num_supertiles, current_supertile_index, selected_supertile_for_map
        prompt = f"Enter number of supertiles (1-{MAX_SUPERTILES}):"
        new_count_str = simpledialog.askstring("Set Supertile Count", prompt, initialvalue=str(num_supertiles))
        if new_count_str:
            try:
                new_count = int(new_count_str)
                if not (1 <= new_count <= MAX_SUPERTILES):
                    messagebox.showerror("Invalid Count", f"Count must be between 1 and {MAX_SUPERTILES}.")
                    return
                reduced = new_count < num_supertiles
                confirmed = (not reduced) or messagebox.askokcancel("Reduce Count", f"Reducing count to {new_count} will discard supertiles {new_count} to {num_supertiles-1}. Proceed?")
                if confirmed:
                    if reduced:
                        for i in range(new_count, num_supertiles): self.invalidate_supertile_cache(i)
                    num_supertiles = new_count
                    current_supertile_index = max(0, min(current_supertile_index, num_supertiles - 1))
                    selected_supertile_for_map = max(0, min(selected_supertile_for_map, num_supertiles - 1)) if num_supertiles > 0 else 0
                    self.update_all_displays(changed_level="supertile")
            except ValueError: messagebox.showerror("Invalid Input", "Please enter a valid whole number.")

    def set_map_dimensions(self):
        global map_width, map_height, map_data
        prompt = "Enter new dimensions (Width x Height):"
        dims = simpledialog.askstring("Set Map Dimensions", prompt, initialvalue=f"{map_width}x{map_height}")
        if dims:
            try:
                parts = dims.lower().split('x')
                if len(parts) != 2: raise ValueError("Format must be WidthxHeight")
                new_w = int(parts[0].strip()); new_h = int(parts[1].strip())
                min_dim, max_dim = 1, 1024
                if not (min_dim <= new_w <= max_dim and min_dim <= new_h <= max_dim): raise ValueError(f"Dimensions must be between {min_dim} and {max_dim}")
                if new_w == map_width and new_h == map_height: return
                confirmed = (new_w >= map_width and new_h >= map_height) or messagebox.askokcancel("Resize Map", "Reducing map size will discard data outside the new boundaries. Proceed?")
                if confirmed:
                    new_map_data = [[0 for _ in range(new_w)] for _ in range(new_h)]
                    rows_to_copy = min(map_height, new_h); cols_to_copy = min(map_width, new_w)
                    for r in range(rows_to_copy):
                        for c in range(cols_to_copy): new_map_data[r][c] = map_data[r][c]
                    map_width = new_w; map_height = new_h; map_data = new_map_data
                    self.update_all_displays(changed_level="map")
            except ValueError as e: messagebox.showerror("Invalid Input", f"Error parsing dimensions: {e}")
            except Exception as e: messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def clear_current_tile(self):
        global tileset_patterns, tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        prompt = f"Clear pattern and reset colors for tile {current_tile_index}?"
        if messagebox.askokcancel("Clear Tile", prompt):
            tileset_patterns[current_tile_index] = [[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)]
            tileset_colors[current_tile_index] = [(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)]
            self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")

    def clear_current_supertile(self):
        global supertiles_data, current_supertile_index
        if not (0 <= current_supertile_index < num_supertiles): return
        prompt = f"Clear definition (set all to tile 0) for supertile {current_supertile_index}?"
        if messagebox.askokcancel("Clear Supertile", prompt):
            supertiles_data[current_supertile_index] = [[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)]
            self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")

    def clear_map(self):
        global map_data, map_width, map_height
        prompt = "Clear entire map (set all to supertile 0)?"
        if messagebox.askokcancel("Clear Map", prompt):
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            self.update_all_displays(changed_level="map")

    # --- Copy/Paste Methods --- (One instruction per line)
    def copy_current_tile(self):
        global tile_clipboard_pattern, tile_clipboard_colors
        global current_tile_index, num_tiles_in_set
        global tileset_patterns, tileset_colors
        if not (0 <= current_tile_index < num_tiles_in_set):
            messagebox.showwarning("Copy Tile", "No valid tile selected to copy.")
            return
        pattern_to_copy = tileset_patterns[current_tile_index]
        colors_to_copy = tileset_colors[current_tile_index]
        tile_clipboard_pattern = copy.deepcopy(pattern_to_copy)
        tile_clipboard_colors = copy.deepcopy(colors_to_copy)
        print(f"Tile {current_tile_index} copied to clipboard.")

    def paste_tile(self):
        global tile_clipboard_pattern, tile_clipboard_colors
        global current_tile_index, num_tiles_in_set
        global tileset_patterns, tileset_colors
        if tile_clipboard_pattern is None or tile_clipboard_colors is None:
            messagebox.showinfo("Paste Tile", "Tile clipboard is empty. Copy a tile first.")
            return
        if not (0 <= current_tile_index < num_tiles_in_set):
            messagebox.showwarning("Paste Tile", "No valid tile selected to paste onto.")
            return
        prompt = f"Overwrite Tile {current_tile_index} with clipboard data?"
        confirm = messagebox.askokcancel("Paste Tile", prompt)
        if confirm:
            tileset_patterns[current_tile_index] = copy.deepcopy(tile_clipboard_pattern)
            tileset_colors[current_tile_index] = copy.deepcopy(tile_clipboard_colors)
            self.invalidate_tile_cache(current_tile_index)
            self.update_all_displays(changed_level="tile")
            print(f"Pasted tile data onto Tile {current_tile_index}.")

    def copy_current_supertile(self):
        global supertile_clipboard_data
        global current_supertile_index, num_supertiles
        global supertiles_data
        if not (0 <= current_supertile_index < num_supertiles):
            messagebox.showwarning("Copy Supertile", "No valid supertile selected to copy.")
            return
        data_to_copy = supertiles_data[current_supertile_index]
        supertile_clipboard_data = copy.deepcopy(data_to_copy)
        print(f"Supertile {current_supertile_index} copied to clipboard.")

    def paste_supertile(self):
        global supertile_clipboard_data
        global current_supertile_index, num_supertiles
        global supertiles_data
        if supertile_clipboard_data is None:
            messagebox.showinfo("Paste Supertile", "Supertile clipboard is empty. Copy a supertile first.")
            return
        if not (0 <= current_supertile_index < num_supertiles):
            messagebox.showwarning("Paste Supertile", "No valid supertile selected to paste onto.")
            return
        prompt = f"Overwrite Supertile {current_supertile_index} with clipboard data?"
        confirm = messagebox.askokcancel("Paste Supertile", prompt)
        if confirm:
            supertiles_data[current_supertile_index] = copy.deepcopy(supertile_clipboard_data)
            self.invalidate_supertile_cache(current_supertile_index)
            self.update_all_displays(changed_level="supertile")
            print(f"Pasted supertile data onto Supertile {current_supertile_index}.")

    # --- Add New Tile/Supertile Methods --- (One instruction per line)
    def add_new_tile(self):
        global num_tiles_in_set, current_tile_index
        if num_tiles_in_set >= MAX_TILES:
            messagebox.showwarning("Maximum Tiles", f"Cannot add more tiles. The maximum is {MAX_TILES}.")
            return
        num_tiles_in_set = num_tiles_in_set + 1
        new_tile_idx = num_tiles_in_set - 1
        tileset_patterns[new_tile_idx] = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
        tileset_colors[new_tile_idx] = [(WHITE_IDX, BLACK_IDX) for _ in range(TILE_HEIGHT)] # Use default indices
        current_tile_index = new_tile_idx
        self.update_all_displays(changed_level="tile")
        self.scroll_viewers_to_tile(current_tile_index)

    def add_new_supertile(self):
        global num_supertiles, current_supertile_index
        if num_supertiles >= MAX_SUPERTILES:
            messagebox.showwarning("Maximum Supertiles", f"Cannot add more supertiles. The maximum is {MAX_SUPERTILES}.")
            return
        num_supertiles = num_supertiles + 1
        new_st_idx = num_supertiles - 1
        supertiles_data[new_st_idx] = [[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)]
        current_supertile_index = new_st_idx
        self.update_all_displays(changed_level="supertile")
        self.scroll_selectors_to_supertile(current_supertile_index)

    # --- Zoom Methods --- (One instruction per line)
    def change_map_zoom(self, delta):
        current_zoom = self.map_zoom_level
        new_zoom = current_zoom + delta
        min_zoom = 0.25
        max_zoom = 4.0
        clamped_zoom = max(min_zoom, min(max_zoom, new_zoom))
        self.set_map_zoom(clamped_zoom)

    def set_map_zoom(self, new_zoom_level):
        safe_zoom_level = float(new_zoom_level)
        if safe_zoom_level <= 0:
             return
        current_map_zoom = self.map_zoom_level
        if current_map_zoom != safe_zoom_level:
            self.map_zoom_level = safe_zoom_level
            self.draw_map_canvas() # Redraw map canvas which also updates label

    def get_zoomed_map_cell_size(self):
        base_size = MAP_CELL_PREVIEW_SIZE
        current_zoom = self.map_zoom_level
        zoomed_size_float = base_size * current_zoom
        zoomed_size_int = int(zoomed_size_float)
        # Ensure minimum size of 1 pixel
        final_size = max(1, zoomed_size_int)
        return final_size

    # --- Scrolling Methods --- (One instruction per line)
    def scroll_viewers_to_tile(self, tile_index):
        if tile_index < 0:
            return
        padding = 1
        tile_size = VIEWER_TILE_SIZE
        items_per_row = NUM_TILES_ACROSS
        row, _ = divmod(tile_index, items_per_row)
        target_y = row * (tile_size + padding)
        # Scroll main viewer
        canvas_main = self.tileset_canvas
        try:
            scroll_info_tuple = canvas_main.cget("scrollregion")
            scroll_info = str(scroll_info_tuple).split() # Convert if tuple
            if len(scroll_info) == 4:
                total_height = float(scroll_info[3])
                if total_height > 0:
                    fraction = target_y / total_height
                    clamped_fraction = min(1.0, max(0.0, fraction))
                    canvas_main.yview_moveto(clamped_fraction)
        except Exception as e:
            print(f"Error scrolling main tileset viewer: {e}")
        # Scroll ST viewer
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
        except Exception as e:
            print(f"Error scrolling ST tileset viewer: {e}")

    def scroll_selectors_to_supertile(self, supertile_index):
        if supertile_index < 0:
             return
        padding = 1
        item_size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        items_per_row = NUM_SUPERTILES_ACROSS
        row, _ = divmod(supertile_index, items_per_row)
        target_y = row * (item_size + padding)
        # Scroll ST tab selector
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
        except Exception as e:
            print(f"Error scrolling ST selector: {e}")
        # Scroll Map tab selector
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
        except Exception as e:
             print(f"Error scrolling Map selector: {e}")

    # --- Palette Conversion Helpers ---
    def _hex_to_rgb7(self, hex_color):
        """Converts a hex color string (#RRGGBB) to its exact matching MSX2 R,G,B (0-7) tuple
           by looking it up in the pre-generated list. Returns (0,0,0) if not found."""
        try:
            # Validate input type and basic format
            if not isinstance(hex_color, str):
                raise TypeError("Input must be a string.")
            if not hex_color.startswith('#') or len(hex_color) != 7:
                raise ValueError(f"Input '{hex_color}' is not a valid #RRGGBB format.")

            # Prepare for lookup (use lowercase)
            lookup_hex = hex_color.lower()

            # Find the index in the pre-generated 512 hex color list
            # list.index() raises ValueError if not found
            idx512 = msx2_512_colors_hex.index(lookup_hex)

            # Return the corresponding (r,g,b) tuple from the parallel list
            return msx2_512_colors_rgb7[idx512]

        except ValueError:
            # Handle case where the hex format was bad OR the exact hex was not found
            print(f"Warning: Could not find exact MSX2 RGB7 mapping for hex '{hex_color}'. Returning (0,0,0).")
            return (0, 0, 0) # Fallback to black
        except TypeError as e:
            # Handle case where input wasn't a string
            print(f"Error in _hex_to_rgb7: Input type error for '{hex_color}'. {e}")
            return (0, 0, 0) # Fallback to black
        except Exception as e:
            # Catch any other unexpected errors
            print(f"Unexpected error in _hex_to_rgb7 for '{hex_color}': {e}")
            return (0, 0, 0) # Fallback to black

    def _rgb7_to_hex(self, r, g, b):
        """Converts MSX2 R,G,B (0-7) tuple to hex color string."""
        try:
            # 1. Ensure values are integers and clamp them to the valid 0-7 range
            # (int() handles potential float inputs, clamp ensures range)
            safe_r = max(0, min(7, int(r)))
            safe_g = max(0, min(7, int(g)))
            safe_b = max(0, min(7, int(b)))

            # 2. Approximate conversion to 0-255 range for display hex
            #    7 * 36 = 252, which is the standard approximation.
            #    Using min(255,...) is technically redundant after clamping but safe.
            r_255 = min(255, safe_r * 36)
            g_255 = min(255, safe_g * 36)
            b_255 = min(255, safe_b * 36)

            # 3. Format as a standard Tkinter hex color string (#RRGGBB)
            #    :02x ensures two digits with leading zero if needed.
            hex_color = f"#{r_255:02x}{g_255:02x}{b_255:02x}"

            # 4. Return the formatted string
            return hex_color

        # 5. Handle potential errors during conversion (e.g., non-numeric input)
        except (ValueError, TypeError) as e:
            print(f"Error in _rgb7_to_hex converting input ({r},{g},{b}): {e}")
            return "#000000" # Fallback to black on error
        except Exception as e: # Catch any other unexpected errors
            print(f"Unexpected error in _rgb7_to_hex for ({r},{g},{b}): {e}")
            return "#000000" # Fallback to black

    def save_palette(self):
        """Saves the current 16 active palette colors to a binary file."""
        # Ask user for the save file path
        filepath = filedialog.asksaveasfilename(
            defaultextension=".msxpal", # Use a specific extension
            filetypes=[("MSX Palette File", "*.msxpal"), ("All Files", "*.*")],
            title="Save MSX Palette As..."
        )
        # Exit if the user cancelled the dialog
        if not filepath:
            return

        # Use try...except for robust file handling
        try:
            # Open the file in binary write mode ('wb')
            with open(filepath, 'wb') as f:
                # Check if the active palette has 16 colors (sanity check)
                if len(self.active_msx_palette) != 16:
                    messagebox.showerror("Palette Error", "Internal Error: Active palette does not contain 16 colors.")
                    return

                # Loop through the 16 hex color strings in the active palette
                for i in range(16):
                    hex_color = self.active_msx_palette[i]
                    # Convert the hex color back to its R,G,B (0-7) representation
                    r, g, b = self._hex_to_rgb7(hex_color)

                    # Pack these three integer values (0-7) as three consecutive unsigned bytes
                    packed_bytes = struct.pack('BBB', r, g, b)

                    # Write the packed 3 bytes to the file
                    f.write(packed_bytes)

            # Inform the user of success
            messagebox.showinfo("Save Successful", f"Palette saved successfully to {filepath}")

        # Handle potential errors during file writing or conversion
        except Exception as e:
            messagebox.showerror("Save Palette Error", f"Failed to save palette file:\n{e}")

    def open_palette(self):
        """Loads a 16-color palette (3 bytes per color, RGB 0-7) from a binary file."""
        # Ask user to select the file to load
        filepath = filedialog.askopenfilename(
            filetypes=[("MSX Palette File", "*.msxpal"), ("All Files", "*.*")],
            title="Open MSX Palette"
        )
        # Exit if the user cancelled the dialog
        if not filepath:
            return

        try:
            # Define the exact expected file size (16 colors * 3 bytes/color)
            expected_size = 16 * 3
            # Temporary list to store the loaded hex colors
            new_palette_hex = []

            # Open the file in binary read mode ('rb')
            with open(filepath, 'rb') as f:
                # Read the expected number of bytes (plus one extra to check size)
                palette_data = f.read(expected_size + 1)

                # Validate the file size
                if len(palette_data) < expected_size:
                    raise ValueError(f"Invalid file size. Expected {expected_size} bytes, got {len(palette_data)}.")
                if len(palette_data) > expected_size:
                    # Allow slightly larger files but warn the user
                    print(f"Warning: File '{os.path.basename(filepath)}' is larger than expected ({expected_size} bytes). Extra data ignored.")

                # Process the 16 colors from the read data
                for i in range(16):
                    # Calculate the offset for the current color's bytes
                    offset = i * 3
                    # Unpack 3 consecutive bytes starting from the offset
                    r, g, b = struct.unpack_from('BBB', palette_data, offset)

                    # Validate that the R,G,B values are within the expected 0-7 range
                    if not (0 <= r <= 7 and 0 <= g <= 7 and 0 <= b <= 7):
                        print(f"Warning: Invalid RGB value ({r},{g},{b}) found in file at slot {i}. Clamping to 0-7 range.")
                        # Clamp values just in case, although ideally raise error? For now, clamp.
                        r = max(0, min(7, r))
                        g = max(0, min(7, g))
                        b = max(0, min(7, b))

                    # Convert the valid/clamped R,G,B (0-7) back to a hex color string
                    hex_color = self._rgb7_to_hex(r, g, b)
                    # Add the resulting hex color to our temporary list
                    new_palette_hex.append(hex_color)

            # --- Ask for confirmation before overwriting ---
            confirm = messagebox.askokcancel(
                "Load Palette",
                "Replace the current active palette with data from this file?"
            )

            if confirm:
                # --- Commit changes only after successful load and confirmation ---
                self.active_msx_palette = new_palette_hex
                # Reset the selected slot in the palette editor UI
                self.selected_palette_slot = 0

                # --- Crucial: Palette change invalidates everything visually ---
                self.clear_all_caches() # Clear rendered tile/supertile images
                self.update_all_displays(changed_level="all") # Force redraw of all tabs

                # Inform user of success
                messagebox.showinfo("Load Successful", f"Loaded palette from {filepath}")

        # Handle potential errors during file reading, unpacking, or validation
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except struct.error as e:
             messagebox.showerror("Open Error", f"Error unpacking data (incorrect format or file size?):\n{e}")
        except ValueError as e:
             # Catches explicit ValueErrors raised or from int conversion etc.
             messagebox.showerror("Open Error", f"Invalid data or size in palette file:\n{e}")
        except Exception as e:
             # Catch any other unexpected errors
             messagebox.showerror("Open Error", f"Failed to open or parse palette file:\n{e}")

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TileEditorApp(root)
    root.mainloop()