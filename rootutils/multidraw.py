"""
Efficiently draw multiple histograms with one loop over all events in a TTree
This script injects a MultiDraw method into TTree when it is imported.
"""

import os
import re
import ROOT

multidraw_cxx = """

// MultiDraw.cxx (code from pwaller)
// Draws many histograms in one loop over a tree.
// A little bit like a TTree::Draw which can make many histograms

#include <TTree.h>
#include <TH1D.h>
#include <TTreeFormula.h>
#include <TStopwatch.h>

#include <iostream>

// Get an Element from an array
#define EL( type, array, index ) dynamic_cast<type *>( array->At( index ) )

void MultiDraw(TTree *tree, TObjArray *formulae, TObjArray *weights, TObjArray *hists, UInt_t list_len)
{
  Long64_t i = 0;
  Long64_t num_events = tree->GetEntries();


  Double_t value = 0, weight = 0, common_weight = 0;

  Int_t tree_number = -1;

  for (i = 0; i<num_events; i++) {

    // Display progress every 10000 events
    if (i % 100000 == 0) {
      std::cout.precision(2);
      std::cout << "Done " << (double(i) / ( double(num_events)) * 100.0f) << "%   \r";
      std::cout.flush();
    }

    if (tree_number != tree->GetTreeNumber()) {
      tree_number = tree->GetTreeNumber();
    }

    tree->LoadTree(tree->GetEntryNumber(i));

    for (UInt_t j=0; j<list_len; j++) {
      // If the Value or the Weight is the same as the previous, then it can be re-used.
      // In which case, this element fails to dynamic_cast to a formula, and evaluates to NULL
      if ( EL(TTreeFormula, formulae, j) )
        value = EL(TTreeFormula, formulae, j)->EvalInstance();

      if ( EL(TTreeFormula, weights, j) )
        weight = EL(TTreeFormula, weights, j)->EvalInstance();

      if (weight)
        EL(TH1D, hists, j)->Fill(value, weight);
    }
  }
}
"""


def MakeTObjArray(the_list):
    """Turn a python iterable into a ROOT TObjArray"""

    result = ROOT.TObjArray()
    result.SetOwner()

    # Make PyROOT give up ownership of the things that are being placed in the
    # TObjArary. They get deleted because of result.SetOwner()
    for item in the_list:
        ROOT.SetOwnership(item, False)
        result.Add(item)

    return result


def MultiDraw(self, *draw_list):
    """
    Draws (projects) many histograms in one loop over a tree.

        Instead of:
        tree.Project("hname1", "ph_pt",  "weightA")
        tree.Project("hname2", "met_et", "weightB")

        Do:
        tree.MultiDraw( ("hname1", "ph_pt", "weightA" ),
                        ("hname2", "met_et", "weightB" ) )
    """


    hnames, variables, selections = [], [], []

    last_variable, last_selection = None, None

    histograms = []
    for i, drawexp in enumerate(draw_list):

        # Expand out origFormula and weight, otherwise just use weight of 1.
        hname, variable, selection = drawexp

        hist = ROOT.gDirectory.Get(hname)
        if not hist:
            raise RuntimeError( "MultiDraw: Couldn't find histogram to fill '%s' in current directory." % name )

        histograms.append(hist)

        # The following two 'if' clauses check that the next formula is different
        # to the previous one. If it is not, we add an ordinary TObject.
        # Then, the dynamic cast in MultiDraw.cxx fails, giving 'NULL', and
        # The previous value is used. This saves the recomputing of identical values
        if variable != last_variable:
            f = ROOT.TTreeFormula("variable%i" % i, variable, self)
            if not f.GetTree():
                raise RuntimeError("TTreeFormula didn't compile: " + variable)
            f.SetQuickLoad(True)
            variables.append(f)
        else:
            variables.append(ROOT.TObject())

        if selection != last_selection:
            f = ROOT.TTreeFormula("selection%i" % i, selection, self)
            if not f.GetTree():
                raise RuntimeError("TTreeFormula didn't compile: " + selection)
            f.SetQuickLoad( True )
            selections.append( f )
        else:
            selections.append( ROOT.TObject() )

        last_variable, last_selection = variable, selection


    # Only compile MultiDraw once
    try:
        from ROOT import MultiDraw as _MultiDraw
    except ImportError:
        ROOT.gInterpreter.Declare(multidraw_cxx)
        from ROOT import MultiDraw as _MultiDraw

    # Ensure that formulae are told when tree changes
    fManager = ROOT.TTreeFormulaManager()
    for variable in variables + selections:
        if type(variable) == ROOT.TTreeFormula:
            fManager.Add(variable)

    fManager.Sync()
    self.SetNotify(fManager)

    # Draw everything!
    _MultiDraw(self,
               MakeTObjArray(variables),
               MakeTObjArray(selections),
               MakeTObjArray(histograms),
               len(variables))

    return

ROOT.TTree.MultiDraw = MultiDraw
