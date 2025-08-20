# Makefile for MSX Tile Forge

# Define the name of the main script and all helper scripts to be included.
MAIN_SCRIPT = msxtileforge.py
HELPER_SCRIPTS = msxtileexport.py msxtilemagic.py tilerandomizer.py supertilerandomizer.py

# Define default output filenames. These can be overridden from the command line.
# Example: make win WIN_ZIP="my_custom_name_win.zip"
WIN_ZIP ?= msxtileforge_win.zip
LIN_TGZ ?= msxtileforge_lin.tar.gz
SRC_ZIP ?= msxtileforge_src.zip

# --- Build Targets ---

win:
	python -m PyInstaller --noconsole --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		$(MAIN_SCRIPT)
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	# Create the final zip archive directly with the specified name
	cd dist && zip -r $(WIN_ZIP) $(MAIN_SCRIPT:.py=)

lin:
	python3 -m PyInstaller --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		$(MAIN_SCRIPT)
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	# Create the final tar.gz archive directly with the specified name
	cd dist && tar -czvf $(LIN_TGZ) $(MAIN_SCRIPT:.py=)

deb:
	# The .deb filename is controlled by debian/changelog.
	# The calling workflow is responsible for finding the generated .deb file and renaming it.
	debuild -us -uc

sdist:
	mkdir -p dist/msxtileforge-source
	cp *.py icon.bmp LICENSE README.md requirements.txt dist/msxtileforge-source/
	# Create the final source zip archive directly with the specified name
	cd dist && zip -r $(SRC_ZIP) msxtileforge-source

clean:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes