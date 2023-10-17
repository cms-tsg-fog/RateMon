import pickle
from DBParser import *
from plotTriggerRates import *
from referenceRuns import referenceRuns

myMonCon = MonitorController()
myParser = DBParser.DBParser()

#d = open("Fits/Cosmics/COSMICS_Rates.pkl", "rb")
#loaded_dictionary = pickle.load(d)
#print(list(loaded_dictionary.keys()))

listLoadTriggers = ['HLT_Physics', 'HLT_Random', 'HLT_L1FatEvents', 'HLT_DQML1SeedsGroup1', 'HLT_L1SingleMuCosmics', 'HLT_L1SingleMuOpen', 'HLT_L1SingleMuOpen_DT', 'HLT_L1SingleMu3', 'HLT_L1SingleMu5', 'HLT_L1SingleMu7', 'HLT_L1DoubleMu0', 'HLT_L1TripleMu0TriMass1to4', 'HLT_L1QuadMu0OS', 'HLT_L1SingleMuOpenupt5', 'HLT_L1Mu0upt0', 'HLT_L1Mu0upt20ip03', 'HLT_L1MASSUPT_0_0_10', 'HLT_L2Mu10_NoVertex_NoBPTX', 'HLT_L2Mu40_NoVertex_3Sta_NoBPTX3BX', 'HLT_L1SingleJet35', 'HLT_L1SingleJet200', 'HLT_L1SingleEG10', 'HLT_L1SingleEG15', 'L1_SingleMuCosmics', 'L1_SingleMuOpen', 'L1_SingleMu3', 'L1_SingleMu5', 'L1_SingleMu7', 'L1_DoubleMu0', 'L1_DoubleMu18er2p1', 'L1_TripleMu0', 'L1_QuadMu0', 'L1_SingleMuOpenupt5', 'L1_Mu0upt0', 'L1_Mu0upt20ip03', 'L1_MASSUPT_0_0_10', 'L1_SingleTau120er2p1', 'L1_DoubleTau70er2p1', 'L1_DoubleIsoTau32er2p1', 'L1_HTT400er', 'L1_ETM120', 'L1_ETMHF100']
listPickle = ['L1_SingleMuCosmics', 'L1_SingleMuOpen', 'L1_SingleMu3', 'L1_SingleMu5', 'L1_SingleMu7', 'L1_DoubleMu0', 'L1_DoubleMu18er2p1', 'L1_TripleMu0', 'L1_QuadMu0', 'L1_SingleMuOpenupt5', 'L1_Mu0upt0', 'L1_Mu0upt20ip03', 'L1_MASSUPT_0_0_10', 'L1_SingleTau120er2p1', 'L1_DoubleTau70er2p1', 'L1_DoubleIsoTau32er2p1', 'L1_HTT400er', 'L1_ETM120', 'L1_ETMHF100', 'HLT_Physics', 'HLT_Random', 'HLT_L1FatEvents', 'HLT_DQML1SeedsGroup1', 'HLT_L1SingleMuCosmics', 'HLT_L1SingleMuOpen', 'HLT_L1SingleMuOpen_DT', 'HLT_L1SingleMu3', 'HLT_L1SingleMu5', 'HLT_L1SingleMu7', 'HLT_L1DoubleMu0', 'HLT_L1TripleMu0TriMass1to4', 'HLT_L1QuadMu0OS', 'HLT_L1SingleMuOpenupt5', 'HLT_L1Mu0upt0', 'HLT_L1Mu0upt20ip03', 'HLT_L1MASSUPT_0_0_10', 'HLT_L2Mu10_NoVertex_NoBPTX', 'HLT_L2Mu40_NoVertex_3Sta_NoBPTX3BX', 'HLT_L1SingleJet35', 'HLT_L1SingleJet200', 'HLT_L1SingleEG10', 'HLT_L1SingleEG15']

print(list(set(listLoadTriggers).difference(set(listPickle))))


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

#with open('COSMICS_Rates.pkl', 'wb') as handle:
        #pickle.dump(allTriggers,handle,protocol=pickle.HIGHEST_PROTOCOL)        
