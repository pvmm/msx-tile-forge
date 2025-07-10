#!/usr/bin/env python3

# --- Program Identification ---
SCRIPT_NAME = "MSX Tile Magic"
SCRIPT_VERSION = "0.0.26"

# --- Imports ---
import os
import sys
import argparse
from collections import Counter, defaultdict
import numpy as np
from PIL import Image
from tqdm import tqdm
import multiprocessing
from itertools import combinations
import heapq
import warnings

# --- Global Warning Filter ---
warnings.filterwarnings("ignore", message='.*"Matplotlib" related API features are not available.*')

# --- Optional Dependency Import for Advanced Color Metrics ---
try:
    import colour
    from colour.utilities import ColourUsageWarning
    COLOUR_SCIENCE_AVAILABLE = True
except ImportError:
    COLOUR_SCIENCE_AVAILABLE = False

# --- MSX2 Palette Constants ---
MSX2_MASTER_PALETTE_0_7 = [(r,g,b) for r in range(8) for g in range(8) for b in range(8)]
MSX2_MASTER_PALETTE_0_255 = [(r * 255 // 7, g * 255 // 7, b * 255 // 7) for r, g, b in MSX2_MASTER_PALETTE_0_7]

# --- Splash Screen ---
def print_splash_screen(script_name, script_version):
    COLOR_BLUE_DARK = '\033[34m'
    COLOR_BLUE_BRIGHT = '\033[94m'
    COLOR_ORANGE_DARK = '\033[33m'
    COLOR_ORANGE_BRIGHT = '\033[93m'
    COLOR_TITLE = '\033[1;97m'
    COLOR_VERSION = '\033[97m'
    COLOR_RESET = '\033[0m'

    if not sys.stdout.isatty():
        COLOR_BLUE_DARK = COLOR_BLUE_BRIGHT = COLOR_ORANGE_DARK = ""
        COLOR_ORANGE_BRIGHT = COLOR_TITLE = COLOR_VERSION = COLOR_RESET = ""

    block_char = "\u2588" * 2
    b_dark = f"{COLOR_BLUE_DARK}{block_char}{COLOR_RESET}"
    b_bright = f"{COLOR_BLUE_BRIGHT}{block_char}{COLOR_RESET}"
    o_dark = f"{COLOR_ORANGE_DARK}{block_char}{COLOR_RESET}"
    o_bright = f"{COLOR_ORANGE_BRIGHT}{block_char}{COLOR_RESET}"

    logo_lines = [
        f"{b_dark}{b_bright}{b_bright}{b_dark}",
        f"{b_bright}{o_dark}{o_bright}{b_bright}",
        f"{b_bright}{o_bright}{o_dark}{b_bright}",
        f"{b_dark}{b_bright}{b_bright}{b_dark}"
    ]

    text_lines = [
        f"{COLOR_TITLE}{script_name}{COLOR_RESET} (v{script_version})",
        f"{COLOR_VERSION}MSX Tile Forge suite, version 1.0.0RC8{COLOR_RESET}"
    ]

    print()
    print(f"{logo_lines[0]}")
    print(f"{logo_lines[1]}  {text_lines[0]}")
    print(f"{logo_lines[2]}  {text_lines[1]}")
    print(f"{logo_lines[3]}")
    print("-" * 60)

# --- Color Difference Functions ---
def color_distance_rgb(c1_rgb255, c2_rgb255):
    r1,g1,b1 = c1_rgb255
    r2,g2,b2 = c2_rgb255
    return (r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2

def color_distance_weighted_rgb(c1_rgb255, c2_rgb255):
    r1,g1,b1 = c1_rgb255
    r2,g2,b2 = c2_rgb255
    dr, dg, db = r1-r2, g1-g2, b1-b2
    return (30*dr)**2 + (59*dg)**2 + (11*db)**2

if COLOUR_SCIENCE_AVAILABLE:
    def color_distance_cie76(c1_rgb255, c2_rgb255):
        rgb_array = np.array([c1_rgb255, c2_rgb255]) / 255.0
        xyz_array = colour.sRGB_to_XYZ(rgb_array)
        lab_array = colour.XYZ_to_Lab(xyz_array)
        delta_e = colour.delta_E(lab_array[0], lab_array[1], method='CIE 1976')
        return delta_e.item()

    def color_distance_ciede2000(c1_rgb255, c2_rgb255):
        rgb_array = np.array([c1_rgb255, c2_rgb255]) / 255.0
        xyz_array = colour.sRGB_to_XYZ(rgb_array)
        lab_array = colour.XYZ_to_Lab(xyz_array)
        delta_e = colour.delta_E(lab_array[0], lab_array[1], method='CIE 2000')
        return delta_e.item()

def get_color_distance_function(metric_name):
    if metric_name == 'rgb':
        return color_distance_rgb
    if metric_name == 'weighted-rgb':
        return color_distance_weighted_rgb
    if metric_name == 'cie76':
        return color_distance_cie76
    if metric_name == 'ciede2000':
        return color_distance_ciede2000
    return color_distance_weighted_rgb

# --- Helper Functions ---
def find_closest_msx_color(rgb_tuple_0_255, color_dist_func):
    min_dist = float('inf')
    closest_msx_color_0_7 = (0,0,0)
    for idx, msx_color_candidate in enumerate(MSX2_MASTER_PALETTE_0_255):
        dist = color_dist_func(rgb_tuple_0_255, msx_color_candidate)
        if dist < min_dist:
            min_dist = dist
            closest_msx_color_0_7 = MSX2_MASTER_PALETTE_0_7[idx]
        if dist == 0:
            break
    return closest_msx_color_0_7

def quantize_image_to_msx_colors(image: Image.Image, num_target_colors: int, dither_enabled: bool, color_dist_func):
    if image.mode != 'RGB':
        image = image.convert('RGB')
    try:
        temp_quantized_img = image.quantize(colors=num_target_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    except Exception:
        temp_quantized_img = image.convert('P', palette=Image.Palette.ADAPTIVE, colors=num_target_colors, dither=Image.Dither.NONE)
    
    pil_palette_255_flat = temp_quantized_img.getpalette()
    ideal_colors_255=[]
    if pil_palette_255_flat:
        for i in range(num_target_colors):
            if i*3+2<len(pil_palette_255_flat):
                ideal_colors_255.append((pil_palette_255_flat[i*3], pil_palette_255_flat[i*3+1], pil_palette_255_flat[i*3+2]))

    final_msx_palette_0_7_set=set()
    final_msx_palette_0_7_list=[]
    for r255,g255,b255 in ideal_colors_255:
        msx_color_0_7=find_closest_msx_color((r255,g255,b255), color_dist_func)
        if msx_color_0_7 not in final_msx_palette_0_7_set:
            final_msx_palette_0_7_set.add(msx_color_0_7)
            final_msx_palette_0_7_list.append(msx_color_0_7)
    
    idx_master=0
    while len(final_msx_palette_0_7_list)<num_target_colors and idx_master<len(MSX2_MASTER_PALETTE_0_7):
        candidate_color=MSX2_MASTER_PALETTE_0_7[idx_master]
        if candidate_color not in final_msx_palette_0_7_set:
            final_msx_palette_0_7_list.append(candidate_color)
            final_msx_palette_0_7_set.add(candidate_color)
        idx_master+=1
    
    final_msx_palette_0_7 = final_msx_palette_0_7_list[:num_target_colors]
    pil_palette_for_quantize_flat=[]
    for r07,g07,b07 in final_msx_palette_0_7:
        pil_palette_for_quantize_flat.extend([(r07*255//7),(g07*255//7),(b07*255//7)])
    
    if len(pil_palette_for_quantize_flat)<256*3:
        pil_palette_for_quantize_flat.extend([0,0,0]*(256-(len(pil_palette_for_quantize_flat)//3)))
    
    palette_image_for_remap=Image.new('P',(1,1))
    palette_image_for_remap.putpalette(pil_palette_for_quantize_flat)
    dither_method = Image.Dither.FLOYDSTEINBERG if dither_enabled else Image.Dither.NONE
    return image.quantize(palette=palette_image_for_remap, dither=dither_method), final_msx_palette_0_7

def _offset_worker_initializer(img_data):
    global worker_img_data, worker_height, worker_width
    worker_img_data = img_data
    worker_height, worker_width = img_data.shape

def _calculate_offset_score_worker(offset):
    dx, dy = offset
    current_score = 0
    num_tile_rows = (worker_height - dy) // 8
    num_tile_cols = (worker_width - dx) // 8

    for ty in range(num_tile_rows):
        for tx in range(num_tile_cols):
            y_start = dy + ty * 8
            x_start = dx + tx * 8
            tile = worker_img_data[y_start : y_start + 8, x_start : x_start + 8]
            
            if tile.shape != (8, 8):
                continue

            for r in range(8):
                if len(np.unique(tile[r, :])) > 2:
                    current_score += 1
    
    return current_score, offset

def find_best_tiling_offset(quantized_image, num_cores):
    img_data = np.array(quantized_image)
    tasks = [(dx, dy) for dy in range(8) for dx in range(8)]
    
    results = []
    init_args = (img_data,)
    with multiprocessing.Pool(processes=num_cores, initializer=_offset_worker_initializer, initargs=init_args) as pool:
        for result in tqdm(pool.imap_unordered(_calculate_offset_score_worker, tasks), total=len(tasks), desc="   Finding best offset", leave=False, unit="offset"):
            results.append(result)
            
    if not results:
        return (0, 0)
        
    best_score, best_offset = min(results, key=lambda item: item[0])
    return best_offset

def process_tile_for_screen4(tile_indices_np, palette_0_255, color_dist_func):
    pattern_data=np.zeros(8,dtype=np.uint8)
    color_data=np.zeros(8,dtype=np.uint8)
    for r in range(8):
        row_indices=tile_indices_np[r]
        counts=Counter(row_indices)
        bg_idx,fg_idx=0,0
        if len(counts)>2:
            (c1_idx,_),(c2_idx,_) = counts.most_common(2)
            bg_idx,fg_idx=sorted([c1_idx,c2_idx])
            c1_rgb=palette_0_255[c1_idx]
            c2_rgb=palette_0_255[c2_idx]
            new_row=np.copy(row_indices)
            for c in range(8):
                original_idx=row_indices[c]
                if original_idx!=c1_idx and original_idx!=c2_idx:
                    original_rgb=palette_0_255[original_idx]
                    dist1=color_dist_func(original_rgb,c1_rgb)
                    dist2=color_dist_func(original_rgb,c2_rgb)
                    new_row[c]=c1_idx if dist1<=dist2 else c2_idx
            row_indices=new_row
        elif len(counts)==2:
            c1_idx,c2_idx=counts.keys()
            bg_idx,fg_idx=sorted([c1_idx,c2_idx])
        elif len(counts)==1:
            bg_idx=fg_idx=list(counts.keys())[0]
        color_data[r]=(fg_idx<<4)|bg_idx
        row_pattern_byte=0
        for c in range(8):
            if row_indices[c]==fg_idx:
                row_pattern_byte|=(1<<(7-c))
        pattern_data[r]=row_pattern_byte
    return pattern_data,color_data

def calculate_tile_difference(tile1_tuple, tile2_tuple, palette_255, color_dist_func):
    pattern1, color1 = tile1_tuple
    pattern2, color2 = tile2_tuple
    total_damage = 0
    def _get_pixel_rgb(row, col, pattern_data, color_data):
        pattern_byte = pattern_data[row]
        color_byte = color_data[row]
        is_foreground = (pattern_byte >> (7 - col)) & 1
        palette_idx = (color_byte >> 4) & 0x0F if is_foreground else color_byte & 0x0F
        return palette_255[palette_idx]
    for r in range(8):
        for c in range(8):
            rgb1 = _get_pixel_rgb(r, c, pattern1, color1)
            rgb2 = _get_pixel_rgb(r, c, pattern2, color2)
            total_damage += color_dist_func(rgb1, rgb2)
    return total_damage

def pad_image_to_tile_size(image: Image.Image):
    width, height = image.size
    pad_right = (8 - (width % 8)) % 8
    pad_bottom = (8 - (height % 8)) % 8
    if pad_right==0 and pad_bottom==0:
        return image
    new_width = width + pad_right
    new_height = height + pad_bottom
    padded_image = Image.new('P', (new_width, new_height), color=0)
    padded_image.putpalette(image.getpalette())
    padded_image.paste(image, (0, 0))
    return padded_image

# --- Multiprocessing Worker and Initializer ---
def _init_worker(tiles_data, palette, metric_name):
    global worker_tiles_data, worker_palette, worker_color_dist_func
    if COLOUR_SCIENCE_AVAILABLE:
        warnings.filterwarnings("ignore", category=ColourUsageWarning)
    worker_tiles_data = tiles_data
    worker_palette = palette
    worker_color_dist_func = get_color_distance_function(metric_name)

def _calculate_initial_costs_worker(pair):
    idx1, idx2 = pair
    tile1, tile2 = worker_tiles_data[idx1], worker_tiles_data[idx2]
    diff = calculate_tile_difference(tile1["data"], tile2["data"], worker_palette, worker_color_dist_func)
    if diff == 0:
        return None
    if tile1["count"] > tile2["count"]:
        loser_count = tile2["count"]
    elif tile2["count"] > tile1["count"]:
        loser_count = tile1["count"]
    else:
        loser_count = tile1["count"]
    cost = diff * loser_count
    return (cost, idx1, idx2)

def optimize_by_precomputation_and_heap(source_tiles, max_tiles, tm_width, tm_height, palette_255, num_cores, color_metric):
    print("   Finding unique source tiles and their map counts...")
    unique_tile_groups = defaultdict(list)
    initial_unique_count = len(unique_tile_groups)
    for i, tile_data in enumerate(source_tiles):
        key = tile_data[0].tobytes() + tile_data[1].tobytes()
        unique_tile_groups[key].append(i)
    initial_unique_count = len(unique_tile_groups)
    print(f"   [INFO] Found {initial_unique_count} unique tiles.")
    if initial_unique_count <= max_tiles:
        print(f"   [INFO] Initial unique tile count ({initial_unique_count}) is within limit. No merge needed.")
        final_patterns = [source_tiles[locs[0]] for locs in unique_tile_groups.values()]
        final_tile_map = np.zeros((tm_height, tm_width), dtype=np.int16)
        for i, locs in enumerate(unique_tile_groups.values()):
            for loc_idx in locs:
                r,c = divmod(loc_idx,tm_width)
                final_tile_map[r, c] = i
        return final_patterns, final_tile_map

    active_tiles = { i: {"data": source_tiles[locs[0]], "count": len(locs), "original_indices": {i}}
                     for i, (key, locs) in enumerate(unique_tile_groups.items()) }

    print("   Generating memory structure to hold tile pairs...")
    all_pairs = list(combinations(active_tiles.keys(), 2))

    print(f"   Initializing worker pool and transferring data to {num_cores} cores.\r\n      -> This may take some seconds, please wait..")
    chunksize = max(1, len(all_pairs) // (num_cores * 16))
    merge_heap = []
    
    init_args = (active_tiles, palette_255, color_metric)
    with multiprocessing.Pool(processes=num_cores, initializer=_init_worker, initargs=init_args) as pool:
        for result in tqdm(pool.imap_unordered(_calculate_initial_costs_worker, all_pairs, chunksize=chunksize), total=len(all_pairs), desc="   Pre-calculating costs", mininterval=10.0):
            if result:
                heapq.heappush(merge_heap, result)

    num_merges_to_perform = len(active_tiles) - max_tiles
    print(f"   Performing {num_merges_to_perform} merges to reach target of {max_tiles} tiles...")
    is_active = {idx: True for idx in active_tiles.keys()}
    
    with tqdm(total=num_merges_to_perform, desc="   Merging tiles") as pbar:
        merges_done = 0
        while merges_done < num_merges_to_perform and merge_heap:
            cost, idx1, idx2 = heapq.heappop(merge_heap)
            if not (is_active.get(idx1) and is_active.get(idx2)):
                continue
            tile1, tile2 = active_tiles[idx1], active_tiles[idx2]
            if tile1["count"] > tile2["count"]:
                winner_idx, loser_idx = idx1, idx2
            elif tile2["count"] > tile1["count"]:
                winner_idx, loser_idx = idx2, idx1
            else:
                winner_idx, loser_idx = (idx1, idx2) if idx1 < idx2 else (idx2, idx1)
            active_tiles[winner_idx]["count"] += active_tiles[loser_idx]["count"]
            active_tiles[winner_idx]["original_indices"].update(active_tiles[loser_idx]["original_indices"])
            del active_tiles[loser_idx]
            is_active[loser_idx] = False
            merges_done += 1
            pbar.update(1)

    print("   Building final tileset and map...")
    final_patterns, final_merge_map = [], {}
    for final_idx, (key, tile_info) in enumerate(active_tiles.items()):
        final_patterns.append(tile_info["data"])
        for original_unique_idx in tile_info["original_indices"]:
            final_merge_map[original_unique_idx] = final_idx
    final_tile_map = np.zeros((tm_height, tm_width), dtype=np.int16)
    original_to_unique_idx = {key: i for i, key in enumerate(unique_tile_groups.keys())}
    for i, tile_data in enumerate(source_tiles):
        key = tile_data[0].tobytes() + tile_data[1].tobytes()
        final_idx = final_merge_map[original_to_unique_idx[key]]
        r, c = divmod(i, tm_width)
        final_tile_map[r, c] = final_idx
    return final_patterns, final_tile_map

def write_sc4_palette(filename, palette_0_7):
    with open(filename, "wb") as f:
        f.write(b'\x00' * 4)
        for i in range(16):
            if i < len(palette_0_7):
                f.write(bytes(palette_0_7[i]))
            else:
                f.write(b'\x00\x00\x00')

def write_sc4_tiles(filename, unique_patterns):
    num_tiles = len(unique_patterns)
    header_byte = num_tiles if num_tiles < 256 else 0
    with open(filename, "wb") as f:
        f.write(bytes([header_byte]))
        f.write(b'\x00' * 4)
        for pattern_data, _ in unique_patterns:
            f.write(pattern_data.tobytes())
        for _, color_data in unique_patterns:
            f.write(color_data.tobytes())

def write_sc4_supertiles(filename, supertile_definitions, super_w, super_h):
    num_supertiles = len(supertile_definitions)
    with open(filename, "wb") as f:
        if num_supertiles > 255:
            f.write(b'\x00')
            f.write(num_supertiles.to_bytes(2, 'little'))
        else:
            f.write(bytes([num_supertiles]))
        f.write(bytes([super_w, super_h]))
        f.write(b'\x00' * 4)
        for supertile_block in supertile_definitions:
            max_idx = np.max(supertile_block)
            bytes_per_idx = 2 if max_idx > 255 else 1
            for base_tile_idx in supertile_block.flat:
                f.write(int(base_tile_idx).to_bytes(bytes_per_idx, 'little'))

def write_sc4_map(filename, tile_map, num_supertiles):
    map_height, map_width = tile_map.shape
    bytes_per_index = 2 if num_supertiles > 255 else 1
    with open(filename, "wb") as f:
        f.write(map_width.to_bytes(2, 'little'))
        f.write(map_height.to_bytes(2, 'little'))
        f.write(b'\x00' * 4)
        for tile_idx in tile_map.flat:
            f.write(int(tile_idx).to_bytes(bytes_per_index, 'little'))

def reconstruct_sc4_tile_pil(pattern_data, color_data, pil_palette_flat):
    tile_img = Image.new('P', (8, 8))
    tile_img.putpalette(pil_palette_flat)
    pixels = tile_img.load()
    for r in range(8):
        color_byte = color_data[r]
        pattern_byte = pattern_data[r]
        bg_idx = int(color_byte & 0x0F)
        fg_idx = int((color_byte >> 4) & 0x0F)
        for c in range(8):
            is_fg_pixel = (pattern_byte >> (7 - c)) & 1
            pixels[c, r] = fg_idx if is_fg_pixel else bg_idx
    return tile_img

def discover_supertiles(tile_map, super_w, super_h):
    map_h, map_w = tile_map.shape
    if map_w % super_w != 0 or map_h % super_h != 0:
        print(f"Warning: Image dimensions ({map_w*8}x{map_h*8}) are not perfectly divisible by supertile dimensions ({super_w*8}x{super_h*8}).")
    
    super_map_w = map_w // super_w
    super_map_h = map_h // super_h
    supertile_map = np.zeros((super_map_h, super_map_w), dtype=np.int16)
    
    unique_supertiles = {}
    supertile_definitions = []
    
    for r_super in range(super_map_h):
        for c_super in range(super_map_w):
            r_start = r_super * super_h
            c_start = c_super * super_w
            block = tile_map[r_start : r_start + super_h, c_start : c_start + super_w]
            block_key = block.tobytes()
            
            if block_key not in unique_supertiles:
                new_supertile_id = len(supertile_definitions)
                unique_supertiles[block_key] = new_supertile_id
                supertile_definitions.append(block)
                supertile_map[r_super, c_super] = new_supertile_id
            else:
                supertile_id = unique_supertiles[block_key]
                supertile_map[r_super, c_super] = supertile_id
                
    return supertile_definitions, supertile_map

def main():
    if COLOUR_SCIENCE_AVAILABLE:
        warnings.filterwarnings("ignore", category=ColourUsageWarning)
        
    print_splash_screen(SCRIPT_NAME, SCRIPT_VERSION)
    
    parser = argparse.ArgumentParser(description=f"Transforming maps in MSX SC4 tiles like a charm.")
    parser.add_argument("input_image", help="Input image file path")
    parser.add_argument("--max-tiles", type=int, default=256, help="Target maximum number of unique tiles")
    parser.add_argument("--num-colors", type=int, default=16, help="Number of colors for the palette (max 16)")
    parser.add_argument("--output-dir", default=".", help="Directory for output files (defaults to current directory).")
    parser.add_argument("--output-basename", help="Basename for output files (defaults to the input file's name).")
    parser.add_argument("--no-dithering", action="store_true", help="Disable dithering during color quantization.")
    parser.add_argument("--cores", type=int, default=os.cpu_count(), help="Number of CPU cores to use. Defaults to all.")
    parser.add_argument("--color-metric", choices=['rgb', 'weighted-rgb', 'cie76', 'ciede2000'], default='weighted-rgb',
                        help="Algorithm for color difference calculation. 'weighted-rgb' is default. CIE modes require 'pip install colormath'.")
    parser.add_argument("--supertile-width", type=int, default=4, help="Width of supertiles in tiles.")
    parser.add_argument("--supertile-height", type=int, default=4, help="Height of supertiles in tiles.")
    parser.add_argument("--find-best-offset", action="store_true", help="Test all 64 tile offsets in parallel and pick the best one.")

    args = parser.parse_args()

    if (args.color_metric in ['cie76', 'ciede2000']) and not COLOUR_SCIENCE_AVAILABLE:
        print("\n--- ERROR ---")
        print(f"Color metric '{args.color_metric}' requires the 'colour-science' library.")
        print("Please install it using: pip install colour-science")
        return

    if args.num_colors > 16:
        print("Warning: --num_colors > 16. Setting to 16.")
        args.num_colors = 16

    try:
        original_pil_image = Image.open(args.input_image)
    except FileNotFoundError:
        print(f"Error: Input image '{args.input_image}' not found.")
        return

    if args.output_basename:
        base_name = args.output_basename
    else:
        base_name = os.path.splitext(os.path.basename(args.input_image))[0]

    full_output_path = os.path.join(args.output_dir, base_name)
    color_dist_func = get_color_distance_function(args.color_metric)

    print(f"1. Quantizing image to MSX palette (metric: {args.color_metric})...")
    quantized_pil_image, msx_palette_0_7 = quantize_image_to_msx_colors(original_pil_image, args.num_colors, not args.no_dithering, color_dist_func)
    print(f"   [INFO] Palette quantization complete. Selected {len(msx_palette_0_7)} unique MSX colors.")
    palette_0_255 = [MSX2_MASTER_PALETTE_0_255[MSX2_MASTER_PALETTE_0_7.index(c)] for c in msx_palette_0_7]

    if args.find_best_offset:
        print(f"1b. Evaluating 64 possible offsets on {args.cores} cores to find the optimal tile grid...")
        best_offset = find_best_tiling_offset(quantized_pil_image, args.cores)
        dx, dy = best_offset
        print(f"   [INFO] Optimal offset found at ({dx}, {dy}). Cropping image.")
        width, height = quantized_pil_image.size
        quantized_pil_image = quantized_pil_image.crop((dx, dy, width, height))

    quantized_pil_image = pad_image_to_tile_size(quantized_pil_image)
    img_width, img_height = quantized_pil_image.size
    tile_map_width, tile_map_height = img_width // 8, img_height // 8

    print("2. Extracting and processing source tiles...")
    all_source_tiles_data = []
    quantized_np_indices = np.array(quantized_pil_image.getdata(), dtype=np.uint8).reshape((img_height, img_width))
    for ty in tqdm(range(tile_map_height), desc="   Processing Tiles"):
        for tx in range(tile_map_width):
            tile_block = quantized_np_indices[ty*8:(ty+1)*8, tx*8:(tx+1)*8]
            all_source_tiles_data.append(process_tile_for_screen4(tile_block, palette_0_255, color_dist_func))
    print(f"   [INFO] Image contains a total of {len(all_source_tiles_data)} tiles (including duplicates).")

    print("3. Optimizing tiles...")
    final_unique_patterns, final_tile_map_indices = optimize_by_precomputation_and_heap(all_source_tiles_data, args.max_tiles, tile_map_width, tile_map_height, palette_0_255, args.cores, args.color_metric)
    
    num_unique_base_patterns = len(final_unique_patterns)
    print(f"   [INFO] Optimization complete. Final tile count: {num_unique_base_patterns}")

    supertile_definitions = []
    final_map_to_write = final_tile_map_indices
    num_supertiles = num_unique_base_patterns
    use_supertiles = args.supertile_width > 1 or args.supertile_height > 1

    if use_supertiles:
        print(f"4. Discovering {args.supertile_width}x{args.supertile_height} supertiles from optimized tileset...")
        print(f"   [INFO] Map dimensions: {tile_map_width}x{tile_map_height} tiles.")
        super_map_h, super_map_w = final_map_to_write.shape
        super_map_h = super_map_h // args.supertile_height
        super_map_w = super_map_w // args.supertile_width
        print(f"   [INFO] Map dimensions: {super_map_w}x{super_map_h} = {super_map_w * super_map_h} supertiles.")
        supertile_definitions, supertile_map = discover_supertiles(final_tile_map_indices, args.supertile_width, args.supertile_height)
        num_supertiles = len(supertile_definitions)
        final_map_to_write = supertile_map
        print(f"   [INFO] Found {num_supertiles} unique {args.supertile_width}x{args.supertile_height} supertiles.")
    else:
        print("4. Generating 1x1 supertile definitions...")
        print(f"   [INFO] Map dimensions: {tile_map_width}x{tile_map_height} tiles.")
        for i in range(num_unique_base_patterns):
            supertile_definitions.append(np.array([[i]], dtype=np.int16))

    print("5. Generating output files...")
    os.makedirs(args.output_dir, exist_ok=True)

    write_sc4_palette(f"{full_output_path}.SC4Pal", msx_palette_0_7)
    write_sc4_tiles(f"{full_output_path}.SC4Tiles", final_unique_patterns)
    write_sc4_supertiles(f"{full_output_path}.SC4Super", supertile_definitions, args.supertile_width, args.supertile_height)
    write_sc4_map(f"{full_output_path}.SC4Map", final_map_to_write, num_supertiles)

    print("6. Generating visual outputs...")
    pil_final_palette_flat = [c for rgb in palette_0_255 for c in rgb]
    if len(pil_final_palette_flat) < 256*3:
        pil_final_palette_flat.extend([0,0,0] * (256 - len(palette_0_255)))
    reconstructed_img = Image.new('P', (img_width, img_height), color=0)
    reconstructed_img.putpalette(pil_final_palette_flat)
    for r_map in range(tile_map_height):
        for c_map in range(tile_map_width):
            pattern_idx = final_tile_map_indices[r_map, c_map]
            if 0 <= pattern_idx < num_unique_base_patterns:
                tile_to_paste = reconstruct_sc4_tile_pil(final_unique_patterns[pattern_idx][0], final_unique_patterns[pattern_idx][1], pil_final_palette_flat)
                reconstructed_img.paste(tile_to_paste, (c_map * 8, r_map * 8))
    reconstructed_img.save(f"{full_output_path}_reconstructed.png")

    tiles_per_row = 16
    num_rows = (num_unique_base_patterns + tiles_per_row - 1) // tiles_per_row
    tileset_vis = Image.new('P', (tiles_per_row*8, num_rows*8), color=0)
    tileset_vis.putpalette(pil_final_palette_flat)
    for i, (p_data, c_data) in enumerate(final_unique_patterns):
        r_vis, c_vis = divmod(i, tiles_per_row)
        tile_to_paste = reconstruct_sc4_tile_pil(p_data, c_data, pil_final_palette_flat)
        tileset_vis.paste(tile_to_paste, (c_vis * 8, r_vis * 8))
    tileset_vis.save(f"{full_output_path}_tileset.png")
    
    print("\nProcessing complete.")

if __name__ == "__main__":
    main()