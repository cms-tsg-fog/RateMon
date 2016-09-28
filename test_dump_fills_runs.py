from DBParser import *
import subprocess
#from RateMonitorNCR import *

#outputDirBase = "/afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/"


dbparser = DBParser()
recentRunsFill = dbparser.getRecentRuns()

lastFill = str(recentRunsFill[1])
#print lastFill
print 5340

thing = []
for item in recentRunsFill[0]:
    thing.append(str(item))

print " ".join(thing)




#-----------------------
#print lastFill
#print recentRuns
#
#
#commandString = []
#commandString.append("python plotTriggerRates.py")
##commandString.append("plotTriggerRates.py")
#commandString.append("--triggerList=monitorlist_COLLISIONS.list")
#commandString.append("--fitFile=Fits/2016/FOG.pkl")
#
#outputDirBase += lastFill
#
#print outputDirBase
#
#outputDirBaseArg = "--saveDirectory="+outputDirBase
#lastFillArg = "--useFills "+lastFill
#
#
#commandString.append(outputDirBaseArg)
#commandString.append(lastFillArg)
#
#subprocess.call(["mkdir",outputDirBase])
#subprocess.call(commandString)
