# Makefile for MSX Tile Forge

# Define the name of the main script and all helper scripts to be included.
MAIN_SCRIPT = msxtileforge.py
HELPER_SCRIPTS = msxtileexport.py msxtilemagic.py tilerandomizer.py superfilerandomizer.py

# --- Build Targets ---
all: win lin deb

win:
	# --onedir creates a folder instead of a single file.
	# The --add-data flags copy the helper scripts into the final build folder.
	pyinstaller --noconsole --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "superfilerandomizer.py:." \
		$(MAIN_SCRIPT)
	# After building, copy the non-Python assets into the folder.
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	# Zip the entire folder for distribution.
	cd dist && zip -r msxtileforge_windows.zip $(MAIN_SCRIPT:.py=)

lin:
	pyinstaller --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "superfilerandomizer.py:." \
		$(MAIN_SCRIPT)
	# Copy non-Python assets into the Linux build folder.
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	# Create the tar.gz archive of the entire folder.
	cd dist && tar -czvf msxtileforge_linux.tar.gz $(MAIN_SCRIPT:.py=)

deb:
	debuild -us -uc
	mv ../msxtileforge_*.deb dist/

clean:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes