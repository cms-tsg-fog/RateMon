import sys
import csv
import array
import math
from colors import *
write = sys.stdout.write

def PrettyPrintTable(Headers,Data,ColWidths,WarningCol=[],border='*'):
   
   PrintHLine(ColWidths,border)
   PrintLine(Headers,ColWidths,False,border)
   PrintHLine(ColWidths,border)
   if WarningCol==[]:
      WarningCol=[False]*len(Data)
   for [line,Warn] in zip(Data,WarningCol):
       PrintLine(line,ColWidths,Warn,border)
   PrintHLine(ColWidths,border)

def PrintHLine(ColWidths,border): ## writes a horizontal line of the right width
   #write = sys.stdout.write
   for entry in ColWidths:
      write(border)
      for i in range(entry):
         write(border)
   write(border)
   write('\n')

def PrintLine(line,ColWidths,Warn,border):
   assert Warn in [True,False]
   try:
      assert len(line)==len(ColWidths)
   except:
      print line
      print ColWidths
      raise
   if Warn:
      write(bcolors.FAIL)
   else:
      write(bcolors.OKGREEN)
   if "Trigger" in str(line[0]):
      write(bcolors.ENDC)
       
   for [width, entry] in zip(ColWidths,line):
      write(border)
      try:
         entry = str(entry)
      except:
         print "\n\n\n Weird Data .. Bailing out\n\n"
         sys.exit(0)
      for i in range(width):
         if i==0:
            write(' ')
         elif i<len(entry)+1:
            write(entry[i-1])
         else:
            write(' ')
   write(border)
   write('\n')
   write(bcolors.ENDC)



#################################################
#one method of determining rate differences
def priot(wp_bool,print_trigger,meanps,f1,f2,fit_type,av):
    if wp_bool:
        global w2
        lumi=8000
        x0 = f1.GetParameter(0)
        x1 = f1.GetParameter(1)
        linear = x0 + x1*lumi

        if fit_type  == "line":
            z0 = f2.GetParameter(0)
            z1 = f2.GetParameter(1)
            z2 = 0
            z3 = 0
            fit = z0 + z1*lumi
        elif fit_type  == "quad":
            z0 = f2.GetParameter(0)
            z1 = f2.GetParameter(1)
            z2 = f2.GetParameter(2)
            z3 = 0
            fit = z0 + z1*lumi +z2*lumi*lumi
        elif fit_type == "cubic":
            z0 = f2.GetParameter(0)
            z1 = f2.GetParameter(1)
            z2 = f2.GetParameter(2)
            z3 = f2.GetParameter(3)
            fit = z0 + z1*lumi +z2*lumi*lumi +z3*lumi*lumi*lumi
        elif fit_type == "expo":
            z0 = f2.GetParameter(0)
            z1 = f2.GetParameter(1)
            z2 = f2.GetParameter(2)
            z3 = f2.GetParameter(3)
            fit = z0 + z1*math.exp(z2+z3*lumi)

        diff = fit - linear
        psdiff = diff/meanps
        linearChiSqNDOF = f1.GetChisquare()/f1.GetNDF()
        fitChiSqNDOF = f2.GetChisquare()/f2.GetNDF()
        metric = diff/linear
#        metric = diff/av        
        
        if priot.has_been_called==False:
            f2 = open('nonlinear.csv',"wb")
            w2 = csv.writer(f2)
            w2.writerow(["Trigger","diff@"+str(lumi),"diff (prescaled)","ps","fit type","linear ChiSq/ndof","fit ChiSq/ndof","average rate","metric","x0","x1","z0","z1","z2","z3"])
            w2.writerow([str(print_trigger),diff,psdiff,meanps,fit_type,linearChiSqNDOF,fitChiSqNDOF,av,metric,x0,x1,z0,z1,z2,z3])
        elif priot.has_been_called==True:
            w2.writerow([str(print_trigger),diff,psdiff,meanps,fit_type,linearChiSqNDOF,fitChiSqNDOF,av,metric,x0,x1,z0,z1,z2,z3])

        priot.has_been_called=True

#################################################

def prettyCSVwriter(f_out,ColWidths,Headers,Data,WarningCol=[]):
   file = open(f_out,'wb')
   c = csv.writer(file)
   PrintCSV(c,ColWidths,Headers,False)
   if WarningCol==[]:
      WarningCol=[False]*len(Data)
   for [line,Warn] in zip(Data,WarningCol):
       PrintCSV(c,ColWidths,line,Warn)
#################################################
def PrintCSV(c,ColWidths,line,Warn):
   rowlist = []
   assert Warn in [True,False]
     
   for [width, entry] in zip(ColWidths,line):
      try:
         entry = str(entry)
      except:
         print "\n\n\n Weird Data .. Bailing out\n\n"
         sys.exit(0)

      rowlist.append(entry)
      
   if "Trigger" in line[0]:
      rowlist.append("Warn?")
   else:
      rowlist.append(Warn)
   c.writerow(rowlist)
#################################################
