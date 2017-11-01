# RateMon
Repository with various tools to monitor HLT and L1 rates. More details on the [twiki](https://twiki.cern.ch/twiki/bin/viewauth/CMS/RateMonitoringScriptWithReferenceComparison)


Connect to online (.cms) network or lxplus and install: 
	
	ssh -Y cmsusr.cern.ch
	git clone git@github.com:cms-tsg-fog/RateMon.git
	cd RateMon

Before running either the plot making script or shift monitor tool, you will need to setup a config file for DBParser. In the RateMon directory:

	cp DBConfigFile_example.py DBConfigFile.py

Next open 'DBConfigFile.py' and fill in the appropriate connection info

Run shifter rate monitoring tool:

	source set.sh
	python ShiftMonitorTool.py
