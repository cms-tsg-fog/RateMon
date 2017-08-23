from HTMLGenerator import *

import os
import sys

# Builds the HTML info for the tables displayed on the left side of the front page
def buildRateTables(dataset_list):
    # Make the Rate Collections Table
    rc_attributes = {
        'id': 'rate_collections_table',
        'class': 'example table-stripeclass:alternate',
    }

    rc_header_cols = [
        {
            'content': 'Rate Collections',
            'attributes':
                {
                    'width': '120px',
                },
        }
    ]

    rc_rows = [
        [
            {'tags': [HyperLinkTag('./MoreTriggers/Streams/','Stream Rates')]},
        ],
        [
            {'tags': [HyperLinkTag('./MoreTriggers/Datasets/','Dataset Rates')]},
        ],
        [
            {'tags': [HyperLinkTag('./MoreTriggers/L1A_Rates/','L1A Rates')]},
        ],
        [
            {'tags': [HyperLinkTag('./MoreTriggers/L1_Triggers/','L1 Trigger Rates')]},
        ],
        [
            {'tags': [HyperLinkTag('./MoreTriggers/HLT_Triggers/','HLT Trigger Rates')]},
        ],
    ]

    rate_collections_table = TableTag(rc_attributes,rc_header_cols)
    fillTable(rate_collections_table,rc_rows)

    # Make the Triggers by Dataset Table
    td_attributes = {
        'id': 'triggers_by_dataset_table',
        'class': 'example table-stripeclass:alternate',
    }

    td_header_cols = [
        {
            'content': 'Triggers by Dataset',
            'attributes':
                {
                    'width': '120px'
                },
        },
    ]

    td_rows = []
    for dataset in dataset_list:
        new_element = []
        if len(dataset) > 18:
            # Crop long dataset names
            dataset_name = dataset[0:15] + '...'
        else:
            dataset_name = dataset
        dataset_path = './MoreTriggers/%s/' % dataset
        table_data = {
            'tags': [HyperLinkTag(dataset_path,dataset_name)],
        }
        new_element.append(table_data)
        td_rows.append(new_element)

    triggers_by_dataset_table = TableTag(td_attributes,td_header_cols)
    fillTable(triggers_by_dataset_table,td_rows)

    rate_tables_div_tag = DivisionTag()
    rate_tables_div_tag.addTag(rate_collections_table)
    rate_tables_div_tag.addTag(BreakTag())
    rate_tables_div_tag.addTag(triggers_by_dataset_table)

    return rate_tables_div_tag

# Builds the HTML info for displaying the monitored triggers on the front page
def buildMonitoredTriggersDisplay(save_dir,monitored_triggers_list):
    image_div_list = []
    for image_name in monitored_triggers_list:
        image_src = os.path.join(save_dir,'MoreTriggers/png/%s.png' % image_name)
        if not os.access(image_src,os.F_OK):
            # Check to make sure the image exists!
            print "WARNING: Unable to access: %s" % image_src
            continue
        image_src = './MoreTriggers/png/%s.png' % image_name
        image_tag = ImgTag()
        image_tag.addAttribute('width',355) # Original: 398
        image_tag.addAttribute('height',229)
        image_tag.addAttribute('border',0)
        image_tag.addAttribute('src',image_src)

        new_link = HyperLinkTag('./MoreTriggers/png/%s.png' % image_name,'')
        new_link.addAttribute('target','_blank')
        new_link.addTag(image_tag)

        text_div = DivisionTag()
        text_div.addAttribute('style','width:355px')
        text_div.setContent(image_name)

        new_div = DivisionTag()
        new_div.addAttribute('class','image')
        new_div.addTag(new_link)
        new_div.addTag(text_div)

        image_div_list.append(new_div)

    monitor_heading_tag = HeadingTag(3)
    monitor_heading_tag.setContent('Monitored Triggers:')
    monitor_heading_tag.addAttribute('style','margin: 0')

    image_div = DivisionTag()
    image_div.addTag(monitor_heading_tag)
    for element in image_div_list:
        image_div.addTag(element)

    return image_div

# Fills the specified table with the an array of rows (uses WBM style alternating colors for rows)
def fillTable(table,row_list = []):
    # row_list is just a list of lists --> row_list = [ [tag_info] ]
    for cell_list in row_list:
        row_attributes = {}
        if table.nRows() % 2 == 0:
            row_attributes['class'] = 'alternate'
        table.appendTableRow(row_attributes,cell_list)

