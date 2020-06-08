#!/usr/bin/env python
import smtplib
from email.mime.text import MIMEText
import DatabaseParser
from datetime import datetime,timedelta
import sys
import socket
sys.path.append('/nfshome0/hltpro/scripts')

emailList = ["cms-tsg-fog@cern.ch", "cms-l1t-operations@cern.ch"]

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
            expressRates = runParser.GetTriggerRatesByLS("HLTriggerFinalPath") #ExpressCosmicsOutput
        
        ExpRate = 0
        if len(list(expressRates.values()))>0:
            ExpRate = sum(expressRates.values())/len(list(expressRates.values()))
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

def sendMail(email,subject,sender,msgtxt):
    msg = MIMEText(msgtxt)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = email
    s = smtplib.SMTP('localhost')
    #s.sendmail("hlt@cern.ch", email, msg.as_string())
    #s.sendmail(email, email, msg.as_string())
    s.sendmail(sender,email,msg.as_string())
    s.quit()

def mailAlert(text):
    sender = "FOG <cms-tsg-fog@cern.ch>"
    subject = "[HLTRateMon] Trigger Rate Warning"
    host = "_".join(socket.gethostname().split('.'))
    text += "\nSent from: %s" % host
    try:
        for email in emailList:
            #sendMail(email,"[HLTRateMon] Trigger Rate Warning","HLT",text)
            sendMail(email,subject,sender,text)
            print("Mail sent to:", email)
    except:
        print("Failed to send mail")
        print(text)

if __name__=='__main__':
    sender = "FOG <cms-tsg-fog@cern.ch>"
    rec = "andrew.steven.wightman@cern.ch"
    text = "Some test text"
    text += "\nSent from: %s" % socket.gethostname()

    msg = MIMEText(text)
    msg['Subject'] = "[HLTRateMonDebug] Test Subject"
    msg['From'] = sender
    msg['To'] = rec

    #s = smtplib.SMTP('localhost')
    #s.sendmail(sender,rec,msg.as_string())
    #s.quit()

    sendMail(rec,"[HLTRateMonDebug] Test Subject",sender,text)

    #isBad,text = digest(1)
    #sendMail("a.zucchetta@cern.ch","[HLTRateMonDebug] Express Rate Digest","HLTDebug","HLTDebug",text)
    #sendMail("charles.mueller@cern.ch","[HLTRateMonDebug] Express Rate Digest","HLTDebug","HLTDebug",text)
    #try:
    #    if isBad:
    #        for email in emailList.emailList: sendMail(email,"[HLTRateMon] Express Rate Digest","HLT","HLT",text)
    #except:            
    #    print text
