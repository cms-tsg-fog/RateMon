SHELL:=/bin/bash
.DEFAULT_GOAL := build

AGG_PATH=aggregationapi/src/main/java/ch/cern/cms/daq/oms/api/aggregation/model/glenn

.PHONY: clean
clean:
	rm -f ${AGG_PATH} aggregationapi/Makefile

${AGG_PATH}:
	ln -s $(shell pwd)/glenn ${AGG_PATH}

aggregationapi/Makefile:
	cp -f Makefile aggregationapi


.PHONY: build
build: ${AGG_PATH} aggregationapi/Makefile
	make -C aggregationapi package

.PHONY: package
package:
	mvn generate-sources
	mvn package