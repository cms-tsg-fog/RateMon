SHELL:=/bin/bash
.DEFAULT_GOAL := build

.PHONY: clean
clean:
	mvn clean
	rm -rf src

.PHONY: build
build:
	./generate.py
	git describe --tags --abbrev=0 > version || echo "0.0.1" > version
	mvn generate-sources
	mvn package