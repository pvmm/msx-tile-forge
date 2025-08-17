# Makefile for MSX Tile Forge

# Define the name of the main script and all helper scripts to be included.
MAIN_SCRIPT = msxtileforge.py
HELPER_SCRIPTS = msxtileexport.py msxtilemagic.py tilerandomizer.py supertilerandomizer.py

# --- Build Targets ---

win:
	# Use python -m to ensure the correct PyInstaller is called
	python -m PyInstaller --noconsole --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		$(MAIN_SCRIPT)
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	cd dist && zip -r msxtileforge_windows.zip $(MAIN_SCRIPT:.py=)

lin:
	# Use python3 -m on Linux to ensure the correct PyInstaller is called
	python3 -m PyInstaller --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		$(MAIN_SCRIPT)
	cp README.md LICENSE dist/$(MAIN_SCRIPT:.py=)/
	cd dist && tar -czvf msxtileforge_linux.tar.gz $(MAIN_SCRIPT:.py=)

deb:
	debuild -us -uc
	mv ../msxtileforge_*.deb dist/

clean:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes