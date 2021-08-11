import plotTriggerRates as ptr
import yaml

from flask import send_from_directory
from Exceptions import *

# Read database configuration from file
with open("dbConfig.yaml", 'r') as stream:
    dbCfg = yaml.safe_load(stream)

def getRatesROOT(runNumber: int, triggerKey: str):
        # Initialize the RateMon controller
        controller = ptr.MonitorController()
        saveDirectory = "/rtmdata/" + str(runNumber)
        try:
            rates = controller.runStandalone(
                oldParser=True, # NOTE: This is temporary, till the issues with the rates with the OMS Parser is figured out
                dbConfig=dbCfg,
                exportRoot=True,
                saveDirectory=saveDirectory,
                makeTitle=False,
                triggerList=[triggerKey],
                bestFit=True,
                data_lst=[runNumber]
            )
        except NoDataError as e:
            return e.message,400
        except NoValidTriggersError as e:
            return e.message,400
        else:
            return send_from_directory(
                saveDirectory,
                triggerKey + '.ROOT',
                as_attachment=True # Keep the filename
            )

def getRatesJSON(runNumber: int, triggerKey: str, queryByFill: bool, createFit: bool):

        # Initialize the RateMon controller
        controller = ptr.MonitorController()

        # If this flag is false, we want to skip setting this option
        if not queryByFill:
            queryByFill = None

        # Whether to create a fit or use ref fit
        bestFitVal = None
        refFitVal = None
        if createFit:
            bestFitVal = True
        else:
            refFitVal = "Fits/All_Triggers/FOG.pkl"

        # Specify the save directory
        saveDirectory = "/rtmdata/" + str(runNumber) + '/' + triggerKey + '/'

        try:
            rates = controller.runStandalone(
                oldParser=True, # NOTE: This is temporary, till the issues with the rates with the OMS Parser is figured out
                dbConfig=dbCfg,
                exportRoot=False,
                exportJson=True,
                saveDirectory=saveDirectory,
                triggerList=[triggerKey],
                bestFit=bestFitVal,
                fitFile=refFitVal,
                data_lst=[runNumber],
                useFills=queryByFill
            )

        except NoDataError as e:
            return e.message,400
        except NoValidTriggersError as e:
            return e.message,400
        else:
            return send_from_directory(
                saveDirectory,
                triggerKey + '.json',
                as_attachment=True # Keep the filename
            )
