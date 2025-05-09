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

SUPERTILE_GRID_DIM = 4 # 4x4 tiles
SUPERTILE_DEF_TILE_SIZE = TILE_WIDTH * 4 # 32 - Size of tiles in supertile definition grid
SUPERTILE_SELECTOR_PREVIEW_SIZE = TILE_WIDTH * 4 # 32 - Size of one supertile preview in selector
NUM_SUPERTILES_ACROSS = 8
MAX_SUPERTILES = 256

MAP_CELL_PREVIEW_SIZE = TILE_WIDTH * 2 # 16 - Size of one supertile cell drawn on map
DEFAULT_MAP_WIDTH = 32
DEFAULT_MAP_HEIGHT = 24

# MSX 16 Colors (Approximate RGB values)
MSX_COLORS = [
    "#000000", "#000000", "#3EB849", "#74D07D", "#5955E0", "#8076F1",
    "#B95E51", "#65DBEF", "#D96459", "#FF897D", "#CCC35E", "#DED087",
    "#3AA241", "#B766B5", "#CCCCCC", "#FFFFFF",
]
# Placeholder colors for invalid indices (more visible than magenta/cyan)
INVALID_TILE_COLOR = "#FF00FF" # Bright Magenta
INVALID_SUPERTILE_COLOR = "#00FFFF" # Bright Cyan


# --- Data Structures ---
# Tile Data
tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
current_tile_index = 0
num_tiles_in_set = 1
selected_color_index = 15
last_drawn_pixel = None

