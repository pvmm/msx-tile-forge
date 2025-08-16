# Makefile for MSX Tile Forge (Linux/Debian builds)

# The 'all' target is now the 'lin' target by default.
all: lin

lin:
	# Use python3 -m to ensure the correct PyInstaller is called
	python3 -m PyInstaller --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		msxtileforge.py
	# After building, copy assets into the new folder
	cp README.md LICENSE dist/msxtileforge/
	# Create the tar.gz archive
	cd dist && tar -czvf msxtileforge_linux.tar.gz msxtileforge

clean:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes