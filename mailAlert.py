#!/usr/bin/env python
import os
import smtplib
from email.mime.text import MIMEText
import time
import DatabaseParser
from datetime import datetime,timedelta
import sys
sys.path.append('/nfshome0/hltpro/scripts')
try:  ## so that we don't publish the list of on-calls in CVS
    import emailList
    eList=True
except:
    eList=False
def getLastRuns(h=24):
    lastRun,isCol,isGood = DatabaseParser.GetLatestRunNumber()
    
    curs = DatabaseParser.ConnectDB()
    query ="""SELECT A.RUNNUMBER,B.STARTTIME, B.STOPTIME,B.TRIGGERS
    FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_WBM.RUNSUMMARY B
    WHERE A.RUNNUMBER=B.RUNNUMBER AND B.TRIGGERS>100 AND A.RUNNUMBER > %d-1000""" % (lastRun,)
    #query = query +repr(datetime.now()+timedelta(days=-1))
    curs.execute(query)
    runs = []
    past = datetime.now()+timedelta(hours=-h)
    for r,starttime,stoptime,trig in curs.fetchall():
        if not stoptime or stoptime > past:
            runs.append((r,trig,stoptime))
    return runs

def digest(hours,maxRate=35,printAll=False):
    isBadRun=False
    text=""
    runs = getLastRuns(hours)
    for run,nTrig,time in runs:
        run,isCol,isGood = DatabaseParser.GetLatestRunNumber(run)
        runParser = DatabaseParser.DatabaseParser()
        runParser.RunNumber = run
        runParser.ParseRunSetup()
        #lumiRange = runParser.GetLSRange(0,99999,isCol)
        expressRates = {}
        if isCol:
            expressRates = runParser.GetTriggerRatesByLS("ExpressOutput")
        else:
            expressRates = runParser.GetTriggerRatesByLS("ExpressCosmicsOutput")
        ExpRate = sum(expressRates.values())/len(expressRates.values())
        #for ls in lumiRange:
        #    ExpRate+=expressRates.get(ls,0)
        #ExpRate/=len(lumiRange)
        if ExpRate > maxRate or printAll:
            text=text+"%s Run %d: %d Triggers, Average Express Rate %0.1f Hz\n" %(str(time),run,nTrig,ExpRate,)
        if ExpRate > maxRate:
            isBadRun = True
    try:
        text = text+" >> Processed Runs: %d-%d\n" % (runs[0][0],runs[-1][0],)
    except:
        text = text+" >> No Runs in last %d hours" % (hours,)
    return isBadRun,text

def sendMail(email,subject,to,fro,msgtxt):
    msg = MIMEText(msgtxt)
    msg['Subject'] = subject
    msg['From'] = fro
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail("hlt@cern.ch", email, msg.as_string())
    s.quit()

if __name__=='__main__':
    isBad,text = digest(1)
    sendMail("alex.mott@cern.ch","[HLTRateMonDebug] Express Rate Digest","HLTDebug","HLTDebug",text)
    if eList:
        if isBad:
            for email in emailList.emailList:
                sendMail(email,"[HLTRateMon] Express Rate Digest","HLT","HLT",text)
    else:
        print text
