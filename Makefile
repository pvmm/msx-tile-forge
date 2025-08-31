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
SHELL := cmd.exe /c
TARGET := $(subst /,\,$(TARGET))
SDIST := $(subst /,\,$(SDIST))
COPY ?= "cmd /C copy"
PYTHON ?= python
all: all-win
sdist: sdist-win
clean: clean-win
else # MacOS or Linux
COPY ?= cp
PYTHON ?= python3
all: all-lin
sdist: sdist-lin
clean: clean-lin
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

all-win: prepackage common
	$(COPY) README.md $(TARGET)
	$(COPY) LICENSE $(TARGET)
	rem Create the final zip archive directly with the specified name
	cd dist && powershell Compress-Archive -Force -Path $(MAIN_SCRIPT:.py=) -DestinationPath $(WIN_ZIP)

all-lin: prepackage common
	$(COPY) README.md $(TARGET)
	$(COPY) LICENSE $(TARGET)
	# Create the final tar.gz archive directly with the specified name
	cd dist && tar -czvf $(LIN_TGZ) $(MAIN_SCRIPT:.py=)

deb:
	# The .deb filename is controlled by debian/changelog.
	# The calling workflow is responsible for finding the generated .deb file and renaming it.
	debuild -us -uc

dist/msxtileforge-source:
	mkdir -p $(SDIST)

sdist-common: dist/msxtileforge-source
	$(COPY) *.py $(SDIST)
	$(COPY) icon.bmp $(SDIST)
	$(COPY) LICENSE $(SDIST)
	$(COPY) README.md $(SDIST)
	$(COPY) requirements.txt $(SDIST)

sdist-win: sdist-common
	rem Create the final source zip archive directly with the specified name
	cd dist && powershell Compress-Archive -Force -Path $(MAIN_SCRIPT:.py=)-source -DestinationPath $(MAIN_SCRIPT:.py=)-source.zip

sdist-lin: sdist-common
	# Create the final source zip archive directly with the specified name
	cd dist && zip -r $(SRC_ZIP) msxtileforge-source

clean-lin:
	rm -rf build dist *.spec
	rm -f ../msxtileforge_*.deb ../msxtileforge_*.buildinfo ../msxtileforge_*.changes

clean-win:
	@if exist build rmdir /S /Q build
	@if exist dist rmdir /S /Q dist
	@if exist *.spec del /S /Q *.spec
	@if exist ..\msxtileforge_*.deb del /S /Q ..\msxtileforge_*.deb
	@if exist ..\msxtileforge_*.buildinfo del /S /Q ..\msxtileforge_*.buildinfo
	@if exist ..\msxtileforge_*.changes del /S /Q ..\msxtileforge_*.changes
