# DunioCli makefile

THIS_DIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))
TOP_DIR ?= $(THIS_DIR)

DUINO_MAKEFILE ?= $(THIS_DIR)/../libraries/duino_makefile

ifeq ("$(wildcard $(DUINO_MAKEFILE)/Makefile)","")
$(error Unable to open $(DUINO_MAKEFILE)/Makefile)
else
include $(DUINO_MAKEFILE)/Makefile
endif

# Creates the source distribution tarball
sdist:
	rm -rf dist/*
	python3 setup.py sdist

# Creates the distribution tarball and uploads to the pypi live server
upload-pypi: sdist
	twine upload -r pypi-duino-cli dist/*
