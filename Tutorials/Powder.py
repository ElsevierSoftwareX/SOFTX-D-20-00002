import sys
sys.path.append('../')

from MJOLNIR.Data import DataSet
import matplotlib.pyplot as plt
file = '../TestData/cameasim2018n000011.nxs'

DataObj = DataSet.DataSet(convertedFiles=file)

I = DataObj.I
qx = DataObj.qx
qy = DataObj.qy
energy = DataObj.energy
Norm = DataObj.Norm
Monitor = DataObj.Monitor

EBinEdges = DataSet.binEdges(energy,tolerance=0.125)

ax,Data,qbins = DataObj.plotCutPowder(EBinEdges,qMinBin=0.01)
plt.colorbar(ax.pmeshs[0])

ax2,Data2,qbins2 = DataSet.plotCutPowder([qx,qy,energy],I,Norm,Monitor,EBinEdges,qMinBin=0.01)
plt.colorbar(ax2.pmeshs[0])

Data3,qbins3 = DataObj.cutPowder(EBinEdges)

ax2.set_clim(0,1e-6)
plt.show()