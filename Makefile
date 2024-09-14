PYTHON_FILES = $(shell find . -name '*.py' -not -path  './.direnv/*')

.PHONY: style
style:
	yapf -i $(PYTHON_FILES)

.PHONY: lint
lint:
	pylint $(PYTHON_FILES)

# Install any required python tools and modules
.PHONY: requirements
requirements:
	python3 -m pip install --upgrade pip
	pip3 install -r requirements.txt

# Run tests
.PHONY: test
test:
	python -m pytest -vv

# Do coverage analysis and print a report
.PHONY: coverage
coverage:
	coverage run -m pytest
	coverage report -m
