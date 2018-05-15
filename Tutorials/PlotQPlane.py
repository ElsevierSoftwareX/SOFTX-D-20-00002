import sys
sys.path.append('../')

from MJOLNIR.Data import DataSet
import numpy as np
file = '../TestData/cameasim2018n000011.nxs'

Data = DataSet.DataSet(convertedFiles=file)
EMin = np.min(Data.energy)
EMax = EMin+0.75

ax = Data.plotQPlane(EMin,EMax,binning='polar',xBinTolerance=0.025,yBinTolerance=0.025,
                     enlargen=True,log=False,ax=None,RLUPlot=True,vmin=0,vmax=1e-6)

ax.set_clim(0,5e-7)

ax = Data.plotQPlane(EMin,EMax,binning='xy',xBinTolerance=0.025,yBinTolerance=0.025,
                     enlargen=False,log=False,ax=None,RLUPlot=True,vmin=0,vmax=1e-6)
