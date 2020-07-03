# Exporting trigger rates using the plotTriggerRates 
#  class as a library
import plotTriggerRates as ptr
import yaml

# Read database configuration from file
with open("dbConfig.yaml", 'r') as stream:
    dbCfg = yaml.safe_load(stream)

# Specify which triggers we want
triggers = ["HLT_Ele40_WPTight_Gsf",
            "HLT_DoubleEle33_CaloIdL_MW"]

# Initialize the RateMon controller
controller = ptr.MonitorController()

# Get Trigger Rates from Fill 6303, creating fits
triggerrates = controller.runStandalone(dbConfig=dbCfg,
                         triggerList=triggers,
                         useFills=True,
                         vsLS=False,
                         createFit=True,
                         bestFit=True,
                         data_lst=[6303])

# Print result
print(triggerrates)