from HTMLParser import HTMLParser
from urllib2 import urlopen
import cPickle as pickle
import sys

class Page1Parser(HTMLParser):
    
    def __init__(self):
        HTMLParser.__init__(self)
        self.InRow=0
        self.InEntry=0
        self.table =  []
        self.tmpRow = []
        self.hyperlinks = []
        self.RunNumber = 0
        self.TriggerRates = []
        self.Nevts = []
        self.LiveLumiByLS = []
        self.DeliveredLumiByLS = []
        self.FirstLS = -1
        self.LastLS = -1
        self.AvLiveLumi = []
        self.AvDeliveredLumi = []
        self.AvDeadtime = []
        self.DeadTime = []#grant
        self.L1Prescales=[]
        self.RunPage = ''
        self.RatePage = ''
        self.LumiPage = ''
        self.L1Page=''
        self.L1_LS_Page = ''#grant
        self.PrescaleColumn=[]
        self.PrescaleColumnString = ''

    def _Parse(self,url):
        self.table = []
        self.hyperlinks = []
        try:
            req = urlopen(url)
            self.feed(req.read())
        except:
            print "Error Getting page: "+url
            print "Please retry.  If problem persists, contact developer"
            sys.exit(1)
            
    def handle_starttag(self,tag,attrs):
        if tag == 'a' and attrs:
            self.hyperlinks.append(attrs[0][1])
        if tag == 'tr':
            self.InRow=1
        if tag == 'td':
            self.InEntry=1

    def handle_endtag(self,tag):
        if tag =='tr':
            if self.InRow==1:
                self.InRow=0
                self.table.append(self.tmpRow)
                self.tmpRow=[]
        if tag == 'td':
            self.InEntry=0

    def handle_data(self,data):
        if self.InEntry:
            self.tmpRow.append(data)

    def ParsePage1(self):
        try:
            # Find the first non-empty row on page one
            MostRecent = self.table[0]
            for line in self.table:
                if line == []:
                    continue # skip empty rows, not exactly sure why they show up
                MostRecent = line
                break # find first non-empty line
            TriggerMode = MostRecent[3]
            isCollisions = not (TriggerMode.find('l1_hlt_collisions') == -1)
            if not isCollisions:
                return ''
            self.RunNumber = MostRecent[0]
            for link in self.hyperlinks:
                if not link.find('RUN='+self.RunNumber)==-1:
                    self.RunPage = link
                    return link
        except:
            print "Cannot parse Page 1 to find the most recent run. Is WBM down?  If not, and this message persists, post problem on elog!"
            sys.exit(0)
        
    def ParseRunPage(self):
        try:
            for entry in self.hyperlinks:
                entry = entry.replace('../../','http://cmswbm/')
                if not entry.find('HLTSummary') == -1:
                     self.RatePage = entry
                if not entry.find('L1Summary') == -1:
                    self.L1Page = entry
                if not entry.find('LumiSections') == -1:
                    self.LumiPage = "http://cmswbm/cmsdb/servlet/"+entry
            return [self.RatePage,self.LumiPage,self.L1Page]
        except:
            print "Cannot parse Run Page. Is WBM down?  If not, and this message persists, post problem on elog!"
            sys.exit(0)

    def ParseRunSummaryPage(self):
        try:
            for line in self.table:
                if not len(line)>6:  # All relevant lines in the table will be at least this long
                    continue
                if line[1].startswith('HLT_'):
                    TriggerName = line[1][:line[1].find(' ')] # Format is HLT_... (####), this gets rid of the (####)
                    TriggerRate = float(line[6].replace(',','')) # Need to remove the ","s, since float() can't parse them
                    self.Nevts.append([TriggerName,int(line[3]),int(line[4]),int(line[5]),line[9]]) # 3-5 are the accept columns, 9 is the L1 seed name
                    PS=0
                    if int(line[4])>0:
                        PS = float(line[3])/float(line[4])

                    self.TriggerRates.append([TriggerName,TriggerRate,PS,line[9]])
        except:
            print "Cannot parse HLT Rate Page. Is WBM down?  If not, and this message persists, post problem on elog!"
            sys.exit(0)

    def ParseLumiPage(self, StartLS=999999, EndEndLS=111111):
        #previous_lumi = 0 ##Andrew - This and following lines with previous_lumi stop parsing when "Active" goes red
        #already_continued = False
        try:
            for line in self.table:
                if len(line)<2 or len(line)>12:
                    continue
                if int(line[0]) > EndEndLS:
                    continue

                #if float(line[6]) == previous_lumi and float(line[4]) != 0 and int(line[2]) == 0 and self.FirstLS != -1: #Stops when "Active" goes red
                    #already_continued = True
                    #continue
                #if already_continued == True:
                    #continue

                self.LiveLumiByLS.append(float(line[6]))  # Live lumi is in position 6
                self.DeliveredLumiByLS.append(float(line[5])) #Delivered lumi is in position 5
                self.PrescaleColumn.append(int(line[2]))     # Prescale column is in position 2

                #if float(line[4]) != 0 and int(line[2]) == 0 and self.FirstLS != -1: #Initializes last_lumi when Prescale goes to 0
                    #previous_lumi = float(line[6])
                
                if self.FirstLS == -1 and float(line[6]) > 0:  # live lumi is in position 6, the first lumiblock with this > 0 should be recorded
                    self.FirstLS = int(line[0])
 
            if not StartLS==999999:
 
                if StartLS<0:  # negative startLS means we want to do sliding window
                    StartLS = len(self.LiveLumiByLS)+StartLS-3 #start LS is -1*window, plus an offset of 3 LS to mitigate problems from parsing WBM live

                if StartLS < self.FirstLS:
                    print "\n>>> Selected LS is before stable beam, defaulting to first LS of stable beam\n"
                elif StartLS>len(self.LiveLumiByLS):
                    print "\n>>> Selected LS is out of range!"
                    sys.exit(0)
                else:
                    self.FirstLS = StartLS

            self.FirstLS-=2 ##The parsing starts from the second lumisection, so index = 0 corresponds to LS = 2, index = 5 -> LS = 7, etc.
            if EndEndLS == 111111:
                self.LastLS = self.FirstLS + (len(self.LiveLumiByLS[self.FirstLS:]) - 1) - 3 #len() is one off, plus WBM parsing offset
            else:
                self.LastLS = EndEndLS - 2 ##The parsing starts from the second lumisection, so index = 0 corresponds to LS = 2, index = 5 -> LS = 7, etc
                
            self.AvLiveLumi = 1000 * ( max(self.LiveLumiByLS[self.FirstLS:self.LastLS]) - self.LiveLumiByLS[self.FirstLS] ) / ( ( len(self.LiveLumiByLS[self.FirstLS:self.LastLS]) - 1 ) * 23.3 )
            self.AvDeliveredLumi = 1000 * ( max(self.DeliveredLumiByLS[self.FirstLS:self.LastLS]) - self.DeliveredLumiByLS[self.FirstLS] ) / ( ( len(self.DeliveredLumiByLS[self.FirstLS:self.LastLS]) - 1 ) * 23.3 )

            self.AvDeadtime = 100 * (self.AvDeliveredLumi - self.AvLiveLumi) / (self.AvDeliveredLumi + 0.1)
            
            if max(self.PrescaleColumn[self.FirstLS:]) == min(self.PrescaleColumn[self.FirstLS:]):
                self.PrescaleColumnString = str(self.PrescaleColumn[self.FirstLS])
            else:
                self.PrescaleColumnString = str(max(self.PrescaleColumn[self.FirstLS:]))+" and "+str(min(self.PrescaleColumn[self.FirstLS:]))
            self.FirstLS+=2 ##For purposes of printing output later on
            self.LastLS+=2

        except:
            print "Cannot parse Lumi Page. Is WBM down?  If not, and this message persists, post problem on elog!"
            sys.exit(0)

    def ParseL1Page(self):
        try:
            for line in self.table:
                if len(line) < 9:
                    continue
                if line[1].startswith('L1_'):
                    self.L1Prescales.append([line[1],float(line[8])])
        except:
            print "Cannot parse L1 Page. Is WBM down?  If not, and this message persists, post problem on elog!"
            sys.exit(0)

    def Parse_LS_L1Page(self):
        try:
            self.DeadTime=[]
            for line in self.table:
                if line != [] and len(line)<5:
                        MostRecent = line[:]
                        if '%' in MostRecent:
                            print MostRecent
                            self.DeadTime.append(MostRecent[2])
        except:
            print"Unable to parse DeadTimes"
            sys.exit(0)
        
    def Save(self, fileName):
        pickle.dump( self, open( fileName, 'w' ) )

    def Load(self, fileName):
        self = pickle.load( open( fileName ) )
