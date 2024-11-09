# DunioCli makefile

THIS_DIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))
TOP_DIR ?= $(THIS_DIR)
$(info TOP_DIR = $(TOP_DIR))

DUINO_MAKEFILE ?= $(THIS_DIR)/../libraries/DuinoMakefile

ifeq ("$(wildcard $(DUINO_MAKEFILE)/Makefile)","")
$(error Unable to open $(DUINO_MAKEFILE)/Makefile)
else
include $(DUINO_MAKEFILE)/Makefile
endif

PYTHON_FILES = $(shell find . -name '*.py' -not -path  './.direnv/*' -not -path './tests/*' -not -path './.vscode/*')

pystyle:
	yapf -i $(PYTHON_FILES)

pylint:
	pylint $(PYTHON_FILES)

# Creates the source distribution tarball
sdist:
	python3 setup.py sdist

# Creates the distribution tarball and uploads to the pypi test server
upload-test:
	rm -rf dist/*
	python3 setup.py sdist
	twine upload -r testpypi dist/*

# Creates the distribution tarball and uploads to the pypi live server
upload-pypi:
	rm -rf dist/*
	python3 setup.py sdist
	twine upload -r pypi dist/*

# Registers this package on the pypi live server
requirements:
	pip install -r requirements.txt
