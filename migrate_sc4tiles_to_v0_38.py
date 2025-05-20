import struct
import os
import sys
import shutil # For more robust renaming/moving

# Constants from your main application (ensure these match)
TILE_WIDTH = 8
TILE_HEIGHT = 8
MAX_TILES = 256

def migrate_sc4tiles_file(input_filepath, output_filepath):
    """
    Migrates a single .SC4Tiles file from the old format (interleaved pattern/color per tile)
    to the new format (all patterns, then all colors).

    Args:
        input_filepath (str): Path to the old format .SC4Tiles file.
        output_filepath (str): Path to save the new format .SC4Tiles file.

    Returns:
        bool: True if migration was successful, False otherwise.
    """
    print(f"Attempting to migrate '{input_filepath}' to '{output_filepath}'...")

    temp_patterns = []
    temp_colors = []
    actual_num_tiles_in_file = 0
    original_header_byte = None # Store the original header byte

    try:
        with open(input_filepath, "rb") as f_in:
            num_tiles_header_byte_val = f_in.read(1)
            if not num_tiles_header_byte_val:
                print(f"Error: Input file '{input_filepath}' is empty or missing header.")
                return False
            
            original_header_byte = num_tiles_header_byte_val # Save for writing
            header_value = struct.unpack("B", num_tiles_header_byte_val)[0]
            actual_num_tiles_in_file = 256 if header_value == 0 else header_value

            if not (1 <= actual_num_tiles_in_file <= MAX_TILES):
                print(f"Error: Invalid tile count '{actual_num_tiles_in_file}' in header of '{input_filepath}'.")
                return False
            
            print(f"  Header indicates {actual_num_tiles_in_file} tiles.")

            for i in range(actual_num_tiles_in_file):
                pattern_block = f_in.read(TILE_HEIGHT)
                if len(pattern_block) < TILE_HEIGHT:
                    print(f"Error: Unexpected EOF reading pattern for tile {i} in '{input_filepath}'.")
                    return False
                temp_patterns.append(pattern_block)

                color_block = f_in.read(TILE_HEIGHT)
                if len(color_block) < TILE_HEIGHT:
                    print(f"Error: Unexpected EOF reading colors for tile {i} in '{input_filepath}'.")
                    return False
                temp_colors.append(color_block)
            
            extra_data = f_in.read(1)
            if extra_data:
                print(f"Warning: Input file '{input_filepath}' contains unexpected extra data after declared tiles.")

        with open(output_filepath, "wb") as f_out:
            f_out.write(original_header_byte) 
            for pattern_block in temp_patterns:
                f_out.write(pattern_block)
            for color_block in temp_colors:
                f_out.write(color_block)
        
        print(f"  Successfully migrated {actual_num_tiles_in_file} tiles.")
        print(f"  New file saved to '{output_filepath}'.")
        return True

    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found.")
        return False
    except (EOFError, ValueError, struct.error) as e:
        print(f"Error processing file '{input_filepath}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during migration of '{input_filepath}': {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("MSX Tile Forge - .SC4Tiles Migrator (to v0.0.38 format)")
        print("-------------------------------------------------------")
        print("Converts old format .SC4Tiles files (interleaved pattern/color per tile)")
        print("to the new format (all patterns first, then all colors).")
        print("\nUsage:")
        print(f"  python {os.path.basename(__file__)} <input_file.SC4Tiles> [output_file.SC4Tiles]")
        print(f"  python {os.path.basename(__file__)} <directory_with_sc4tiles_files>")
        print("\nIf only <input_file.SC4Tiles> is given, the original is renamed to")
        print("'<input_file>_old.SC4Tiles>' and the new format file gets the original name.")
        print("If a directory is specified, all .SC4Tiles files in it will be migrated,")
        print("creating '<filename>_migrated.SC4Tiles' for each (original is not renamed).")
        sys.exit(1)

    path_arg = sys.argv[1]

    if os.path.isdir(path_arg):
        print(f"Processing directory: {path_arg}")
        files_processed = 0
        files_migrated_successfully = 0
        for filename in os.listdir(path_arg):
            if filename.lower().endswith(".sc4tiles") and not filename.lower().endswith("_old.sc4tiles") and not filename.lower().endswith("_migrated.sc4tiles"):
                input_file = os.path.join(path_arg, filename)
                base, ext = os.path.splitext(filename)
                # For directory processing, always create a new "_migrated" file
                output_file = os.path.join(path_arg, f"{base}_migrated{ext}")
                
                if os.path.exists(output_file):
                    overwrite = input(f"Output file '{output_file}' already exists. Overwrite? (y/N): ").lower()
                    if overwrite != 'y':
                        print(f"Skipping '{input_file}'.")
                        continue
                
                print("-" * 30)
                if migrate_sc4tiles_file(input_file, output_file):
                    files_migrated_successfully += 1
                files_processed +=1
        print("-" * 30)
        print(f"\nDirectory processing complete. Migrated {files_migrated_successfully}/{files_processed} files.")

    elif os.path.isfile(path_arg):
        input_file_original_name = path_arg
        
        if len(sys.argv) > 2: # Output file explicitly specified
            output_file_target_name = sys.argv[2]
            if os.path.abspath(input_file_original_name) == os.path.abspath(output_file_target_name):
                print(f"Error: Input and explicit output file cannot be the same ('{input_file_original_name}').")
                print("If you want to replace the original, provide only the input filename.")
                sys.exit(1)
            
            if os.path.exists(output_file_target_name):
                overwrite = input(f"Output file '{output_file_target_name}' already exists. Overwrite? (y/N): ").lower()
                if overwrite != 'y':
                    print(f"Skipping '{input_file_original_name}'.")
                    sys.exit(0)
            
            migrate_sc4tiles_file(input_file_original_name, output_file_target_name)

        else: # Only input file specified, rename original and output to original name
            base, ext = os.path.splitext(input_file_original_name)
            backup_file_name = f"{base}_old{ext}"
            output_file_target_name = input_file_original_name # New file will get original name

            if os.path.abspath(backup_file_name) == os.path.abspath(output_file_target_name):
                # This case should ideally not happen with "_old" suffix but good for safety
                print(f"Error: Backup name '{backup_file_name}' conflicts with target name '{output_file_target_name}'. Cannot proceed.")
                sys.exit(1)

            if os.path.exists(backup_file_name):
                overwrite_backup = input(f"Backup file '{backup_file_name}' already exists. Overwrite backup? (y/N): ").lower()
                if overwrite_backup != 'y':
                    print(f"Skipping '{input_file_original_name}' to protect existing backup.")
                    sys.exit(0)
                else:
                    try:
                        os.remove(backup_file_name)
                        print(f"  Removed existing backup '{backup_file_name}'.")
                    except OSError as e:
                        print(f"Error: Could not remove existing backup '{backup_file_name}': {e}")
                        sys.exit(1)
            
            # Rename original to backup
            try:
                print(f"  Renaming '{input_file_original_name}' to '{backup_file_name}'...")
                shutil.move(input_file_original_name, backup_file_name)
            except OSError as e:
                print(f"Error: Could not rename '{input_file_original_name}' to '{backup_file_name}': {e}")
                print("Migration aborted. Original file might still be in place.")
                sys.exit(1)

            # Perform migration from backup to original name
            if migrate_sc4tiles_file(backup_file_name, output_file_target_name):
                print(f"  Original file '{input_file_original_name}' has been updated to the new format.")
                print(f"  Old version preserved as '{backup_file_name}'.")
            else:
                print(f"Error during migration. Attempting to restore original file...")
                try:
                    # If output was partially created, remove it before restoring backup
                    if os.path.exists(output_file_target_name):
                        os.remove(output_file_target_name)
                    shutil.move(backup_file_name, input_file_original_name)
                    print(f"  Successfully restored '{input_file_original_name}' from backup.")
                except OSError as e_restore:
                    print(f"CRITICAL ERROR: Could not restore '{input_file_original_name}' from '{backup_file_name}': {e_restore}")
                    print("Please manually check your files.")
                sys.exit(1)
    else:
        print(f"Error: Path '{path_arg}' is not a valid file or directory.")
        sys.exit(1)

if __name__ == "__main__":
    main()