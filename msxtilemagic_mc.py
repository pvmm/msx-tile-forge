#!/usr/bin/env python3

# --- Program Identification ---
SCRIPT_NAME = "MSX Tile Magic"
SCRIPT_VERSION = "0.0.10"

# --- Imports ---
import argparse
import os
from collections import Counter, defaultdict
import numpy as np
from PIL import Image
from tqdm import tqdm
import multiprocessing
from itertools import combinations
import heapq

# --- MSX2 Palette Constants ---
MSX2_MASTER_PALETTE_0_7 = []
for r_val in range(8):
    for g_val in range(8):
        for b_val in range(8):
            MSX2_MASTER_PALETTE_0_7.append((r_val, g_val, b_val))

MSX2_MASTER_PALETTE_0_255 = [(r * 255 // 7, g * 255 // 7, b * 255 // 7) for r, g, b in MSX2_MASTER_PALETTE_0_7]

# --- Helper Functions ---
def msx_rgb_to_0_255(r07, g07, b07):
    return (r07 * 255 // 7, g07 * 255 // 7, b07 * 255 // 7)

def find_closest_msx_color_from_rgb255(rgb_tuple_0_255):
    min_dist_sq = float('inf')
    closest_msx_color_0_7 = (0, 0, 0)
    r_in, g_in, b_in = rgb_tuple_0_255
    for idx, msx_color_0_255_candidate in enumerate(MSX2_MASTER_PALETTE_0_255):
        r_msx, g_msx, b_msx = msx_color_0_255_candidate
        dist_sq = (r_in - r_msx)**2 + (g_in - g_msx)**2 + (b_in - b_msx)**2
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_msx_color_0_7 = MSX2_MASTER_PALETTE_0_7[idx]
            if dist_sq == 0:
                break
    return closest_msx_color_0_7

def color_distance_sq(c1_rgb255, c2_rgb255):
    r1, g1, b1 = c1_rgb255
    r2, g2, b2 = c2_rgb255
    return (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2

def quantize_image_to_msx_colors(image: Image.Image, num_target_colors: int, dither_enabled: bool):
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    dither_method = Image.Dither.FLOYDSTEINBERG if dither_enabled else Image.Dither.NONE

    try:
        temp_quantized_img = image.quantize(colors=num_target_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    except Exception:
        temp_quantized_img = image.convert('P', palette=Image.Palette.ADAPTIVE, colors=num_target_colors, dither=Image.Dither.NONE)

    pil_palette_255_flat = temp_quantized_img.getpalette()
    ideal_colors_255 = []
    if pil_palette_255_flat:
        for i in range(num_target_colors):
            if i * 3 + 2 < len(pil_palette_255_flat):
                ideal_colors_255.append((pil_palette_255_flat[i*3], pil_palette_255_flat[i*3+1], pil_palette_255_flat[i*3+2]))

    final_msx_palette_0_7_set = set()
    final_msx_palette_0_7_list = []
    for r255, g255, b255 in ideal_colors_255:
        msx_color_0_7 = find_closest_msx_color_from_rgb255((r255, g255, b255))
        if msx_color_0_7 not in final_msx_palette_0_7_set:
            final_msx_palette_0_7_set.add(msx_color_0_7)
            final_msx_palette_0_7_list.append(msx_color_0_7)
    
    idx_master = 0
    while len(final_msx_palette_0_7_list) < num_target_colors and idx_master < len(MSX2_MASTER_PALETTE_0_7):
        candidate_color = MSX2_MASTER_PALETTE_0_7[idx_master]
        if candidate_color not in final_msx_palette_0_7_set:
            final_msx_palette_0_7_list.append(candidate_color)
            final_msx_palette_0_7_set.add(candidate_color)
        idx_master += 1
    
    final_msx_palette_0_7 = final_msx_palette_0_7_list[:num_target_colors]
    
    pil_palette_for_quantize_flat = []
    for r07, g07, b07 in final_msx_palette_0_7:
        pil_palette_for_quantize_flat.extend(msx_rgb_to_0_255(r07, g07, b07))
    
    if len(pil_palette_for_quantize_flat) < 256 * 3:
        pil_palette_for_quantize_flat.extend([0,0,0] * (256 - (len(pil_palette_for_quantize_flat) // 3)))
    
    palette_image_for_remap = Image.new('P', (1, 1))
    palette_image_for_remap.putpalette(pil_palette_for_quantize_flat)

    quant_image_pil = image.quantize(palette=palette_image_for_remap, dither=dither_method)
    
    return quant_image_pil, final_msx_palette_0_7

def process_tile_for_screen4(tile_indices_np, palette_0_255):
    pattern_data = np.zeros(8, dtype=np.uint8)
    color_data = np.zeros(8, dtype=np.uint8)

    for r in range(8):
        row_indices = tile_indices_np[r]
        counts = Counter(row_indices)
        
        bg_idx, fg_idx = 0, 0

        if len(counts) > 2:
            (c1_idx, _), (c2_idx, _) = counts.most_common(2)
            bg_idx, fg_idx = sorted([c1_idx, c2_idx])
            
            c1_rgb = palette_0_255[c1_idx]
            c2_rgb = palette_0_255[c2_idx]

            new_row = np.copy(row_indices)
            for c in range(8):
                original_idx = row_indices[c]
                if original_idx != c1_idx and original_idx != c2_idx:
                    original_rgb = palette_0_255[original_idx]
                    dist1 = color_distance_sq(original_rgb, c1_rgb)
                    dist2 = color_distance_sq(original_rgb, c2_rgb)
                    new_row[c] = c1_idx if dist1 <= dist2 else c2_idx
            row_indices = new_row
        elif len(counts) == 2:
            c1_idx, c2_idx = counts.keys()
            bg_idx, fg_idx = sorted([c1_idx, c2_idx])
        elif len(counts) == 1:
            bg_idx = fg_idx = list(counts.keys())[0]
            
        color_data[r] = (fg_idx << 4) | bg_idx

        row_pattern_byte = 0
        for c in range(8):
            if row_indices[c] == fg_idx:
                row_pattern_byte |= (1 << (7 - c))
        pattern_data[r] = row_pattern_byte

    return pattern_data, color_data

def calculate_tile_difference(tile1_tuple, tile2_tuple, palette_255):
    pattern1, color1 = tile1_tuple
    pattern2, color2 = tile2_tuple
    total_damage = 0

    def _get_pixel_rgb(row, col, pattern_data, color_data):
        pattern_byte, color_byte = pattern_data[row], color_data[row]
        is_foreground = (pattern_byte >> (7 - col)) & 1
        palette_idx = (color_byte >> 4) & 0x0F if is_foreground else color_byte & 0x0F
        return palette_255[palette_idx]

    for r in range(8):
        for c in range(8):
            rgb1 = _get_pixel_rgb(r, c, pattern1, color1)
            rgb2 = _get_pixel_rgb(r, c, pattern2, color2)
            total_damage += color_distance_sq(rgb1, rgb2)
    return total_damage

def pad_image_to_tile_size(image: Image.Image, tile_size: int):
    width, height = image.size
    pad_right = (tile_size - (width % tile_size)) % tile_size
    pad_bottom = (tile_size - (height % tile_size)) % tile_size

    if pad_right == 0 and pad_bottom == 0: return image

    new_width, new_height = width + pad_right, height + pad_bottom
    padded_image = Image.new('P', (new_width, new_height), color=0)
    padded_image.putpalette(image.getpalette())
    padded_image.paste(image, (0, 0))
    return padded_image

# --- Multiprocessing Worker Function ---
def _calculate_initial_costs_worker(args_tuple):
    pair, tiles_data, palette = args_tuple
    idx1, idx2 = pair
    tile1, tile2 = tiles_data[idx1], tiles_data[idx2]
    
    diff = calculate_tile_difference(tile1["data"], tile2["data"], palette)
    if diff == 0: return None

    if tile1["count"] > tile2["count"]: loser_count = tile2["count"]
    elif tile2["count"] > tile1["count"]: loser_count = tile1["count"]
    else: loser_count = tile1["count"]
        
    cost = diff * loser_count
    return (cost, idx1, idx2)

def optimize_by_precomputation_and_heap(source_tiles, max_patterns, tm_width, tm_height, palette_255, num_cores):
    print("   Finding unique source tiles and their map counts...")
    unique_tile_groups = defaultdict(list)
    for i, tile_data in enumerate(source_tiles):
        key = tile_data[0].tobytes() + tile_data[1].tobytes()
        unique_tile_groups[key].append(i)
    
    initial_unique_count = len(unique_tile_groups)
    if initial_unique_count <= max_patterns:
        print(f"   Initial unique tile count ({initial_unique_count}) is within limit. No merge needed.")
        final_patterns = [source_tiles[locs[0]] for locs in unique_tile_groups.values()]
        final_tile_map = np.zeros((tm_height, tm_width), dtype=np.int16)
        for i, locs in enumerate(unique_tile_groups.values()):
            for loc_idx in locs:
                r, c = loc_idx // tm_width, loc_idx % tm_width
                final_tile_map[r, c] = i
        return final_patterns, final_tile_map

    active_tiles = {}
    for i, (key, locs) in enumerate(unique_tile_groups.items()):
        active_tiles[i] = { "data": source_tiles[locs[0]], "count": len(locs), "original_indices": {i} }

    # --- Phase 1: The "Big Calculation" (Parallel) ---
    print(f"   Pre-calculating merge costs for all pairs using {num_cores} cores...")
    all_pairs = list(combinations(active_tiles.keys(), 2))
    tasks = [(pair, active_tiles, palette_255) for pair in all_pairs]
    
    merge_heap = []
    with multiprocessing.Pool(processes=num_cores) as pool:
        for result in tqdm(pool.imap_unordered(_calculate_initial_costs_worker, tasks), total=len(tasks), desc="   Pre-calculating costs"):
            if result:
                heapq.heappush(merge_heap, result)

    # --- Phase 2: The Iterative Merge Loop (Sequential but Fast) ---
    num_merges_to_perform = len(active_tiles) - max_patterns
    print(f"   Performing {num_merges_to_perform} merges to reach target of {max_patterns} patterns...")
    
    is_active = {idx: True for idx in active_tiles.keys()}
    
    with tqdm(total=num_merges_to_perform, desc="   Merging tiles") as pbar:
        merges_done = 0
        while merges_done < num_merges_to_perform and merge_heap:
            cost, idx1, idx2 = heapq.heappop(merge_heap)
            
            # Validate the merge: ensure both tiles are still active
            if not (is_active.get(idx1) and is_active.get(idx2)):
                continue # This pair is stale, get the next one
            
            # Determine winner and loser
            tile1, tile2 = active_tiles[idx1], active_tiles[idx2]
            if tile1["count"] > tile2["count"]: winner_idx, loser_idx = idx1, idx2
            elif tile2["count"] > tile1["count"]: winner_idx, loser_idx = idx2, idx1
            else: winner_idx, loser_idx = (idx1, idx2) if idx1 < idx2 else (idx2, idx1)
            
            # Perform the merge
            active_tiles[winner_idx]["count"] += active_tiles[loser_idx]["count"]
            active_tiles[winner_idx]["original_indices"].update(active_tiles[loser_idx]["original_indices"])
            
            # Deactivate the loser tile
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
        original_unique_idx = original_to_unique_idx[key]
        final_idx = final_merge_map[original_unique_idx]
        r, c = i // tm_width, i % tm_width
        final_tile_map[r, c] = final_idx
        
    return final_patterns, final_tile_map

# --- File Writing Functions & Visual Reconstruction (unchanged) ---
def write_sc4_palette(filename, palette_0_7):
    with open(filename, "wb") as f: f.write(b'\x00'*4); [f.write(bytes(c)) for c in palette_0_7]; f.write(b'\x00'*(16-len(palette_0_7))*3)
def write_sc4_tiles(filename, unique_patterns):
    n = len(unique_patterns); h = n if n<256 else 0
    with open(filename, "wb") as f: f.write(bytes([h])); f.write(b'\x00'*4); [f.write(p.tobytes()) for p,_ in unique_patterns]; [f.write(c.tobytes()) for _,c in unique_patterns]
def write_sc4_supertiles(filename, n):
    with open(filename, "wb") as f: f.write(b'\x00'+n.to_bytes(2,'little') if n>255 else bytes([n])); f.write(b'\x01\x01\x00\x00\x00\x00'); [f.write(bytes([i])) for i in range(n)]
def write_sc4_map(filename, tile_map, num_supertiles):
    h,w = tile_map.shape; b = 2 if num_supertiles > 255 else 1
    with open(filename, "wb") as f: f.write(w.to_bytes(2,'little')); f.write(h.to_bytes(2,'little')); f.write(b'\x00'*4); [f.write(int(i).to_bytes(b,'little')) for i in tile_map.flat]
def reconstruct_sc4_tile_pil(pattern_data, color_data, pil_palette_flat):
    img=Image.new('P',(8,8)); img.putpalette(pil_palette_flat); pix=img.load()
    for r in range(8): c_b,p_b=color_data[r],pattern_data[r]; bg,fg=int(c_b&0x0F),int((c_b>>4)&0x0F); [pix.__setitem__((c,r),fg if (p_b>>(7-c))&1 else bg) for c in range(8)]
    return img

def main():
    print(f"{SCRIPT_NAME} - Version {SCRIPT_VERSION}")
    
    parser = argparse.ArgumentParser(description=f"{SCRIPT_NAME} v{SCRIPT_VERSION}")
    parser.add_argument("input_image", help="Input image file path")
    parser.add_argument("--max_patterns", type=int, default=256, help="Target maximum number of unique patterns (max 256 for Screen 4)")
    parser.add_argument("--num_colors", type=int, default=16, help="Number of colors for the palette (max 16)")
    parser.add_argument("--tile_size", type=int, default=8, help="Tile size in pixels (must be 8 for this script)")
    parser.add_argument("--output_basename", default="output", help="Basename for output files (e.g., 'mymap')")
    parser.add_argument("--no_dithering", action="store_true", help="Disable dithering during color quantization.")
    parser.add_argument("--cores", type=int, default=os.cpu_count(), help="Number of CPU cores to use for optimization. Defaults to all available cores.")
    args = parser.parse_args()

    if args.num_colors > 16: print("Warning: --num_colors cannot be greater than 16. Setting to 16."); args.num_colors = 16
    if args.tile_size != 8: print("Error: --tile_size must be 8 for Screen 4 processing."); return

    try: original_pil_image = Image.open(args.input_image)
    except FileNotFoundError: print(f"Error: Input image '{args.input_image}' not found."); return

    print("1. Quantizing image to MSX palette...")
    quantized_pil_image, msx_palette_0_7 = quantize_image_to_msx_colors(original_pil_image, args.num_colors, not args.no_dithering)
    
    palette_0_255 = [msx_rgb_to_0_255(*c) for c in msx_palette_0_7]
    
    quantized_pil_image = pad_image_to_tile_size(quantized_pil_image, args.tile_size)
    img_width, img_height = quantized_pil_image.size
    tile_map_width, tile_map_height = img_width // args.tile_size, img_height // args.tile_size

    print("2. Extracting and processing source tiles for Screen 4 compliance...")
    all_source_tiles_data = []
    quantized_np_indices = np.array(quantized_pil_image.getdata(), dtype=np.uint8).reshape((img_height, img_width))
    for ty in tqdm(range(tile_map_height), desc="Processing Tiles"):
        for tx in range(tile_map_width):
            all_source_tiles_data.append(process_tile_for_screen4(quantized_np_indices[ty*8:(ty+1)*8, tx*8:(tx+1)*8], palette_0_255))
    
    print("3. Optimizing patterns using parallel pre-computation and heap...")
    final_unique_patterns, final_tile_map_indices = optimize_by_precomputation_and_heap(
        all_source_tiles_data, args.max_patterns, tile_map_width, tile_map_height, palette_0_255, args.cores
    )
    
    num_unique_patterns = len(final_unique_patterns)
    print(f"Optimization complete. Final unique pattern count: {num_unique_patterns}")

    print("4. Generating output files...")
    output_dir = os.path.dirname(args.output_basename)
    if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)

    write_sc4_palette(f"{args.output_basename}.SC4Pal", msx_palette_0_7)
    write_sc4_tiles(f"{args.output_basename}.SC4Tiles", final_unique_patterns)
    write_sc4_supertiles(f"{args.output_basename}.SC4Super", num_unique_patterns)
    write_sc4_map(f"{args.output_basename}.SC4Map", final_tile_map_indices, num_unique_patterns)

    print("5. Generating visual outputs...")
    pil_final_palette_flat = []
    for r,g,b in palette_0_255: pil_final_palette_flat.extend([r,g,b])
    if len(pil_final_palette_flat) < 256 * 3: pil_final_palette_flat.extend([0,0,0] * (256 - len(pil_final_palette_flat)))

    reconstructed_img = Image.new('P', (img_width, img_height), color=0)
    reconstructed_img.putpalette(pil_final_palette_flat)
    for r_map in range(tile_map_height):
        for c_map in range(tile_map_width):
            pattern_idx = final_tile_map_indices[r_map, c_map]
            if 0 <= pattern_idx < num_unique_patterns:
                p_data, c_data = final_unique_patterns[pattern_idx]
                reconstructed_img.paste(reconstruct_sc4_tile_pil(p_data, c_data, pil_final_palette_flat), (c_map * args.tile_size, r_map * args.tile_size))
    reconstructed_img.save(f"{args.output_basename}_reconstructed_image.png")

    tiles_per_row_visual = 16
    num_rows_visual = (num_unique_patterns + tiles_per_row_visual - 1) // tiles_per_row_visual
    tileset_vis = Image.new('P', (tiles_per_row_visual * 8, num_rows_visual * 8), color=0)
    tileset_vis.putpalette(pil_final_palette_flat)
    for i, (p_data, c_data) in enumerate(final_unique_patterns):
        row_vis, col_vis = divmod(i, tiles_per_row_visual)
        tileset_vis.paste(reconstruct_sc4_tile_pil(p_data, c_data, pil_final_palette_flat), (col_vis * 8, row_vis * 8))
    tileset_vis.save(f"{args.output_basename}_tileset.png")
    
    print("\nProcessing complete.")
    print(f"  Output files generated with basename: '{args.output_basename}'")
    print(f"  - {os.path.basename(args.output_basename)}.SC4Pal")
    print(f"  - {os.path.basename(args.output_basename)}.SC4Tiles")
    print(f"  - {os.path.basename(args.output_basename)}.SC4Super")
    print(f"  - {os.path.basename(args.output_basename)}.SC4Map")

if __name__ == "__main__":
    main()