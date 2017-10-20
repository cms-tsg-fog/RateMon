//This script will take all the rate comparison plots from a 
//root file and print them into a single pdf for easy viewing
//Usage: root -b -l -q 'dumpToPDF.C+("infile.root", "fitName")'  

#include <iostream>
#include "TFile.h"
#include "TCanvas.h"
#include "TKey.h"

void
dumpToPDF(string inName, string fitName){
  TFile *fin = TFile::Open(inName.c_str(), "read"); assert(fin);


  string outName = inName;
  outName.replace(outName.find(".root"), 5, ".pdf");

  //fitName = "HLT_10LS_delivered_vs_rate_Run190949-191090.root";
  TFile *fFit = TFile::Open(fitName.c_str(), "read"); assert(fFit);

  TCanvas c1;
  c1.Print(Form("%s[", outName.c_str()), "pdf"); //Open .pdf

  //get list of keys
  int nplots = fin->GetNkeys(); 
  int nfits = fFit->GetNkeys(); 
  printf("nplots: %i, nfits: %i\n", nplots, nfits);
  if(nplots != nfits){
    cout<<" PDF output will be wrong since different number of triggers in fit and current run"<<endl;
    abort();
  }
  TList* plots = fin->GetListOfKeys();  
  TList* fits  = fFit->GetListOfKeys();
  for(int i=0; i<nplots; ++i){
    TKey* plot = (TKey*) plots->At(i);
    TKey* fit = (TKey*) fits->At(i);//assume they're in the same order for now

    if(!fin->GetKey(plot->GetName())){
      cout<<"Didn't find "<<plot<<". Removing."<<endl;
      abort();
    }
    if(!fFit->GetKey(fit->GetName())){
      cout<<"Didn't find "<<fit<<". Removing."<<endl;
      abort();
    }
    TCanvas* c = new TCanvas();
    c->Divide(1,2);

    TCanvas* cPlot = (TCanvas*) fin->Get(plot->GetName());
    c->cd(1);
    cPlot->DrawClonePad();

    TCanvas* cFit  = (TCanvas*) fFit->Get(fit->GetName());
    c->cd(2);
    cFit->DrawClonePad();

    string bookmarkName = "Title: ";
    bookmarkName += plot->GetName();

    c->Print(outName.c_str(), bookmarkName.c_str());
  }

  c1.Print(Form("%s]", outName.c_str()), "pdf"); //Close .pdf

}
