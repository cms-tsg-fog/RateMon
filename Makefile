SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

CI_COMMIT_TAG ?= 0.0.0
VERSION = ${CI_COMMIT_TAG}
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

RPM_NAME = ratemon-${VERSION}.${ARCH}.${BRANCH}.${HASH}

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

	mkdir -p rpms/python34 rpms/python36

	# Launch fpm to package the prepared folder	
	fpm \
	-p ${RPM_NAME}-python36.rpm \
	-n ratemon \
	-s dir \
	-t rpm \
	-v ${VERSION} \
	-a ${ARCH} \
	-d python3 -d root -d python36-root \
	--iteration ${RELEASE} \
	--description "Rate monitoring tools for HLT and L1" \
	--url "https://gitlab.cern.ch/cms-tsg-fog/ratemon" \
	--vendor "CERN" \
	rpmroot/=/

	mv *-python36.rpm rpms/python36

	fpm \
	-p ${RPM_NAME}-python34.rpm \
	-n ratemon \
	-s dir \
	-t rpm \
	-v ${VERSION} \
	-a ${ARCH} \
	-d python34 -d root -d python34-root \
	--iteration ${RELEASE} \
	--description "Rate monitoring tools for HLT and L1" \
	--url "https://gitlab.cern.ch/cms-tsg-fog/ratemon" \
	--vendor "CERN" \
	rpmroot/=/

	mv *-python34.rpm rpms/python34
