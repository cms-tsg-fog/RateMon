SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

rpm:
	# Clean up directory
	rm -rf rpmroot
	# Create destination in /opt
	mkdir -p rpmroot/opt
	# Systemd unit folder
	mkdir -p rpmroot/usr/lib/systemd/system
	# Copy the systemd unit file
	cp systemd/* rpmroot/usr/lib/systemd/system
	# Copy everything by the rpmroot folder (ratemon software)
	cp -r ratemon rpmroot/opt

	
	cd rpmroot && fpm \
	-s dir \
	-t rpm \
	-n ratemon \
	--vendor "CERN" \
	.=/ && mv *.rpm ..
