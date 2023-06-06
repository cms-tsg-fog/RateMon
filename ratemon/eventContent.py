import copy
full = [
        'keep GlobalObjectMapRecord_hltGtStage2ObjectMap_*_*',
        'keep FEDRawDataCollection_rawDataCollector_*_*',
        'keep FEDRawDataCollection_source_*_*',
        'keep edmTriggerResults_*_*_*',
        'keep triggerTriggerEvent_*_*_*']

core_content = {
        'A': full,
        'B': full,
        'AlcaPi0': [
          'keep *_hltAlCaEtaEBUncalibrator_*_*',
          'keep *_hltAlCaEtaEEUncalibrator_*_*',
          'keep *_hltAlCaEtaRecHitsFilterEEonly_etaEcalRecHitsES_*',
          'keep *_hltAlCaPi0EBUncalibrator_*_*',
          'keep *_hltAlCaPi0EEUncalibrator_*_*',
          'keep *_hltAlCaPi0RecHitsFilterEEonly_pi0EcalRecHitsES_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*'],
        'AlcaPhiSym': [
          'keep *_hltAlCaPhiSymUncalibrator_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*'],
        'AlcaLumiPixel': [
          'keep *_hltFEDSelectorLumiPixels_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*'],
       'Calibration': [
          'keep *_hltEcalCalibrationRaw_*_*',
          'keep *_hltHcalCalibrationRaw_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*'],
        'DQMOnlineBeamspot': [
          'keep *_hltFEDSelectorTCDS_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep recoTracks_hltPFMuonMerging_*_*',
          'keep recoVertexs_hltVerticesPFFilter_*_*'],
        'DQM_PA': full,
        'EcalCalibration': [
          'keep *_hltEcalCalibrationRaw_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*'],
        'Express': full,
        'HLTDQM':  [
          'keep *_hltTriggerSummaryAOD_*_*',
          'keep DcsStatuss_hltScalersRawToDigi_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep LumiScalerss_hltScalersRawToDigi_*_*',
          'keep edmTriggerResults_*_*_*'],
        'NanoDST':[
          'keep *_hltFEDSelectorTCDS_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*'],
        'PhysicsDST':[
          'keep *_hltActivityPhotonClusterShape_*_*',
          'keep *_hltActivityPhotonEcalIso_*_*',
          'keep *_hltActivityPhotonHcalForHE_*_*',
          'keep *_hltActivityPhotonHcalIso_*_*',
          'keep *_hltCaloJetIDPassed_*_*',
          'keep *_hltElectronActivityDetaDphi_*_*',
          'keep *_hltHitElectronActivityTrackIsol_*_*',
          'keep *_hltKT6CaloJets_rho*_*',
          'keep *_hltL3MuonCandidates_*_*',
          'keep *_hltL3MuonCombRelIsolations_*_*',
          'keep *_hltMetClean_*_*',
          'keep *_hltMet_*_*',
          'keep *_hltPixelMatchElectronsActivity_*_*',
          'keep *_hltPixelVertices_*_*',
          'keep *_hltRecoEcalSuperClusterActivityCandidate_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*'],
        'RPCMON':[
          'keep *_hltCscSegments_*_*',
          'keep *_hltDt4DSegments_*_*',
          'keep *_hltMuonCSCDigis_MuonCSCStripDigi_*',
          'keep *_hltMuonCSCDigis_MuonCSCWireDigi_*',
          'keep *_hltMuonDTDigis_*_*',
          'keep *_hltMuonRPCDigis_*_*',
          'keep *_hltRpcRecHits_*_*',
          'keep *_hltGtStage2Digis_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*',
          'keep *_hltFEDSelectorTCDS_*_*',
          'keep *_hltGemRecHits_*_*',
          'keep *_hltMuonGEMDigis_AMC13Status_*',
          'keep *_hltMuonGEMDigis_AMCStatus_*',
          'keep *_hltMuonGEMDigis_OHStatus_*',
          'keep *_hltMuonGEMDigis_VFATStatus_*'],
        'TrackerCalibration':[
          'keep *_hltTrackerCalibrationRaw_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*'],
        'DQM': [
          'keep *_hltL3NoFiltersNoVtxMuonCandidates_*_*',
          'keep *_hltOnlineBeamSpot_*_*',
          'keep *_hltPFJetForBtag_*_*',
          'keep *_hltPixelTracks_*_*',
          'keep *_hltSelector8CentralJetsL1FastJet_*_*',
          'keep *_hltSiPixelClusters_*_*',
          'keep *_hltSiStripRawToClustersFacility_*_*',
          'keep FEDRawDataCollection_rawDataCollector_*_*',
          'keep FEDRawDataCollection_source_*_*',
          'keep GlobalObjectMapRecord_hltGtStage2ObjectMap_*_*',
          'keep edmTriggerResults_*_*_*',
          'keep triggerTriggerEvent_*_*_*'],
        }

collision_extra_content = {
        'DQM':[
          'keep *_hltHoreco_*_*',
          'keep *_hltSiPixelClustersCache_*_*',
          'keep *_hltDeepCombinedSecondaryVertexBJetTagsPF_*_*',
          'keep *_hltDeepCombinedSecondaryVertexBJetTagsCalo_*_*',
          'keep *_hltHfreco_*_*',
          'keep *_hltHbhereco_*_*',
          'keep *_hltEcalRecHit_*_*',
          'keep *_hltIter0HighPtTkMuTrackSelectionHighPurity_*_*',
          'keep *_hltEgammaGsfElectrons_*_*',
          'keep *_hltEgammaCandidates_*_*',
          'keep *_hltPixelVertices_*_*',
          'keep *_hltMergedTracks_*_*'],
        'DQMOnlineBeamspot': [
          'keep *_hltFEDSelectorOnlineMetaData_*_*']
       }

cosmic_extra_content = {}

requiredEventContent_collision = {key:core_content.get(key,[]) + collision_extra_content.get(key,[]) for key in set(list(core_content.keys()) + list(collision_extra_content.keys()))}
requiredEventContent_cosmic    = {key:core_content.get(key,[]) + cosmic_extra_content.get(key,[])    for key in set(list(core_content.keys()) + list(cosmic_extra_content.keys()))}
requiredEventContent_circulating = requiredEventContent_cosmic
