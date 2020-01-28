import time

from Something import DBParser2
from OMSDBParser import DBParser

my_db2 = DBParser2()

my_db = DBParser()

#my_db2.getL1Rates(runNumber=322355)

#my_db2.getHLTRates(runNumber=322355)

#t0 = int(time.time())
#my_lst = my_db.getPSRates(runNumber=322355)
#t1 = int(time.time())
#print(t1-t0)
#t0 = int(time.time())
#my_lst2 = my_db2.getPSRates(runNumber=322355)
#t1 = int(time.time())
#print(t1-t0)
#if my_lst == my_lst2:
#    print("YES!!!")
#else:
#    print(my_lst)
#    print(my_lst2)

#my_db.getL1Prescales(runNumber=320149)

#my_db.getRunInfo(runNumber=305112)

#lst = my_db.getLumiInfo(runNumber=305112)

#lst = my_db.getQuickLumiInfo(runNumber=322355)

#lst = my_db.getRunInfo(runNumber=322355)

#my_db.getL1Prescales(runNumber=320149)

#lst = my_db.getHLTNameMap(runNumber=322355)

#lst = my_db.getDeadTime(runNumber=322355)

#my_db.getL1NameIndexAssoc(runNumber=322355)

#lst = my_db.getTriggerMode(runNumber=322355)

#lst = my_db.getL1APhysicsLost(runNumber=322355)

#lst = my_db.getL1APhysics(runNumber=322355)

#lst = my_db.getL1Triggers(runNumber=322355)

#lst = my_db.getL1ACalib(runNumber=322355)

#lst = my_db.getPrescaleNames(runNumber=322355)

#lst = my_db.getRunKeys(runNumber=322355)

#lst = my_db.getPSRates(runNumber=322355)

#my_db.getHLTSeeds(runNumber=322355)

#lst = my_db.getTriggerMode(runNumber=322355)

#lst = my_db.getStreamData(runNumber=322355)

#lst = my_db.getHLTRates(runNumber=322355)

#lst = my_db.getFillRuns(fillNumber=7132)

#lst = my_db.getPrimaryDatasets(runNumber=322355)

#my_db.getHLTPrescales(runNumber=322355)

#lst = my_db.getNumberCollidingBunches(runNumber=322355)

#my_db.getHLTPrescales(runNumber=322355)

#lst = my_db.getPathsInDatasets(runNumber=322355)

#lst2 = my_db.getPathsInStreams(runNumber=322355)

my_db2.getLHCStatus()

#lst = my_db.getGlobalTag(runNumber=322355)

#lst = my_db.getLSInfo(runNumber=322355)
