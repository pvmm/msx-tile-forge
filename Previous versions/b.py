import tkinter as tk
from tkinter import ttk
import random

# --- Constants (same as before) ---
SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW = 2
PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT = 64
MIN_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH = 8
MAX_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH = 256
PREVIEW_IMAGE_FIXED_TARGET_HEIGHT = PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW
ROW_PADDING = 4
TREEVIEW_ROW_HEIGHT_STYLE = PREVIEW_IMAGE_FIXED_TARGET_HEIGHT + ROW_PADDING

INITIAL_COL0_WIDTH = 150
COL0_INTERNAL_LEFT_OFFSET_GUESS = 20 
MIN_IMAGE_AREA_WIDTH_COL0 = (8 * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW)
MIN_COL0_WIDTH_STYLE = MIN_IMAGE_AREA_WIDTH_COL0 + COL0_INTERNAL_LEFT_OFFSET_GUESS
INITIAL_DATA_COL_WIDTH = 80

DUMMY_SUPERTILE_DATA = []
for i in range(30):
    current_st_msx_pixel_width = random.randint(
        MIN_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH, MAX_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH
    )
    DUMMY_SUPERTILE_DATA.append((i, i * 3 + 5, current_st_msx_pixel_width))

class TestApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Treeview Test v7.1 - Stateful Drag Refresh")
        self.root.geometry("700x550")
        self._image_references = []
        self._refresh_timer_id = None
        
        self._is_dragging_col_separator = False # Flag to track drag state
        self._col_being_dragged = None # To store which column ID is being dragged
        self._col0_width_at_drag_start = 0 # Store width at start of drag

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.style = ttk.Style()
        self.style.configure('Treeview', rowheight=TREEVIEW_ROW_HEIGHT_STYLE)
        self.style.map('Treeview', 
                       background=[('selected', self.style.lookup('Treeview', 'background'))],
                       foreground=[('selected', self.style.lookup('Treeview', 'foreground'))])

        self.tree = ttk.Treeview(
            main_frame,
            columns=("index_col", "usage_col"),
            show="tree headings",
            style='Treeview'
        )

        self.tree.column("#0", width=INITIAL_COL0_WIDTH, minwidth=MIN_COL0_WIDTH_STYLE, stretch=tk.YES, anchor=tk.W)
        self.tree.heading("#0", text="Supertile", command=lambda: self.sort_by_column_test("#0"))
        self.tree.column("index_col", width=INITIAL_DATA_COL_WIDTH, minwidth=50, stretch=tk.YES, anchor=tk.CENTER) 
        self.tree.heading("index_col", text="Index", command=lambda: self.sort_by_column_test("index_col"))
        self.tree.column("usage_col", width=INITIAL_DATA_COL_WIDTH, minwidth=60, stretch=tk.YES, anchor=tk.CENTER)
        self.tree.heading("usage_col", text="Usage Count", command=lambda: self.sort_by_column_test("usage_col"))

        tree_v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_v_scrollbar.set)
        tree_h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_h_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_v_scrollbar.grid(row=0, column=1, sticky="ns")
        tree_h_scrollbar.grid(row=1, column=0, sticky="ew")

        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        self.root.after(20, self.populate_treeview)

        # --- Bindings for dynamic refresh ---
        self.tree.bind("<ButtonPress-1>", self.on_tree_button_press) # New: Detect start of drag
        # Bind ButtonRelease to the root window to catch it even if mouse leaves tree
        self.root.bind("<ButtonRelease-1>", self.on_root_button_release, add='+') # Use add='+'
        self.tree.bind("<Configure>", self.on_tree_configure_debounced)


    def on_tree_configure_debounced(self, event=None):
        if self._refresh_timer_id:
            self.root.after_cancel(self._refresh_timer_id)
        self._refresh_timer_id = self.root.after(100, self.do_populate_if_tree_valid)

    def on_tree_button_press(self, event):
        """Handles ButtonPress-1 on the Treeview to detect start of column drag."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            self._is_dragging_col_separator = True
            # identify_column(x) gives the column to the left of the separator clicked (or #0)
            # For the separator to the right of column "#0", identify_column might give "#0"
            # For the separator to the right of "index_col", it might give "index_col".
            # We need to know if the *width* of col #0 could change.
            # A drag on the separator *right* of column #0 changes column #0's width.
            # A drag on the separator *right* of column "index_col" changes "index_col"'s width.
            
            # If the separator is immediately to the right of column #0
            col_id_left_of_sep = self.tree.identify_column(event.x)

            # Heuristic: if the click is near the right edge of col #0's current width
            col0_current_width = self.tree.column("#0", "width")
            # We need to map event.x (widget coords) to the logical start of columns.
            # This is getting complicated quickly.
            # Let's simplify: if *any* separator is dragged, we'll check col #0's width on release.
            # A more precise method would involve more detailed coordinate geometry.
            print(f"Drag started on a separator (near column: {col_id_left_of_sep}).")
            self._col0_width_at_drag_start = self.tree.column("#0", "width") # Store current width
        else:
            self._is_dragging_col_separator = False


    def on_root_button_release(self, event):
        """Handles ButtonRelease-1 on the root window to finalize column drag."""
        # print(f"Root <ButtonRelease-1>: Dragging flag was {self._is_dragging_col_separator}") #Debug
        if self._is_dragging_col_separator:
            self._is_dragging_col_separator = False # Reset flag
            print("Column drag ended (release detected on root). Checking Col #0 width.")
            
            # Use after_idle to give Tkinter time to update the column width internally
            # after the drag operation finishes.
            self.root.after_idle(self.check_col0_width_and_refresh_after_drag)

    def check_col0_width_and_refresh_after_drag(self):
        """Called after_idle post-drag to check width and refresh if needed."""
        if not self.tree.winfo_exists(): return

        current_col0_width = self.tree.column("#0", "width")
        if current_col0_width != self._col0_width_at_drag_start:
            print(f"Col #0 width changed by drag: {self._col0_width_at_drag_start} -> {current_col0_width}. Refreshing.")
            # We don't need to schedule another debounced one here,
            # as this is the *end* of a user action.
            self.do_populate_if_tree_valid()
        else:
            print(f"Col #0 width ({current_col0_width}) unchanged after drag. No refresh.")


    def do_populate_if_tree_valid(self):
        if self.tree and self.tree.winfo_exists() and self.tree.winfo_ismapped():
            self.populate_treeview()
        else:
            print("Skipping populate: Tree not valid or not mapped.")

    def create_cropped_image_fixed_scale(self, supertile_msx_w, supertile_msx_h, 
                                         target_image_area_width, unique_id):
        # (This function remains the same)
        full_scaled_img_w = supertile_msx_w * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW
        full_scaled_img_h = PREVIEW_IMAGE_FIXED_TARGET_HEIGHT
        full_scaled_img_w = max(1, int(full_scaled_img_w))

        temp_full_photo = tk.PhotoImage(width=full_scaled_img_w, height=full_scaled_img_h)
        colors = ["#FFD700", "#FFEC8B", "#FFFFE0", "#FAFAD2", "#EEE8AA", "#F0E68C"]
        fill_color = colors[unique_id % len(colors)]
        
        if full_scaled_img_w > 0 and full_scaled_img_h > 0:
            temp_full_photo.put("#333333", to=(0, 0, full_scaled_img_w, full_scaled_img_h))
            if full_scaled_img_w > 2 and full_scaled_img_h > 2:
                 temp_full_photo.put(fill_color, to=(1, 1, full_scaled_img_w - 1, full_scaled_img_h - 1))
            else:
                 temp_full_photo.put(fill_color, to=(0,0, full_scaled_img_w, full_scaled_img_h))

        final_photo_width = max(1, int(target_image_area_width))
        final_photo_height = full_scaled_img_h
        final_photo = tk.PhotoImage(width=final_photo_width, height=final_photo_height)
        
        default_bg_name = self.style.lookup('Treeview', 'background')
        hex_bg_color = "#F0F0F0" 
        try:
            rgb_tuple = self.root.winfo_rgb(default_bg_name) 
            r_8bit, g_8bit, b_8bit = rgb_tuple[0]//256, rgb_tuple[1]//256, rgb_tuple[2]//256
            hex_bg_color = f"#{r_8bit:02x}{g_8bit:02x}{b_8bit:02x}"
        except tk.TclError:
            pass

        final_photo.put(hex_bg_color, to=(0,0, final_photo_width, final_photo_height))

        width_to_copy_from_source = min(temp_full_photo.width(), final_photo.width())
        height_to_copy_from_source = final_photo_height

        if width_to_copy_from_source > 0 and height_to_copy_from_source > 0:
            try:
                final_photo.tk.call(final_photo, 'copy', temp_full_photo,
                                    '-from', 0, 0, width_to_copy_from_source, height_to_copy_from_source,
                                    '-to', 0, 0)
            except tk.TclError as e:
                print(f"Error during PhotoImage copy: {e}")
        
        return final_photo

    def populate_treeview(self):
        if not self.tree or not self.tree.winfo_exists():
            print("Populate called, but tree does not exist.")
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        self._image_references.clear()

        total_col0_width = self.tree.column("#0", "width")
        image_area_width_for_col0 = max(1, total_col0_width - COL0_INTERNAL_LEFT_OFFSET_GUESS)
        
        print(f"Populating. Total Col #0 Width: {total_col0_width}px. "
              f"Target Image Area Width: {image_area_width_for_col0}px")

        for i, (idx, usage, st_msx_w) in enumerate(DUMMY_SUPERTILE_DATA):
            photo_img = self.create_cropped_image_fixed_scale(
                st_msx_w,
                PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT,
                image_area_width_for_col0,
                i
            )
            self._image_references.append(photo_img)

            self.tree.insert(
                parent="",
                index="end",
                iid=f"item_{idx}",
                text="", 
                image=photo_img,
                values=(f"  {idx}", usage),
                tags=('data_row',)
            )
        
        try:
            row_bg = self.style.lookup('Treeview', 'background')
            self.tree.tag_configure('data_row', background=row_bg)
        except tk.TclError:
            pass

    def sort_by_column_test(self, col_id):
        print(f"Placeholder: Sort by column '{col_id}'")

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()