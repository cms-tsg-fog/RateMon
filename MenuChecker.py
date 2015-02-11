#!/usr/bin/env python

import os
import sys
import getopt
from MenuAnalyzer import MenuAnalyzer
from termcolor import colored, cprint

def usage():
    print "Usage: "+sys.argv[0]+" <path to cdaq area>"
    print "Options: "
    print "-v                          Verbose mode (print out ALL checks)"
    print "--doAnalysis=<analysis>     Specify a specific check to so (default: do all)"

def main():
    try:
        opt, args = getopt.getopt(sys.argv[1:],"v",["doAnalysis="])

    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    if len(args)<1:
        usage()
        sys.exit()

    menu = args[0]
    verbose = False
    toDo = []
    for o,a in opt: # get options passed on the command line
        if o=="-v":
            Verbose = True
        elif o=="--doAnalysis":
            toDo.append(a)
        else:
            print "\nUnknown option "+o
            sys.exit()

    
    analyzer = MenuAnalyzer(menu)
    if len(toDo)==0: analyzer.AddAllAnalyses()
    else:
        for a in toDo: analyzer.AddAnalysis(a)
    analyzer.Analyze()

    ## check the results
    if not analyzer.expressType=='':
        print "\nEXPRESS Reconstruction will be:  %s" % analyzer.expressType
    else:
        print "WARNING: Cannot determine express reconstruction"

    print "\n"
    failed=[]
    format = "ANALYSIS%26s  %s"
    pass_txt = colored("SUCCEEDED",'green')
    fail_txt = colored("FAILED",'red')
    for analysis,result in analyzer.Results.iteritems():
        if isinstance(result,list): # list output
            if len(result) == 0:
                print format % (analysis,pass_txt,)
            else:
                print format % (analysis,fail_txt,)
                failed.append(analysis)
        else:
            if result==0:
                print format % (analysis,pass_txt,)
            else:
                print format % (analysis,fail_txt,)
                failed.append(analysis)


    if len(failed)!=0: print "\nLIST OF FAILED ANALYSES:"
    for analysis in failed:
        print analyzer.ProblemDescriptions[analysis]+":  "
        for line in analyzer.Results[analysis]: print line
        print ""

if __name__=='__main__':
    main()
