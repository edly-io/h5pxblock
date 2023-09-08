PACKAGE_NAME := h5pxblock
EXTRACT_DIR := $(PACKAGE_NAME)/locale/en/LC_MESSAGES
EXTRACTED_DJANGO := $(EXTRACT_DIR)/django-partial.po
EXTRACTED_DJANGOJS := $(EXTRACT_DIR)/djangojs-partial.po
EXTRACTED_TEXT := $(EXTRACT_DIR)/text.po
JS_TARGET := public/js/translations
TRANSLATIONS_DIR := $(PACKAGE_NAME)/translations

extract_translations: symlink_translations ## extract strings to be translated, outputting .po files
	cd $(PACKAGE_NAME) && i18n_tool extract
	mv $(EXTRACTED_DJANGO) $(EXTRACTED_TEXT)
	if [ -f "$(EXTRACTED_DJANGOJS)" ]; then cat $(EXTRACTED_DJANGOJS) >> $(EXTRACTED_TEXT); rm $(EXTRACTED_DJANGOJS); fi

compile_translations: symlink_translations ## compile translation files, outputting .mo files for each supported language
	cd $(PACKAGE_NAME) && i18n_tool generate

detect_changed_source_translations:
	cd $(PACKAGE_NAME) && i18n_tool changed

symlink_translations:
	if [ ! -d "$(TRANSLATIONS_DIR)" ]; then ln -s locale/ $(TRANSLATIONS_DIR); fi
