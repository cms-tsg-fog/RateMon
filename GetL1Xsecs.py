from DatabaseParser import *

RUN = 180250

def DumpCSV(dat,filename):
    [x,y]=dat
    if not len(x)==len(y):
        return
    outfile = open(filename,'w')
    outfile.write("lumi/F:Rate/F\n")
    for xa,ya in zip(x,y):
        outfile.write("%f %f\n" % (xa,ya,) )
    outfile.close()

def GetL1():
    parser = DatabaseParser()
    parser.RunNumber = RUN
    parser.ParseRunSetup()
    return [parser.GetTotalL1Rates(),parser.GetLSRange(1,9999)]

def GetPSColumns(rateDict):
    psc=[]
    for rate,ps,lumi in rateDict.itervalues():
        psc.append(ps)
    return set(psc)

def MakeXY(rateDict,psCol,mask,xsec=False):
    x=[]
    y=[]
    for ls,val in rateDict.iteritems():
        [rate,ps,lumi] = val
        if ls in mask and ps==psCol:
            x.append(lumi)
            if xsec:
                y.append(rate/lumi)
    return [x,y]

if __name__ == '__main__':
    [rates,mask] = GetL1()
    print "Prescale Columns:"
    for column in GetPSColumns(rates):
        print column
        DumpCSV(MakeXY(rates,column,mask),"RateByLumi_Col%d.txt" % column)
        DumpCSV(MakeXY(rates,column,mask,True),"RateByXsec_Col%d.txt" % column)
