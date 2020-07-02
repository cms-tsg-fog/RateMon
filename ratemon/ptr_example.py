# Exporting trigger rates using the plotTriggerRates 
#  class as a library
import plotTriggerRates as ptr
import yaml

with open("dbConfig.yaml", 'r') as stream:
    dbCfg = yaml.safe_load(stream)

triggers = ["HLT_Ele40_WPTight_Gsf",
            "HLT_DoubleEle33_CaloIdL_MW"]

controller = ptr.MonitorController()
triggerrates = controller.runStandalone(dbConfig=dbCfg,
                         triggerList=triggers,
                         useFills=True,
                         vsLS=False,
                         createFit=True,
                         bestFit=True,
                         data_lst=[6303])