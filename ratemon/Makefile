SHELL:=/bin/bash
.DEFAULT_GOAL := build

.PHONY: build
build:
	virtualenv -p /usr/bin/python3 --system-site-packages --download --copies venv
	source venv/bin/activate && \
	python -m pip install -r requirements.txt