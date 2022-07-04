from DBParser import *
from plotTriggerRates import *
import pickle

myMonCon = MonitorController()
myParser = DBParser.DBParser()

def avg(lst): return sum(lst) / len(lst)
run = 349527

triggerList = myMonCon.readTriggerList("TriggerLists/monitorlist_COSMICS.list")
L1trig = triggerList[24:]
HLTtrig = triggerList[:24]
HLTtrig.remove('HLT_L1SingleEG5')

L1Rate = myParser.getL1Rates(run,minLS=-1,maxLS=9999999,trigList=L1trig)
HLTRate = myParser.getHLTRates(run,trigger_list=HLTtrig,minLS=-1,maxLS=9999999)

avgL1TriggerRates = {}
for trigger in L1trig:
        avgL1TriggerRates[trigger] = avg([item[0] for item in list(L1Rate[trigger].values())])
avgHLTTriggerRates = {}
for trigger in HLTtrig:
        avgHLTTriggerRates[trigger] = avg([item[0] for item in list(HLTRate[trigger].values())])

allTriggers = {**avgL1TriggerRates,**avgHLTTriggerRates}
with open('COSMICS_Rates.pkl', 'wb') as handle:
        pickle.dump(allTriggers,handle,protocol=pickle.HIGHEST_PROTOCOL)
