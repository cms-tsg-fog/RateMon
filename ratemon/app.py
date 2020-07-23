import plotTriggerRates as ptr
import yaml

from flask import send_from_directory

# Read database configuration from file
with open("dbConfig.yaml", 'r') as stream:
    dbCfg = yaml.safe_load(stream)

# Initialize the RateMon controller
controller = ptr.MonitorController()

def getRatesROOT(runNumber: int, triggerKey: str):
	saveDirectory = "/rtmdata/" + str(runNumber)
	rates = controller.runStandalone(
						 dbConfig=dbCfg,
                         exportRoot=True,
                         exportJSON=False,
                         saveDirectory=saveDirectory,
                         makeTitle=True,
                         triggerList=[triggerKey],
                         vsLS=False,
                         createFit=True,
                         bestFit=True,
                         data_lst=[runNumber])

	return send_from_directory(saveDirectory,
							   triggerKey + '.ROOT',
							   as_attachment=True) # Keep the filename