# Supertile Data
supertiles_data = [[[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
current_supertile_index = 0
num_supertiles = 1
selected_tile_for_supertile = 0

# Map Data
map_width = DEFAULT_MAP_WIDTH
map_height = DEFAULT_MAP_HEIGHT
map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
selected_supertile_for_map = 0
last_painted_map_cell = None

# Clipboard storage
tile_clipboard_pattern = None
tile_clipboard_colors = None
supertile_clipboard_data = None

# --- Utility Functions ---
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
        self.map_zoom_level = 1.0 # Start at 100%
        self.root = root
        self.root.title("MSX SCREEN 4 Tile/Map Editor - Untitled")
        self.root.state('zoomed')

        # --- Image Caches ---
        self.tile_image_cache = {} # key: (tile_index, size), value: PhotoImage
        self.supertile_image_cache = {} # key: (supertile_index, size), value: PhotoImage

        # --- UI Setup ---
        self.create_menu()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")
        self.tab_tile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_supertile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_map_editor = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_tile_editor, text='Tile Editor')
        self.notebook.add(self.tab_supertile_editor, text='Supertile Editor')
        self.notebook.add(self.tab_map_editor, text='Map Editor')
        self.create_tile_editor_widgets(self.tab_tile_editor)
        self.create_supertile_editor_widgets(self.tab_supertile_editor)
        self.create_map_editor_widgets(self.tab_map_editor)
        self.update_all_displays(changed_level="all")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    # --- Cache Management ---
    def invalidate_tile_cache(self, tile_index):
        keys_to_remove = [k for k in self.tile_image_cache if k[0] == tile_index]
        for key in keys_to_remove:
            del self.tile_image_cache[key]
        for st_index in range(num_supertiles):
            if any(supertiles_data[st_index][r][c] == tile_index for r in range(SUPERTILE_GRID_DIM) for c in range(SUPERTILE_GRID_DIM)):
                self.invalidate_supertile_cache(st_index)

    def invalidate_supertile_cache(self, supertile_index):
        keys_to_remove = [k for k in self.supertile_image_cache if k[0] == supertile_index]
        for key in keys_to_remove:
            del self.supertile_image_cache[key]

    def clear_all_caches(self):
        self.tile_image_cache.clear()
        self.supertile_image_cache.clear()


    # --- Image Generation ---
    def create_tile_image(self, tile_index, size):
        cache_key = (tile_index, size)
        if cache_key in self.tile_image_cache: return self.tile_image_cache[cache_key]
        size = max(1, int(size)); img = tk.PhotoImage(width=size, height=size)
        if not (0 <= tile_index < num_tiles_in_set):
            img.put(INVALID_TILE_COLOR, to=(0, 0, size, size)); self.tile_image_cache[cache_key] = img; return img
        pattern = tileset_patterns[tile_index]; colors = tileset_colors[tile_index]
        pixel_w_ratio = TILE_WIDTH / size; pixel_h_ratio = TILE_HEIGHT / size
        for y in range(size):
            tile_r = min(TILE_HEIGHT - 1, int(y * pixel_h_ratio)); fg_idx, bg_idx = colors[tile_r]
            bg_color = MSX_COLORS[bg_idx]; fg_color = MSX_COLORS[fg_idx]; row_colors = []
            for x in range(size):
                tile_c = min(TILE_WIDTH - 1, int(x * pixel_w_ratio)); pixel_val = pattern[tile_r][tile_c]
                row_colors.append(fg_color if pixel_val == 1 else bg_color)
            try: img.put("{" + " ".join(row_colors) + "}", to=(0, y))
            except tk.TclError as e: print(f"Warning: TclError tile {tile_index} size {size} row {y}: {e}"); img.put(row_colors[0], to=(0, y, size, y+1))
        self.tile_image_cache[cache_key] = img; return img

    # --- vvv THIS METHOD WAS CORRECTED vvv ---
    def create_supertile_image(self, supertile_index, total_size):
        """Creates or retrieves a PhotoImage for a supertile at a specific size."""
        cache_key = (supertile_index, total_size)
        if cache_key in self.supertile_image_cache: return self.supertile_image_cache[cache_key]

        total_size = max(1, int(total_size)); img = tk.PhotoImage(width=total_size, height=total_size)

        if not (0 <= supertile_index < num_supertiles):
            img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, total_size, total_size)); self.supertile_image_cache[cache_key] = img; return img

        definition = supertiles_data[supertile_index]; mini_tile_size = total_size / SUPERTILE_GRID_DIM

        if mini_tile_size < 1: print(f"Warning: ST {supertile_index} size {total_size} -> too small mini-tiles."); img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, total_size, total_size)); self.supertile_image_cache[cache_key] = img; return img

        mini_tile_pixel_h = TILE_HEIGHT / mini_tile_size; mini_tile_pixel_w = TILE_WIDTH / mini_tile_size

        for y in range(total_size):
            mini_tile_r = min(SUPERTILE_GRID_DIM - 1, int(y / mini_tile_size)); y_in_mini = y % mini_tile_size
            row_colors = [] # Start new list for this row

            for x in range(total_size):
                mini_tile_c = min(SUPERTILE_GRID_DIM - 1, int(x / mini_tile_size)); x_in_mini = x % mini_tile_size
                tile_idx = definition[mini_tile_r][mini_tile_c]

                # Default color for this pixel (used if tile_idx is invalid or try fails)
                pixel_color = INVALID_TILE_COLOR

                if 0 <= tile_idx < num_tiles_in_set:
                    tile_r = min(TILE_HEIGHT - 1, int(y_in_mini * mini_tile_pixel_h))
                    tile_c = min(TILE_WIDTH - 1, int(x_in_mini * mini_tile_pixel_w))
                    try:
                        pattern = tileset_patterns[tile_idx]
                        colors = tileset_colors[tile_idx]
                        fg_idx, bg_idx = colors[tile_r] # Potential IndexError
                        pixel_val = pattern[tile_r][tile_c] # Potential IndexError
                        # If successful, set the actual color
                        pixel_color = MSX_COLORS[fg_idx] if pixel_val == 1 else MSX_COLORS[bg_idx]
                    except IndexError:
                         print(f"Warning: IndexError accessing data for tile {tile_idx} at [{tile_r},{tile_c}]")
                         # pixel_color remains INVALID_TILE_COLOR

                # This line needs correct indentation within the 'for x' loop
                row_colors.append(pixel_color)

            # Put the completed row onto the image
            try: img.put("{" + " ".join(row_colors) + "}", to=(0, y))
            except tk.TclError as e: print(f"Warning: TclError ST {supertile_index} size {total_size} row {y}: {e}"); img.put(row_colors[0], to=(0, y, total_size, y+1)) # Fallback

        self.supertile_image_cache[cache_key] = img; return img
    # --- ^^^ END OF CORRECTED METHOD ^^^ ---


    # --- Menu Creation ---
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # --- File Menu --- (Remains the same)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project (All)", command=self.new_project)
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

        # --- Edit Menu --- (Modified)
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # -- Copy/Paste --
        edit_menu.add_command(label="Copy Tile", command=self.copy_current_tile)
        edit_menu.add_command(label="Paste Tile", command=self.paste_tile)
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy Supertile", command=self.copy_current_supertile)
        edit_menu.add_command(label="Paste Supertile", command=self.paste_supertile)
        edit_menu.add_separator()
        # -- Clear --
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile)
        edit_menu.add_command(label="Clear Current Supertile", command=self.clear_current_supertile)
        edit_menu.add_command(label="Clear Map", command=self.clear_map)
        edit_menu.add_separator()
        # -- Settings --
        edit_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size)
        edit_menu.add_command(label="Set Supertile Count...", command=self.set_supertile_count)
        edit_menu.add_command(label="Set Map Dimensions...", command=self.set_map_dimensions)

    # --- Widget Creation ---
    def create_tile_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)"); editor_frame.grid(row=0, column=0, pady=(0, 10))
        self.editor_canvas = tk.Canvas( editor_frame, width=TILE_WIDTH * EDITOR_PIXEL_SIZE, height=TILE_HEIGHT * EDITOR_PIXEL_SIZE, bg="grey")
        self.editor_canvas.grid(row=0, column=0); self.editor_canvas.bind("<Button-1>", self.handle_editor_click); self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag); self.editor_canvas.bind("<Button-3>", self.handle_editor_click); self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag)
        attr_frame = ttk.LabelFrame(left_frame, text="Row Colors (Click to set FG/BG)"); attr_frame.grid(row=1, column=0, sticky=(tk.W, tk.E)); self.attr_row_frames = []; self.attr_fg_labels = []; self.attr_bg_labels = []
        for r in range(TILE_HEIGHT):
            row_f = ttk.Frame(attr_frame); row_f.grid(row=r, column=0, sticky=tk.W, pady=1); ttk.Label(row_f, text=f"{r}:").grid(row=0, column=0, padx=(0, 5))
            fg_label = tk.Label(row_f, text=" FG ", width=3, relief="raised", borderwidth=2); fg_label.grid(row=0, column=1, padx=(0, 2)); fg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'fg')); self.attr_fg_labels.append(fg_label)
            bg_label = tk.Label(row_f, text=" BG ", width=3, relief="raised", borderwidth=2); bg_label.grid(row=0, column=2); bg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'bg')); self.attr_bg_labels.append(bg_label)
            self.attr_row_frames.append(row_f)
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S)); main_frame.grid_rowconfigure(0, weight=1)
        palette_frame = ttk.LabelFrame(right_frame, text="Color Palette"); palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.N, tk.W, tk.E))
        self.palette_canvas = tk.Canvas(palette_frame, width=4 * (PALETTE_SQUARE_SIZE + 2), height=4 * (PALETTE_SQUARE_SIZE + 2), borderwidth=0, highlightthickness=0)
        self.palette_canvas.grid(row=0, column=0); self.palette_canvas.bind("<Button-1>", self.handle_palette_click); self.palette_labels = []
        for i in range(16): row, col = divmod(i, 4); x1, y1 = col * (PALETTE_SQUARE_SIZE + 2) + 1, row * (PALETTE_SQUARE_SIZE + 2) + 1; x2, y2 = x1 + PALETTE_SQUARE_SIZE, y1 + PALETTE_SQUARE_SIZE; self.palette_canvas.create_rectangle(x1, y1, x2, y2, fill=MSX_COLORS[i], outline="grey", width=1, tags=f"pal_{i}")
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
        # ... main_frame setup ...
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10))
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_columnconfigure(1, weight=0); main_frame.grid_rowconfigure(0, weight=1)

        # --- Contents of Left Frame ---
        map_controls_frame = ttk.Frame(left_frame)
        map_controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Map Size Label
        ttk.Label(map_controls_frame, text="Map Size:").grid(row=0, column=0, padx=(0,5))
        self.map_size_label = ttk.Label(map_controls_frame, text=f"{map_width} x {map_height}")
        self.map_size_label.grid(row=0, column=1, padx=(0, 10))

        # --- vvv ZOOM CONTROLS vvv ---
        zoom_frame = ttk.Frame(map_controls_frame)
        zoom_frame.grid(row=0, column=2, padx=(10, 0)) # Place next to size label

        ttk.Button(zoom_frame, text="-", width=2, command=lambda: self.change_map_zoom(-0.25)).pack(side=tk.LEFT)
        self.map_zoom_label = ttk.Label(zoom_frame, text="100%", width=5, anchor=tk.CENTER)
        self.map_zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="+", width=2, command=lambda: self.change_map_zoom(0.25)).pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="Reset", width=5, command=lambda: self.set_map_zoom(1.0)).pack(side=tk.LEFT, padx=(5,0))
        # --- ^^^ ZOOM CONTROLS ^^^ ---

        # ... rest of left_frame setup (map_canvas_frame, weights) ...
        map_canvas_frame = ttk.LabelFrame(left_frame, text="Map (Click/Drag to place selected Supertile)"); map_canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        left_frame.grid_rowconfigure(0, weight=0); left_frame.grid_rowconfigure(1, weight=1); left_frame.grid_columnconfigure(0, weight=1)

        # ... rest of map canvas setup ...
        map_hbar = ttk.Scrollbar(map_canvas_frame, orient=tk.HORIZONTAL); map_vbar = ttk.Scrollbar(map_canvas_frame, orient=tk.VERTICAL)
        # Initial scrollregion will be updated by draw_map_canvas
        self.map_canvas = tk.Canvas(map_canvas_frame, bg="black", xscrollcommand=map_hbar.set, yscrollcommand=map_vbar.set)
        map_hbar.config(command=self.map_canvas.xview); map_vbar.config(command=self.map_canvas.yview)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        map_canvas_frame.grid_rowconfigure(0, weight=1); map_canvas_frame.grid_columnconfigure(0, weight=1); map_canvas_frame.grid_rowconfigure(1, weight=0); map_canvas_frame.grid_columnconfigure(1, weight=0)
        self.map_canvas.bind("<Button-1>", self.handle_map_click); self.map_canvas.bind("<B1-Motion>", self.handle_map_drag)

        # ... rest of right_frame setup ...
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Palette (Click to select for map)"); st_selector_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(0, weight=1); right_frame.grid_columnconfigure(0, weight=1)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1; st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS); st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        map_st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL); map_st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.map_supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=map_st_sel_hbar.set, yscrollcommand=map_st_sel_vbar.set)
        map_st_sel_hbar.config(command=self.map_supertile_selector_canvas.xview); map_st_sel_vbar.config(command=self.map_supertile_selector_canvas.yview); self.map_supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E)); st_selector_frame.grid_rowconfigure(0, weight=1); st_selector_frame.grid_columnconfigure(0, weight=1); st_selector_frame.grid_rowconfigure(1, weight=0); st_selector_frame.grid_columnconfigure(1, weight=0)
        self.map_supertile_selector_canvas.bind("<Button-1>", self.handle_map_supertile_selector_click)
        self.map_supertile_select_label = ttk.Label(right_frame, text=f"Selected Supertile for Painting: {selected_supertile_for_map}"); self.map_supertile_select_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0)); right_frame.grid_rowconfigure(1, weight=0)


    # --- Drawing Functions ---
    def update_all_displays(self, changed_level="all"):
        if changed_level in ["all", "tile"]:
            self.draw_editor_canvas(); self.draw_attribute_editor(); self.draw_palette()
            self.draw_tileset_viewer(self.tileset_canvas, current_tile_index)
            self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
            self.update_tile_info_label()
        if changed_level in ["all", "tile", "supertile"]:
            self.draw_supertile_definition_canvas()
            self.draw_supertile_selector(self.supertile_selector_canvas, current_supertile_index)
            self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
            self.update_supertile_info_labels()
        if changed_level in ["all", "tile", "supertile", "map"]:
             self.draw_map_canvas(); self.update_map_info_labels()
    
    def draw_editor_canvas(self): # Direct drawing
        self.editor_canvas.delete("all") # Clear canvas before drawing
        if not (0 <= current_tile_index < num_tiles_in_set): return # Check index validity

        pattern = tileset_patterns[current_tile_index] # Get pattern data
        colors = tileset_colors[current_tile_index]    # Get color data ((fg, bg) per row)

        # Loop through each row (0 to 7)
        for r in range(TILE_HEIGHT):
            # Get colors for this specific row
            fg_index, bg_index = colors[r]
            fg_color = MSX_COLORS[fg_index]
            bg_color = MSX_COLORS[bg_index]

            # Loop through each column (0 to 7)
            for c in range(TILE_WIDTH):
                # Get the pixel value (0 or 1) for this cell
                pixel_val = pattern[r][c]
                # Determine the actual color string
                color = fg_color if pixel_val == 1 else bg_color

                # Calculate coordinates for the rectangle representing this pixel
                x1 = c * EDITOR_PIXEL_SIZE
                y1 = r * EDITOR_PIXEL_SIZE  # Y depends on the row 'r'
                x2 = x1 + EDITOR_PIXEL_SIZE
                y2 = y1 + EDITOR_PIXEL_SIZE

                # Create the rectangle on the canvas
                self.editor_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color, outline="darkgrey", width=1
                )
    
    def draw_attribute_editor(self):
        if not (0 <= current_tile_index < num_tiles_in_set): return
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT): fg_idx, bg_idx = colors[r]; self.attr_fg_labels[r].config(bg=MSX_COLORS[fg_idx], fg=get_contrast_color(MSX_COLORS[fg_idx])); self.attr_bg_labels[r].config(bg=MSX_COLORS[bg_idx], fg=get_contrast_color(MSX_COLORS[bg_idx]))
    def draw_palette(self):
        self.palette_canvas.itemconfig(tk.ALL, outline="grey", width=1)
        if 0 <= selected_color_index < 16: self.palette_canvas.itemconfig(f"pal_{selected_color_index}", outline="red", width=2)
    def draw_tileset_viewer(self, canvas, highlighted_tile_index):
        canvas.delete("all"); padding = 1; size = VIEWER_TILE_SIZE; max_rows = math.ceil(num_tiles_in_set / NUM_TILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding; canvas_width = NUM_TILES_ACROSS * (size + padding) + padding; str_scroll = f"0 0 {float(canvas_width)} {float(canvas_height)}"
        if canvas.cget("scrollregion") != str_scroll: canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        for i in range(num_tiles_in_set):
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS); base_x = tile_c * (size + padding) + padding; base_y = tile_r * (size + padding) + padding
            img = self.create_tile_image(i, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"tile_img_{i}")
            outline_color = "red" if i == highlighted_tile_index else "grey"; outline_width = 2 if i == highlighted_tile_index else 1
            canvas.create_rectangle(base_x - padding/2, base_y - padding/2, base_x + size + padding/2, base_y + size + padding/2, outline=outline_color, width=outline_width, tags=f"tile_border_{i}")
    def update_tile_info_label(self): self.tile_info_label.config(text=f"Tile: {current_tile_index}/{max(0, num_tiles_in_set-1)}") # Avoid -1 if 0 tiles
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
        if canvas.cget("scrollregion") != str_scroll: canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        for i in range(num_supertiles):
            st_r, st_c = divmod(i, NUM_SUPERTILES_ACROSS); base_x = st_c * (size + padding) + padding; base_y = st_r * (size + padding) + padding
            img = self.create_supertile_image(i, size); canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"st_img_{i}")
            outline_color = "red" if i == highlighted_supertile_index else "grey"; outline_width = 2 if i == highlighted_supertile_index else 1
            canvas.create_rectangle(base_x - padding/2, base_y - padding/2, base_x + size + padding/2, base_y + size + padding/2, outline=outline_color, width=outline_width, tags=f"st_border_{i}")
    def update_supertile_info_labels(self): self.supertile_def_info_label.config(text=f"Editing Supertile: {current_supertile_index}/{max(0, num_supertiles-1)}"); self.supertile_tile_select_label.config(text=f"Selected Tile for Placing: {selected_tile_for_supertile}"); self.supertile_sel_info_label.config(text=f"Supertiles: {num_supertiles}")

    def draw_map_canvas(self):
        """Draws the map using cached supertile PhotoImages at the current zoom."""
        canvas = self.map_canvas
        canvas.delete("all") # Clear everything before redraw

        # --- vvv Use Zoomed Size vvv ---
        zoomed_cell_size = self.get_zoomed_map_cell_size()
        # --- ^^^ Use Zoomed Size ^^^ ---

        # Calculate total canvas dimensions based on zoom
        map_canvas_width = map_width * zoomed_cell_size
        map_canvas_height = map_height * zoomed_cell_size
        str_scroll = f"0 0 {float(map_canvas_width)} {float(map_canvas_height)}"

        # --- vvv Update Scrollregion vvv ---
        # Update scrollregion unconditionally on redraw to reflect zoom changes
        canvas.config(scrollregion=(0, 0, map_canvas_width, map_canvas_height))
        # --- ^^^ Update Scrollregion ^^^ ---

        # Draw visible cells (Tkinter clips automatically, but drawing all is simpler)
        for r in range(map_height):
            for c in range(map_width):
                 supertile_idx = map_data[r][c]
                 base_x = c * zoomed_cell_size # Use zoomed size for position
                 base_y = r * zoomed_cell_size # Use zoomed size for position

                 # Get cached supertile image at the required ZOOMED size
                 img = self.create_supertile_image(supertile_idx, zoomed_cell_size)
                 canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"map_cell_{r}_{c}")

        # Update the zoom display label as part of the redraw
        self.map_zoom_label.config(text=f"{int(self.map_zoom_level * 100)}%")
    
    def update_map_info_labels(self): self.map_size_label.config(text=f"{map_width} x {map_height}"); self.map_supertile_select_label.config(text=f"Selected Supertile for Painting: {selected_supertile_for_map}")

    # --- Event Handlers ---
    def on_tab_change(self, event):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: self.update_all_displays(changed_level="tile")
        elif selected_tab == 1: self.update_all_displays(changed_level="supertile")
        elif selected_tab == 2: self.update_all_displays(changed_level="map")
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
    def handle_palette_click(self, event):
            global selected_color_index
            item = self.palette_canvas.find_closest(event.x, event.y)[0] # Find item clicked
            tags = self.palette_canvas.gettags(item) # Get its tags
            for tag in tags:                         # Loop through tags (usually just one or two)
                if tag.startswith("pal_"):           # Check if it's a palette tag
                    try:                             # Start error handling for tag parsing
                        # --- Code inside the try block ---
                        new_index = int(tag.split("_")[1]) # Extract index after "pal_"
                        if new_index != selected_color_index: # If different from current
                            selected_color_index = new_index  # Update global selection
                            self.draw_palette()               # Redraw palette with new highlight
                        # --- Important: break belongs to the 'for' loop, executed if try succeeds ---
                        break # Exit the 'for tag in tags' loop once we found the right tag
                    except (IndexError, ValueError): # If int() or split() fails
                        # --- Code inside the except block ---
                        pass # Ignore malformed tags, do nothing
                # --- End of if block ---
            # --- End of for loop ---
        # --- End of method ---
    def set_row_color(self, row, fg_or_bg):
        global tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if not (0 <= selected_color_index < 16): return
        if 0 <= row < TILE_HEIGHT:
            current_fg, current_bg = tileset_colors[current_tile_index][row]; changed = False
            if fg_or_bg == 'fg' and current_fg != selected_color_index: tileset_colors[current_tile_index][row] = (selected_color_index, current_bg); changed = True
            elif fg_or_bg == 'bg' and current_bg != selected_color_index: tileset_colors[current_tile_index][row] = (current_fg, selected_color_index); changed = True
            if changed: self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
    def handle_tileset_click(self, event): # Click in main tileset viewer
        global current_tile_index
        canvas = self.tileset_canvas; padding = 1; size = VIEWER_TILE_SIZE; col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and current_tile_index != clicked_index: current_tile_index = clicked_index; self.update_all_displays(changed_level="tile")
    def handle_st_tileset_click(self, event): # Click in Supertile tab's tileset viewer
        global selected_tile_for_supertile
        canvas = self.st_tileset_canvas; padding = 1; size = VIEWER_TILE_SIZE; col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding)); clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and selected_tile_for_supertile != clicked_index: selected_tile_for_supertile = clicked_index; self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile); self.update_supertile_info_labels()
    def handle_supertile_def_click(self, event): # Click on the 4x4 definition grid
        global current_supertile_index, supertiles_data
        if not (0 <= current_supertile_index < num_supertiles): return
        if not (0 <= selected_tile_for_supertile < num_tiles_in_set): return
        canvas = self.supertile_def_canvas; size = SUPERTILE_DEF_TILE_SIZE; col = event.x // size; row = event.y // size
        if 0 <= row < SUPERTILE_GRID_DIM and 0 <= col < SUPERTILE_GRID_DIM:
            if supertiles_data[current_supertile_index][row][col] != selected_tile_for_supertile:
                supertiles_data[current_supertile_index][row][col] = selected_tile_for_supertile
                self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")
    def handle_supertile_selector_click(self, event): # Click in ST tab's selector
        global current_supertile_index
        canvas = self.supertile_selector_canvas; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and current_supertile_index != clicked_index: current_supertile_index = clicked_index; self.update_all_displays(changed_level="supertile")
    def handle_map_supertile_selector_click(self, event): # Click in Map tab's selector
        global selected_supertile_for_map
        canvas = self.map_supertile_selector_canvas; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE; col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding)); clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and selected_supertile_for_map != clicked_index: selected_supertile_for_map = clicked_index; self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map); self.update_map_info_labels()

    def _paint_map_cell(self, event_x, event_y):
        global map_data, last_painted_map_cell
        canvas = self.map_canvas

        # --- vvv Use Zoomed Size vvv ---
        zoomed_cell_size = self.get_zoomed_map_cell_size()
        if zoomed_cell_size <= 0: return # Prevent division by zero if zoom is bad
        # --- ^^^ Use Zoomed Size ^^^ ---

        # Convert scrolled canvas coords to map cell coords, accounting for zoom
        c = int(canvas.canvasx(event_x) // zoomed_cell_size)
        r = int(canvas.canvasy(event_y) // zoomed_cell_size)

        if 0 <= r < map_height and 0 <= c < map_width:
            if (r, c) != last_painted_map_cell:
                 if map_data[r][c] != selected_supertile_for_map:
                    map_data[r][c] = selected_supertile_for_map
                    # Redraw the specific cell using zoomed size
                    base_x = c * zoomed_cell_size # Use zoomed size for position
                    base_y = r * zoomed_cell_size # Use zoomed size for position
                    # Get image at zoomed size
                    img = self.create_supertile_image(selected_supertile_for_map, zoomed_cell_size)
                    canvas.delete(f"map_cell_{r}_{c}")
                    canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"map_cell_{r}_{c}")
                 last_painted_map_cell = (r,c)

    def handle_map_click(self, event): global last_painted_map_cell; last_painted_map_cell = None; self._paint_map_cell(event.x, event.y)

    def handle_map_drag(self, event): self._paint_map_cell(event.x, event.y)


    # --- File Menu Commands ---
    def new_project(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, supertiles_data, current_supertile_index, num_supertiles, selected_tile_for_supertile, map_data, map_width, map_height, selected_supertile_for_map, last_painted_map_cell
        if messagebox.askokcancel("New Project", "Discard all current data (Tiles, Supertiles, Map) and start new?"):
            tileset_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; current_tile_index = 0; num_tiles_in_set = 1
            supertiles_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]; current_supertile_index = 0; num_supertiles = 1; selected_tile_for_supertile = 0
            map_width = DEFAULT_MAP_WIDTH; map_height = DEFAULT_MAP_HEIGHT; map_data = [[0]*map_width for _ in range(map_height)]; selected_supertile_for_map = 0; last_painted_map_cell = None
            self.root.title("MSX SCREEN 4 Tile/Map Editor - Untitled"); self.clear_all_caches(); self.update_all_displays(changed_level="all")
    def save_tileset(self):
        global num_tiles_in_set
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Tiles", filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Save Tileset As...")
        if not filepath: return
        try:
             with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_tiles_in_set))
                for i in range(num_tiles_in_set):
                    for r in range(TILE_HEIGHT): f.write(struct.pack('B', sum(1 << (7 - c) for c in range(TILE_WIDTH) if tileset_patterns[i][r][c] == 1)))
                    for r in range(TILE_HEIGHT): fg, bg = tileset_colors[i][r]; f.write(struct.pack('B', ((fg & 0x0F) << 4) | (bg & 0x0F)))
             messagebox.showinfo("Save Successful", f"Tileset saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save tileset:\n{e}")
    def open_tileset(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, selected_tile_for_supertile
        filepath = filedialog.askopenfilename( filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Open Tileset")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 loaded_num_tiles = struct.unpack('B', f.read(1))[0]
                 if not (1 <= loaded_num_tiles <= MAX_TILES): raise ValueError("Invalid tile count")
                 new_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]; new_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 for i in range(loaded_num_tiles):
                     for r in range(TILE_HEIGHT): byte_val = struct.unpack('B', f.read(1))[0]; [ new_patterns[i][r].__setitem__(c, (byte_val >> (7 - c)) & 1) for c in range(TILE_WIDTH) ]
                     for r in range(TILE_HEIGHT): byte_val = struct.unpack('B', f.read(1))[0]; new_colors[i][r] = ((byte_val >> 4) & 0x0F, byte_val & 0x0F)
            tileset_patterns = new_patterns; tileset_colors = new_colors; num_tiles_in_set = loaded_num_tiles; current_tile_index = 0; selected_tile_for_supertile = 0
            self.clear_all_caches(); self.update_all_displays(changed_level="all"); messagebox.showinfo("Open Successful", f"Loaded {num_tiles_in_set} tiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse tileset:\n{e}")
    def save_supertiles(self):
        global num_supertiles, supertiles_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Super", filetypes=[("MSX Supertiles", "*.SC4Super")], title="Save Supertiles As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_supertiles))
                [ f.write(struct.pack('B', supertiles_data[i][r][c])) for i in range(num_supertiles) for r in range(SUPERTILE_GRID_DIM) for c in range(SUPERTILE_GRID_DIM) ]
            messagebox.showinfo("Save Successful", f"Supertiles saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save supertiles:\n{e}")
    def open_supertiles(self):
        global supertiles_data, num_supertiles, current_supertile_index, selected_supertile_for_map
        filepath = filedialog.askopenfilename( filetypes=[("MSX Supertiles", "*.SC4Super")], title="Open Supertiles")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 loaded_num_st = struct.unpack('B', f.read(1))[0]
                 if not (1 <= loaded_num_st <= MAX_SUPERTILES): raise ValueError("Invalid supertile count")
                 new_st_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
                 for i in range(loaded_num_st): [ new_st_data[i][r].__setitem__(c, struct.unpack('B', f.read(1))[0]) for r in range(SUPERTILE_GRID_DIM) for c in range(SUPERTILE_GRID_DIM) ]
            supertiles_data = new_st_data; num_supertiles = loaded_num_st; current_supertile_index = 0; selected_supertile_for_map = 0
            self.supertile_image_cache.clear(); self.update_all_displays(changed_level="supertile"); messagebox.showinfo("Open Successful", f"Loaded {num_supertiles} supertiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse supertiles:\n{e}")
    def save_map(self):
        global map_width, map_height, map_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Map", filetypes=[("MSX Map", "*.SC4Map")], title="Save Map As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f: f.write(struct.pack('>HH', map_width, map_height)); [ f.write(struct.pack('B', map_data[r][c])) for r in range(map_height) for c in range(map_width) ]
            messagebox.showinfo("Save Successful", f"Map saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save map:\n{e}")
    def open_map(self):
        # Declare globals needed
        global map_data, map_width, map_height

        # Ask for filepath
        filepath = filedialog.askopenfilename(
            filetypes=[("MSX Map", "*.SC4Map"), ("All Files", "*.*")],
            title="Open Map"
        )
        # Exit if no file selected
        if not filepath:
            return

        # --- Start of outer try block for all operations ---
        try:
            # Open file in binary read mode
            with open(filepath, 'rb') as f:
                # --- Code inside 'with open' block ---

                # Read dimensions (4 bytes)
                dim_bytes = f.read(4)
                # Check if enough bytes were read for dimensions
                if len(dim_bytes) < 4:
                    # Raise specific error if header is too short
                    raise ValueError("Invalid map file header (too short)")

                # Unpack width and height (Big-endian unsigned short)
                loaded_w, loaded_h = struct.unpack('>HH', dim_bytes)

                # Validate dimensions (adjust limits if needed)
                if not (1 <= loaded_w <= 1024 and 1 <= loaded_h <= 1024):
                    raise ValueError(f"Invalid map dimensions in header: {loaded_w}x{loaded_h}")

                # Prepare the new map data structure (initialized to 0)
                new_map_data = [[0 for _ in range(loaded_w)] for _ in range(loaded_h)]

                # Read the map data bytes one by one
                for r in range(loaded_h):         # Loop through rows
                    for c in range(loaded_w):     # Loop through columns
                        # Read one byte for the supertile index
                        st_idx_byte = f.read(1)
                        # Check if a byte was actually read (handles truncated files)
                        if not st_idx_byte:
                            raise EOFError(f"Unexpected end of file reading map data at row {r}, col {c}. Expected {loaded_w*loaded_h} data bytes.")
                        # Unpack the byte and store it
                        new_map_data[r][c] = struct.unpack('B', st_idx_byte)[0]
                # --- End of loops for reading data ---

            # --- Code after 'with open' block but still inside 'try' ---
            # Commit changes only AFTER successfully reading everything
            map_width = loaded_w
            map_height = loaded_h
            map_data = new_map_data

            # Update display (no specific cache clear needed, map uses supertile cache)
            self.update_all_displays(changed_level="map")
            messagebox.showinfo("Open Successful", f"Loaded {map_width}x{map_height} map from {filepath}")

        # --- End of outer try block ---

        # --- Exception handling blocks (aligned with 'try') ---
        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except EOFError as e:
             messagebox.showerror("Open Error", f"File is incomplete or corrupt:\n{e}")
        except struct.error as e:
             # This can happen if dim_bytes is not 4 bytes, or st_idx_byte is empty
             messagebox.showerror("Open Error", f"Error unpacking data (incorrect format?):\n{e}")
        except ValueError as e:
            # Catches the explicit ValueErrors raised above
            messagebox.showerror("Open Error", f"Invalid data in file:\n{e}")
        except Exception as e:
             # Catch any other unexpected errors during file processing
             messagebox.showerror("Open Error", f"Failed to open or parse map:\n{e}")
        # --- End of exception handling ---
    # --- End of method ---


    # --- Edit Menu Commands ---
    def set_tileset_size(self):
        # Declare globals needed
        global num_tiles_in_set, current_tile_index, selected_tile_for_supertile

        # Ask user for the new size
        new_size_str = simpledialog.askstring(
            "Set Tileset Size",
            f"Enter number of tiles (1-{MAX_TILES}):",
            initialvalue=str(num_tiles_in_set)
        )

        # Proceed only if the user entered something (didn't cancel)
        if new_size_str:
            # --- Start of outer try block for input validation ---
            try:
                # Convert input string to an integer
                new_size = int(new_size_str)

                # Validate the integer is within the allowed range
                if 1 <= new_size <= MAX_TILES:
                    # --- Code inside the valid range check ---

                    # Check if the size is being reduced
                    reduced = new_size < num_tiles_in_set

                    # If reducing, ask for confirmation
                    # The 'not reduced or messagebox...' handles both cases:
                    # - If not reduced, the first part is False, short-circuit evaluation skips messagebox.
                    # - If reduced, the first part is True, so the messagebox result matters.
                    if not reduced or messagebox.askokcancel("Reduce Size", f"Reducing size to {new_size} will discard tiles {new_size} to {num_tiles_in_set-1}. Proceed?"):
                        # --- Code inside the confirmation block (or if not reducing) ---

                        # If size was reduced, invalidate caches for discarded tiles
                        if reduced:
                            # Loop through indices being removed
                            for i in range(new_size, num_tiles_in_set):
                                # Invalidate cache (handles dependent supertiles too)
                                self.invalidate_tile_cache(i)

                        # Update the global tile count
                        num_tiles_in_set = new_size

                        # Adjust selected indices if they are now out of bounds
                        # Ensure current_tile_index stays within [0, num_tiles_in_set - 1]
                        current_tile_index = max(0, min(current_tile_index, num_tiles_in_set - 1))
                        # Ensure selected_tile_for_supertile is valid or reset to 0
                        # (Use max(0,...) in case num_tiles_in_set becomes 0, though our range check prevents that)
                        selected_tile_for_supertile = max(0, min(selected_tile_for_supertile, num_tiles_in_set - 1)) if num_tiles_in_set > 0 else 0

                        # Trigger a full UI update as tile counts affect everything
                        self.update_all_displays(changed_level="all")
                    # --- End of confirmation block ---
                    # else: # Implicit else from askokcancel == False -> do nothing

                # If input integer was outside the allowed range
                else:
                    messagebox.showerror("Invalid Size", f"Size must be between 1 and {MAX_TILES}.")
                # --- End of valid range check ---

            # --- End of outer try block ---

            # --- Exception handling block (aligned with 'try') ---
            except ValueError:
                # Handle case where int(new_size_str) fails
                messagebox.showerror("Invalid Input", "Please enter a valid whole number.")
            # --- End of exception handling ---
        # --- End of 'if new_size_str:' block ---
        # else: # Implicit else from simpledialog returning None (Cancel pressed) -> do nothing
    # --- End of method ---
    
    def set_supertile_count(self):
        # Declare globals needed
        global num_supertiles, current_supertile_index, selected_supertile_for_map

        # Ask user for the new count
        new_count_str = simpledialog.askstring(
            "Set Supertile Count",
            f"Enter number of supertiles (1-{MAX_SUPERTILES}):",
            initialvalue=str(num_supertiles)
        )

        # Proceed only if the user entered something (didn't cancel)
        if new_count_str:
            # --- Start of outer try block for input validation ---
            try:
                # Convert input string to an integer
                new_count = int(new_count_str)

                # Validate the integer is within the allowed range
                if 1 <= new_count <= MAX_SUPERTILES:
                    # --- Code inside the valid range check ---

                    # Check if the count is being reduced
                    reduced = new_count < num_supertiles

                    # If reducing, ask for confirmation
                    # (Short-circuit evaluation handles non-reducing case)
                    if not reduced or messagebox.askokcancel("Reduce Count", f"Reducing count to {new_count} will discard supertiles {new_count} to {num_supertiles-1}. Proceed?"):
                        # --- Code inside the confirmation block (or if not reducing) ---

                        # If count was reduced, invalidate caches for discarded supertiles
                        if reduced:
                            # Loop through indices being removed
                            for i in range(new_count, num_supertiles):
                                # Invalidate cache for the specific supertile
                                self.invalidate_supertile_cache(i)

                        # Update the global supertile count
                        num_supertiles = new_count

                        # Adjust selected indices if they are now out of bounds
                        # Ensure current_supertile_index stays within [0, num_supertiles - 1]
                        current_supertile_index = max(0, min(current_supertile_index, num_supertiles - 1))
                        # Ensure selected_supertile_for_map is valid or reset to 0
                        selected_supertile_for_map = max(0, min(selected_supertile_for_map, num_supertiles - 1)) if num_supertiles > 0 else 0

                        # Trigger UI update for supertile-related components
                        # (This will redraw selectors and potentially the map if visible)
                        self.update_all_displays(changed_level="supertile")
                    # --- End of confirmation block ---
                    # else: # Implicit else from askokcancel == False -> do nothing

                # If input integer was outside the allowed range
                else:
                    messagebox.showerror("Invalid Count", f"Count must be between 1 and {MAX_SUPERTILES}.")
                # --- End of valid range check ---

            # --- End of outer try block ---

            # --- Exception handling block (aligned with 'try') ---
            except ValueError:
                # Handle case where int(new_count_str) fails
                messagebox.showerror("Invalid Input", "Please enter a valid whole number.")
            # --- End of exception handling ---
        # --- End of 'if new_count_str:' block ---
        # else: # Implicit else from simpledialog returning None (Cancel pressed) -> do nothing
    # --- End of method ---

    def set_map_dimensions(self):
        global map_width, map_height, map_data

        dims = simpledialog.askstring(
            "Set Map Dimensions",
            "Enter new dimensions (Width x Height):",
            initialvalue=f"{map_width}x{map_height}"
        )

        if dims:
            try:
                parts = dims.lower().split('x')
                if len(parts) != 2:
                    raise ValueError("Format must be WidthxHeight")

                new_w = int(parts[0].strip())
                new_h = int(parts[1].strip())

                # Define reasonable limits (adjust if needed)
                min_dim, max_dim = 1, 1024
                if not (min_dim <= new_w <= max_dim and min_dim <= new_h <= max_dim):
                    raise ValueError(f"Dimensions must be between {min_dim} and {max_dim}")

                # Skip if dimensions haven't changed
                if new_w == map_width and new_h == map_height:
                    return

                # Confirm if reducing size
                if (new_w < map_width or new_h < map_height):
                    if not messagebox.askokcancel("Resize Map", "Reducing map size will discard data outside the new boundaries. Proceed?"):
                        return # User cancelled reduction

                # Create new map data structure, preserving old data
                new_map_data = [[0 for _ in range(new_w)] for _ in range(new_h)]

                # Copy existing data within the bounds of both old and new maps
                rows_to_copy = min(map_height, new_h)
                cols_to_copy = min(map_width, new_w)
                for r in range(rows_to_copy):
                    for c in range(cols_to_copy):
                        new_map_data[r][c] = map_data[r][c]

                # Commit changes to global variables
                map_width = new_w
                map_height = new_h
                map_data = new_map_data

                # Update map display (no cache invalidation needed here)
                self.update_all_displays(changed_level="map")

            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Error parsing dimensions: {e}")
            except Exception as e:
                # Catch potential unexpected errors during resize
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def clear_current_tile(self):
        global tileset_patterns, tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if messagebox.askokcancel("Clear Tile", f"Clear pattern and reset colors for tile {current_tile_index}?"): tileset_patterns[current_tile_index] = [[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)]; tileset_colors[current_tile_index] = [(15, 1) for _ in range(TILE_HEIGHT)]; self.invalidate_tile_cache(current_tile_index); self.update_all_displays(changed_level="tile")
    def clear_current_supertile(self):
        global supertiles_data, current_supertile_index
        if not (0 <= current_supertile_index < num_supertiles): return
        if messagebox.askokcancel("Clear Supertile", f"Clear definition (set all to tile 0) for supertile {current_supertile_index}?"): supertiles_data[current_supertile_index] = [[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)]; self.invalidate_supertile_cache(current_supertile_index); self.update_all_displays(changed_level="supertile")
    def clear_map(self):
        global map_data, map_width, map_height
        if messagebox.askokcancel("Clear Map", "Clear entire map (set all to supertile 0)?"): map_data = [[0]*map_width for _ in range(map_height)]; self.update_all_displays(changed_level="map")


    # --- Add New Tile/Supertile Methods ---
    def add_new_tile(self):
        global num_tiles_in_set, current_tile_index
        if num_tiles_in_set >= MAX_TILES: messagebox.showwarning("Maximum Tiles", f"Cannot add more tiles. The maximum is {MAX_TILES}."); return
        num_tiles_in_set += 1; new_tile_idx = num_tiles_in_set - 1
        tileset_patterns[new_tile_idx] = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
        tileset_colors[new_tile_idx] = [(15, 1) for _ in range(TILE_HEIGHT)]
        current_tile_index = new_tile_idx; self.update_all_displays(changed_level="tile"); self.scroll_viewers_to_tile(current_tile_index)

    def add_new_supertile(self):
        global num_supertiles, current_supertile_index
        if num_supertiles >= MAX_SUPERTILES: messagebox.showwarning("Maximum Supertiles", f"Cannot add more supertiles. The maximum is {MAX_SUPERTILES}."); return
        num_supertiles += 1; new_st_idx = num_supertiles - 1
        supertiles_data[new_st_idx] = [[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)]
        current_supertile_index = new_st_idx; self.update_all_displays(changed_level="supertile"); self.scroll_selectors_to_supertile(current_supertile_index)

    def scroll_viewers_to_tile(self, tile_index):
        if tile_index < 0: return; padding = 1; tile_size = VIEWER_TILE_SIZE; items_per_row = NUM_TILES_ACROSS; row, _ = divmod(tile_index, items_per_row); target_y = row * (tile_size + padding)
        try:
            scroll_info = self.tileset_canvas.cget("scrollregion").split();
            total_height = float(scroll_info[3]);
            if total_height > 0:
                self.tileset_canvas.yview_moveto(min(1.0, target_y / total_height))
        except Exception as e: print(f"Error scrolling main tileset viewer: {e}")
        try: 
            scroll_info_st = self.st_tileset_canvas.cget("scrollregion").split();
            total_height_st = float(scroll_info_st[3]);
            if total_height_st > 0:
                self.st_tileset_canvas.yview_moveto(min(1.0, target_y / total_height_st))
        except Exception as e: print(f"Error scrolling ST tileset viewer: {e}")

    def scroll_selectors_to_supertile(self, supertile_index):
        """Scrolls the supertile selectors to make the specified index visible."""
        # Basic validation
        if supertile_index < 0:
            return

        # Define layout parameters
        padding = 1
        item_size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        items_per_row = NUM_SUPERTILES_ACROSS

        # Calculate target row and the y-coordinate of its top edge
        row, _ = divmod(supertile_index, items_per_row)
        target_y = row * (item_size + padding)

        # --- Scroll Supertile Editor's Selector ---
        canvas_st = self.supertile_selector_canvas
        try:
            # Get scroll region "0 0 width height"
            scroll_info_st = canvas_st.cget("scrollregion").split()
            # Ensure format is correct before attempting float conversion
            if len(scroll_info_st) == 4:
                total_height_st = float(scroll_info_st[3])
                # Avoid division by zero and calculate fraction
                if total_height_st > 0:
                    fraction_st = min(1.0, max(0.0, target_y / total_height_st))
                    canvas_st.yview_moveto(fraction_st)
            else:
                 print(f"Warning: Invalid scrollregion format for ST selector: {scroll_info_st}")
        except tk.TclError as e:
             # Catch errors related to canvas operations (e.g., invalid state)
            print(f"TclError scrolling ST selector: {e}")
        except (ValueError, IndexError) as e:
            # Catch errors from split() or float() if scrollregion is bad
            print(f"Error parsing scrollregion for ST selector: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            print(f"Unexpected error scrolling ST selector: {e}")

        # --- Scroll Map Editor's Selector ---
        canvas_map = self.map_supertile_selector_canvas
        try:
            scroll_info_map = canvas_map.cget("scrollregion").split()
            if len(scroll_info_map) == 4:
                total_height_map = float(scroll_info_map[3])
                if total_height_map > 0:
                    fraction_map = min(1.0, max(0.0, target_y / total_height_map))
                    canvas_map.yview_moveto(fraction_map)
            else:
                 print(f"Warning: Invalid scrollregion format for Map selector: {scroll_info_map}")
        except tk.TclError as e:
             print(f"TclError scrolling Map selector: {e}")
        except (ValueError, IndexError) as e:
             print(f"Error parsing scrollregion for Map selector: {e}")
        except Exception as e:
            print(f"Unexpected error scrolling Map selector: {e}")

    def change_map_zoom(self, delta):
        """Increases or decreases the map zoom level."""
        new_zoom = self.map_zoom_level + delta
        # Define zoom limits (e.g., 25% to 400%)
        min_zoom = 0.25
        max_zoom = 4.0
        self.set_map_zoom(max(min_zoom, min(max_zoom, new_zoom)))

    def set_map_zoom(self, new_zoom_level):
        """Sets the map zoom to a specific level and updates the display."""
        new_zoom_level = float(new_zoom_level)
        if new_zoom_level <= 0: # Prevent zero or negative zoom
             return
        if self.map_zoom_level != new_zoom_level:
            self.map_zoom_level = new_zoom_level
            # Update the zoom percentage label
            self.map_zoom_label.config(text=f"{int(self.map_zoom_level * 100)}%")
            # Trigger a redraw of the map with the new zoom
            # We only need to redraw the map part
            self.draw_map_canvas()
            # Update map info labels (optional, but keeps things consistent)
            # self.update_map_info_labels() # Already called by draw_map_canvas via update_all_displays if needed

    def get_zoomed_map_cell_size(self):
        """Calculates the current cell size based on base size and zoom."""
        # Ensure minimum size of 1 pixel even at very low zoom
        return max(1, int(MAP_CELL_PREVIEW_SIZE * self.map_zoom_level))

    # --- Copy/Paste Methods ---

    def copy_current_tile(self):
        """Copies the current tile's pattern and color data to the tile clipboard."""
        global tile_clipboard_pattern, tile_clipboard_colors
        global current_tile_index, num_tiles_in_set
        global tileset_patterns, tileset_colors

        if not (0 <= current_tile_index < num_tiles_in_set):
            messagebox.showwarning("Copy Tile", "No valid tile selected to copy.")
            return

        # Get data from the current tile
        pattern_to_copy = tileset_patterns[current_tile_index]
        colors_to_copy = tileset_colors[current_tile_index]

        # Make deep copies for the clipboard
        tile_clipboard_pattern = copy.deepcopy(pattern_to_copy)
        tile_clipboard_colors = copy.deepcopy(colors_to_copy)

        print(f"Tile {current_tile_index} copied to clipboard.") # User feedback

    def paste_tile(self):
        """Pastes the tile data from the clipboard onto the current tile."""
        global tile_clipboard_pattern, tile_clipboard_colors
        global current_tile_index, num_tiles_in_set
        global tileset_patterns, tileset_colors

        if tile_clipboard_pattern is None or tile_clipboard_colors is None:
            messagebox.showinfo("Paste Tile", "Tile clipboard is empty. Copy a tile first.")
            return

        if not (0 <= current_tile_index < num_tiles_in_set):
            messagebox.showwarning("Paste Tile", "No valid tile selected to paste onto.")
            return

        # Confirmation dialog
        confirm = messagebox.askokcancel(
            "Paste Tile",
            f"Overwrite Tile {current_tile_index} with clipboard data?"
        )

        if confirm:
            # Make deep copies *from* the clipboard *to* the target
            tileset_patterns[current_tile_index] = copy.deepcopy(tile_clipboard_pattern)
            tileset_colors[current_tile_index] = copy.deepcopy(tile_clipboard_colors)

            # Invalidate cache for the modified tile
            self.invalidate_tile_cache(current_tile_index)
            # Update display
            self.update_all_displays(changed_level="tile")
            print(f"Pasted tile data onto Tile {current_tile_index}.") # User feedback

    def copy_current_supertile(self):
        """Copies the current supertile's definition to the supertile clipboard."""
        global supertile_clipboard_data
        global current_supertile_index, num_supertiles
        global supertiles_data

        if not (0 <= current_supertile_index < num_supertiles):
            messagebox.showwarning("Copy Supertile", "No valid supertile selected to copy.")
            return

        # Get data from the current supertile
        data_to_copy = supertiles_data[current_supertile_index]

        # Make a deep copy for the clipboard
        supertile_clipboard_data = copy.deepcopy(data_to_copy)

        print(f"Supertile {current_supertile_index} copied to clipboard.") # User feedback

    def paste_supertile(self):
        """Pastes the supertile definition from the clipboard onto the current supertile."""
        global supertile_clipboard_data
        global current_supertile_index, num_supertiles
        global supertiles_data

        if supertile_clipboard_data is None:
            messagebox.showinfo("Paste Supertile", "Supertile clipboard is empty. Copy a supertile first.")
            return

        if not (0 <= current_supertile_index < num_supertiles):
            messagebox.showwarning("Paste Supertile", "No valid supertile selected to paste onto.")
            return

        # Confirmation dialog
        confirm = messagebox.askokcancel(
            "Paste Supertile",
            f"Overwrite Supertile {current_supertile_index} with clipboard data?"
        )

        if confirm:
            # Make a deep copy *from* the clipboard *to* the target
            supertiles_data[current_supertile_index] = copy.deepcopy(supertile_clipboard_data)

            # Invalidate cache for the modified supertile
            self.invalidate_supertile_cache(current_supertile_index)
            # Update display
            self.update_all_displays(changed_level="supertile")
            print(f"Pasted supertile data onto Supertile {current_supertile_index}.") # User feedback

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TileEditorApp(root)
    root.mainloop()