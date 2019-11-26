
# -----------------------------------------------------------------------------
# Name:        cern sso website parser
# Purpose:     simple function to read the content of a cern sso protected website in python
#              highly wbm biased
#
# Author:      Sam Harper
#
# Created:     01.08.2015
# Copyright:   (c) Sam Harper 2015
# Licence:     GPLv3
# -----------------------------------------------------------------------------

from htmlTableParser import HTMLTableParser

def printCookieHelp():
    cmdToGetWBMSSOCookie="cern-get-sso-cookie --krb -r -u https://cmswbm.web.cern.ch/cmswbm -o $SSO_COOKIE"
    print "a SSO cookie be obtained by typing \"%s\"" % cmdToGetWBMSSOCookie
    print "more information can be found at http://linux.web.cern.ch/linux/docs/cernssocookie.shtml"
      

def readURL(url):
    import cookielib, urllib2,os,sys

    cookieLocation=os.environ.get('SSO_COOKIE')
    if cookieLocation==None:
        print "please set the enviroment varible SSO_COOKIE to point to the location of the CERN SSO cookie"
        printCookieHelp()
        sys.exit()

    import os.path
    if os.path.isfile(cookieLocation)==False:
        print "cookie %s does not exist " % cookieLocation
        printCookieHelp()
        sys.exit()

    pythonVersionStr=sys.version.split()[0].split(".")
    pythonVersion=float(pythonVersionStr[0]+"."+pythonVersionStr[1])
    if pythonVersion<2.7:
        print "Warning python version is: "
        print sys.version
        print "problems have been encountered in 2.6, suggest you move to>= 2.7 (CMSSW version)"
        import time
        time.sleep(5)
        
    cj = cookielib.MozillaCookieJar(cookieLocation)
    cj.load()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    return opener.open(urllib2.Request(url)).read()

def parseURLTables(url):
    parser = HTMLTableParser()
    parser.feed(readURL(url))
    try:
        if parser.titles[0]=="Cern Authentication":
            print "cern authentication page detected, you need to renew your sso cookie"
            printCookieHelp()
            import time
            time.sleep(5)
    except:
        pass
    return parser.tables

#url="https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/RunSummary?RUN=253813&DB=default"
#print parseURLTables("https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/RunFiles?RUN=%s" % 253813)
#print parseURLTables(url)
