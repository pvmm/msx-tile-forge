# --- TEMPORARY DIAGNOSTIC SCRIPT ---

import sys
import os

print("--- STARTING DIAGNOSTIC ---")
print(f"Python Executable Being Used: {sys.executable}")
print("-" * 20)
print("This executable will search for modules in the following directories (sys.path):")
for path in sys.path:
    print(f"  - {path}")
print("-" * 20)

# Check for the specific site-packages directory where pip says it is.
# This is the most important check.
target_site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
print(f"Checking if the expected site-packages directory is in the search path...")
print(f"Expected path: {target_site_packages}")

if target_site_packages in sys.path:
    print("\n[SUCCESS] The expected site-packages directory IS in the search path.")
else:
    # A more robust check for variations (e.g., case differences)
    found_in_path = any(os.path.samefile(p, target_site_packages) for p in sys.path if os.path.exists(p))
    if found_in_path:
        print("\n[SUCCESS] The expected site-packages directory IS in the search path (checked with samefile).")
    else:
        print("\n[FAILURE] The expected site-packages directory IS NOT in the search path.")
        print("This is the likely reason for the import error.")

print("-" * 20)
print("Now, attempting to import 'colormath'...")

try:
    # We will try to import the specific submodule that the main script needs
    from colormath.color_objects import sRGBColor
    print("\n[SUCCESS] Successfully imported 'sRGBColor' from 'colormath.color_objects'.")
    print("This means the 'colormath' library IS accessible to this script.")

except ImportError as e:
    print(f"\n[FAILURE] Failed to import 'colormath'.")
    print(f"The exact error was: {e}")
    print("\nThis confirms that this Python executable, in this specific environment, cannot find the library.")

except Exception as e:
    print(f"\n[UNEXPECTED ERROR] An error other than ImportError occurred.")
    print(f"The error was: {e}")


print("\n--- DIAGNOSTIC COMPLETE ---")