#charlie mueller May 30th 2016
import cx_Oracle
import socket
import sys


########################
########################
##### usage: python findRuns.py <L1_HLT_Key>
#####
##### example: python findRuns.py l1_hlt_collisions2016/v178  
########################
########################


class DBQueryTool:

    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = 'cms_omds_adg' #offline
        else: self.dsn_ = 'cms_omds_lb' #online

        #orcl = cx_Oracle.connect(user='cms_hlt_r',password='***REMOVED***',dsn=self.dsn_) #for access to db containing hlt menus
        orcl = cx_Oracle.connect(user='cms_trg_r',password='***REMOVED***',dsn=self.dsn_)
        self.curs = orcl.cursor()
        
    def test_query(self):
        try: l1_hlt_key = str(sys.argv[1])
        except: print "Usage: python findRuns.py <L1_HLT_Key>"; return
        
        output_file_name = "runs.txt"
        output_file = open(output_file_name, "w")
        output_file.write("L1_HLT_Key = %s\n\n" % (l1_hlt_key))

        query = """ SELECT DESCRIPTION FROM CMS_L1_HLT.V_L1_HLT_CONF_FULL WHERE ID='%s'""" % (l1_hlt_key)        
        self.curs.execute(query)
        desc = self.curs.fetchone()[0]
        output_file.write("Comments = %s\n\n" % (desc))
        
        query = """ SELECT RUNNUMBER FROM CMS_WBM.RUNSUMMARY WHERE TRIGGERMODE='%s'""" % (l1_hlt_key)        
        self.curs.execute(query)        
        run_numbers = self.curs.fetchall()

        for run_num in run_numbers: output_file.write("%s\n"%(run_num[0]))

        output_file.close()
        print "\nOutput in: %s\n" % (output_file_name)


## ----------- End of class ------------ ##

if __name__ == "__main__":
    
    query_tool = DBQueryTool()
    query_tool.test_query()
