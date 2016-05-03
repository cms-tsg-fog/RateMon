# Imports
import cx_Oracle
import socket
# For the parsing
import re


class DBQueryTool:

    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = 'cms_omds_adg' #offline
        else: self.dsn_ = 'cms_omds_lb' #online

        orcl = cx_Oracle.connect(user='cms_hlt_r',password='convertMe!',dsn=self.dsn_)
        orcl = cx_Oracle.connect(user='cms_trg_r',password='X3lmdvu4',dsn=self.dsn_)
        # Create a DB cursor
        self.curs = orcl.cursor()

    def test_query(self):

#        query="""SELECT MAX(A.RUNNUMBER), MAX(B.LIVELUMISECTION) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0 """
        query="""SELECT LAST(B.LUMISECTION) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0 """
#        query="""SELECT column_name FROM all_tab_cols WHERE table_name = 'LUMI_SECTIONS' AND owner = 'CMS_RUNTIME_LOGGER'"""
        
        self.curs.execute(query)
        print self.curs.fetchall()
#        print self.curs.fetchone()



## ----------- End of class ------------ ##

if __name__ == "__main__":
    query_tool = DBQueryTool()
    query_tool.test_query()
