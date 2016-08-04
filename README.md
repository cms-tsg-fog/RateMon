# RateMon
Repository with various tools to monitor HLT and L1 rates. More details on the [twiki](https://twiki.cern.ch/twiki/bin/viewauth/CMS/RateMonitoringScriptWithReferenceComparison)


Connect to online network and install: 
	
	ssh -Y cmsusr.cern.ch
	git clone git@github.com:cms-tsg-fog/RateMon.git
	cd RateMon

Run shifter rate monitoring tool:

	source set.sh
	python ShiftMonitorTool.py
