import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog # Need this for map size etc.
import struct
import os
import math # For ceiling division

# --- Constants ---
TILE_WIDTH = 8
TILE_HEIGHT = 8
EDITOR_PIXEL_SIZE = 30
VIEWER_TILE_SIZE = TILE_WIDTH * 2 # Size of each tile in the tileset viewer
PALETTE_SQUARE_SIZE = 20
NUM_TILES_ACROSS = 16 # Tileset viewer width
MAX_TILES = 256

SUPERTILE_GRID_DIM = 4 # Supertiles are 4x4 tiles
SUPERTILE_DEF_TILE_SIZE = TILE_WIDTH * 4 # Size of tiles in supertile definition grid
SUPERTILE_SELECTOR_PREVIEW_SIZE = TILE_WIDTH * 4 # Size of one supertile preview in selector
NUM_SUPERTILES_ACROSS = 8 # Supertile selector width
MAX_SUPERTILES = 256

MAP_CELL_PREVIEW_SIZE = TILE_WIDTH * 2 # Size of one supertile cell drawn on map
DEFAULT_MAP_WIDTH = 32
DEFAULT_MAP_HEIGHT = 24

# MSX 16 Colors (Approximate RGB values) - Same as before
MSX_COLORS = [
    "#000000", "#000000", "#3EB849", "#74D07D", "#5955E0", "#8076F1",
    "#B95E51", "#65DBEF", "#D96459", "#FF897D", "#CCC35E", "#DED087",
    "#3AA241", "#B766B5", "#CCCCCC", "#FFFFFF",
]

# --- Data Structures ---
# Tile Data (as before)
tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)] # Default: White on Black
current_tile_index = 0
num_tiles_in_set = 1 # Start with one tile
selected_color_index = 15 # Default to white
last_drawn_pixel = None # To avoid redundant draws on drag

