# -----------------------------------------------------------------------------
# Name:        html_table_parser
# Purpose:     Simple class for parsing an (x)html string to extract tables.
#              Written in python3
#
# Author:      Josua Schmid with hacks from Sam Harper
#
# Created:     05.03.2014
# Copyright:   (c) Josua Schmid 2014
# Licence:     GPLv3
# -----------------------------------------------------------------------------

from HTMLParser import HTMLParser


class HTMLTableParser(HTMLParser):
    """ This class serves as a html table parser. It is able to parse multiple
    tables which you feed in. You can access the result per .tables field.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self._in_td = False
        self._in_th = False
        self._in_title =False
        self._current_table = []
        self._current_row = []
        self._current_cell = []
        self.tables = []
        self.titles = []

    def handle_starttag(self, tag, attrs):
        """ We need to remember the opening point for the content of interest.
        The other tags (<table>, <tr>) are only handled at the closing point.
        """
        if tag == 'td':
            self._in_td = True
        if tag == 'th':
            self._in_th = True
        if tag == 'title':
            self._in_title = True

    def handle_data(self, data):
        """ This is where we save content to a cell """
#        print data,self._in_td,self._in_th
       # if self._in_td ^ self._in_th:
        if self._in_td or self._in_th:
#            print data,"adding"
            self._current_cell.append(data.strip())
        if self._in_title:
            self.titles.append(data.strip())
            

    def handle_endtag(self, tag):
        """ Here we exit the tags. If the closing tag is </tr>, we know that we
        can save our currently parsed cells to the current table as a row and
        prepare for a new row. If the closing tag is </table>, we save the
        current table and prepare for a new one.
        """
        if tag == 'td':
            self._in_td = False
        elif tag == 'th':
            self._in_th = False
        elif tag == 'title':
            self._in_title = False
            


        if tag in ['td', 'th']:
            final_cell = " ".join(self._current_cell).strip()
            self._current_row.append(final_cell)
            self._current_cell = []
        elif tag == 'tr':
            self._current_table.append(self._current_row)
            self._current_row = []
        elif tag == 'table':
            self.tables.append(self._current_table)
            self._current_table = []

