# script to update all reference fits, taking input from referenceRuns.py

from plotTriggerRates import MonitorController 
from referenceRuns import referenceRuns

controller = MonitorController()

controller.ops_dict["updateOnlineFits"] = True

for run_type in referenceRuns.keys(): # ["collisions", "collisionsHI"]
    if run_type == "cosmics": continue # cosmics naturally do not have PU-dependence, so are calculated differently as averages in updateReferenceFits_cosmics.py

    controller.ops_dict["runType="] = run_type
    controller.usr_input_data_lst = referenceRuns[run_type] 
    
    # monitored triggers 
    controller.ops_dict["allTriggers"] = False
    controller.ops_dict["triggerList="] = "TriggerLists/monitorlist_%s.list"%run_type.upper()
    controller.run()
    
    # all triggers
    controller.ops_dict["allTriggers"] = True
    controller.ops_dict["triggerList="] = None
    controller.run()
