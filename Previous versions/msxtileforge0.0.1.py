import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser
from tkinter import filedialog
from tkinter import messagebox
import struct
import os

# --- Constants ---
TILE_WIDTH = 8
TILE_HEIGHT = 8
EDITOR_PIXEL_SIZE = 30  # Size of each pixel in the editor grid
VIEWER_TILE_SIZE = TILE_WIDTH * 2 # Size of each tile in the tileset viewer
PALETTE_SQUARE_SIZE = 20
NUM_TILES_ACROSS = 16 # How many tiles to show horizontally in the viewer
MAX_TILES = 256

# MSX 16 Colors (Approximate RGB values)
MSX_COLORS = [
    "#000000",  # 0 Transparent (often treated as Black)
    "#000000",  # 1 Black
    "#3EB849",  # 2 Medium Green
    "#74D07D",  # 3 Light Green
    "#5955E0",  # 4 Dark Blue
    "#8076F1",  # 5 Light Blue
    "#B95E51",  # 6 Dark Red
    "#65DBEF",  # 7 Cyan
    "#D96459",  # 8 Medium Red
    "#FF897D",  # 9 Light Red
    "#CCC35E",  # 10 Dark Yellow
    "#DED087",  # 11 Light Yellow
    "#3AA241",  # 12 Dark Green
    "#B766B5",  # 13 Magenta
    "#CCCCCC",  # 14 Gray
    "#FFFFFF",  # 15 White
]

# --- Data Structures ---
# tileset_patterns[tile_index][row][col] = 0 or 1
tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]

# tileset_colors[tile_index][row] = (fg_index, bg_index)
tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)] # Default: White on Black

current_tile_index = 0
selected_color_index = 15 # Default to white
num_tiles_in_set = 1 # Start with one tile
drawing_mode = 'fg' # 'fg' or 'bg' (left/right mouse)
last_drawn_pixel = None # To avoid redundant draws on drag

