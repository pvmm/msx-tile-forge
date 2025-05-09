import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
import struct
import os
import math

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
        """Removes a specific tile from the cache and all dependent supertiles."""
        # Remove specific tile images of all sizes
        keys_to_remove = [k for k in self.tile_image_cache if k[0] == tile_index]
        for key in keys_to_remove:
            del self.tile_image_cache[key]

        # Invalidate supertiles that use this tile
        for st_index in range(num_supertiles):
            definition = supertiles_data[st_index]
            used = any(definition[r][c] == tile_index
                       for r in range(SUPERTILE_GRID_DIM)
                       for c in range(SUPERTILE_GRID_DIM))
            if used:
                self.invalidate_supertile_cache(st_index) # Recursive invalidation not needed here

    def invalidate_supertile_cache(self, supertile_index):
        """Removes a specific supertile from the cache."""
        keys_to_remove = [k for k in self.supertile_image_cache if k[0] == supertile_index]
        for key in keys_to_remove:
            del self.supertile_image_cache[key]

    def clear_all_caches(self):
        self.tile_image_cache.clear()
        self.supertile_image_cache.clear()


    # --- Image Generation ---

    def create_tile_image(self, tile_index, size):
        """Creates or retrieves a PhotoImage for a tile at a specific size."""
        cache_key = (tile_index, size)
        if cache_key in self.tile_image_cache:
            return self.tile_image_cache[cache_key]

        # Ensure size is at least 1x1
        size = max(1, int(size))
        img = tk.PhotoImage(width=size, height=size)

        if not (0 <= tile_index < num_tiles_in_set):
            # Draw placeholder for invalid tile index
            img.put(INVALID_TILE_COLOR, to=(0, 0, size, size)) # Fill with placeholder color
            self.tile_image_cache[cache_key] = img # Cache the placeholder too
            return img

        pattern = tileset_patterns[tile_index]
        colors = tileset_colors[tile_index]
        pixel_w_ratio = TILE_WIDTH / size
        pixel_h_ratio = TILE_HEIGHT / size

        # Build pixel data row by row
        for y in range(size):
            tile_r = min(TILE_HEIGHT - 1, int(y * pixel_h_ratio)) # Corresponding row in 8x8 tile data
            fg_idx, bg_idx = colors[tile_r]
            bg_color = MSX_COLORS[bg_idx]
            fg_color = MSX_COLORS[fg_idx]
            row_colors = []
            for x in range(size):
                tile_c = min(TILE_WIDTH - 1, int(x * pixel_w_ratio)) # Corresponding col in 8x8 tile data
                pixel_val = pattern[tile_r][tile_c]
                color = fg_color if pixel_val == 1 else bg_color
                row_colors.append(color)
            try:
                img.put("{" + " ".join(row_colors) + "}", to=(0, y)) # Put the whole row
            except tk.TclError as e:
                print(f"Warning: TclError putting row {y} for tile {tile_index} size {size}: {e}")
                # Fallback: Put single color if row fails (e.g., size 1 issue)
                if row_colors: img.put(row_colors[0], to=(0, y, size, y+1))


        self.tile_image_cache[cache_key] = img
        return img

    def create_supertile_image(self, supertile_index, total_size):
        """Creates or retrieves a PhotoImage for a supertile at a specific size."""
        cache_key = (supertile_index, total_size)
        if cache_key in self.supertile_image_cache:
            return self.supertile_image_cache[cache_key]

        total_size = max(1, int(total_size))
        img = tk.PhotoImage(width=total_size, height=total_size)

        if not (0 <= supertile_index < num_supertiles):
            img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, total_size, total_size))
            self.supertile_image_cache[cache_key] = img # Cache placeholder
            return img

        definition = supertiles_data[supertile_index]
        mini_tile_size = total_size / SUPERTILE_GRID_DIM

        # Check if mini_tile_size is valid
        if mini_tile_size < 1:
             # Fallback: Draw placeholder if resulting tiles are too small
            print(f"Warning: Supertile {supertile_index} size {total_size} results in too small mini-tiles.")
            img.put(INVALID_SUPERTILE_COLOR, to=(0, 0, total_size, total_size))
            self.supertile_image_cache[cache_key] = img
            return img


        # --- More efficient method: Build pixel data directly ---
        mini_tile_pixel_h = TILE_HEIGHT / mini_tile_size # Ratio for source pixels
        mini_tile_pixel_w = TILE_WIDTH / mini_tile_size  # Ratio for source pixels

        for y in range(total_size):
            # Figure out which row of mini-tiles we are in
            mini_tile_r = min(SUPERTILE_GRID_DIM - 1, int(y / mini_tile_size))
            # Y position within that mini-tile row
            y_in_mini = y % mini_tile_size

            row_colors = [] # Colors for this row of the final supertile image

            for x in range(total_size):
                # Figure out which column of mini-tiles we are in
                mini_tile_c = min(SUPERTILE_GRID_DIM - 1, int(x / mini_tile_size))
                # X position within that mini-tile column
                x_in_mini = x % mini_tile_size

                # Get the tile index for this mini-tile position
                tile_idx = definition[mini_tile_r][mini_tile_c]

                # Default to placeholder if tile index is bad
                pixel_color = INVALID_TILE_COLOR

                if 0 <= tile_idx < num_tiles_in_set:
                    # Find the corresponding pixel in the source 8x8 tile
                    tile_r = min(TILE_HEIGHT - 1, int(y_in_mini * mini_tile_pixel_h))
                    tile_c = min(TILE_WIDTH - 1, int(x_in_mini * mini_tile_pixel_w))

                    # Get pattern and color for that source pixel
                    try:
                        pattern = tileset_patterns[tile_idx]
                        colors = tileset_colors[tile_idx]
                        fg_idx, bg_idx = colors[tile_r]
                        bg_color = MSX_COLORS[bg_idx]
                        fg_color = MSX_COLORS[fg_idx]
                        pixel_val = pattern[tile_r][tile_c]
                        pixel_color = fg_color if pixel_val == 1 else bg_color
                    except IndexError:
                         print(f"Warning: IndexError accessing data for tile {tile_idx} at [{tile_r},{tile_c}]")
                         pixel_color = INVALID_TILE_COLOR # Use placeholder on error

                row_colors.append(pixel_color)

            # Put the constructed row onto the image
            try:
                img.put("{" + " ".join(row_colors) + "}", to=(0, y))
            except tk.TclError as e:
                 print(f"Warning: TclError putting row {y} for supertile {supertile_index} size {total_size}: {e}")
                 if row_colors: img.put(row_colors[0], to=(0, y, total_size, y+1)) # Fallback

        self.supertile_image_cache[cache_key] = img
        return img

    # --- Menu Creation --- (Remains the same)
    def create_menu(self):
        menubar = tk.Menu(self.root); self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="File", menu=file_menu)
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
        file_menu.add_separator(); file_menu.add_command(label="Exit", command=self.root.quit)
        edit_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size)
        edit_menu.add_command(label="Set Supertile Count...", command=self.set_supertile_count)
        edit_menu.add_command(label="Set Map Dimensions...", command=self.set_map_dimensions)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile)
        edit_menu.add_command(label="Clear Current Supertile", command=self.clear_current_supertile)
        edit_menu.add_command(label="Clear Map", command=self.clear_map)


    # --- Widget Creation --- (Mostly the same, canvas sizes might need checking)
    def create_tile_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)"); editor_frame.grid(row=0, column=0, pady=(0, 10))
        self.editor_canvas = tk.Canvas( editor_frame, width=TILE_WIDTH * EDITOR_PIXEL_SIZE, height=TILE_HEIGHT * EDITOR_PIXEL_SIZE, bg="grey")
        self.editor_canvas.grid(row=0, column=0); self.editor_canvas.bind("<Button-1>", self.handle_editor_click); self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag); self.editor_canvas.bind("<Button-3>", self.handle_editor_click); self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag)
        attr_frame = ttk.LabelFrame(left_frame, text="Row Colors (Click to set FG/BG)"); attr_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.attr_row_frames = []; self.attr_fg_labels = []; self.attr_bg_labels = []
        for r in range(TILE_HEIGHT):
            row_f = ttk.Frame(attr_frame); row_f.grid(row=r, column=0, sticky=tk.W, pady=1)
            ttk.Label(row_f, text=f"{r}:").grid(row=0, column=0, padx=(0, 5))
            fg_label = tk.Label(row_f, text=" FG ", width=3, relief="raised", borderwidth=2); fg_label.grid(row=0, column=1, padx=(0, 2)); fg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'fg')); self.attr_fg_labels.append(fg_label)
            bg_label = tk.Label(row_f, text=" BG ", width=3, relief="raised", borderwidth=2); bg_label.grid(row=0, column=2); bg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'bg')); self.attr_bg_labels.append(bg_label)
            self.attr_row_frames.append(row_f)
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S)); main_frame.grid_rowconfigure(0, weight=1)
        palette_frame = ttk.LabelFrame(right_frame, text="Color Palette"); palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.N, tk.W, tk.E))
        self.palette_canvas = tk.Canvas(palette_frame, width=4 * (PALETTE_SQUARE_SIZE + 2), height=4 * (PALETTE_SQUARE_SIZE + 2), borderwidth=0, highlightthickness=0)
        self.palette_canvas.grid(row=0, column=0); self.palette_canvas.bind("<Button-1>", self.handle_palette_click); self.palette_labels = []
        for i in range(16):
            row, col = divmod(i, 4); x1, y1 = col * (PALETTE_SQUARE_SIZE + 2) + 1, row * (PALETTE_SQUARE_SIZE + 2) + 1; x2, y2 = x1 + PALETTE_SQUARE_SIZE, y1 + PALETTE_SQUARE_SIZE
            rect = self.palette_canvas.create_rectangle(x1, y1, x2, y2, fill=MSX_COLORS[i], outline="grey", width=1, tags=f"pal_{i}"); self.palette_labels.append(rect)
        viewer_frame = ttk.LabelFrame(right_frame, text="Tileset"); viewer_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(1, weight=1)
        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1; num_rows_in_viewer = math.ceil(MAX_TILES / NUM_TILES_ACROSS); viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1
        viewer_hbar = ttk.Scrollbar(viewer_frame, orient=tk.HORIZONTAL); viewer_vbar = ttk.Scrollbar(viewer_frame, orient=tk.VERTICAL)
        self.tileset_canvas = tk.Canvas( viewer_frame, bg="lightgrey", scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height), xscrollcommand=viewer_hbar.set, yscrollcommand=viewer_vbar.set)
        viewer_hbar.config(command=self.tileset_canvas.xview); viewer_vbar.config(command=self.tileset_canvas.yview)
        self.tileset_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        viewer_frame.grid_rowconfigure(0, weight=1); viewer_frame.grid_columnconfigure(0, weight=1); self.tileset_canvas.bind("<Button-1>", self.handle_tileset_click)
        self.tile_info_label = ttk.Label(right_frame, text="Tile: 0/0"); self.tile_info_label.grid(row=2, column=0, sticky=tk.W, pady=(5,0))

    def create_supertile_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        def_frame = ttk.LabelFrame(left_frame, text="Supertile Definition (Click to place selected tile)"); def_frame.grid(row=0, column=0, pady=(0, 10))
        # Ensure canvas size matches expected definition image size
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
        self.supertile_sel_info_label = ttk.Label(right_frame, text=f"Supertiles: {num_supertiles}"); self.supertile_sel_info_label.grid(row=2, column=0, sticky=tk.W, pady=(5,0))

    def create_map_editor_widgets(self, parent_frame):
        main_frame = ttk.Frame(parent_frame); main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame); left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10)); main_frame.grid_rowconfigure(0, weight=1); main_frame.grid_columnconfigure(0, weight=1)
        map_controls_frame = ttk.Frame(left_frame); map_controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(map_controls_frame, text="Map Size:").grid(row=0, column=0, padx=(0,5)); self.map_size_label = ttk.Label(map_controls_frame, text=f"{map_width} x {map_height}"); self.map_size_label.grid(row=0, column=1)
        map_canvas_frame = ttk.LabelFrame(left_frame, text="Map (Click/Drag to place selected Supertile)"); map_canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); left_frame.grid_rowconfigure(1, weight=1)
        map_hbar = ttk.Scrollbar(map_canvas_frame, orient=tk.HORIZONTAL); map_vbar = ttk.Scrollbar(map_canvas_frame, orient=tk.VERTICAL)
        map_canvas_width = map_width * MAP_CELL_PREVIEW_SIZE; map_canvas_height = map_height * MAP_CELL_PREVIEW_SIZE
        self.map_canvas = tk.Canvas(map_canvas_frame, bg="black", scrollregion=(0,0, map_canvas_width, map_canvas_height), xscrollcommand=map_hbar.set, yscrollcommand=map_vbar.set)
        map_hbar.config(command=self.map_canvas.xview); map_vbar.config(command=self.map_canvas.yview)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        map_canvas_frame.grid_rowconfigure(0, weight=1); map_canvas_frame.grid_columnconfigure(0, weight=1); self.map_canvas.bind("<Button-1>", self.handle_map_click); self.map_canvas.bind("<B1-Motion>", self.handle_map_drag)
        right_frame = ttk.Frame(main_frame); right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Palette (Click to select for map)"); st_selector_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); right_frame.grid_rowconfigure(0, weight=1); right_frame.grid_columnconfigure(0, weight=1)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1; st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS); st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        map_st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL); map_st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.map_supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=map_st_sel_hbar.set, yscrollcommand=map_st_sel_vbar.set)
        map_st_sel_hbar.config(command=self.map_supertile_selector_canvas.xview); map_st_sel_vbar.config(command=self.map_supertile_selector_canvas.yview)
        self.map_supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E)); map_st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S)); map_st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        st_selector_frame.grid_rowconfigure(0, weight=1); st_selector_frame.grid_columnconfigure(0, weight=1); self.map_supertile_selector_canvas.bind("<Button-1>", self.handle_map_supertile_selector_click)
        self.map_supertile_select_label = ttk.Label(right_frame, text=f"Selected Supertile for Painting: {selected_supertile_for_map}"); self.map_supertile_select_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))


    # --- Drawing Functions ---

    def update_all_displays(self, changed_level="all"):
        """Initiates redraws based on change level. Caching handles optimization."""
        # Tile Editor parts
        if changed_level in ["all", "tile"]:
            self.draw_editor_canvas() # Still needs direct drawing
            self.draw_attribute_editor() # Direct update
            self.draw_palette() # Direct update
            self.draw_tileset_viewer(self.tileset_canvas, current_tile_index) # Uses cache
            self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile) # Uses cache
            self.update_tile_info_label()

        # Supertile Editor parts
        if changed_level in ["all", "tile", "supertile"]:
            self.draw_supertile_definition_canvas() # Uses tile cache
            self.draw_supertile_selector(self.supertile_selector_canvas, current_supertile_index) # Uses supertile cache
            self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map) # Uses supertile cache
            self.update_supertile_info_labels()

        # Map Editor parts
        if changed_level in ["all", "tile", "supertile", "map"]:
             self.draw_map_canvas() # Uses supertile cache
             self.update_map_info_labels()

    # --- Tile Drawing ---
    def draw_editor_canvas(self): # Remains direct pixel drawing
        self.editor_canvas.delete("all")
        if not (0 <= current_tile_index < num_tiles_in_set): return
        pattern = tileset_patterns[current_tile_index]
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]; fg_color = MSX_COLORS[fg_index]; bg_color = MSX_COLORS[bg_index]
            for c in range(TILE_WIDTH):
                color = fg_color if pattern[r][c] == 1 else bg_color
                x1,y1 = c * EDITOR_PIXEL_SIZE, r * EDITOR_PIXEL_SIZE; x2,y2 = x1 + EDITOR_PIXEL_SIZE, y1 + EDITOR_PIXEL_SIZE
                self.editor_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="darkgrey", width=1)

    def draw_attribute_editor(self): # Remains direct label update
        if not (0 <= current_tile_index < num_tiles_in_set): return
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]
            self.attr_fg_labels[r].config(bg=MSX_COLORS[fg_index], fg=get_contrast_color(MSX_COLORS[fg_index]))
            self.attr_bg_labels[r].config(bg=MSX_COLORS[bg_index], fg=get_contrast_color(MSX_COLORS[bg_index]))

    def draw_palette(self): # Remains direct item config
        self.palette_canvas.itemconfig(tk.ALL, outline="grey", width=1)
        if 0 <= selected_color_index < 16:
             self.palette_canvas.itemconfig(f"pal_{selected_color_index}", outline="red", width=2)

    def draw_tileset_viewer(self, canvas, highlighted_tile_index):
        """Draws the tileset using cached PhotoImages."""
        canvas.delete("tile_image") # Delete only images, keep borders? No, clear all is easier.
        canvas.delete("all")
        padding = 1
        size = VIEWER_TILE_SIZE
        max_rows = math.ceil(num_tiles_in_set / NUM_TILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding
        canvas_width = NUM_TILES_ACROSS * (size + padding) + padding
        str_scrollregion = f"0 0 {float(canvas_width)} {float(canvas_height)}"
        if canvas.cget("scrollregion") != str_scrollregion:
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        for i in range(num_tiles_in_set):
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS)
            base_x = tile_c * (size + padding) + padding
            base_y = tile_r * (size + padding) + padding

            # Use cached image
            img = self.create_tile_image(i, size)
            canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"tile_img_{i}")

            # Draw border (on top of image)
            outline_color = "red" if i == highlighted_tile_index else "grey"
            outline_width = 2 if i == highlighted_tile_index else 1
            canvas.create_rectangle(
                base_x - padding/2, base_y - padding/2,
                base_x + size + padding/2, base_y + size + padding/2,
                outline=outline_color, width=outline_width, tags=f"tile_border_{i}"
            )

    def update_tile_info_label(self): # Remains direct label update
         self.tile_info_label.config(text=f"Tile: {current_tile_index}/{num_tiles_in_set-1}")

    # --- Supertile Drawing ---

    def draw_supertile_definition_canvas(self):
        """Draws the 4x4 supertile definition using cached tile PhotoImages."""
        canvas = self.supertile_def_canvas
        canvas.delete("all")
        if not (0 <= current_supertile_index < num_supertiles): return

        definition = supertiles_data[current_supertile_index]
        size = SUPERTILE_DEF_TILE_SIZE # Size of each tile shown in the definition grid

        for r in range(SUPERTILE_GRID_DIM):
            for c in range(SUPERTILE_GRID_DIM):
                tile_idx = definition[r][c]
                base_x = c * size
                base_y = r * size

                # Use cached tile image
                img = self.create_tile_image(tile_idx, size)
                canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"def_tile_{r}_{c}")
                # Draw grid cell boundary (optional)
                canvas.create_rectangle(base_x, base_y, base_x + size, base_y + size, outline="grey")

    def draw_supertile_selector(self, canvas, highlighted_supertile_index):
        """Draws the supertile selector using cached supertile PhotoImages."""
        canvas.delete("all")
        padding = 1
        size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        max_rows = math.ceil(num_supertiles / NUM_SUPERTILES_ACROSS)
        canvas_height = max_rows * (size + padding) + padding
        canvas_width = NUM_SUPERTILES_ACROSS * (size + padding) + padding
        str_scrollregion = f"0 0 {float(canvas_width)} {float(canvas_height)}"
        if canvas.cget("scrollregion") != str_scrollregion:
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        for i in range(num_supertiles):
            st_r, st_c = divmod(i, NUM_SUPERTILES_ACROSS)
            base_x = st_c * (size + padding) + padding
            base_y = st_r * (size + padding) + padding

            # Use cached supertile image
            img = self.create_supertile_image(i, size)
            canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"st_img_{i}")

            # Draw border
            outline_color = "red" if i == highlighted_supertile_index else "grey"
            outline_width = 2 if i == highlighted_supertile_index else 1
            canvas.create_rectangle(
                base_x - padding/2, base_y - padding/2,
                base_x + size + padding/2, base_y + size + padding/2,
                outline=outline_color, width=outline_width, tags=f"st_border_{i}"
            )

    def update_supertile_info_labels(self): # Remains direct label update
         self.supertile_def_info_label.config(text=f"Editing Supertile: {current_supertile_index}/{num_supertiles-1}")
         self.supertile_tile_select_label.config(text=f"Selected Tile for Placing: {selected_tile_for_supertile}")
         self.supertile_sel_info_label.config(text=f"Supertiles: {num_supertiles}")

    # --- Map Drawing ---
    def draw_map_canvas(self):
        """Draws the map using cached supertile PhotoImages."""
        canvas = self.map_canvas
        canvas.delete("map_image") # Only delete images for potential speedup? Clear all is safer.
        canvas.delete("all")
        size = MAP_CELL_PREVIEW_SIZE

        map_canvas_width = map_width * size
        map_canvas_height = map_height * size
        str_scrollregion = f"0 0 {float(map_canvas_width)} {float(map_canvas_height)}"
        if canvas.cget("scrollregion") != str_scrollregion:
             canvas.config(scrollregion=(0, 0, map_canvas_width, map_canvas_height))

        for r in range(map_height):
            for c in range(map_width):
                 supertile_idx = map_data[r][c]
                 base_x = c * size
                 base_y = r * size
                 # Use cached supertile image
                 img = self.create_supertile_image(supertile_idx, size)
                 canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"map_cell_{r}_{c}")
                 # Optional grid lines:
                 # canvas.create_rectangle(base_x, base_y, base_x + size, base_y + size, outline="darkgrey", width=1, tags="map_grid")

    def update_map_info_labels(self): # Remains direct label update
         self.map_size_label.config(text=f"{map_width} x {map_height}")
         self.map_supertile_select_label.config(text=f"Selected Supertile for Painting: {selected_supertile_for_map}")

    # --- Event Handlers ---

    def on_tab_change(self, event):
        # Force redraw of relevant sections when changing tabs to ensure view is current
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: self.update_all_displays(changed_level="tile")
        elif selected_tab == 1: self.update_all_displays(changed_level="supertile")
        elif selected_tab == 2: self.update_all_displays(changed_level="map")

    # --- Tile Editor Handlers ---
    def handle_editor_click(self, event):
        global last_drawn_pixel, current_tile_index, tileset_patterns
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE; r = event.y // EDITOR_PIXEL_SIZE
        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            pixel_value = 1 if event.num == 1 else 0
            if tileset_patterns[current_tile_index][r][c] != pixel_value:
                tileset_patterns[current_tile_index][r][c] = pixel_value
                # MODIFIED: Invalidate cache and trigger update
                self.invalidate_tile_cache(current_tile_index)
                self.update_all_displays(changed_level="tile")
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
                    # MODIFIED: Invalidate cache and trigger update
                    self.invalidate_tile_cache(current_tile_index)
                    self.update_all_displays(changed_level="tile")
                last_drawn_pixel = (r, c)

    def handle_palette_click(self, event):
        global selected_color_index
        item = self.palette_canvas.find_closest(event.x, event.y)[0]
        tags = self.palette_canvas.gettags(item)
        for tag in tags:
            if tag.startswith("pal_"):
                try:
                    new_index = int(tag.split("_")[1])
                    if new_index != selected_color_index:
                        selected_color_index = new_index
                        self.draw_palette() # Only redraw palette
                    break
                except (IndexError, ValueError): pass

    def set_row_color(self, row, fg_or_bg):
        global tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if not (0 <= selected_color_index < 16): return
        if 0 <= row < TILE_HEIGHT:
            current_fg, current_bg = tileset_colors[current_tile_index][row]; changed = False
            if fg_or_bg == 'fg' and current_fg != selected_color_index:
                tileset_colors[current_tile_index][row] = (selected_color_index, current_bg); changed = True
            elif fg_or_bg == 'bg' and current_bg != selected_color_index:
                tileset_colors[current_tile_index][row] = (current_fg, selected_color_index); changed = True
            if changed:
                 # MODIFIED: Invalidate cache and trigger update
                self.invalidate_tile_cache(current_tile_index)
                self.update_all_displays(changed_level="tile")

    def handle_tileset_click(self, event): # Click in main tileset viewer
        global current_tile_index
        canvas = self.tileset_canvas; padding = 1; size = VIEWER_TILE_SIZE
        col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding))
        clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and current_tile_index != clicked_index:
            current_tile_index = clicked_index
            # Update affected displays (tile level - redraws editor etc)
            self.update_all_displays(changed_level="tile")

    # --- Supertile Editor Handlers ---
    def handle_st_tileset_click(self, event): # Click in Supertile tab's tileset viewer
        global selected_tile_for_supertile
        canvas = self.st_tileset_canvas; padding = 1; size = VIEWER_TILE_SIZE
        col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding))
        clicked_index = row * NUM_TILES_ACROSS + col
        if 0 <= clicked_index < num_tiles_in_set and selected_tile_for_supertile != clicked_index:
             selected_tile_for_supertile = clicked_index
             # Only redraw the specific viewer highlight and update labels
             self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
             self.update_supertile_info_labels()

    def handle_supertile_def_click(self, event): # Click on the 4x4 definition grid
        global current_supertile_index, supertiles_data
        if not (0 <= current_supertile_index < num_supertiles): return
        if not (0 <= selected_tile_for_supertile < num_tiles_in_set): return
        canvas = self.supertile_def_canvas; size = SUPERTILE_DEF_TILE_SIZE
        col = event.x // size; row = event.y // size
        if 0 <= row < SUPERTILE_GRID_DIM and 0 <= col < SUPERTILE_GRID_DIM:
            if supertiles_data[current_supertile_index][row][col] != selected_tile_for_supertile:
                supertiles_data[current_supertile_index][row][col] = selected_tile_for_supertile
                # MODIFIED: Invalidate cache and trigger update
                self.invalidate_supertile_cache(current_supertile_index)
                self.update_all_displays(changed_level="supertile")

    def handle_supertile_selector_click(self, event): # Click in ST tab's selector
        global current_supertile_index
        canvas = self.supertile_selector_canvas; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding))
        clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and current_supertile_index != clicked_index:
            current_supertile_index = clicked_index
            # Update affected displays (supertile level - redraws definition etc)
            self.update_all_displays(changed_level="supertile")

    # --- Map Editor Handlers ---
    def handle_map_supertile_selector_click(self, event): # Click in Map tab's selector
        global selected_supertile_for_map
        canvas = self.map_supertile_selector_canvas; padding = 1; size = SUPERTILE_SELECTOR_PREVIEW_SIZE
        col = int(canvas.canvasx(event.x) // (size + padding)); row = int(canvas.canvasy(event.y) // (size + padding))
        clicked_index = row * NUM_SUPERTILES_ACROSS + col
        if 0 <= clicked_index < num_supertiles and selected_supertile_for_map != clicked_index:
             selected_supertile_for_map = clicked_index
             # Only redraw the specific selector highlight and update labels
             self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
             self.update_map_info_labels()

    def _paint_map_cell(self, event_x, event_y):
        global map_data, last_painted_map_cell
        canvas = self.map_canvas; size = MAP_CELL_PREVIEW_SIZE
        c = int(canvas.canvasx(event_x) // size); r = int(canvas.canvasy(event_y) // size)
        if 0 <= r < map_height and 0 <= c < map_width:
            # MODIFIED: Update map data and redraw ONLY the affected cell using cached image
            if (r, c) != last_painted_map_cell: # Check if different cell first
                 if map_data[r][c] != selected_supertile_for_map: # Check if value needs change
                    map_data[r][c] = selected_supertile_for_map
                    # Redraw the specific cell
                    base_x = c * size; base_y = r * size
                    img = self.create_supertile_image(selected_supertile_for_map, size)
                    # Delete old image item for this cell if it exists
                    canvas.delete(f"map_cell_{r}_{c}")
                    canvas.create_image(base_x, base_y, image=img, anchor=tk.NW, tags=f"map_cell_{r}_{c}")
                 last_painted_map_cell = (r,c) # Update last cell painted

    def handle_map_click(self, event):
        global last_painted_map_cell
        last_painted_map_cell = None; self._paint_map_cell(event.x, event.y)

    def handle_map_drag(self, event):
        self._paint_map_cell(event.x, event.y)


    # --- File Menu Commands --- (Need cache clearing)

    def new_project(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        global supertiles_data, current_supertile_index, num_supertiles, selected_tile_for_supertile
        global map_data, map_width, map_height, selected_supertile_for_map, last_painted_map_cell
        if messagebox.askokcancel("New Project", "..."):
            # Reset data... (same as before)
            tileset_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            current_tile_index = 0; num_tiles_in_set = 1
            supertiles_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
            current_supertile_index = 0; num_supertiles = 1; selected_tile_for_supertile = 0
            map_width = DEFAULT_MAP_WIDTH; map_height = DEFAULT_MAP_HEIGHT
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            selected_supertile_for_map = 0; last_painted_map_cell = None
            self.root.title("MSX SCREEN 4 Tile/Map Editor - Untitled")
            # MODIFIED: Clear cache and update all
            self.clear_all_caches()
            self.update_all_displays(changed_level="all")

    def save_tileset(self): # Save logic unchanged
        global num_tiles_in_set
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Tiles", filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Save Tileset As...")
        if not filepath: return
        try: # ... (save logic same) ...
             with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_tiles_in_set))
                for i in range(num_tiles_in_set):
                    for r in range(TILE_HEIGHT): # Pattern
                        byte_val = sum(1 << (7 - c) for c in range(TILE_WIDTH) if tileset_patterns[i][r][c] == 1)
                        f.write(struct.pack('B', byte_val))
                    for r in range(TILE_HEIGHT): # Color
                         fg, bg = tileset_colors[i][r]
                         f.write(struct.pack('B', ((fg & 0x0F) << 4) | (bg & 0x0F)))
             messagebox.showinfo("Save Successful", f"Tileset saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save tileset:\n{e}")

    def open_tileset(self): # Load logic needs cache clearing
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, selected_tile_for_supertile
        filepath = filedialog.askopenfilename( filetypes=[("MSX Tileset", "*.SC4Tiles")], title="Open Tileset")
        if not filepath: return
        try: # ... (load logic same) ...
            with open(filepath, 'rb') as f:
                 num_tiles_byte = f.read(1); loaded_num_tiles = struct.unpack('B', num_tiles_byte)[0]
                 if not (1 <= loaded_num_tiles <= MAX_TILES): raise ValueError("Invalid tile count")
                 new_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 new_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 # ... (rest of load logic same) ...
                 for i in range(loaded_num_tiles):
                     for r in range(TILE_HEIGHT): # Pattern
                         byte_val = struct.unpack('B', f.read(1))[0]
                         for c in range(TILE_WIDTH): new_patterns[i][r][c] = (byte_val >> (7 - c)) & 1
                     for r in range(TILE_HEIGHT): # Color
                         byte_val = struct.unpack('B', f.read(1))[0]
                         new_colors[i][r] = ((byte_val >> 4) & 0x0F, byte_val & 0x0F)

            # Commit changes
            tileset_patterns = new_patterns; tileset_colors = new_colors
            num_tiles_in_set = loaded_num_tiles; current_tile_index = 0
            selected_tile_for_supertile = 0
            # MODIFIED: Clear cache and update all
            self.clear_all_caches() # Tile changes affect supertiles too
            self.update_all_displays(changed_level="all")
            messagebox.showinfo("Open Successful", f"Loaded {num_tiles_in_set} tiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse tileset:\n{e}")

    def save_supertiles(self): # Save logic unchanged
        global num_supertiles, supertiles_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Super", filetypes=[("MSX Supertiles", "*.SC4Super")], title="Save Supertiles As...")
        if not filepath: return
        try: # ... (save logic same) ...
            with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_supertiles))
                for i in range(num_supertiles):
                    for r in range(SUPERTILE_GRID_DIM):
                        for c in range(SUPERTILE_GRID_DIM):
                             f.write(struct.pack('B', supertiles_data[i][r][c]))
            messagebox.showinfo("Save Successful", f"Supertiles saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save supertiles:\n{e}")

    def open_supertiles(self): # Load logic needs cache clearing
        global supertiles_data, num_supertiles, current_supertile_index, selected_supertile_for_map
        filepath = filedialog.askopenfilename( filetypes=[("MSX Supertiles", "*.SC4Super")], title="Open Supertiles")
        if not filepath: return
        try: # ... (load logic same) ...
            with open(filepath, 'rb') as f:
                 num_st_byte = f.read(1); loaded_num_st = struct.unpack('B', num_st_byte)[0]
                 if not (1 <= loaded_num_st <= MAX_SUPERTILES): raise ValueError("Invalid supertile count")
                 new_st_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
                 # ... (rest of load logic same) ...
                 for i in range(loaded_num_st):
                     for r in range(SUPERTILE_GRID_DIM):
                         for c in range(SUPERTILE_GRID_DIM):
                              new_st_data[i][r][c] = struct.unpack('B', f.read(1))[0]

            # Commit changes
            supertiles_data = new_st_data; num_supertiles = loaded_num_st
            current_supertile_index = 0; selected_supertile_for_map = 0
            # MODIFIED: Clear supertile cache and update
            self.supertile_image_cache.clear()
            self.update_all_displays(changed_level="supertile")
            messagebox.showinfo("Open Successful", f"Loaded {num_supertiles} supertiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse supertiles:\n{e}")

    def save_map(self): # Save logic unchanged
        global map_width, map_height, map_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Map", filetypes=[("MSX Map", "*.SC4Map")], title="Save Map As...")
        if not filepath: return
        try: # ... (save logic same) ...
            with open(filepath, 'wb') as f:
                 f.write(struct.pack('>HH', map_width, map_height)) # Save dimensions
                 for r in range(map_height):
                     for c in range(map_width): f.write(struct.pack('B', map_data[r][c]))
            messagebox.showinfo("Save Successful", f"Map saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save map:\n{e}")

    def open_map(self): # Load logic unchanged regarding cache
        global map_data, map_width, map_height
        filepath = filedialog.askopenfilename( filetypes=[("MSX Map", "*.SC4Map")], title="Open Map")
        if not filepath: return
        try: # ... (load logic same) ...
            with open(filepath, 'rb') as f:
                 dim_bytes = f.read(4); loaded_w, loaded_h = struct.unpack('>HH', dim_bytes)
                 if not (1 <= loaded_w <= 1024 and 1 <= loaded_h <= 1024): raise ValueError("Invalid map dimensions")
                 new_map_data = [[0 for _ in range(loaded_w)] for _ in range(loaded_h)]
                 # ... (rest of load logic same) ...
                 for r in range(loaded_h):
                     for c in range(loaded_w): new_map_data[r][c] = struct.unpack('B', f.read(1))[0]

            # Commit changes
            map_width = loaded_w; map_height = loaded_h; map_data = new_map_data
            # No specific cache clear needed, map display will use existing supertile cache
            self.update_all_displays(changed_level="map")
            messagebox.showinfo("Open Successful", f"Loaded {map_width}x{map_height} map from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse map:\n{e}")


    # --- Edit Menu Commands --- (Need cache clearing on reduction)

    def set_tileset_size(self):
        global num_tiles_in_set, current_tile_index, selected_tile_for_supertile
        # ... (Dialog logic same) ...
        new_size_str = simpledialog.askstring("Set Tileset Size", f"... (1-{MAX_TILES}):", initialvalue=str(num_tiles_in_set))
        if new_size_str:
             try:
                new_size = int(new_size_str)
                if 1 <= new_size <= MAX_TILES:
                    reduced = new_size < num_tiles_in_set
                    if reduced and not messagebox.askokcancel("Reduce Size", "..."): return
                    # MODIFIED: Clear cache for removed items if size reduced
                    if reduced:
                        for i in range(new_size, num_tiles_in_set):
                            self.invalidate_tile_cache(i) # This handles dependent supertiles too
                    num_tiles_in_set = new_size
                    if current_tile_index >= num_tiles_in_set: current_tile_index = max(0, num_tiles_in_set - 1)
                    if selected_tile_for_supertile >= num_tiles_in_set: selected_tile_for_supertile = 0
                    self.update_all_displays(changed_level="all") # Treat as major change
                else: messagebox.showerror("Invalid Size", ...)
             except ValueError: messagebox.showerror("Invalid Input", ...)

    def set_supertile_count(self):
        global num_supertiles, current_supertile_index, selected_supertile_for_map
        # ... (Dialog logic same) ...
        new_count_str = simpledialog.askstring("Set Supertile Count", f"... (1-{MAX_SUPERTILES}):", initialvalue=str(num_supertiles))
        if new_count_str:
            try:
                new_count = int(new_count_str)
                if 1 <= new_count <= MAX_SUPERTILES:
                    reduced = new_count < num_supertiles
                    if reduced and not messagebox.askokcancel("Reduce Count", "..."): return
                    # MODIFIED: Clear cache for removed items if count reduced
                    if reduced:
                        for i in range(new_count, num_supertiles):
                            self.invalidate_supertile_cache(i)
                    num_supertiles = new_count
                    if current_supertile_index >= num_supertiles: current_supertile_index = max(0, num_supertiles - 1)
                    if selected_supertile_for_map >= num_supertiles: selected_supertile_for_map = 0
                    self.update_all_displays(changed_level="supertile")
                else: messagebox.showerror("Invalid Count", ...)
            except ValueError: messagebox.showerror("Invalid Input", ...)

    def set_map_dimensions(self): # No cache changes needed here usually
        global map_width, map_height, map_data
        # ... (Dialog and resize logic same) ...
        dims = simpledialog.askstring("Set Map Dimensions", ..., initialvalue=f"{map_width}x{map_height}")
        if dims:
            try: # ... (Parsing and range check same) ...
                 parts = dims.lower().split('x'); new_w, new_h = int(parts[0].strip()), int(parts[1].strip())
                 if not (1 <= new_w <= 1024 and 1 <= new_h <= 1024): raise ValueError("Dimensions out of range")
                 if new_w == map_width and new_h == map_height: return
                 if (new_w < map_width or new_h < map_height) and not messagebox.askokcancel("Resize Map", "..."): return
                 # ... (Map data resize logic same) ...
                 new_map_data = [[0]*new_w for _ in range(new_h)]
                 for r in range(min(map_height, new_h)):
                     for c in range(min(map_width, new_w)): new_map_data[r][c] = map_data[r][c]
                 map_width = new_w; map_height = new_h; map_data = new_map_data
                 self.update_all_displays(changed_level="map")
            except ValueError as e: messagebox.showerror("Invalid Input", ...)

    def clear_current_tile(self):
        global tileset_patterns, tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if messagebox.askokcancel("Clear Tile", ...):
            tileset_patterns[current_tile_index] = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
            tileset_colors[current_tile_index] = [(15, 1) for _ in range(TILE_HEIGHT)]
            # MODIFIED: Invalidate cache and update
            self.invalidate_tile_cache(current_tile_index)
            self.update_all_displays(changed_level="tile")

    def clear_current_supertile(self):
        global supertiles_data, current_supertile_index
        if not (0 <= current_supertile_index < num_supertiles): return
        if messagebox.askokcancel("Clear Supertile", ...):
             supertiles_data[current_supertile_index] = [[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)]
             # MODIFIED: Invalidate cache and update
             self.invalidate_supertile_cache(current_supertile_index)
             self.update_all_displays(changed_level="supertile")

    def clear_map(self):
        global map_data, map_width, map_height
        if messagebox.askokcancel("Clear Map", ...):
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            # No cache invalidation needed, just redraw
            self.update_all_displays(changed_level="map")


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TileEditorApp(root)
    root.mainloop()