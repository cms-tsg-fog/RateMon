SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

CI_COMMIT_TAG ?= 0.0.0
VERSION = ${CI_COMMIT_TAG}
RELEASE = 1
ARCH = amd64
# Get the git branch name and the short commit hash
CI_COMMIT_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)
BRANCH = ${CI_COMMIT_BRANCH}
HASH = $(shell git rev-parse --short HEAD)

# e.g. 'python36'
PYTHON_VERSION = $(shell python3 --version | sed -E 's|^Python ([0-9])\.([0-9])\..*$$|python\1\2|')
$(info python version '${PYTHON_VERSION}')

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

	mkdir -p rpms/${PYTHON_VERSION}

	# Launch fpm to package the prepared folder	
	fpm \
	-p ${RPM_NAME}-${PYTHON_VERSION}.rpm \
	-n ratemon \
	-s dir \
	-t rpm \
	-v ${VERSION} \
	-a ${ARCH} \
	-d root -d ${PYTHON_VERSION}-root -d ${PYTHON_VERSION}-omsapi \
	--iteration ${RELEASE} \
	--description "Rate monitoring tools for HLT and L1" \
	--url "https://gitlab.cern.ch/cms-tsg-fog/ratemon" \
	--vendor "CERN" \
	rpmroot/=/

	mv *-${PYTHON_VERSION}.rpm rpms/${PYTHON_VERSION}
