SHELL:=/bin/bash
.DEFAULT_GOAL := build

.PHONY: build
build:
	virtualenv -p /usr/bin/python3 venv
	source venv/bin/activate
	pip3 install --upgrade pip
	pip3 install -r requirements.txt