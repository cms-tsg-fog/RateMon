SHELL:=/bin/bash
.DEFAULT_GOAL := rpm

rpm:
	# Clean up directory
	rm -rf rpmroot
	# Create destination in /opt
	mkdir -p rpmroot/opt/ratemon
	# Systemd unit folder
	mkdir -p rpmroot/usr/lib/systemd/system
	# Copy the systemd unit file
	cp systemd/* rpmroot/usr/lib/systemd/system
	# Copy everything by the rpmroot folder (ratemon software)
	rsync -avz --exclude '.git' --exclude 'rpmroot' . rpmroot/opt/ratemon
	
	cd rpmroot && fpm \
	-s dir \
	-t rpm \
	-n ratemon \
	--vendor "CERN" \
	.=/ && mv *.rpm ..
	
