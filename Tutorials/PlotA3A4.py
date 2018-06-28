import sys
sys.path.append('/home/lass/Dropbox/PhD/Software/MJOLNIR/')

import matplotlib.pyplot as plt
import numpy as np
from MJOLNIR.Data import DataSet
File1 = '../TestData/T0Phonon10meV.nxs'
File2 = '../TestData/T0Phonon10meV93_5A4.nxs'

DS = DataSet.DataSet(convertedFiles=[File1,File2])

files = DS.convertedFiles


planes2 = list(np.arange(64).reshape(8,8)) # Plot all planes binned with 8 pixels together
ax = [DS.createRLUAxes() for _ in range(len(planes2))] # Create custom axes for plotting

ax2 = DS.plotA3A4(files,planes=planes2,ax=ax)

counter = 0
for ax in ax2: # loop through axes to increase size and save
    fig = ax.get_figure()
    fig.set_size_inches(10.5, 10.5, forward=True)
    fig.tight_layout()
    fig.savefig('A3A4/{:03d}.png'.format(counter),format='png')
    counter+=1