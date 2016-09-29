from DBParser import *

dbparser = DBParser()
recentRunsFill = dbparser.getRecentRuns()

lastFill = str(recentRunsFill[1])

print lastFill

runList = []
for item in recentRunsFill[0]:
    runList.append(str(item))

print " ".join(runList)
