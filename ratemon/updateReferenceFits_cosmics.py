import pickle
from DBParser import *
from plotTriggerRates import *
from referenceRuns import referenceRuns

myMonCon = MonitorController()
myParser = DBParser.DBParser()

def avg(lst): return sum(lst) / len(lst)
run = referenceRuns['cosmics'][0] # picking only first run

triggerList = myMonCon.readTriggerList("TriggerLists/monitorlist_COSMICS.list")
L1trig = triggerList[23:]
HLTtrig = triggerList[:23]

L1Rate = myParser.getL1Rates(run,minLS=-1,maxLS=9999999,trigList=L1trig)
HLTRate = myParser.getHLTRates(run,trigger_list=HLTtrig,minLS=-1,maxLS=9999999)

avgL1TriggerRates = {}
for trigger in L1trig:
        avgL1TriggerRates[trigger] = avg([item[0] for item in list(L1Rate[trigger].values())])
avgHLTTriggerRates = {}
for trigger in HLTtrig:
        avgHLTTriggerRates[trigger] = avg([item[0] for item in list(HLTRate[trigger].values())])

allTriggers = {**avgL1TriggerRates,**avgHLTTriggerRates}

with open('referenceFits_cosmics_monitored.pkl', 'wb') as handle:
    pickle.dump(allTriggers,handle,protocol=pickle.HIGHEST_PROTOCOL)        
