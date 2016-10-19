from RateMonitor_rewrite import *

def test_run_input():
    run_list = [282092,282037,281976]   # Longer runs --> slow testing
    run_list = [282035,282034,281975]   # Shorter runs
    run_list = [282037,282035,282034,282033]    # Fill 5352
    run_list = [282035,282034,282033]

    # 282037 282035 282034 282033
    
    save_dir = "/afs/cern.ch/user/a/awightma/www/dev/rewrite_test2"

    monitor = RateMonitor()

    monitor.save_dir = save_dir
    monitor.run_list = run_list
    monitor.object_list = ["HLT_AK8DiPFJet280_200_TrimMass30_BTagCSV_p20",
                            "HLT_Ele115_CaloIdVT_GsfTrkIdT",
                            "HLT_HT650",
                            "L1_SingleEG24"]

    monitor.use_fills  = False
    monitor.use_pileup = True
    monitor.use_lumi   = False

    monitor.data_parser.mode = "triggers"

    monitor.plotter.use_fills   = False
    monitor.plotter.use_fit     = True
    monitor.plotter.show_errors = True
    monitor.plotter.show_eq     = True
    monitor.plotter.save_png    = True
    monitor.plotter.file_name   = "testing_plot_rewrite.root"

    monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
    monitor.plotter.name_X = "< PU >"
    monitor.plotter.units_X = ""

    monitor.run()

def test_fill_input():
    fill_list = [5352]
    save_dir  = "/afs/cern.ch/user/a/awightma/www/dev/rewrite_test1"

    monitor = RateMonitor()

    monitor.save_dir = save_dir
    monitor.fill_list = fill_list
    monitor.object_list = ["HLT_AK8DiPFJet280_200_TrimMass30_BTagCSV_p20",
                            "HLT_Ele115_CaloIdVT_GsfTrkIdT",
                            "HLT_HT650",
                            "L1_SingleEG24"]

    monitor.use_fills  = True   # Gets run_list from fills
    monitor.use_pileup = True
    monitor.use_lumi   = False

    monitor.data_parser.mode = "triggers"

    monitor.plotter.use_fills   = True     # Colors data by fills
    monitor.plotter.use_fit     = True
    monitor.plotter.show_errors = True
    monitor.plotter.show_eq     = True
    monitor.plotter.save_png    = True
    monitor.plotter.file_name   = "testing_plot_rewrite.root"

    monitor.plotter.label_Y = "pre-deadtime unprescaled rate / num colliding bx [Hz]"
    monitor.plotter.name_X  = "< PU >"
    monitor.plotter.units_X = ""

    monitor.run()

def test_dataset_input():
    fill_list = [5352]
    save_dir = "/afs/cern.ch/user/a/awightma/www/dev/rewrite_test1"

    monitor = RateMonitor()

    monitor.save_dir  = save_dir
    monitor.fill_list = fill_list

    monitor.use_fills  = True
    monitor.use_pileup = True
    monitor.data_parser.mode = "datasets"   # Need to decide how to implement this flag --> bools or strings? Who owns the flag?
    monitor.plotter.use_fills   = False
    monitor.plotter.use_fit     = False
    monitor.plotter.show_errors = False
    monitor.plotter.show_eq     = False
    monitor.plotter.save_png    = True
    monitor.plotter.file_name   = "testing_plot_rewrite.root"
    monitor.plotter.label_Y = "dataset rate / num colliding bx [Hz]"
    monitor.plotter.name_X  = "< PU >"
    monitor.plotter.units_X = ""

    monitor.run()

def test_stream_input():
    fill_list = [5352]
    save_dir = "/afs/cern.ch/user/a/awightma/www/dev/rewrite_test1"

    monitor = RateMonitor()

    monitor.save_dir  = save_dir
    monitor.fill_list = fill_list

    monitor.use_fills  = True
    monitor.use_pileup = True

    monitor.data_parser.mode = "streams"

    monitor.plotter.use_fills   = False
    monitor.plotter.use_fit     = False
    monitor.plotter.show_errors = False
    monitor.plotter.show_eq     = False
    monitor.plotter.save_png    = True
    monitor.plotter.file_name   = "testing_plot_rewrite.root"

    monitor.plotter.label_Y = "stream rate / num colliding bx [Hz]"
    monitor.plotter.name_X  = "< PU >"
    monitor.plotter.units_X = ""

    monitor.run()

if __name__ == "__main__":
    #test_run_input()
    #test_fill_input()
    #test_dataset_input()
    test_stream_input()
    print "We Ran!"