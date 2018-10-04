#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 24 14:46:53 2018

@author: Jakob Lass

Conversion tool for converting output h5 files to nxs files.
"""


import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib._pylab_helpers
import os
import sys
import _tools
settingsName = 'ConvertionDir'

sys.path.append('/home/lass/Dropbox/PhD/Software/MJOLNIR/')

from MJOLNIR.Data import DataSet

import warnings



parser = argparse.ArgumentParser(description="Conversion tool for converting output h5 files to nxs files.")
parser.add_argument("DataFile", nargs ='?', default=argparse.SUPPRESS, type=str,help="Data file to convert. If none provided file dialog will appear.")
parser.add_argument("-s", "--save", type=str, default= '',help="Location to which the generated file will be saved.")
parser.add_argument("-b", "--binning", type=int, default= '8',help="Binning performed. Default '8'")

args = parser.parse_args()


if not 'DataFile' in args:
    startingPath = _tools.loadSetting(settingsName)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except:
        import Tkinter as tk
        import tkFileDialog as filedialog
    
    root = tk.Tk()
    root.withdraw()
    
    
    files = filedialog.askopenfilenames(initialdir=startingPath, title = 'Select file(s) for conversion',filetypes=(('CAMEA Data files',('*.h5')),('All Files','*')))
    
    if len(files)==0: # No file chosen
        sys.exit()
    
    
    directory = os.path.split(files[0])[0]
    _tools.updateSetting(settingsName,directory)


else:
    files = args.DataFile
binning = args.binning

if not args.save is '':
    saveLocation = args.save
else:
    saveLocation = directory
    
 
for file in files:
    dataSet = DataSet.DataSet(dataFiles = file)
    dataSet.convertDataFile(binning=binning,saveLocation=saveLocation)