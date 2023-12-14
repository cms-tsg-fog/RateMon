import plotTriggerRates as ptr
import yaml
from DBParser import DBParser

from flask import send_from_directory
from Exceptions import *

# Read database parser 
parser = DBParser()

def getRatesROOT(runNumber: int, triggerKey: str):
    # Initialize the RateMon controller
    controller = ptr.MonitorController()
    saveDirectory = "/rtmdata/" + str(runNumber)
    
    run_type = controller.getRunType(runNumber)

    try:
        rates = controller.runStandalone(
            exportRoot = True,
            saveDirectory = saveDirectory,
            makeTitle = False,
            triggerList = [triggerKey],
            bestFit = True,
            data_lst = [runNumber],
            runType = run_type
        )

    except NoDataError as e:
        return e.message,400
    except NoValidTriggersError as e:
        return e.message,400
    else:
        return send_from_directory(
            saveDirectory,
            triggerKey + '.ROOT',
            as_attachment = True # Keep the filename
        )

def getRatesJSON(runNumber: int, triggerKey: str, queryByFill: bool, createFit: bool):
    # Initialize the RateMon controller
    controller = ptr.MonitorController()
    
    run_type = controller.getRunType(runNumber)
    
    # If this flag is false, we want to skip setting this option
    if not queryByFill:
        queryByFill = None
    
    # Whether to create a fit or use ref fit
    bestFitVal = None
    refFitVal = None
    if createFit:
        bestFitVal = True
    else:
        refFitVal = "Fits/{runType}/referenceFits_{runType}_all.pkl".format(runType = run_type)
    
    # Specify the save directory
    saveDirectory = "/rtmdata/" + str(runNumber) + '/' + triggerKey + '/'
    
    try:
        rates = controller.runStandalone(
            exportRoot = False,
            exportJson = True,
            saveDirectory = saveDirectory,
            triggerList = [triggerKey],
            bestFit = bestFitVal,
            fitFile = refFitVal,
            data_lst = [runNumber],
            runType = run_type,
            useFills = queryByFill
        )
    
    except NoDataError as e:
        return e.message,400
    except NoValidTriggersError as e:
        return e.message,400
    else:
        return send_from_directory(
            saveDirectory,
            triggerKey + '.json',
            as_attachment = True # Keep the filename
        )
