#charlie mueller May 17th 2016
# Imports
import cx_Oracle
import socket
# For the parsing
import re


########################
########################
##### usage: python dump_l1_prescales.py
#####
##### To dump prescales for a specific run, specify run number in test_query function
########################
########################


class DBQueryTool:

    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = 'cms_omds_adg' #offline
        else: self.dsn_ = 'cms_omds_lb' #online

        orcl = cx_Oracle.connect(user='cms_hlt_r',password='***REMOVED***',dsn=self.dsn_)
        orcl = cx_Oracle.connect(user='cms_trg_r',password='***REMOVED***',dsn=self.dsn_)
        # Create a DB cursor
        self.curs = orcl.cursor()
        
    def test_query(self):


        run_number = 273017


        query = """SELECT A.ALGO_INDEX, A.ALGO_NAME, B.PRESCALE, B.PRESCALE_INDEX FROM CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING A, CMS_UGT_MON.VIEW_UGT_RUN_PRESCALE B WHERE
        A.ALGO_INDEX=B.ALGO_INDEX AND A.RUN_NUMBER = B.RUN_NUMBER AND A.RUN_NUMBER=%s ORDER BY A.ALGO_INDEX""" % (run_number)
        
        self.curs.execute(query)
        
        l1_ps_table = {}
        bit_to_name_dict = {}
        ps_table = self.curs.fetchall()
        for object in ps_table:
            algo_index = object[0]
            algo_name = object[1]
            algo_ps = object[2]
            ps_index = object[3]
            #print algo_index," ",algo_name
            if not bit_to_name_dict.has_key(algo_index): bit_to_name_dict[algo_index] = algo_name
            if not l1_ps_table.has_key(algo_index): l1_ps_table[algo_index] = {}
            l1_ps_table[algo_index][ps_index] = algo_ps 
        for algo in l1_ps_table: print algo," ",bit_to_name_dict[algo]," :  ",l1_ps_table[algo]


## ----------- End of class ------------ ##

if __name__ == "__main__":
    query_tool = DBQueryTool()
    query_tool.test_query()
