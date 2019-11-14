SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

VERSION = 1.0.0
RELEASE = 1
ARCH = amd64
RPM_NAME = ratemon-${VERSION}.${ARCH}.rpm


.PHONY: rpm

rpm: ${RPM_NAME}

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
	-n ratemon \
	-s dir \
	-t rpm \
	-v ${VERSION} \
	-a ${ARCH} \
	--iteration ${RELEASE} \
	--description "Rate monitoring tools for HLT and L1" \
	--url "https://gitlab.cern.ch/avivace/ratemon" \
	--vendor "CERN" \
	.=/ && mv *.rpm ..
