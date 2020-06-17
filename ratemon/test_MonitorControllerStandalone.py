
from DBParser import *
from RateMonitor import *

# Very similar to MonitorController from plotTriggerRates, but pass it args instead of specifying args from CLI
class MonitorControllerStandalone: 
    def __init__(self,dbCfg,trgLst,vsLS,useFills,data):

        #print (dbCfg)
        self.parser = DBParser(dbCfg)
        self.rate_monitor = RateMonitor(dbCfg)

        # Default options:
        # type: () -> None
        self.do_cron_job = False

        # Set the default state for the rate_monitor and plotter to produce plots for triggers
        self.rate_monitor.object_list = []

        self.rate_monitor.plotter.set_plotter_fits = False
        self.rate_monitor.plotter.compare_fits = False

        self.rate_monitor.use_fills          = False
        self.rate_monitor.use_pileup         = True
        self.rate_monitor.use_lumi           = False
        self.rate_monitor.make_fits          = False
        self.rate_monitor.update_online_fits = False

        self.rate_monitor.data_parser.normalize_bunches  = True
        self.rate_monitor.data_parser.use_prescaled_rate = False
        self.rate_monitor.data_parser.use_cross_section  = False

        self.rate_monitor.data_parser.use_L1_triggers  = True
        self.rate_monitor.data_parser.use_HLT_triggers = True
        self.rate_monitor.data_parser.use_streams  = False 
        self.rate_monitor.data_parser.use_datasets = False
        self.rate_monitor.data_parser.use_L1A_rate = False

        self.rate_monitor.fitter.use_best_fit = False

        self.rate_monitor.plotter.color_by_fill  = False       # Determines how to color the plots
        self.rate_monitor.plotter.use_fit        = False
        self.rate_monitor.plotter.use_multi_fit  = False
        self.rate_monitor.plotter.show_errors    = False
        self.rate_monitor.plotter.show_eq        = False
        self.rate_monitor.plotter.save_png       = True
        self.rate_monitor.plotter.save_root_file = True
        self.rate_monitor.plotter.show_fit_runs  = False

        self.rate_monitor.plotter.root_file_name   = "rate_plots.root"
        self.rate_monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
        self.rate_monitor.plotter.name_X  = "< PU >"
        self.rate_monitor.plotter.units_X = ""

        self.rate_monitor.plotter.ls_options['show_bad_ls']  = False
        self.rate_monitor.plotter.ls_options['rm_bad_beams'] = False
        self.rate_monitor.plotter.ls_options['rm_bad_det']   = False

        # Trigger list:
        trigger_list = trgLst
        self.rate_monitor.object_list = trigger_list
        self.rate_monitor.data_parser.hlt_triggers = []
        self.rate_monitor.data_parser.l1_triggers = []
        for name in trigger_list:
            if name[0:4] == "HLT_":
                self.rate_monitor.data_parser.hlt_triggers.append(name)
            elif name[0:3] == "L1_":
                self.rate_monitor.data_parser.l1_triggers.append(name)

        if vsLS:
            self.rate_monitor.use_pileup = False
            self.rate_monitor.use_lumi = False
            self.rate_monitor.use_LS = True

        if useFills:
            self.rate_monitor.use_fills = True
            self.rate_monitor.plotter.color_by_fill = True  # Might want to make this an optional switch

        # Process runs/fills
        if len(data) > 0: # There are arguments to look at
            arg_list = data
            if self.rate_monitor.use_fills:
                self.rate_monitor.fill_list = arg_list
                self.rate_monitor.fitter.data_dict['user_input'] = self.getRuns(arg_list)
            else:
                self.rate_monitor.fill_list = []
                self.rate_monitor.fitter.data_dict['user_input'] = arg_list

        # Append the user specified fills or runs to the dictionary made from the compareFits text file 
        # (Note: compareFits option not yet implemented)
        unique_runs = set()
        for data_group,runs in self.rate_monitor.fitter.data_dict.items():
            unique_runs = unique_runs.union(runs)
        self.rate_monitor.run_list = list(unique_runs)
        print ("Run list:",self.rate_monitor.run_list )

        if len(self.rate_monitor.run_list) == 0:
            print("ERROR: No runs specified!")
            return False

        # Run rate_monitor.run:
        self.rate_monitor.run()


    # Gets the runs from each fill specified in arg_list
    def getRuns(self,arg_list):
        # type: (List[int]) -> List[int]
        if len(arg_list) == 0:
            print("No fills specified!")
            return []

        run_list = []
        fill_map = {}   # {run_number: fill_number}
        for fill in sorted(arg_list):
            print("Getting runs from fill %d..." % fill)
            new_runs = self.parser.getFillRuns(fill)
            if len(new_runs) == 0:
                print("\tFill %d has no eligible runs!")
                continue
            for run in new_runs:
                fill_map[run] = fill
            run_list += new_runs
        self.rate_monitor.plotter.fill_map = fill_map
        return run_list

