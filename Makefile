SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

VERSION = 1.0.0
RELEASE = 1
ARCH = amd64
# Get the git branch name and the short commit hash
BRANCH = $(shell git rev-parse --abbrev-ref HEAD)
HASH = $(shell git rev-parse --short HEAD)

.PHONY: test
test:
	echo todo

.PHONY: build
build:
	make -C ratemon build

RPM_NAME = ratemon-${VERSION}.${ARCH}.${BRANCH}.${HASH}.rpm

.PHONY: rpm
rpm: build ${RPM_NAME}
${RPM_NAME}:
	# Clean up the rpmroot directory
	rm -rf rpmroot
	# Create /opt
	mkdir -p rpmroot/opt
	# Systemd unit folder
	mkdir -p rpmroot/usr/lib/systemd/system
	# Copy the systemd unit file
	cp systemd/* rpmroot/usr/lib/systemd/system
	# Copy the ratemon folder
	cp -r ratemon rpmroot/opt

	# Launch fpm to package the prepared folder	
	cd rpmroot && fpm \
	-p ${RPM_NAME} \
	-n ratemon \
	-s dir \
	-t rpm \
	-v ${VERSION} \
	-a ${ARCH} \
	--iteration ${RELEASE} \
	--description "Rate monitoring tools for HLT and L1" \
	--url "https://gitlab.cern.ch/cms-tsg-fog/ratemon" \
	--vendor "CERN" \
	.=/ && mv *.rpm ..
	mkdir -p rpms
	mv *.rpm rpms
