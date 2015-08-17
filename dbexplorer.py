#!/usr/bin/env python
# Author: Nathaniel Rupprecht
# Created: June 29, 2015
# Last Modified: August 17, 2015

import cx_Oracle

# FILE NAME
fileName = "out.txt"

# Use: Prints all the table and column data available to the given cursor to the given file
def getData(curs, file):
    # Get pairs { table name, column name }
    curs.execute("select owner, table_name, column_name from all_tab_columns")
    
    columns = {} # A dictionary
    
    # Put our data into the dictionary
    count = 0
    for owner, table_name, column_name in curs.fetchall():
        if not columns.has_key(table_name): # Create the entry if it does not exist
            columns[table_name]=[owner, [column_name]]
        elif not column_name in columns[table_name][1]:
            columns[table_name][1].append(column_name)
        else: continue # Make sure we aren't double counting columns
        count += 1 

        # Do some counting
    nColumns = count
    nTables = len(columns)
    
    # Write DB table info
    for table_name in sorted(columns):
        number = len(columns[table_name][1])
        owner = columns[table_name][0]
        file.write(table_name + ":\nThere are %s columns. Table Owner: %s\nFull Name: %s.%s\n| " % (number, owner, owner, table_name))
        for col in columns[table_name][1]:
            file.write(col+" | ")
        file.write("\n\n")
    return [nTables, nColumns]
        

# main function
if __name__ == "__main__":
    file = open(fileName, "wb") # Open file

    # Get the HLT cursor
    orcl = cx_Oracle.connect(user='cms_hlt_r',password='convertMe!',dsn='cms_omds_lb')
    curs = orcl.cursor()
    file.write("***********************************************************************************\n")
    file.write("CMS HLT DATABASE\n")
    file.write("***********************************************************************************\n\n\n")
    nHLTTables, nHLTColumns = getData(curs, file)

    # Get the trigger cursor
    orcl = cx_Oracle.connect(user='cms_trg_r',password='X3lmdvu4',dsn='cms_omds_lb')
    curs = orcl.cursor()
    file.write("***********************************************************************************\n")
    file.write("CMS TRG DATABASE\n")
    file.write("***********************************************************************************\n\n\n")
    nTrgTables, nTrgColumns = getData(curs, file)

    # Find totals
    nTables = nHLTTables + nTrgTables
    nColumns = nHLTColumns + nTrgColumns

    # Print footer
    file.write("Fun facts: There are %s tables in the system, with a total of %s columns.\n\n\n" % (nTables, nColumns))
    file.write("Thank you for reading. That is all.")
    file.close() # Close file
    print "Database summary written to %s" % (fileName)
