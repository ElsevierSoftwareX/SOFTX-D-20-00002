import sys
sys.path.append('..')

from MJOLNIR.Data import DataSet,Viewer3D
import numpy as np
import h5py as hdf
import matplotlib.pyplot as plt
fileName = '../TestData/1024/Magnon_ComponentA3Scan.nxs'


file = hdf.File(fileName,'r')

I = np.array(file.get('entry/data/intensity'))
posx = np.array(file.get('entry/data/qx'))
posy = np.array(file.get('entry/data/qy'))
energy = np.array(file.get('entry/data/en'))
Norm = np.array(file.get('entry/data/normalization'))
Monitor = np.array(file.get('entry/data/monitor'))
title = np.string_(file.get('entry/title').value)
file.close()

pos = [posx,posy,energy]

import warnings
Data,bins = DataSet.binData3D(0.02,0.02,0.1,pos,I,norm=Norm,mon=Monitor)

warnings.simplefilter("ignore")
Intensity = np.divide(Data[0]*Data[3],Data[1]*Data[2])
warnings.simplefilter('once')

Viewer = Viewer3D.Viewer3D(Intensity,bins,axis=2)

Viewer.caxis=(0,40)

Viewer.ax.set_title(str(title)[2:-1])
plt.show()
