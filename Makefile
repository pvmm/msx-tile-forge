# Makefile for MSX Tile Forge

# Define the name of the main script and all helper scripts to be included.
MAIN_SCRIPT = msxtileforge.py
TARGET = dist/$(MAIN_SCRIPT:.py=)
SDIST = dist/$(MAIN_SCRIPT:.py=)-source
HELPER_SCRIPTS = msxtileexport.py msxtilemagic.py tilerandomizer.py supertilerandomizer.py

# Define default output filenames. These can be overridden from the command line.
# Example: make win WIN_ZIP="my_custom_name_win.zip"
WIN_ZIP ?= msxtileforge_win.zip
LIN_TGZ ?= msxtileforge_lin.tar.gz
SRC_ZIP ?= msxtileforge_src.zip

ifeq ($(OS),Windows_NT)
TARGET := $(subst /,\,$(TARGET))
SDIST := $(subst /,\,$(SDIST))
PYTHON ?= python
all: all-win
else # MacOS or Linux
PYTHON ?= python3
all: all-lin
endif

# --- Build Targets ---
prepackage:
	$(PYTHON) -m pip install PyInstaller

common:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m PyInstaller --noconsole --onedir --clean \
		--add-data "msxtileexport.py:." \
		--add-data "msxtilemagic.py:." \
		--add-data "tilerandomizer.py:." \
		--add-data "supertilerandomizer.py:." \
		--noconfirm $(MAIN_SCRIPT)
	cp README.md LICENSE $(TARGET_DIR)

all-win: prepackage common
	cd dist && powershell Compress-Archive -Force -Path $(MAIN_SCRIPT:.py=) -DestinationPath $(WIN_ZIP)

all-lin: prepackage common
	cd dist && tar -czvf $(LIN_TGZ) $(MAIN_SCRIPT:.py=)

deb:
	debuild -us -uc

sdist:
	mkdir -p $(SDIST)
	cp *.py $(SDIST)
	cp icon.bmp $(SDIST)
	cp LICENSE $(SDIST)
	cp README.md $(SDIST)
	cp requirements.txt $(SDIST)
	cd dist && zip -r $(SRC_ZIP) msxtileforge-source

clean:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes

.PHONY: all all-win all-lin build-common deb sdist clean
