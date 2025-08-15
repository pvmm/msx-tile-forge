import tkinter as tk
from tkinter import ttk
import random

# --- Constants ---
SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW = 2
PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT = 64 # MSX Pixels (e.g., 8 base tiles high)
# For testing, allow supertiles to have varying widths in MSX pixels
MIN_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH = 8   # e.g., 1 base tile wide
MAX_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH = 128 # e.g., 16 base tiles wide (reduced for better visibility in test)

# Calculated Preview Image Target Height (screen pixels)
PREVIEW_IMAGE_FIXED_TARGET_HEIGHT = PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW
ROW_PADDING = 4 # Visual padding around the image in the row
TREEVIEW_ROW_HEIGHT_STYLE = PREVIEW_IMAGE_FIXED_TARGET_HEIGHT + ROW_PADDING

# Initial width for column #0 (Supertile image) in screen pixels
INITIAL_COL0_WIDTH = 100
# Estimated space for tree indicator and padding to the left of image in col #0 (screen pixels)
# Adjust this based on your OS/theme for best visual fit
COL0_INTERNAL_LEFT_OFFSET_GUESS = 20
# Minimum screen pixel width for the actual image content area in column #0
MIN_IMAGE_CONTENT_AREA_WIDTH_COL0 = MIN_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW
# Minimum total width for column #0, including the offset guess
MIN_COL0_TOTAL_WIDTH_STYLE = MIN_IMAGE_CONTENT_AREA_WIDTH_COL0 + COL0_INTERNAL_LEFT_OFFSET_GUESS

INITIAL_DATA_COL_WIDTH = 70 # For Index and Usage columns

# Dummy data: (unique_id, usage_count, supertile_msx_pixel_width)
DUMMY_SUPERTILE_DATA = []
for i in range(25): # Number of test items
    current_st_msx_pixel_width = random.randint(
        MIN_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH, MAX_PROJECT_SUPERTILE_MSX_PIXEL_WIDTH
    )
    # All test supertiles will have the same MSX pixel height
    DUMMY_SUPERTILE_DATA.append((i, random.randint(0,50), current_st_msx_pixel_width))

class TestApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Treeview Test v7.2 - Dynamic Image Cropping")
        self.root.geometry("600x500") # Adjusted initial size

        self._image_references = []         # To prevent PhotoImage garbage collection
        self._treeview_refresh_timer_id = None # For debouncing <Configure> events
        
        self._is_dragging_col_separator = False # True if user is dragging a column separator
        self._col0_width_at_drag_start = 0    # Width of col #0 when drag started

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.style = ttk.Style()
        self.style.configure('Treeview', rowheight=TREEVIEW_ROW_HEIGHT_STYLE)
        # Optional: Make selected row background same as normal to focus on image
        # self.style.map('Treeview', 
        #                background=[('selected', self.style.lookup('Treeview', 'background'))],
        #                foreground=[('selected', self.style.lookup('Treeview', 'foreground'))])

        self.tree = ttk.Treeview(
            main_frame,
            columns=("index_col", "usage_col"),
            show="tree headings", # Show tree column (#0) and data column headings
            style='Treeview'
        )

        # Column #0: Supertile Image
        self.tree.column("#0", width=INITIAL_COL0_WIDTH, minwidth=MIN_COL0_TOTAL_WIDTH_STYLE, 
                         stretch=tk.YES, anchor=tk.W)
        self.tree.heading("#0", text="Supertile", command=lambda: self.sort_by_column_test("#0"))

        # Column 1: Index
        self.tree.column("index_col", width=INITIAL_DATA_COL_WIDTH, minwidth=50, 
                         stretch=tk.YES, anchor=tk.CENTER) 
        self.tree.heading("index_col", text="Index", command=lambda: self.sort_by_column_test("index_col"))
        
        # Column 2: Usage Count
        self.tree.column("usage_col", width=INITIAL_DATA_COL_WIDTH, minwidth=60,
                         stretch=tk.YES, anchor=tk.CENTER)
        self.tree.heading("usage_col", text="Usage Count", command=lambda: self.sort_by_column_test("usage_col"))

        # Scrollbars
        tree_v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_v_scrollbar.set)
        tree_h_scrollbar = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_h_scrollbar.set)

        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_v_scrollbar.grid(row=0, column=1, sticky="ns")
        tree_h_scrollbar.grid(row=1, column=0, sticky="ew")

        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Initial population: deferred to allow main window to draw and establish initial sizes
        self.root.after(50, self.populate_treeview_if_ready) # Slightly longer delay

        # --- Event Bindings for Dynamic Refresh ---
        self.tree.bind("<ButtonPress-1>", self.on_tree_button_press)
        self.root.bind("<ButtonRelease-1>", self.on_root_button_release, add='+') # Catch release anywhere
        self.tree.bind("<Configure>", self.on_tree_configure_debounced) # Treeview's own resize

    def populate_treeview_if_ready(self):
        """Wrapper to ensure treeview is valid before populating."""
        if self.tree and self.tree.winfo_exists() and self.tree.winfo_ismapped():
            self.populate_treeview()
        else:
            # If not ready, try again shortly. This handles race conditions on startup.
            print("Tree not ready for initial populate, retrying...")
            self.root.after(100, self.populate_treeview_if_ready)

    def on_tree_configure_debounced(self, event=None):
        """Debounced refresh when the Treeview widget itself is resized (e.g., main window resize)."""
        if self._treeview_refresh_timer_id:
            self.root.after_cancel(self._treeview_refresh_timer_id)
        self._treeview_refresh_timer_id = self.root.after(100, self.populate_treeview_if_ready)
        # print("Tree <Configure> event - refresh scheduled.")


    def on_tree_button_press(self, event):
        """Handles ButtonPress-1 on the Treeview to detect start of column drag."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            self._is_dragging_col_separator = True
            self._col0_width_at_drag_start = self.tree.column("#0", "width")
            # print(f"Drag started on separator. Col #0 initial width: {self._col0_width_at_drag_start}")
        else:
            self._is_dragging_col_separator = False

    def on_root_button_release(self, event):
        """Handles ButtonRelease-1 on the root window to finalize column drag."""
        if self._is_dragging_col_separator:
            self._is_dragging_col_separator = False
            # print("Column drag ended (release on root). Scheduling width check.")
            # Use after_idle to ensure column width has settled in Tkinter
            self.root.after_idle(self.check_col0_width_and_refresh_after_drag)

    def check_col0_width_and_refresh_after_drag(self):
        """Called after_idle post-drag to check column #0 width and refresh if it changed."""
        if not self.tree or not self.tree.winfo_exists(): return

        current_col0_width = self.tree.column("#0", "width")
        if current_col0_width != self._col0_width_at_drag_start:
            print(f"Col #0 width changed by drag: {self._col0_width_at_drag_start} -> {current_col0_width}. Refreshing.")
            self.populate_treeview_if_ready() # This will re-crop images
        # else:
            # print(f"Col #0 width ({current_col0_width}) unchanged after drag.")


    def create_cropped_image_fixed_scale(self, supertile_msx_w, supertile_msx_h, 
                                         target_image_content_width, unique_id):
        """
        Creates a PhotoImage for display in Treeview column #0.
        The PhotoImage width will be target_image_content_width.
        The PhotoImage height will be PREVIEW_IMAGE_FIXED_TARGET_HEIGHT.
        The supertile content is rendered at fixed scale and then cropped/copied.
        """
        # 1. Calculate full scaled dimensions of the supertile content
        full_scaled_content_w = supertile_msx_w * SCREEN_PIXELS_PER_MSX_PIXEL_IN_PREVIEW
        full_scaled_content_h = PREVIEW_IMAGE_FIXED_TARGET_HEIGHT # Height is fixed by design
        full_scaled_content_w = max(1, int(full_scaled_content_w))

        # 2. Create a temporary PhotoImage for the full scaled content
        temp_full_photo = tk.PhotoImage(width=full_scaled_content_w, height=full_scaled_content_h)
        
        # Simple distinct color based on unique_id for visualization
        colors = ["#6A5ACD", "#7B68EE", "#8A2BE2", "#9370DB", "#9932CC", "#BA55D3"]
        fill_color = colors[unique_id % len(colors)]
        
        if full_scaled_content_w > 0 and full_scaled_content_h > 0:
            temp_full_photo.put("#101010", to=(0, 0, full_scaled_content_w, full_scaled_content_h)) # Dark border
            if full_scaled_content_w > 2 and full_scaled_content_h > 2: # Inner fill if space
                 temp_full_photo.put(fill_color, to=(1, 1, full_scaled_content_w - 1, full_scaled_content_h - 1))
            else: # Too small for border, just fill
                 temp_full_photo.put(fill_color, to=(0,0, full_scaled_content_w, full_scaled_content_h))

        # 3. Create the final PhotoImage with the target display width for the image area
        #    (this width is the total column width minus the guessed left offset)
        final_photo_width = max(1, int(target_image_content_width))
        final_photo_height = full_scaled_content_h # Height is always fixed for the row

        final_photo = tk.PhotoImage(width=final_photo_width, height=final_photo_height)
        
        # 4. Fill final_photo with a background color (e.g., Treeview's default)
        default_bg_name = self.style.lookup('Treeview', 'background')
        hex_bg_color = "#F0F0F0" # Fallback
        try:
            rgb_tuple = self.root.winfo_rgb(default_bg_name) 
            r, g, b = rgb_tuple[0]//256, rgb_tuple[1]//256, rgb_tuple[2]//256
            hex_bg_color = f"#{r:02x}{g:02x}{b:02x}"
        except tk.TclError: pass # Use fallback if lookup fails

        final_photo.put(hex_bg_color, to=(0,0, final_photo_width, final_photo_height))

        # 5. Copy the relevant (potentially cropped) part from temp_full_photo to final_photo
        width_to_copy = min(full_scaled_content_w, final_photo_width)
        height_to_copy = final_photo_height # Should be same as full_scaled_content_h

        if width_to_copy > 0 and height_to_copy > 0:
            try:
                final_photo.tk.call(final_photo, 'copy', temp_full_photo,
                                    '-from', 0, 0, width_to_copy, height_to_copy,
                                    '-to', 0, 0)
            except tk.TclError as e:
                print(f"Error during PhotoImage copy: {e}")
        
        return final_photo

    def populate_treeview(self):
        if not self.tree or not self.tree.winfo_exists():
            # print("Populate treeview: Tree widget no longer exists.")
            return

        for i in self.tree.get_children():
            self.tree.delete(i)
        self._image_references.clear()

        total_col0_width = self.tree.column("#0", "width")
        # Calculate the actual width available for the image content itself
        image_content_area_width = max(1, total_col0_width - COL0_INTERNAL_LEFT_OFFSET_GUESS)
        
        # print(f"Populating. Total Col #0 Width: {total_col0_width}px. "
        #       f"Target Image Content Area Width: {image_content_area_width}px")

        for i, (idx, usage, st_msx_w) in enumerate(DUMMY_SUPERTILE_DATA):
            # Pass the calculated image_content_area_width for cropping
            photo_img = self.create_cropped_image_fixed_scale(
                st_msx_w,
                PROJECT_SUPERTILE_MSX_PIXEL_HEIGHT,
                image_content_area_width, 
                i 
            )
            self._image_references.append(photo_img)

            self.tree.insert(
                parent="",
                index="end",
                iid=f"item_{idx}",
                text="", # No text directly in col #0 beside image for this setup
                image=photo_img,
                values=(f"  {idx}", usage) # Data for subsequent columns
            )
        
        try:
            row_bg = self.style.lookup('Treeview', 'background')
            self.tree.tag_configure('data_row', background=row_bg)
        except tk.TclError:
            pass # Style or widget might not be ready in some edge cases

    def sort_by_column_test(self, col_id):
        print(f"Placeholder: Sort by column '{col_id}' (not implemented in test)")

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()