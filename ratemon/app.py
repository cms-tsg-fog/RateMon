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
                oldParser=True, # TMP!!!
                dbConfig=dbCfg,
                exportRoot=True,
                saveDirectory=saveDirectory,
                makeTitle=False,
                triggerList=[triggerKey],
                createFit=True,
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

def getRunRatesJSON(runNumber: int, triggerKey: str):
        # Initialize the RateMon controller
        controller = ptr.MonitorController()
        saveDirectory = "/rtmdata/" + str(runNumber) + '/' + triggerKey + '/'
        try:
            rates = controller.runStandalone(
                oldParser=True, # TMP!!!
                dbConfig=dbCfg,
                exportRoot=False,
                exportJson=True,
                saveDirectory=saveDirectory,
                triggerList=[triggerKey],
                createFit=True,
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
                triggerKey + '.json',
                as_attachment=True # Keep the filename
            )

def getFillRatesJSON(fillNumber: int, triggerKey: str):
        # Initialize the RateMon controller
        controller = ptr.MonitorController()
        saveDirectory = "/rtmdata/" + str(fillNumber) + '/' + triggerKey + '/'
        try:
            rates = controller.runStandalone(
                oldParser=True, # TMP!!!
                dbConfig=dbCfg,
                exportRoot=False,
                exportJson=True,
                saveDirectory=saveDirectory,
                triggerList=[triggerKey],
                createFit=True,
                bestFit=True,
                useFills=True,
                data_lst=[fillNumber]
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