# Supertile Data
# supertiles_data[supertile_index][row][col] = tile_index (0-255)
supertiles_data = [[[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
current_supertile_index = 0
num_supertiles = 1 # Start with one default supertile
selected_tile_for_supertile = 0 # Tile index selected in tileset viewer (for placing in supertile def)

# Map Data
map_width = DEFAULT_MAP_WIDTH
map_height = DEFAULT_MAP_HEIGHT
# map_data[row][col] = supertile_index (0-255)
map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
selected_supertile_for_map = 0 # Supertile index selected in supertile selector (for placing on map)
last_painted_map_cell = None

# --- Utility Functions ---
def get_contrast_color(hex_color):
    """Chooses black or white text for contrast."""
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
        # Make resizable for map editor
        # self.root.resizable(False, False)
        self.root.state('zoomed') # Start maximized for more space

        # --- UI Setup ---
        self.create_menu()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # Create tabs
        self.tab_tile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_supertile_editor = ttk.Frame(self.notebook, padding="10")
        self.tab_map_editor = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.tab_tile_editor, text='Tile Editor')
        self.notebook.add(self.tab_supertile_editor, text='Supertile Editor')
        self.notebook.add(self.tab_map_editor, text='Map Editor')

        # Populate tabs
        self.create_tile_editor_widgets(self.tab_tile_editor)
        self.create_supertile_editor_widgets(self.tab_supertile_editor)
        self.create_map_editor_widgets(self.tab_map_editor)

        self.update_all_displays(changed_level="all") # Initial draw

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # --- File Menu ---
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

        # --- Edit Menu ---
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size)
        edit_menu.add_command(label="Set Supertile Count...", command=self.set_supertile_count)
        edit_menu.add_command(label="Set Map Dimensions...", command=self.set_map_dimensions)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile)
        edit_menu.add_command(label="Clear Current Supertile", command=self.clear_current_supertile)
        edit_menu.add_command(label="Clear Map", command=self.clear_map)


    # --- Widget Creation ---

    def create_tile_editor_widgets(self, parent_frame):
        # ... (Widget creation code remains the same as before) ...
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)")
        editor_frame.grid(row=0, column=0, pady=(0, 10))
        self.editor_canvas = tk.Canvas( editor_frame, width=TILE_WIDTH * EDITOR_PIXEL_SIZE, height=TILE_HEIGHT * EDITOR_PIXEL_SIZE, bg="grey")
        self.editor_canvas.grid(row=0, column=0)
        self.editor_canvas.bind("<Button-1>", self.handle_editor_click)
        self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag)
        self.editor_canvas.bind("<Button-3>", self.handle_editor_click)
        self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag)
        attr_frame = ttk.LabelFrame(left_frame, text="Row Colors (Click to set FG/BG)")
        attr_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.attr_row_frames = []
        self.attr_fg_labels = []
        self.attr_bg_labels = []
        for r in range(TILE_HEIGHT):
            row_f = ttk.Frame(attr_frame)
            row_f.grid(row=r, column=0, sticky=tk.W, pady=1)
            ttk.Label(row_f, text=f"{r}:").grid(row=0, column=0, padx=(0, 5))
            fg_label = tk.Label(row_f, text=" FG ", width=3, relief="raised", borderwidth=2)
            fg_label.grid(row=0, column=1, padx=(0, 2))
            fg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'fg'))
            self.attr_fg_labels.append(fg_label)
            bg_label = tk.Label(row_f, text=" BG ", width=3, relief="raised", borderwidth=2)
            bg_label.grid(row=0, column=2)
            bg_label.bind("<Button-1>", lambda e, row=r: self.set_row_color(row, 'bg'))
            self.attr_bg_labels.append(bg_label)
            self.attr_row_frames.append(row_f)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        main_frame.grid_rowconfigure(0, weight=1)
        palette_frame = ttk.LabelFrame(right_frame, text="Color Palette")
        palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.N, tk.W, tk.E))
        self.palette_canvas = tk.Canvas(palette_frame, width=4 * (PALETTE_SQUARE_SIZE + 2), height=4 * (PALETTE_SQUARE_SIZE + 2), borderwidth=0, highlightthickness=0)
        self.palette_canvas.grid(row=0, column=0)
        self.palette_canvas.bind("<Button-1>", self.handle_palette_click)
        self.palette_labels = []
        for i in range(16):
            row, col = divmod(i, 4)
            x1, y1 = col * (PALETTE_SQUARE_SIZE + 2) + 1, row * (PALETTE_SQUARE_SIZE + 2) + 1
            x2, y2 = x1 + PALETTE_SQUARE_SIZE, y1 + PALETTE_SQUARE_SIZE
            rect = self.palette_canvas.create_rectangle(x1, y1, x2, y2, fill=MSX_COLORS[i], outline="grey", width=1, tags=f"pal_{i}")
            self.palette_labels.append(rect)
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
        self.tile_info_label = ttk.Label(right_frame, text="Tile: 0/0")
        self.tile_info_label.grid(row=2, column=0, sticky=tk.W, pady=(5,0))

    def create_supertile_editor_widgets(self, parent_frame):
        # ... (Widget creation code remains the same as before) ...
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))
        def_frame = ttk.LabelFrame(left_frame, text="Supertile Definition (Click to place selected tile)")
        def_frame.grid(row=0, column=0, pady=(0, 10))
        self.supertile_def_canvas = tk.Canvas(def_frame, width=SUPERTILE_GRID_DIM * SUPERTILE_DEF_TILE_SIZE, height=SUPERTILE_GRID_DIM * SUPERTILE_DEF_TILE_SIZE, bg="darkgrey")
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
        self.supertile_sel_info_label = ttk.Label(right_frame, text=f"Supertiles: {num_supertiles}")
        self.supertile_sel_info_label.grid(row=2, column=0, sticky=tk.W, pady=(5,0))

    def create_map_editor_widgets(self, parent_frame):
        # ... (Widget creation code remains the same as before) ...
        main_frame = ttk.Frame(parent_frame)
        main_frame.pack(expand=True, fill="both")
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(0, 10))
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        map_controls_frame = ttk.Frame(left_frame)
        map_controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(map_controls_frame, text="Map Size:").grid(row=0, column=0, padx=(0,5))
        self.map_size_label = ttk.Label(map_controls_frame, text=f"{map_width} x {map_height}")
        self.map_size_label.grid(row=0, column=1)
        map_canvas_frame = ttk.LabelFrame(left_frame, text="Map (Click/Drag to place selected Supertile)")
        map_canvas_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        left_frame.grid_rowconfigure(1, weight=1)
        map_hbar = ttk.Scrollbar(map_canvas_frame, orient=tk.HORIZONTAL)
        map_vbar = ttk.Scrollbar(map_canvas_frame, orient=tk.VERTICAL)
        map_canvas_width = map_width * MAP_CELL_PREVIEW_SIZE
        map_canvas_height = map_height * MAP_CELL_PREVIEW_SIZE
        self.map_canvas = tk.Canvas(map_canvas_frame, bg="black", scrollregion=(0,0, map_canvas_width, map_canvas_height), xscrollcommand=map_hbar.set, yscrollcommand=map_vbar.set)
        map_hbar.config(command=self.map_canvas.xview)
        map_vbar.config(command=self.map_canvas.yview)
        self.map_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        map_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        map_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        map_canvas_frame.grid_rowconfigure(0, weight=1)
        map_canvas_frame.grid_columnconfigure(0, weight=1)
        self.map_canvas.bind("<Button-1>", self.handle_map_click)
        self.map_canvas.bind("<B1-Motion>", self.handle_map_drag)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        st_selector_frame = ttk.LabelFrame(right_frame, text="Supertile Palette (Click to select for map)")
        st_selector_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        st_sel_canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        st_sel_num_rows = math.ceil(MAX_SUPERTILES / NUM_SUPERTILES_ACROSS)
        st_sel_canvas_height = st_sel_num_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + 1) + 1
        map_st_sel_hbar = ttk.Scrollbar(st_selector_frame, orient=tk.HORIZONTAL)
        map_st_sel_vbar = ttk.Scrollbar(st_selector_frame, orient=tk.VERTICAL)
        self.map_supertile_selector_canvas = tk.Canvas(st_selector_frame, bg="lightgrey", scrollregion=(0,0, st_sel_canvas_width, st_sel_canvas_height), xscrollcommand=map_st_sel_hbar.set, yscrollcommand=map_st_sel_vbar.set)
        map_st_sel_hbar.config(command=self.map_supertile_selector_canvas.xview)
        map_st_sel_vbar.config(command=self.map_supertile_selector_canvas.yview)
        self.map_supertile_selector_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        map_st_sel_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        map_st_sel_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        st_selector_frame.grid_rowconfigure(0, weight=1)
        st_selector_frame.grid_columnconfigure(0, weight=1)
        self.map_supertile_selector_canvas.bind("<Button-1>", self.handle_map_supertile_selector_click)
        self.map_supertile_select_label = ttk.Label(right_frame, text=f"Selected Supertile for Painting: {selected_supertile_for_map}")
        self.map_supertile_select_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))


    # --- Drawing Functions ---

    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    # MODIFIED update_all_displays
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    def update_all_displays(self, changed_level="all"):
        """
        Updates the display components based on the level of change.
        Levels: 'tile', 'supertile', 'map', 'all'.
        Lower levels imply changes that affect higher levels too.
        """
        # Always update things directly related to the lowest level changed

        # Tile Editor parts (if tile or all changed)
        # These components show/edit the fundamental tile data.
        if changed_level in ["all", "tile"]:
            self.draw_editor_canvas()
            self.draw_attribute_editor()
            self.draw_palette() # Palette selection doesn't change, but draw it for consistency
            # Need to redraw both tileset viewers as they show the same base data
            self.draw_tileset_viewer(self.tileset_canvas, current_tile_index)
            self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
            self.update_tile_info_label()

        # Supertile Editor parts (if supertile, tile or all changed)
        # Supertiles depend on tiles. A change here also affects the map.
        if changed_level in ["all", "tile", "supertile"]:
            self.draw_supertile_definition_canvas()
            # Need to redraw both supertile selectors
            self.draw_supertile_selector(self.supertile_selector_canvas, current_supertile_index)
            self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
            self.update_supertile_info_labels()

        # Map Editor parts (if map, supertile, tile, or all changed)
        # Map depends on supertiles (which depend on tiles).
        if changed_level in ["all", "tile", "supertile", "map"]:
             self.draw_map_canvas()
             self.update_map_info_labels() # Includes map size label update
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # END MODIFIED update_all_displays
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


    # --- Tile Drawing --- (Helpers and draw functions remain the same as before)
    def draw_editor_canvas(self):
        self.editor_canvas.delete("all")
        if not (0 <= current_tile_index < num_tiles_in_set): return
        pattern = tileset_patterns[current_tile_index]
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]
            fg_color = MSX_COLORS[fg_index]
            bg_color = MSX_COLORS[bg_index]
            for c in range(TILE_WIDTH):
                pixel_val = pattern[r][c]
                color = fg_color if pixel_val == 1 else bg_color
                x1,y1 = c * EDITOR_PIXEL_SIZE, r * EDITOR_PIXEL_SIZE
                x2,y2 = x1 + EDITOR_PIXEL_SIZE, y1 + EDITOR_PIXEL_SIZE
                self.editor_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="darkgrey", width=1)

    def draw_attribute_editor(self):
        if not (0 <= current_tile_index < num_tiles_in_set): return
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]
            self.attr_fg_labels[r].config(bg=MSX_COLORS[fg_index], fg=get_contrast_color(MSX_COLORS[fg_index]))
            self.attr_bg_labels[r].config(bg=MSX_COLORS[bg_index], fg=get_contrast_color(MSX_COLORS[bg_index]))

    def draw_palette(self):
        self.palette_canvas.itemconfig(tk.ALL, outline="grey", width=1)
        if 0 <= selected_color_index < 16:
             tag = f"pal_{selected_color_index}"
             self.palette_canvas.itemconfig(tag, outline="red", width=2)

    def _draw_single_tile_preview(self, canvas, tile_index, base_x, base_y, size):
        if not (0 <= tile_index < num_tiles_in_set):
            canvas.create_rectangle(base_x, base_y, base_x + size, base_y + size, fill="magenta", outline="black", width=1)
            canvas.create_line(base_x, base_y, base_x + size, base_y + size, fill="black")
            canvas.create_line(base_x + size, base_y, base_x, base_y + size, fill="black")
            return
        pattern = tileset_patterns[tile_index]
        colors = tileset_colors[tile_index]
        pixel_w = size / TILE_WIDTH
        pixel_h = size / TILE_HEIGHT
        for r in range(TILE_HEIGHT):
            fg_idx, bg_idx = colors[r]
            bg_color = MSX_COLORS[bg_idx]
            fg_color = MSX_COLORS[fg_idx]
            y1 = base_y + r * pixel_h
            y2 = y1 + pixel_h
            canvas.create_rectangle(base_x, y1, base_x + size, y2, fill=bg_color, outline="")
            for c in range(TILE_WIDTH):
                if pattern[r][c] == 1:
                    x1 = base_x + c * pixel_w
                    x2 = x1 + pixel_w
                    canvas.create_rectangle(x1, y1, x2, y2, fill=fg_color, outline="")

    def draw_tileset_viewer(self, canvas, highlighted_tile_index):
        canvas.delete("all")
        padding = 1
        max_rows = math.ceil(num_tiles_in_set / NUM_TILES_ACROSS)
        canvas_height = max_rows * (VIEWER_TILE_SIZE + padding) + padding
        canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + padding) + padding
        current_scrollregion = canvas.cget("scrollregion")
        str_scrollregion = f"0 0 {float(canvas_width)} {float(canvas_height)}" # Ensure float comparison for tk < 8.7
        if current_scrollregion != str_scrollregion:
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        for i in range(num_tiles_in_set):
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS)
            base_x = tile_c * (VIEWER_TILE_SIZE + padding) + padding
            base_y = tile_r * (VIEWER_TILE_SIZE + padding) + padding
            self._draw_single_tile_preview(canvas, i, base_x, base_y, VIEWER_TILE_SIZE)
            outline_color = "red" if i == highlighted_tile_index else "grey"
            outline_width = 2 if i == highlighted_tile_index else 1
            canvas.create_rectangle(
                base_x - padding/2, base_y - padding/2,
                base_x + VIEWER_TILE_SIZE + padding/2, base_y + VIEWER_TILE_SIZE + padding/2,
                outline=outline_color, width=outline_width, tags=f"tile_{i}"
            )

    def update_tile_info_label(self):
         self.tile_info_label.config(text=f"Tile: {current_tile_index}/{num_tiles_in_set-1}")

    # --- Supertile Drawing --- (Helpers and draw functions remain the same as before)
    def _draw_single_supertile_preview(self, canvas, supertile_index, base_x, base_y, total_size):
        if not (0 <= supertile_index < num_supertiles):
            canvas.create_rectangle(base_x, base_y, base_x + total_size, base_y + total_size, fill="cyan", outline="black", width=1)
            return
        definition = supertiles_data[supertile_index]
        mini_tile_size = total_size / SUPERTILE_GRID_DIM
        for r in range(SUPERTILE_GRID_DIM):
            for c in range(SUPERTILE_GRID_DIM):
                tile_idx = definition[r][c]
                mini_base_x = base_x + c * mini_tile_size
                mini_base_y = base_y + r * mini_tile_size
                self._draw_single_tile_preview(canvas, tile_idx, mini_base_x, mini_base_y, mini_tile_size)

    def draw_supertile_definition_canvas(self):
        canvas = self.supertile_def_canvas
        canvas.delete("all")
        if not (0 <= current_supertile_index < num_supertiles): return
        definition = supertiles_data[current_supertile_index]
        padding = 1
        for r in range(SUPERTILE_GRID_DIM):
            for c in range(SUPERTILE_GRID_DIM):
                tile_idx = definition[r][c]
                base_x = c * SUPERTILE_DEF_TILE_SIZE
                base_y = r * SUPERTILE_DEF_TILE_SIZE
                self._draw_single_tile_preview(canvas, tile_idx, base_x, base_y, SUPERTILE_DEF_TILE_SIZE - padding)
                canvas.create_rectangle(base_x, base_y, base_x + SUPERTILE_DEF_TILE_SIZE, base_y + SUPERTILE_DEF_TILE_SIZE, outline="grey")

    def draw_supertile_selector(self, canvas, highlighted_supertile_index):
        canvas.delete("all")
        padding = 1
        max_rows = math.ceil(num_supertiles / NUM_SUPERTILES_ACROSS)
        canvas_height = max_rows * (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding) + padding
        canvas_width = NUM_SUPERTILES_ACROSS * (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding) + padding
        current_scrollregion = canvas.cget("scrollregion")
        str_scrollregion = f"0 0 {float(canvas_width)} {float(canvas_height)}" # Ensure float comparison for tk < 8.7
        if current_scrollregion != str_scrollregion:
            canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))

        for i in range(num_supertiles):
            st_r, st_c = divmod(i, NUM_SUPERTILES_ACROSS)
            base_x = st_c * (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding) + padding
            base_y = st_r * (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding) + padding
            self._draw_single_supertile_preview(canvas, i, base_x, base_y, SUPERTILE_SELECTOR_PREVIEW_SIZE)
            outline_color = "red" if i == highlighted_supertile_index else "grey"
            outline_width = 2 if i == highlighted_supertile_index else 1
            canvas.create_rectangle(
                base_x - padding/2, base_y - padding/2,
                base_x + SUPERTILE_SELECTOR_PREVIEW_SIZE + padding/2, base_y + SUPERTILE_SELECTOR_PREVIEW_SIZE + padding/2,
                outline=outline_color, width=outline_width, tags=f"st_{i}"
            )

    def update_supertile_info_labels(self):
         self.supertile_def_info_label.config(text=f"Editing Supertile: {current_supertile_index}/{num_supertiles-1}")
         self.supertile_tile_select_label.config(text=f"Selected Tile for Placing: {selected_tile_for_supertile}")
         self.supertile_sel_info_label.config(text=f"Supertiles: {num_supertiles}")

    # --- Map Drawing --- (Draw function remains the same)
    def draw_map_canvas(self):
        canvas = self.map_canvas
        canvas.delete("all")
        map_canvas_width = map_width * MAP_CELL_PREVIEW_SIZE
        map_canvas_height = map_height * MAP_CELL_PREVIEW_SIZE
        current_scrollregion = canvas.cget("scrollregion")
        str_scrollregion = f"0 0 {float(map_canvas_width)} {float(map_canvas_height)}" # Ensure float comparison for tk < 8.7
        if current_scrollregion != str_scrollregion:
             canvas.config(scrollregion=(0, 0, map_canvas_width, map_canvas_height))

        for r in range(map_height):
            for c in range(map_width):
                 supertile_idx = map_data[r][c]
                 base_x = c * MAP_CELL_PREVIEW_SIZE
                 base_y = r * MAP_CELL_PREVIEW_SIZE
                 self._draw_single_supertile_preview(canvas, supertile_idx, base_x, base_y, MAP_CELL_PREVIEW_SIZE)

    def update_map_info_labels(self):
         self.map_size_label.config(text=f"{map_width} x {map_height}")
         self.map_supertile_select_label.config(text=f"Selected Supertile for Painting: {selected_supertile_for_map}")

    # --- Event Handlers ---

    def on_tab_change(self, event):
        # Refresh display slightly more efficiently when changing tabs
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: # Tile Editor - redraw tile related things
             self.update_all_displays(changed_level="tile") # Will also redraw ST+Map
        elif selected_tab == 1: # Supertile Editor - redraw supertile related
             self.update_all_displays(changed_level="supertile") # Will also redraw Map
        elif selected_tab == 2: # Map Editor - redraw map related
             self.update_all_displays(changed_level="map")

    # --- Tile Editor Handlers ---
    def handle_editor_click(self, event):
        global last_drawn_pixel, current_tile_index, tileset_patterns
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE
        r = event.y // EDITOR_PIXEL_SIZE

        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            pixel_value = 1 if event.num == 1 else 0
            pattern = tileset_patterns[current_tile_index]
            if pattern[r][c] != pixel_value:
                pattern[r][c] = pixel_value
                # MODIFIED: Call with specific level
                self.update_all_displays(changed_level="tile")
            last_drawn_pixel = (r, c)

    def handle_editor_drag(self, event):
        global last_drawn_pixel, current_tile_index, tileset_patterns
        if not (0 <= current_tile_index < num_tiles_in_set): return
        c = event.x // EDITOR_PIXEL_SIZE
        r = event.y // EDITOR_PIXEL_SIZE

        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            if (r, c) != last_drawn_pixel:
                pixel_value = 1 if event.state & 0x100 else (0 if event.state & 0x400 else -1)
                if pixel_value != -1:
                    pattern = tileset_patterns[current_tile_index]
                    if pattern[r][c] != pixel_value:
                        pattern[r][c] = pixel_value
                        # MODIFIED: Call with specific level
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
                        # MODIFIED: Only redraw palette
                        self.draw_palette()
                    break
                except (IndexError, ValueError): pass

    def set_row_color(self, row, fg_or_bg):
        global tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if not (0 <= selected_color_index < 16): return
        if 0 <= row < TILE_HEIGHT:
            current_fg, current_bg = tileset_colors[current_tile_index][row]
            changed = False
            if fg_or_bg == 'fg' and current_fg != selected_color_index:
                tileset_colors[current_tile_index][row] = (selected_color_index, current_bg)
                changed = True
            elif fg_or_bg == 'bg' and current_bg != selected_color_index:
                tileset_colors[current_tile_index][row] = (current_fg, selected_color_index)
                changed = True
            if changed:
                 # MODIFIED: Call with specific level
                self.update_all_displays(changed_level="tile")

    def handle_tileset_click(self, event): # Click in main tileset viewer
        global current_tile_index
        canvas = self.tileset_canvas
        padding = 1
        col = int(canvas.canvasx(event.x) // (VIEWER_TILE_SIZE + padding))
        row = int(canvas.canvasy(event.y) // (VIEWER_TILE_SIZE + padding))
        clicked_index = row * NUM_TILES_ACROSS + col

        if 0 <= clicked_index < num_tiles_in_set:
            if current_tile_index != clicked_index:
                current_tile_index = clicked_index
                # MODIFIED: Update affected displays (tile level)
                self.update_all_displays(changed_level="tile")


    # --- Supertile Editor Handlers ---
    def handle_st_tileset_click(self, event): # Click in Supertile tab's tileset viewer
        global selected_tile_for_supertile
        canvas = self.st_tileset_canvas
        padding = 1
        col = int(canvas.canvasx(event.x) // (VIEWER_TILE_SIZE + padding))
        row = int(canvas.canvasy(event.y) // (VIEWER_TILE_SIZE + padding))
        clicked_index = row * NUM_TILES_ACROSS + col

        if 0 <= clicked_index < num_tiles_in_set:
             if selected_tile_for_supertile != clicked_index:
                 selected_tile_for_supertile = clicked_index
                 # MODIFIED: Only redraw the specific viewer and update labels
                 self.draw_tileset_viewer(self.st_tileset_canvas, selected_tile_for_supertile)
                 self.update_supertile_info_labels() # Update selected tile label

    def handle_supertile_def_click(self, event): # Click on the 4x4 definition grid
        global current_supertile_index, supertiles_data
        if not (0 <= current_supertile_index < num_supertiles): return
        if not (0 <= selected_tile_for_supertile < num_tiles_in_set):
            print("Select a tile from the tileset first!")
            return

        canvas = self.supertile_def_canvas
        col = event.x // SUPERTILE_DEF_TILE_SIZE
        row = event.y // SUPERTILE_DEF_TILE_SIZE

        if 0 <= row < SUPERTILE_GRID_DIM and 0 <= col < SUPERTILE_GRID_DIM:
            if supertiles_data[current_supertile_index][row][col] != selected_tile_for_supertile:
                supertiles_data[current_supertile_index][row][col] = selected_tile_for_supertile
                # MODIFIED: Update affected displays (supertile level)
                self.update_all_displays(changed_level="supertile")

    def handle_supertile_selector_click(self, event): # Click in ST tab's selector
        global current_supertile_index
        canvas = self.supertile_selector_canvas
        padding = 1
        col = int(canvas.canvasx(event.x) // (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding))
        row = int(canvas.canvasy(event.y) // (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding))
        clicked_index = row * NUM_SUPERTILES_ACROSS + col

        if 0 <= clicked_index < num_supertiles:
            if current_supertile_index != clicked_index:
                current_supertile_index = clicked_index
                # MODIFIED: Update affected displays (supertile level)
                self.update_all_displays(changed_level="supertile")


    # --- Map Editor Handlers ---
    def handle_map_supertile_selector_click(self, event): # Click in Map tab's selector
        global selected_supertile_for_map
        canvas = self.map_supertile_selector_canvas
        padding = 1
        col = int(canvas.canvasx(event.x) // (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding))
        row = int(canvas.canvasy(event.y) // (SUPERTILE_SELECTOR_PREVIEW_SIZE + padding))
        clicked_index = row * NUM_SUPERTILES_ACROSS + col

        if 0 <= clicked_index < num_supertiles:
             if selected_supertile_for_map != clicked_index:
                 selected_supertile_for_map = clicked_index
                 # MODIFIED: Only redraw the specific selector and update labels
                 self.draw_supertile_selector(self.map_supertile_selector_canvas, selected_supertile_for_map)
                 self.update_map_info_labels() # Update selected ST label

    def _paint_map_cell(self, event_x, event_y):
        global map_data, last_painted_map_cell
        canvas = self.map_canvas
        c = int(canvas.canvasx(event_x) // MAP_CELL_PREVIEW_SIZE)
        r = int(canvas.canvasy(event_y) // MAP_CELL_PREVIEW_SIZE)

        if 0 <= r < map_height and 0 <= c < map_width:
            # MODIFIED: No call to update_all_displays here - drawing handled directly.
            if (r, c) != last_painted_map_cell and map_data[r][c] != selected_supertile_for_map:
                map_data[r][c] = selected_supertile_for_map
                base_x = c * MAP_CELL_PREVIEW_SIZE
                base_y = r * MAP_CELL_PREVIEW_SIZE
                self._draw_single_supertile_preview(canvas, selected_supertile_for_map, base_x, base_y, MAP_CELL_PREVIEW_SIZE)
                last_painted_map_cell = (r,c)
            elif (r,c) != last_painted_map_cell:
                 last_painted_map_cell = (r,c)

    def handle_map_click(self, event):
        global last_painted_map_cell
        last_painted_map_cell = None
        self._paint_map_cell(event.x, event.y)

    def handle_map_drag(self, event):
        self._paint_map_cell(event.x, event.y)


    # --- File Menu Commands --- (Saving/Loading logic unchanged)

    def new_project(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        global supertiles_data, current_supertile_index, num_supertiles, selected_tile_for_supertile
        global map_data, map_width, map_height, selected_supertile_for_map, last_painted_map_cell
        if messagebox.askokcancel("New Project", "Discard all current data (Tiles, Supertiles, Map) and start new?"):
            # Reset Tiles
            tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            current_tile_index = 0; num_tiles_in_set = 1
            # Reset Supertiles
            supertiles_data = [[[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
            current_supertile_index = 0; num_supertiles = 1; selected_tile_for_supertile = 0
            # Reset Map
            map_width = DEFAULT_MAP_WIDTH; map_height = DEFAULT_MAP_HEIGHT
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
            selected_supertile_for_map = 0; last_painted_map_cell = None
            self.root.title("MSX SCREEN 4 Tile/Map Editor - Untitled")
             # MODIFIED: Call with specific level
            self.update_all_displays(changed_level="all")

    def save_tileset(self):
        global num_tiles_in_set
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Tiles", filetypes=[("MSX SCREEN 4 Tileset", "*.SC4Tiles"), ("All Files", "*.*")], title="Save Tileset As...")
        if not filepath: return
        try:
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

    def open_tileset(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set, selected_tile_for_supertile
        filepath = filedialog.askopenfilename( filetypes=[("MSX SCREEN 4 Tileset", "*.SC4Tiles"), ("All Files", "*.*")], title="Open Tileset")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                 num_tiles_byte = f.read(1);
                 if not num_tiles_byte: raise ValueError("File empty")
                 loaded_num_tiles = struct.unpack('B', num_tiles_byte)[0]
                 if not (1 <= loaded_num_tiles <= MAX_TILES): raise ValueError(f"Invalid tile count: {loaded_num_tiles}")
                 new_patterns = [[[0]*TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 new_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                 for i in range(loaded_num_tiles):
                     for r in range(TILE_HEIGHT): # Pattern
                         p_byte = f.read(1);
                         if not p_byte: raise EOFError("EOF reading pattern")
                         byte_val = struct.unpack('B', p_byte)[0]
                         for c in range(TILE_WIDTH): new_patterns[i][r][c] = (byte_val >> (7 - c)) & 1
                     for r in range(TILE_HEIGHT): # Color
                         c_byte = f.read(1);
                         if not c_byte: raise EOFError("EOF reading color")
                         byte_val = struct.unpack('B', c_byte)[0]
                         new_colors[i][r] = ((byte_val >> 4) & 0x0F, byte_val & 0x0F)
                 # Commit changes
                 tileset_patterns = new_patterns; tileset_colors = new_colors
                 num_tiles_in_set = loaded_num_tiles; current_tile_index = 0
                 selected_tile_for_supertile = 0 # Reset this too
                 # MODIFIED: Call with specific level
                 self.update_all_displays(changed_level="all")
                 messagebox.showinfo("Open Successful", f"Loaded {num_tiles_in_set} tiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse tileset:\n{e}")

    def save_supertiles(self):
        global num_supertiles, supertiles_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Super", filetypes=[("MSX SCREEN 4 Supertiles", "*.SC4Super"), ("All Files", "*.*")], title="Save Supertiles As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f:
                f.write(struct.pack('B', num_supertiles))
                for i in range(num_supertiles):
                    for r in range(SUPERTILE_GRID_DIM):
                        for c in range(SUPERTILE_GRID_DIM):
                             f.write(struct.pack('B', supertiles_data[i][r][c]))
            messagebox.showinfo("Save Successful", f"Supertiles saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save supertiles:\n{e}")

    def open_supertiles(self):
        global supertiles_data, num_supertiles, current_supertile_index, selected_supertile_for_map
        filepath = filedialog.askopenfilename( filetypes=[("MSX SCREEN 4 Supertiles", "*.SC4Super"), ("All Files", "*.*")], title="Open Supertiles")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                num_st_byte = f.read(1);
                if not num_st_byte: raise ValueError("File empty")
                loaded_num_st = struct.unpack('B', num_st_byte)[0]
                if not (1 <= loaded_num_st <= MAX_SUPERTILES): raise ValueError(f"Invalid supertile count: {loaded_num_st}")
                new_st_data = [[[0]*SUPERTILE_GRID_DIM for _ in range(SUPERTILE_GRID_DIM)] for _ in range(MAX_SUPERTILES)]
                for i in range(loaded_num_st):
                    for r in range(SUPERTILE_GRID_DIM):
                        for c in range(SUPERTILE_GRID_DIM):
                             idx_byte = f.read(1);
                             if not idx_byte: raise EOFError("EOF reading supertile data")
                             new_st_data[i][r][c] = struct.unpack('B', idx_byte)[0]
                # Commit changes
                supertiles_data = new_st_data; num_supertiles = loaded_num_st
                current_supertile_index = 0; selected_supertile_for_map = 0
                # MODIFIED: Call with specific level
                self.update_all_displays(changed_level="supertile")
                messagebox.showinfo("Open Successful", f"Loaded {num_supertiles} supertiles from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse supertiles:\n{e}")

    def save_map(self):
        global map_width, map_height, map_data
        filepath = filedialog.asksaveasfilename( defaultextension=".SC4Map", filetypes=[("MSX SCREEN 4 Map", "*.SC4Map"), ("All Files", "*.*")], title="Save Map As...")
        if not filepath: return
        try:
            with open(filepath, 'wb') as f:
                f.write(struct.pack('>HH', map_width, map_height)) # Save dimensions
                for r in range(map_height):
                    for c in range(map_width):
                         f.write(struct.pack('B', map_data[r][c]))
            messagebox.showinfo("Save Successful", f"Map saved to {filepath}")
        except Exception as e: messagebox.showerror("Save Error", f"Failed to save map:\n{e}")

    def open_map(self):
        global map_data, map_width, map_height
        filepath = filedialog.askopenfilename( filetypes=[("MSX SCREEN 4 Map", "*.SC4Map"), ("All Files", "*.*")], title="Open Map")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f:
                dim_bytes = f.read(4);
                if len(dim_bytes) < 4: raise ValueError("Invalid map file header")
                loaded_w, loaded_h = struct.unpack('>HH', dim_bytes)
                if not (1 <= loaded_w <= 1024 and 1 <= loaded_h <= 1024): raise ValueError(f"Invalid map dimensions: {loaded_w}x{loaded_h}")
                new_map_data = [[0 for _ in range(loaded_w)] for _ in range(loaded_h)]
                for r in range(loaded_h):
                    for c in range(loaded_w):
                         st_idx_byte = f.read(1);
                         if not st_idx_byte: raise EOFError("EOF reading map data")
                         new_map_data[r][c] = struct.unpack('B', st_idx_byte)[0]
                # Commit changes
                map_width = loaded_w; map_height = loaded_h; map_data = new_map_data
                # MODIFIED: Call with specific level
                self.update_all_displays(changed_level="map")
                messagebox.showinfo("Open Successful", f"Loaded {map_width}x{map_height} map from {filepath}")
        except Exception as e: messagebox.showerror("Open Error", f"Failed to open or parse map:\n{e}")


    # --- Edit Menu Commands ---

    def set_tileset_size(self):
        global num_tiles_in_set, current_tile_index, selected_tile_for_supertile
        new_size_str = simpledialog.askstring("Set Tileset Size", f"Enter number of tiles (1-{MAX_TILES}):", initialvalue=str(num_tiles_in_set))
        if new_size_str:
            try:
                new_size = int(new_size_str)
                if 1 <= new_size <= MAX_TILES:
                    if new_size < num_tiles_in_set and not messagebox.askokcancel("Reduce Size", f"Reducing size to {new_size} will discard tiles {new_size} to {num_tiles_in_set-1}. Proceed?"): return
                    num_tiles_in_set = new_size
                    if current_tile_index >= num_tiles_in_set: current_tile_index = max(0, num_tiles_in_set - 1)
                    if selected_tile_for_supertile >= num_tiles_in_set: selected_tile_for_supertile = 0
                     # MODIFIED: Call with specific level
                    self.update_all_displays(changed_level="all") # Treat as major change
                else: messagebox.showerror("Invalid Size", f"Size must be between 1 and {MAX_TILES}.")
            except ValueError: messagebox.showerror("Invalid Input", "Please enter a valid number.")

    def set_supertile_count(self):
        global num_supertiles, current_supertile_index, selected_supertile_for_map
        new_count_str = simpledialog.askstring("Set Supertile Count", f"Enter number of supertiles (1-{MAX_SUPERTILES}):", initialvalue=str(num_supertiles))
        if new_count_str:
            try:
                new_count = int(new_count_str)
                if 1 <= new_count <= MAX_SUPERTILES:
                    if new_count < num_supertiles and not messagebox.askokcancel("Reduce Count", f"Reducing count to {new_count} will discard supertiles {new_count} to {num_supertiles-1}. Proceed?"): return
                    num_supertiles = new_count
                    if current_supertile_index >= num_supertiles: current_supertile_index = max(0, num_supertiles - 1)
                    if selected_supertile_for_map >= num_supertiles: selected_supertile_for_map = 0
                     # MODIFIED: Call with specific level
                    self.update_all_displays(changed_level="supertile")
                else: messagebox.showerror("Invalid Count", f"Count must be between 1 and {MAX_SUPERTILES}.")
            except ValueError: messagebox.showerror("Invalid Input", "Please enter a valid number.")

    def set_map_dimensions(self):
        global map_width, map_height, map_data
        dims = simpledialog.askstring("Set Map Dimensions", "Enter new dimensions (Width x Height):", initialvalue=f"{map_width}x{map_height}")
        if dims:
            try:
                parts = dims.lower().split('x');
                if len(parts)!= 2: raise ValueError("Format WxH")
                new_w, new_h = int(parts[0].strip()), int(parts[1].strip())
                if not (1 <= new_w <= 1024 and 1 <= new_h <= 1024): raise ValueError("Dimensions out of range (1-1024)")
                if new_w == map_width and new_h == map_height: return
                if (new_w < map_width or new_h < map_height) and not messagebox.askokcancel("Resize Map", "Reducing map size will discard data outside the new boundaries. Proceed?"): return

                new_map_data = [[0 for _ in range(new_w)] for _ in range(new_h)]
                for r in range(min(map_height, new_h)):
                    for c in range(min(map_width, new_w)):
                        new_map_data[r][c] = map_data[r][c]
                map_width = new_w; map_height = new_h; map_data = new_map_data
                 # MODIFIED: Call with specific level
                self.update_all_displays(changed_level="map")
            except ValueError as e: messagebox.showerror("Invalid Input", f"Error parsing dimensions: {e}")

    def clear_current_tile(self):
        global tileset_patterns, tileset_colors, current_tile_index
        if not (0 <= current_tile_index < num_tiles_in_set): return
        if messagebox.askokcancel("Clear Tile", f"Clear pattern and reset colors for tile {current_tile_index}?"):
            tileset_patterns[current_tile_index] = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
            tileset_colors[current_tile_index] = [(15, 1) for _ in range(TILE_HEIGHT)]
             # MODIFIED: Call with specific level
            self.update_all_displays(changed_level="tile")

    def clear_current_supertile(self):
        global supertiles_data, current_supertile_index
        if not (0 <= current_supertile_index < num_supertiles): return
        if messagebox.askokcancel("Clear Supertile", f"Clear definition (set all to tile 0) for supertile {current_supertile_index}?"):
             supertiles_data[current_supertile_index] = [[0 for _ in range(SUPERTILE_GRID_DIM)] for _ in range(SUPERTILE_GRID_DIM)]
              # MODIFIED: Call with specific level
             self.update_all_displays(changed_level="supertile")

    def clear_map(self):
        global map_data, map_width, map_height
        if messagebox.askokcancel("Clear Map", f"Clear entire map (set all to supertile 0)?"):
            map_data = [[0 for _ in range(map_width)] for _ in range(map_height)]
             # MODIFIED: Call with specific level
            self.update_all_displays(changed_level="map")


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    # Handle potential Tk version differences for scrollregion format
    try: # Check if we need float conversion for scrollregion (Tk < 8.7)
        test_canvas = tk.Canvas(root)
        test_canvas.config(scrollregion="0 0 100.0 100.0")
        test_canvas.destroy()
    except tk.TclError:
        # If float format fails, assume older Tk, patch math.ceil to return int
        original_ceil = math.ceil
        math.ceil = lambda x: int(original_ceil(x))
        print("Note: Using integer scrollregion values for compatibility.")


    app = TileEditorApp(root)
    root.mainloop()