# --- Application Class ---
class TileEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MSX SCREEN 4 Tile Editor")
        self.root.resizable(False, False) # Usually better for fixed layouts

        self.create_menu()
        self.create_widgets()
        self.update_all_displays()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Tileset", command=self.new_tileset)
        file_menu.add_command(label="Open Tileset (.SC4Tiles)...", command=self.open_tileset)
        file_menu.add_command(label="Save Tileset (.SC4Tiles)...", command=self.save_tileset)
        file_menu.add_separator()
        file_menu.add_command(label="Set Tileset Size...", command=self.set_tileset_size)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Clear Current Tile", command=self.clear_current_tile)
        # Add Copy/Paste later if needed

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Left Column: Editor and Attributes ---
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.N, padx=(0, 10))

        # Editor Canvas
        editor_frame = ttk.LabelFrame(left_frame, text="Tile Editor (Left: FG, Right: BG)")
        editor_frame.grid(row=0, column=0, pady=(0, 10))
        self.editor_canvas = tk.Canvas(
            editor_frame,
            width=TILE_WIDTH * EDITOR_PIXEL_SIZE,
            height=TILE_HEIGHT * EDITOR_PIXEL_SIZE,
            bg="grey"
        )
        self.editor_canvas.grid(row=0, column=0)
        self.editor_canvas.bind("<Button-1>", self.handle_editor_click)
        self.editor_canvas.bind("<B1-Motion>", self.handle_editor_drag)
        self.editor_canvas.bind("<Button-3>", self.handle_editor_click) # Right click
        self.editor_canvas.bind("<B3-Motion>", self.handle_editor_drag) # Right click drag

        # Attribute Editor
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


        # --- Right Column: Palette and Tileset Viewer ---
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=tk.N)

        # Palette
        palette_frame = ttk.LabelFrame(right_frame, text="Color Palette")
        palette_frame.grid(row=0, column=0, pady=(0, 10), sticky=tk.N)
        self.palette_labels = []
        self.palette_canvas = tk.Canvas(
            palette_frame,
            width=4 * (PALETTE_SQUARE_SIZE + 2), # 4 columns
            height=4 * (PALETTE_SQUARE_SIZE + 2), # 4 rows
            borderwidth=0, highlightthickness=0
            )
        self.palette_canvas.grid(row=0, column=0)
        self.palette_canvas.bind("<Button-1>", self.handle_palette_click)

        for i in range(16):
            row, col = divmod(i, 4)
            x1 = col * (PALETTE_SQUARE_SIZE + 2) + 1
            y1 = row * (PALETTE_SQUARE_SIZE + 2) + 1
            x2 = x1 + PALETTE_SQUARE_SIZE
            y2 = y1 + PALETTE_SQUARE_SIZE
            rect = self.palette_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=MSX_COLORS[i],
                outline="grey", width=1, tags=f"pal_{i}"
                )
            self.palette_labels.append(rect)


        # Tileset Viewer
        viewer_frame = ttk.LabelFrame(right_frame, text="Tileset")
        viewer_frame.grid(row=1, column=0, sticky=(tk.N, tk.W, tk.E))

        viewer_canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + 1) + 1
        num_rows_in_viewer = (MAX_TILES + NUM_TILES_ACROSS - 1) // NUM_TILES_ACROSS
        viewer_canvas_height = num_rows_in_viewer * (VIEWER_TILE_SIZE + 1) + 1

        # Add Scrollbars if viewer height is large
        viewer_hbar = ttk.Scrollbar(viewer_frame, orient=tk.HORIZONTAL)
        viewer_vbar = ttk.Scrollbar(viewer_frame, orient=tk.VERTICAL)

        self.tileset_canvas = tk.Canvas(
            viewer_frame,
            width=min(viewer_canvas_width, 500), # Limit initial width
            height=min(viewer_canvas_height, 400), # Limit initial height
            bg="lightgrey",
            scrollregion=(0, 0, viewer_canvas_width, viewer_canvas_height),
            xscrollcommand=viewer_hbar.set,
            yscrollcommand=viewer_vbar.set
        )

        viewer_hbar.config(command=self.tileset_canvas.xview)
        viewer_vbar.config(command=self.tileset_canvas.yview)

        self.tileset_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        viewer_vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        viewer_hbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        viewer_frame.grid_rowconfigure(0, weight=1)
        viewer_frame.grid_columnconfigure(0, weight=1)


        self.tileset_canvas.bind("<Button-1>", self.handle_tileset_click)

        # Info label
        self.info_label = ttk.Label(right_frame, text=f"Tile: {current_tile_index}/{num_tiles_in_set-1}")
        self.info_label.grid(row=2, column=0, sticky=tk.W, pady=(5,0))


    # --- Drawing and Update Functions ---

    def update_all_displays(self):
        self.draw_editor_canvas()
        self.draw_attribute_editor()
        self.draw_palette()
        self.draw_tileset_viewer()
        self.update_info_label()

    def draw_editor_canvas(self):
        self.editor_canvas.delete("all")
        pattern = tileset_patterns[current_tile_index]
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]
            fg_color = MSX_COLORS[fg_index]
            bg_color = MSX_COLORS[bg_index]
            for c in range(TILE_WIDTH):
                pixel_val = pattern[r][c]
                color = fg_color if pixel_val == 1 else bg_color

                x1 = c * EDITOR_PIXEL_SIZE
                y1 = r * EDITOR_PIXEL_SIZE
                x2 = x1 + EDITOR_PIXEL_SIZE
                y2 = y1 + EDITOR_PIXEL_SIZE
                self.editor_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color, outline="darkgrey", width=1
                )

    def draw_attribute_editor(self):
        colors = tileset_colors[current_tile_index]
        for r in range(TILE_HEIGHT):
            fg_index, bg_index = colors[r]
            self.attr_fg_labels[r].config(bg=MSX_COLORS[fg_index])
            self.attr_bg_labels[r].config(bg=MSX_COLORS[bg_index])
            # Set text color for contrast (simple black/white)
            self.attr_fg_labels[r].config(fg=self.get_contrast_color(MSX_COLORS[fg_index]))
            self.attr_bg_labels[r].config(fg=self.get_contrast_color(MSX_COLORS[bg_index]))


    def draw_palette(self):
        # Deselect old
        self.palette_canvas.itemconfig(tk.ALL, outline="grey", width=1)
        # Select new
        if 0 <= selected_color_index < 16:
             tag = f"pal_{selected_color_index}"
             self.palette_canvas.itemconfig(tag, outline="red", width=2)


    def draw_tileset_viewer(self):
        global num_tiles_in_set
        self.tileset_canvas.delete("all")
        padding = 1 # Padding between tiles

        max_rows = (num_tiles_in_set + NUM_TILES_ACROSS - 1) // NUM_TILES_ACROSS
        canvas_height = max_rows * (VIEWER_TILE_SIZE + padding) + padding
        canvas_width = NUM_TILES_ACROSS * (VIEWER_TILE_SIZE + padding) + padding
        self.tileset_canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))


        for i in range(num_tiles_in_set):
            tile_r, tile_c = divmod(i, NUM_TILES_ACROSS)
            pattern = tileset_patterns[i]
            colors = tileset_colors[i]

            base_x = tile_c * (VIEWER_TILE_SIZE + padding) + padding
            base_y = tile_r * (VIEWER_TILE_SIZE + padding) + padding

            # Draw the small tile preview
            # For efficiency, draw 8 rectangles (one per row's BG color)
            # Then draw individual FG pixels on top
            for r in range(TILE_HEIGHT):
                fg_index, bg_index = colors[r]
                bg_color = MSX_COLORS[bg_index]
                fg_color = MSX_COLORS[fg_index]

                # Draw BG color for the whole row segment
                pixel_h = VIEWER_TILE_SIZE / TILE_HEIGHT
                y1 = base_y + r * pixel_h
                y2 = y1 + pixel_h
                self.tileset_canvas.create_rectangle(
                    base_x, y1, base_x + VIEWER_TILE_SIZE, y2,
                    fill=bg_color, outline="" # No outline needed for bg fill
                )

                # Draw FG pixels
                pixel_w = VIEWER_TILE_SIZE / TILE_WIDTH
                for c in range(TILE_WIDTH):
                     if pattern[r][c] == 1:
                         x1 = base_x + c * pixel_w
                         x2 = x1 + pixel_w
                         self.tileset_canvas.create_rectangle(
                             x1, y1, x2, y2,
                             fill=fg_color, outline=""
                         )


            # Draw border around the tile
            self.tileset_canvas.create_rectangle(
                base_x - padding/2, base_y - padding/2,
                base_x + VIEWER_TILE_SIZE + padding/2, base_y + VIEWER_TILE_SIZE + padding/2,
                outline="grey", width=1, tags=f"tile_{i}"
            )

        # Highlight selected tile
        if 0 <= current_tile_index < num_tiles_in_set:
            tag = f"tile_{current_tile_index}"
            self.tileset_canvas.itemconfig(tag, outline="red", width=2)

    def update_info_label(self):
         self.info_label.config(text=f"Tile: {current_tile_index}/{num_tiles_in_set-1}")

    def get_contrast_color(self, hex_color):
        """Chooses black or white text for contrast."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # Simple luminance calculation
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#000000" # Default fallback

    # --- Event Handlers ---

    def handle_editor_click(self, event):
        global last_drawn_pixel
        c = event.x // EDITOR_PIXEL_SIZE
        r = event.y // EDITOR_PIXEL_SIZE

        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            # Determine draw mode based on button
            # Button-1 = Left (FG), Button-3 = Right (BG)
            pixel_value = 1 if event.num == 1 else 0

            pattern = tileset_patterns[current_tile_index]
            if pattern[r][c] != pixel_value: # Only update if changed
                pattern[r][c] = pixel_value
                self.draw_editor_canvas() # Redraw big tile
                self.draw_tileset_viewer() # Redraw small tile preview
            last_drawn_pixel = (r, c)


    def handle_editor_drag(self, event):
        global last_drawn_pixel
        c = event.x // EDITOR_PIXEL_SIZE
        r = event.y // EDITOR_PIXEL_SIZE

        if 0 <= r < TILE_HEIGHT and 0 <= c < TILE_WIDTH:
            if (r, c) != last_drawn_pixel: # Only draw if moved to new pixel
                 # Determine draw mode based on button state
                 # Check event.state for button pressed (tricky, rely on initial click button)
                 # A simpler way: use a variable set on ButtonPress
                 # For now, assume drag follows the button that initiated it
                 # For simplicity, check event.state & 0x100 for Button-1, & 0x400 for Button-3
                pixel_value = 1 if event.state & 0x100 else (0 if event.state & 0x400 else -1)
                if pixel_value != -1:
                    pattern = tileset_patterns[current_tile_index]
                    if pattern[r][c] != pixel_value:
                        pattern[r][c] = pixel_value
                        self.draw_editor_canvas()
                        self.draw_tileset_viewer()
                    last_drawn_pixel = (r, c)


    def handle_palette_click(self, event):
        global selected_color_index
        # Find clicked rectangle
        item = self.palette_canvas.find_closest(event.x, event.y)[0]
        tags = self.palette_canvas.gettags(item) # Find tags associated with item
        for tag in tags:
            if tag.startswith("pal_"):
                try:
                    selected_color_index = int(tag.split("_")[1])
                    self.draw_palette() # Update selection highlight
                    break
                except (IndexError, ValueError):
                    pass # Clicked outside or on something unexpected


    def set_row_color(self, row, fg_or_bg):
        global tileset_colors
        if not (0 <= selected_color_index < 16):
             messagebox.showwarning("No Color", "Please select a color from the palette first.")
             return
        if 0 <= row < TILE_HEIGHT:
            current_fg, current_bg = tileset_colors[current_tile_index][row]
            if fg_or_bg == 'fg':
                if current_fg != selected_color_index:
                    tileset_colors[current_tile_index][row] = (selected_color_index, current_bg)
            else: # 'bg'
                if current_bg != selected_color_index:
                    tileset_colors[current_tile_index][row] = (current_fg, selected_color_index)

            self.draw_attribute_editor() # Update FG/BG swatches
            self.draw_editor_canvas()    # Redraw editor with new colors
            self.draw_tileset_viewer()   # Redraw tile preview


    def handle_tileset_click(self, event):
        global current_tile_index, num_tiles_in_set
        padding = 1
        col = int(event.x // (VIEWER_TILE_SIZE + padding))
        row = int(event.y // (VIEWER_TILE_SIZE + padding))
        clicked_index = row * NUM_TILES_ACROSS + col

        if 0 <= clicked_index < num_tiles_in_set:
            current_tile_index = clicked_index
            self.update_all_displays() # Redraw everything for the new tile


    # --- File Menu Commands ---
    def new_tileset(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        if messagebox.askokcancel("New Tileset", "Discard current tileset and create a new one?"):
            tileset_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            tileset_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
            current_tile_index = 0
            num_tiles_in_set = 1 # Start with one default tile
            self.update_all_displays()
            self.root.title("MSX SCREEN 4 Tile Editor - Untitled")


    def set_tileset_size(self):
        global num_tiles_in_set
        new_size_str = tk.simpledialog.askstring("Set Tileset Size",
                                                f"Enter number of tiles (1-{MAX_TILES}):",
                                                initialvalue=str(num_tiles_in_set))
        if new_size_str:
            try:
                new_size = int(new_size_str)
                if 1 <= new_size <= MAX_TILES:
                    if new_size < num_tiles_in_set:
                        if not messagebox.askokcancel("Reduce Size", f"Reducing size to {new_size} will discard tiles {new_size} to {num_tiles_in_set-1}. Proceed?"):
                            return
                    num_tiles_in_set = new_size
                    # Adjust current_tile_index if it's now out of bounds
                    if current_tile_index >= num_tiles_in_set:
                        current_tile_index = num_tiles_in_set - 1
                    self.update_all_displays()
                else:
                    messagebox.showerror("Invalid Size", f"Size must be between 1 and {MAX_TILES}.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")


    def save_tileset(self):
        global num_tiles_in_set
        filepath = filedialog.asksaveasfilename(
            defaultextension=".SC4Tiles",
            filetypes=[("MSX SCREEN 4 Tileset", "*.SC4Tiles"), ("All Files", "*.*")],
            title="Save Tileset As..."
        )
        if not filepath:
            return

        try:
            with open(filepath, 'wb') as f:
                # Write number of tiles
                f.write(struct.pack('B', num_tiles_in_set)) # Unsigned char (1 byte)

                for i in range(num_tiles_in_set):
                    # Write pattern data (8 bytes)
                    pattern = tileset_patterns[i]
                    for r in range(TILE_HEIGHT):
                        byte_val = 0
                        for c in range(TILE_WIDTH):
                            if pattern[r][c] == 1:
                                byte_val |= (1 << (7 - c)) # MSB is left pixel
                        f.write(struct.pack('B', byte_val))

                    # Write color data (8 bytes)
                    colors = tileset_colors[i]
                    for r in range(TILE_HEIGHT):
                         fg, bg = colors[r]
                         # Combine nibbles: FG in high, BG in low
                         color_byte = ((fg & 0x0F) << 4) | (bg & 0x0F)
                         f.write(struct.pack('B', color_byte))

            self.root.title(f"MSX SCREEN 4 Tile Editor - {os.path.basename(filepath)}")
            messagebox.showinfo("Save Successful", f"Tileset saved to {filepath}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{e}")


    def open_tileset(self):
        global tileset_patterns, tileset_colors, current_tile_index, num_tiles_in_set
        filepath = filedialog.askopenfilename(
            filetypes=[("MSX SCREEN 4 Tileset", "*.SC4Tiles"), ("All Files", "*.*")],
            title="Open Tileset"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'rb') as f:
                 # Read number of tiles
                num_tiles_byte = f.read(1)
                if not num_tiles_byte:
                    raise ValueError("File is empty or invalid.")
                loaded_num_tiles = struct.unpack('B', num_tiles_byte)[0]

                if loaded_num_tiles == 0 or loaded_num_tiles > MAX_TILES:
                    raise ValueError(f"Invalid number of tiles in file: {loaded_num_tiles}")

                # Prepare new data structures (or clear existing ones)
                new_patterns = [[[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]
                new_colors = [[(15, 1) for _ in range(TILE_HEIGHT)] for _ in range(MAX_TILES)]

                for i in range(loaded_num_tiles):
                    # Read pattern data (8 bytes)
                    for r in range(TILE_HEIGHT):
                        pattern_byte = f.read(1)
                        if not pattern_byte: raise EOFError(f"Unexpected end of file while reading pattern for tile {i}, row {r}")
                        byte_val = struct.unpack('B', pattern_byte)[0]
                        for c in range(TILE_WIDTH):
                            if (byte_val >> (7 - c)) & 1:
                                new_patterns[i][r][c] = 1
                            else:
                                new_patterns[i][r][c] = 0

                     # Read color data (8 bytes)
                    for r in range(TILE_HEIGHT):
                         color_byte = f.read(1)
                         if not color_byte: raise EOFError(f"Unexpected end of file while reading colors for tile {i}, row {r}")
                         byte_val = struct.unpack('B', color_byte)[0]
                         fg = (byte_val >> 4) & 0x0F
                         bg = byte_val & 0x0F
                         new_colors[i][r] = (fg, bg)

                # Successfully loaded, now update global state
                tileset_patterns = new_patterns
                tileset_colors = new_colors
                num_tiles_in_set = loaded_num_tiles
                current_tile_index = 0 # Reset to first tile
                self.update_all_displays()
                self.root.title(f"MSX SCREEN 4 Tile Editor - {os.path.basename(filepath)}")
                messagebox.showinfo("Open Successful", f"Loaded {num_tiles_in_set} tiles from {filepath}")


        except FileNotFoundError:
             messagebox.showerror("Open Error", f"File not found:\n{filepath}")
        except EOFError as e:
             messagebox.showerror("Open Error", f"File is incomplete or corrupt:\n{e}")
        except Exception as e:
             messagebox.showerror("Open Error", f"Failed to open or parse file:\n{e}")


    # --- Edit Menu Commands ---
    def clear_current_tile(self):
        global tileset_patterns, tileset_colors
        if messagebox.askokcancel("Clear Tile", f"Clear pattern and reset colors for tile {current_tile_index}?"):
            # Clear pattern
            tileset_patterns[current_tile_index] = [[0] * TILE_WIDTH for _ in range(TILE_HEIGHT)]
            # Reset colors to default (e.g., white on black)
            tileset_colors[current_tile_index] = [(15, 1) for _ in range(TILE_HEIGHT)]
            self.update_all_displays()


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TileEditorApp(root)
    root.mainloop()