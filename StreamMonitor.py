from DatabaseParser import *

class StreamMonitor:
    def getStreamACoreRatesByLS(self,parser,ls_list,config,isCol=True):
        a_rates = parser.GetTrigRatesInLSRange('AOutput',ls_list) # AOutput = Parking trigs + core trig
        prompt_a_rates = parser.GetTrigRatesInLSRange('DQMOutput',ls_list)
        b_rates = parser.GetTrigRatesInLSRange('BOutput',ls_list) # BOutput = Parking trigs ps'd by 20
        ps_columns = parser.GetPSColumnsInLSRange(ls_list)

        HLT_Stream_A = {}
        for ls in ls_list:
            a_rate = a_rates.get(ls,0)
            prompt_a_rate = prompt_a_rates.get(ls,0)*10
            b_rate = b_rates.get(ls,0)*20
            if isCol and (ps_columns.get(ls) != config.CircBeamCol):
                HLT_Stream_A[ls] = prompt_a_rate
            else:
                HLT_Stream_A[ls] = a_rate - b_rate

        return HLT_Stream_A


    def getStreamARatesByLS(self,parser,ls_list):
        a_rates = parser.GetTrigRatesInLSRange('AOutput',ls_list) # AOutput = Parking trigs + core trig

        return a_rates

    def compareStreamARate(self, config, curr_stream_a, ls_list,av_inst_lumi,in_coll):
        if curr_stream_a > config.MaxStreamARate:
            bad_stream_a = True
        else:
            bad_stream_a = False
        
        ## if in_coll:
##             try:
##                 pkl_file = open(config.FitFileName, 'rb')
##                 fit_input = pickle.load(pkl_file)

##                 pred_stream_a = fit_input['HLT_Stream_A'][1]+fit_input['HLT_Stream_A'][2]*av_inst_lumi+fit_input['HLT_Stream_A'][3]*av_inst_lumi*av_inst_lumi
##                 sigma = fit_input['HLT_Stream_A'][5]
 
##                 per_diff = (curr_stream_a - pred_stream_a)/pred_stream_a * 100
##                 sigma_diff = (curr_stream_a - pred_stream_a)/sigma

##                 if abs(sigma_diff) > config.DefAllowRateSigmaDiff*2 and config.DefWarnOnSigmaDiff:
##                     bad_stream_a = True
##                 if abs(per_diff) > config.DefAllowRatePercDiff and not config.DefWarnOnSigmaDiff:
##                     bad_stream_a = True

##             except:  #No fit for stream a; if one is desired, run DatabaseRatePredictor.py with a trigger list including 'HLT_Stream_A'
##                 pass

        return bad_stream_a