# Read the list of monitored triggers from the specified .list file
def getMonitoredTriggersList(f_name='monitorlist_COLLISIONS.list'):
    path = f_name
    f = open(path,'r')

    print "Reading trigger file: %s" % path

    output_list = []
    for line in f:
        line = line.strip() # Remove whitespace/EOL chars
        if line[0] == "#":  # Ignore commented lines
            continue
        output_list.append(line)
    f.close()

    return output_list

# Get the list of group directories
def getGroupList(save_dir):
    ignore_dirs = ['png','L1_Triggers','HLT_Triggers','Streams','Datasets','L1A_Rates','Monitored_Triggers']
    dataset_list = []
    dir_path = os.path.join(save_dir,'MoreTriggers')
    for out in os.listdir(dir_path):
        if (os.path.isdir(os.path.join(dir_path,out))):
            if not out in ignore_dirs:
                dataset_list.append(out)
    return sorted(dataset_list)

# Returns the list of runs used to produce the displayed fits, extracts from the 'command_line.txt' file
def getFitRuns(fits_dir):
    f_name = 'command_line.txt'
    #search_str = 'python plotTriggerRates.py --createFit --nonLinear --AllTriggers'
    search_str = '--updateOnlineFits'

    f_path = os.path.join(fits_dir,f_name)
    f = open(f_path,'r')

    run_list = []
    for line in f:
        line = line.strip() # Remove whitespace/EOL chars
        index = line.rfind(search_str)
        if index < 0:
            continue
        else:
            index += len(search_str)
        sub_str = line[index:]
        sub_str = sub_str.strip()

        run_list = [int(x) for x in sub_str.split(" ")]
        break
    return run_list

# Main function used to build the entire HTML output file for displaying on WBM
def formatRatePlots(monitored_triggers_list,dataset_list,run_list,save_dir):
    # Need to feed in the following:
    #   monitored_triggers_list: List of plots to display on the front-page
    #   dataset_list: List of datasets to include in the 'triggers by dataset' table
    #   run_list: List of runs used to generate the fits in the displayed plots
    my_html = HTMLGenerator()

    # Use WBM CSS style
    style_link_tag = LinkTag()
    style_link_tag.addAttribute('rel','stylesheet')
    style_link_tag.addAttribute('type','text/css')
    style_link_tag.addAttribute('href','style.css')

    # Use WBM CSS style for tables
    table_link_tag = LinkTag()
    table_link_tag.addAttribute('rel','stylesheet')
    table_link_tag.addAttribute('type','text/css')
    table_link_tag.addAttribute('href','table.css')

    my_html.addHeadTag(style_link_tag)
    my_html.addHeadTag(table_link_tag)

    style_tag = StyleTag()
    style_tag.setContent('.image { float:left; margin: 5px; clear:justify; font-size: 6px; font-family: Verdana, Arial, sans-serif; text-align: center;}')
    my_html.addBodyTag(style_tag)

    runs_string = '%s' % run_list
    runs_string = runs_string[1:-1].replace(',','')

    runs_heading_tag = HeadingTag(3)
    runs_heading_tag.setContent('Runs used to produce fits:<br>%s' % runs_string)
    runs_heading_tag.addAttribute('style','margin-top:0;margin-bottom: 10')

    rate_tables_div_tag = buildRateTables(dataset_list)
    image_div = buildMonitoredTriggersDisplay(save_dir,monitored_triggers_list)

    # The parent table is a wrapper to contain (and align) the rate_tables and the monitored_trigger_plots
    parent_table = TableTag()
    td_list = [
        {
            'tags': [rate_tables_div_tag],
        },
        {
            'tags': [image_div],
        }
    ]
    parent_table.appendTableRow({'valign': 'top'},td_list)

    # Build the body of the HTML document

    # Don't add the runs_heading_tag yet...
    my_html.addBodyTag(runs_heading_tag)
    my_html.addBodyTag(parent_table)

    # Save the HTML file
    my_html.saveHTML(f_name='index.html',f_dir=save_dir)

if __name__ == "__main__":
    monitored_triggers = getMonitoredTriggersList(f_name='monitorlist_COLLISIONS.list')

    save_dir = sys.argv[1]
    dataset_list = getGroupList(save_dir=save_dir)
    run_list = getFitRuns(fits_dir='./Fits/All_Triggers/')

    formatRatePlots(
        monitored_triggers_list=monitored_triggers,
        dataset_list=dataset_list,
        run_list=run_list,
        save_dir=save_dir,
    )
