import sys
sys.path.append('.')
sys.path.append('..')
sys.path.append('../..')
import numpy as np
from MJOLNIR.Geometry import GeometryConcept,Analyser,Detector,Wedge
import warnings
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os
import scipy.optimize
import h5py as hdf
import datetime

NumberOfSigmas= 3 # Defining the active area of a peak on a detector as \pm n*sigma


class Instrument(GeometryConcept.GeometryConcept):
    def __init__(self, position=(0,0,0),wedges=[],fileName='',**kwargs):
        """Instrument object used to calculated analytic scattering coverage. 
        Based on the GeometryConcept object it contains all needed information about the setup used in further calculations.

        Kwargs:
            
            - position (float 3d): Position of the instrument alwasy at origin(?) (default (0,0,0))

            - wedges (list of wedges or single wedge): Wedge or list of wedges which the instrument consists of (default empty)

            - fileName (string): Filename of xml file (ending in xml). To load binary files use self.load(filename).

        Raises:
            
            - AttributeError
        
        """
        
        self._wedges = []

        
        self._settings = {}
        if fileName !='':
            if(fileName.split('.')[-1]=='xml'):
                parseXML(self,fileName)
            else:
                raise ValueError('File not of type XML.')
        else:
            super(Instrument,self).__init__(position)
            
            for key in kwargs:
                self.settings[key]=kwargs[key]
            self._settings['Initialized']=False
            self.append(wedges)

    @property
    def wedges(self):
        return self._wedges

    @wedges.getter
    def wedges(self):
        return self._wedges

    @wedges.setter
    def wedges(self,wedges):
        if len(self.wedges)!=0:
            warnings.warn('The list of wedges is not empty! Appending new wedges(s)')
        if isinstance(wedges, list):
            for ana in wedges:
                if not issubclass(type(ana),Wedge.Wedge):
                    raise AttributeError('Object is not an wedge or a simple list of these')
                self._wedges.append(ana)
        else:
            if not issubclass(type(wedges),Wedge.Wedge):
                raise AttributeError('Object is not an analyser or a simple list of these')
            self._wedges.append(wedges)
    
    def append(self,wedge):
        """Append wedge(s) to instrument.

        Args
            
            - wedge (Wedge(s)): Single wedge or list of wedges
        """
        if isinstance(wedge,list):
            for obj in wedge:
                if issubclass(type(obj),Wedge.Wedge):
                    self._wedges.append(obj)
                else:
                    raise AttributeError('Object not wedge or a simple list of wedges')
        else:
            if issubclass(type(wedge),Wedge.Wedge):
                    self._wedges.append(wedge)
            else:
                raise AttributeError('Object not wedge or a simple list of wedges')

    def plot(self,ax):
        """Recursive plotting routine."""
        for wedge in self.wedges:
            wedge.plot(ax,offset=self.position)

    @property
    def settings(self):
        return self._settings

    @settings.getter
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self,*args,**kwargs):
        raise NotImplementedError('Settings cannot be overwritten.')

    def __str__(self):
        string = '{} with settings:\n'.format(self.__class__)
        for attrib in self.settings:
            string+='{}:\t{}\n'.format(attrib,self.settings[attrib])
        string+='\n'    
        string+='Containing the following wedges:\n'
        for wedge in self.wedges:
            string+=str(wedge)+'\n'
        return string

    def initialize(self):
        """Method to initialize and perform analytical calulations of scattering quantities. 
        Initializes:

            -  A4: Matrix holding pixel A4. Shape (len(Wedges),len(detectors),pixels)
            
            -  Ef: Matrix holding pixel Ef. Shape (len(Wedges),len(detectors),pixels)
        """
        factorLambdasqrtE = 9.0445678

        if(len(self.wedges)==0):
            raise ValueError('Instrument does not contain any wedges and can thus not be initialized.')
        self._A4 = []
        self._Ef = []
        beamDirection = np.array([0.0,1.0,0.0])

        for wedge in self.wedges:
            detectorPixelPositions,analyserPixelPositions = wedge.calculateDetectorAnalyserPositions()

            A4 = [-np.arccos(np.divide(np.dot(AnalyserPos,beamDirection),
                np.linalg.norm(AnalyserPos,axis=1))) for AnalyserPos in analyserPixelPositions]

                
            relPos = [detectorPixelPositions[i]-analyserPixelPositions[i] for i in range(len(analyserPixelPositions))]

            A6 = [np.arccos(np.divide(np.einsum('ij,ij->i',analyserPixelPositions[i],relPos[i]),
                np.linalg.norm(analyserPixelPositions[i],axis=1)*np.linalg.norm(relPos[i],axis=1))) for i in range(len(analyserPixelPositions))]
            Ef = [np.power(factorLambdasqrtE/(wedge.analysers[0].d_spacing*2.0*np.sin(A6Sub/2.0)),2.0) for A6Sub in A6] ## TODO: d_spacing Make generic
            self._A4.append(A4)
            self._Ef.append(Ef)





        self.settings['Initialized']=True

    @property
    def A4(self):
        return self._A4
    @A4.getter
    def A4(self):
        if(self.settings['Initialized']==False):
            raise RuntimeError('Instrument is not initialized.')
        return self._A4
    @A4.setter
    def A4(self,*args,**kwargs):
        raise NotImplementedError('A4 cannot be overwritten.')

    @property
    def Ef(self):
        return self._Ef
    @Ef.getter
    def Ef(self):
        if(self.settings['Initialized']==False):
            raise RuntimeError('Instrument is not initialized.')
        return self._Ef
    @Ef.setter
    def Ef(self,*args,**kwargs):
        raise NotImplementedError('Ef cannot be overwritten.')

    
    def saveXML(self,fileName):
        """Method for saving current file as XML in fileName."""
        XMLString = '<?xml version="1.0"?>\n'
        XMLString+= '<Instrument '
        for attrib in self.settings:
            XMLString+="{}='{}' ".format(attrib,self.settings[attrib])

        XMLString+="position='"+','.join([str(x) for x in self.position])+"'"
        XMLString+='>\n'
            
        for wedge in self.wedges:
            XMLString+="\t<Wedge "
            for attrib in wedge.settings:
                XMLString+="{}='{}' ".format(attrib,wedge.settings[attrib])

            XMLString+="position='"+','.join([str(x) for x in wedge.position])+"'"
            XMLString+='>\n'

            for item in wedge.analysers + wedge.detectors:
                itemClass = str(item.__class__).split('.')[-1][:-2]
                XMLString+="\t\t<{}".format(itemClass)
                for key in item.__dict__:
                    value = item.__getattribute__(key)
                    if isinstance(value,type(np.array([0,0,0]))):
                        valueStr = ','.join([str(x) for x in item.__getattribute__(key)])
                    else:
                        valueStr = str(value)
                    XMLString+=" {}='{}'".format(str(key)[1:],valueStr)
                XMLString+="></{}>\n".format(itemClass)
                
            
            XMLString+="\t</Wedge>\n"
        XMLString+="</Instrument>\n"
    
        f = open(fileName,'w')
        f.write(XMLString)
        f.close()

    def generateCAMEAXML(self,fileName):
        """Generate CAMEA XML file to be used as instrument file.

        Args:

            - fileName: Name of file to be saved (required)

        """
        ang_1 = np.zeros((7,))
        ang_2 = np.zeros((6,))

        ang_1[0]=-3.33
        ang_1[1]=-2.22
        ang_1[2]=-1.11
        ang_1[3]=0
        ang_1[4]=1.11
        ang_1[5]=2.22
        ang_1[6]=3.33

        ang_2[0]=-2.775
        ang_2[1]=-1.665
        ang_2[2]=-0.555
        ang_2[3]=0.555
        ang_2[4]=1.665
        ang_2[5]=2.775


        z_an = np.zeros((8,))
        z_an[0]=0.9300
        z_an[1]=0.9939
        z_an[2]=1.0569
        z_an[3]=1.1195
        z_an[4]=1.1827
        z_an[5]=1.2456
        z_an[6]=1.3098
        z_an[7]=1.3747
    
        

        H1 = 0.7
        H2 = 0.71

        det_cen = 1.2
        wedges=8

        offset = -np.max(ang_1) # offset needed


        string = "<?xml version='1.0'?>\n<Instrument Initialized='False' Author='Jakob Lass' Date ='16/03/18' position='0.0,0.0,0.0'>\n"
        for W in -np.arange(wedges):
            
            string+="\t<Wedge position='0.0,0.0,0.0' concept='ManyToMany'>\n"
            
            Anaposx = -np.sin((W*7.5+offset)*np.pi/180)*z_an
            Anaposy = np.cos((W*7.5+offset)*np.pi/180)*z_an
            
            for i in range(len(z_an)):
                string+="\t\t<FlatAnalyser position='"+str(Anaposx[i])+','+str(Anaposy[i])+",0.0' direction='0.707106781187,0.0,0.707106781187' d_spacing='3.35' mosaicity='60' width='0.05' height='0.1'></FlatAnalyser>\n"
            
            
            detx_1 = -np.sin((ang_1+W*7.5+offset)*np.pi/180)*det_cen
            detz_1 = np.cos((ang_1+W*7.5+offset)*np.pi/180)*det_cen
            
            
            detx_2 = -np.sin((ang_2+W*7.5+offset)*np.pi/180)*det_cen
            detz_2 = np.cos((ang_2+W*7.5+offset)*np.pi/180)*det_cen
            for i in range(7):
                string+="\t\t<TubeDetector1D position='"+str(detx_1[i])+','+str(detz_1[i])+','+str(H1)+"' direction='"+str(detx_1[i])+','+str(detz_1[i])+",0.0' pixels='452' length='0.883' diameter='0.02' split='71, 123, 176, 228, 281, 333, 388'></TubeDetector1D>\n"
            for i in range(6):
                string+="\t\t<TubeDetector1D position='"+str(detx_2[i])+','+str(detz_2[i])+','+str(H2)+"' direction='"+str(detx_2[i])+','+str(detz_2[i])+",0.0' pixels='452' length='0.883' diameter='0.02' split='71, 123, 176, 228, 281, 333, 388'></TubeDetector1D>\n"
                
            string+="\t</Wedge>\n"
            
        string+="</Instrument>"

        if fileName.split('.')[-1]!='xml':
            fileName+='.xml'

        with open(fileName,'w') as f:
            f.write(string)


    def generateCalibration(self,Vanadiumdatafile,A4datafile,savelocation='calibration/',tables=['Single','PrismaticLowDefinition','PrismaticHighDefinition'],plot=False):
        """Method to generate look-up tables for normalization. Saves calibration file(s) as 'Calibration_Np.calib', where Np is the number of pixels.
        
        Generates 4 different tables:

            - Prismatic High Definition (8 pixels/energy or 64 pixels/detector)

            - Prismatic Low Definition (3 pixels/energy or 24 pixels/detector)

            - Single (1 pixel/energy or 8 pixels/detector)

            - Number (integer)

        Kwargs:

            - Vanadiumdatafile (string): String to single data file used for normalization, Vanadium Ei scan (required).

            - A4datafile (string): String to single data file used for normalization, AlO A4 scan (required).

            - savelocation (string): String to save location folder (calibration)

            - tables (list): List of needed conversion tables (Default: ['Single','PrismaticLowDefinition','PrismaticHighDefinition'], increasing number of pixels).

            - plot (boolean): Set to True if pictures of all fit are to be stored in savelocation


        .. warning::
            At the moment, the active detector area is defined by NumberOfSigmas (currently 3) times the Guassian width of Vanadium peaks.

        """
        #if self.settings['Initialized']==False:
        self.initialize()
            

        VanFile = hdf.File(Vanadiumdatafile,'r')
        A4File = hdf.File(A4datafile,'r')

        VanFileInstrument = getInstrument(VanFile)
        A4FileInstrument = getInstrument(A4File)

        VanFileInstrumentType = VanFileInstrument.name.split('/')[-1]
        A4FileInstrumentType = A4FileInstrument.name.split('/')[-1]

        if VanFileInstrumentType == A4FileInstrumentType:
            InstrumentType = VanFileInstrumentType
        else:
            raise AttributeError('The provided Vanadium and Powder files does not have the same instrument type ({} and {} respectively).'.format(VanFileInstrumentType,A4FileInstrumentType))        

        if InstrumentType=='CAMEA':

            

            if savelocation[-1]!='/':
                savelocation+='/'
            
            Data = np.array(VanFileInstrument.get('detector/data')).transpose(1,0,2)
            Ei = np.array(VanFileInstrument.get('monochromator/energy'))
            analysers = 8
            pixels = len(self.A4[0][0]) # <------------------- Change!
            detectors = len(self.A4[0])*len(self.A4)
            detectorsorInWedge = len(self.A4[0])
            wedges = len(self.A4)

            if pixels!=Data.shape[2]:
                raise ValueError('The number of pixels ({}) in the data file does not match instrument description ({})!'.format(pixels,Data.shape[2]))

            bins = []
            for table in tables:
                if table=='Unbinned':
                    bins.append(pixels)
                elif table=='PrismaticHighDefinition':
                    bins.append(8)
                elif table=='PrismaticLowDefinition':
                    bins.append(3)
                elif table=='Single':
                    bins.append(1)
                elif isinstance(table,int):
                    bins.append(table)
                else:
                    raise AttributeError("Provided table attribute ({}) not recognized, should be 'Unbinned','PrismaticHighDefinition','PrismaticLowDefinition','Single', and/or integer.".format(table))
            if len(bins)==0:
                raise AttributeError("No binning has been chosen for normalization routine.")
            # Initial finding of peaks
            peakPos = np.ones((detectors,analysers),dtype=float)*(-1)
            peakVal = np.zeros_like(peakPos,dtype=float)
            peakWidth = np.ones_like(peakPos,dtype=float)
            peakBackg = np.zeros_like(peakPos,dtype=float)

            # Looking only at pixel direction (integration over E)
            ESummedData = Data.sum(axis=1)
            dataSubtracted = np.array(ESummedData.copy(),dtype=float)

            

            if plot: # pragma: no cover
                plt.ioff()
                plt.figure(figsize=(16,11))
                if not os.path.exists(savelocation+'Raw'):
                    os.makedirs(savelocation+'Raw')
                for i in range(detectors):
                    plt.clf()
                    plt.scatter(np.arange(pixels),np.sum(Data[:][i],axis=0),s=5)
                    plt.ylim(0,np.max(np.sum(Data[i],axis=0))*1.1)
                    plt.xlabel('Pixel')
                    plt.ylabel('Intensity [arg]')
                    plt.title('Vanadium normalization detector '+str(i))
                    plt.tight_layout()
                    plt.savefig(savelocation+'Raw/detector'+str(i)+'.png',format='png', dpi=150)
            
            for j in range(analysers):
                peakPos[:,j],peakVal[:,j] = findPeak(dataSubtracted) # Find a peak in data
                for i in range(detectors):
                    guess = [peakVal[i,j],float(peakPos[i,j]),pixels/100.0,np.min(ESummedData[i])]
                    res = scipy.optimize.curve_fit(Gaussian,np.arange(ESummedData.shape[1]),dataSubtracted[i,:],p0=[guess])
                    peakPos[i,j] = res[0][1]
                    peakVal[i,j] = res[0][0]
                    peakWidth[i,j]= res[0][2]

                    # Generate peak as the one fitted and subtract it from signal
                    x=np.arange(pixels)
                    y = Gaussian(x,peakVal[i,j],peakPos[i,j],peakWidth[i,j],peakBackg[i,j])
                    peak = y>peakVal[i,j]*0.05
                    dataSubtracted[i,peak]= 0

            if plot: # pragma: no cover
                plt.clf()
                plt.suptitle('Fits')
                x = np.arange(pixels)
                for k in range(wedges):
                    for i in range(detectorsorInWedge):
                        y=np.zeros_like(x,dtype=float)
                        plt.subplot(4, 4, i+1)
                        plt.scatter(np.arange(pixels),ESummedData[i+13*k],s=4)
                        for j in range(analysers):
                            y += Gaussian(x,peakVal[i+13*k,j],peakPos[i+13*k,j],peakWidth[i+13*k,j],peakBackg[i+13*k,j])
                            plt.plot([peakPos[i+13*k,j],peakPos[i+13*k,j]],[0,np.max(ESummedData[i+13*k])*1.1])
                        plt.plot(x,y,'k')
                        plt.xlabel('Pixel')
                        plt.ylabel('Intensity [arg]')
                        plt.title('Detector {}'.format(i))
                        plt.ylim(0,np.max(ESummedData[i+13*k])*1.1)

                    plt.tight_layout()
                    plt.savefig(savelocation+'/Raw/Fit_wedge_'+str(k)+'.png',format='png', dpi=150)
                    print('Saving: {}'.format(savelocation+'/Raw/Fit_wedge_'+str(k)+'.png'))

            
            ## Sort the positions such that peak 1 is the furthermost left peak and assert diff(pos)>100
            sortedPeakPosArg = np.argsort(peakPos,axis=1)
            sortedPeakPos = np.sort(peakPos,axis=1)
            sortedPeakPos[np.logical_or(sortedPeakPos>pixels,sortedPeakPos<0)]=5*pixels # High number

            sortedPeakPosArg2 = np.argsort(sortedPeakPos,axis=1)
            sortedPeakPos.sort(axis=1)

            differences = np.diff(sortedPeakPos,axis=1)
            outliers = np.zeros_like(peakPos,dtype=bool)
            outliers[:,:-1]=differences<pixels/10
            sortedPeakPos[outliers]=5*pixels
            sortedPeakPosArg3 = np.argsort(sortedPeakPos,axis=1)
            argSort = np.array([sortedPeakPosArg[i,sortedPeakPosArg2[i,sortedPeakPosArg3[i,:]]] for i in range(detectors)])
            sortedPeakPos = np.sort(sortedPeakPos,axis=1)
            peaks=np.sum(sortedPeakPos<5*pixels,axis=1) # Number of peaks found


            if np.any(peaks!=analysers):
                raise ValueError('Wrong number of peaks, {} found in detector(s): {}\nIn total error in {} detector(s).'.format(peaks[peaks!=analysers],np.arange(peaks.shape[0])[peaks!=analysers],np.sum(peaks[peaks!=analysers])))

            pixelpos  = np.array([peakPos[i,argSort[i]] for i in range(detectors)])
            widths    = np.array([peakWidth[i,argSort[i]] for i in range(detectors)])

             ## Define the active detector area
            sigmas = NumberOfSigmas # Active area is all pixels inside of pm 3 sigmas

            lowerPixel = pixelpos-sigmas*widths
            upperPixel = pixelpos+sigmas*widths

            split = (lowerPixel[:,1:]-upperPixel[:,:-1])/2+upperPixel[:,:-1]

            extendedSplit=np.zeros((split.shape[0],split.shape[1]+2))
            extendedSplit[:,1:-1] = split
            extendedSplit[:,-1]=np.ones((split.shape[0]))*pixels

            x=np.arange(pixels)
            activePixels = np.zeros((detectors,analysers,pixels),dtype=bool)
            for i in range(detectors):
                if plot: # pragma: no cover
                    plt.clf()
                    plt.title('Detector {} Active pixels'.format(i))
                    plt.scatter(x,ESummedData[i],s=4,color='black')
                for j in range(analysers):
                    activePixels[i,j] = np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])
                    if plot: plt.scatter(x[np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])], # pragma: no cover
                        ESummedData[i,np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])],s=4,color='red')
                if plot: # pragma: no cover
                    plt.ylim(0,np.max(ESummedData[i])*1.1)
                    plt.xlabel('Pixel')
                    plt.ylabel('Intensity [arg]')
                    plt.savefig(savelocation+'/Raw/Active_'+str(i)+'.png',format='png', dpi=150)

            Eguess = np.zeros_like(peakPos,dtype=int)
            for i in range(Eguess.shape[0]):
                for j in range(analysers):
                    Eguess[i,j]=np.argmax(Data[i,:,int(pixelpos[i,j])])
            
            fitParameters = []
            activePixelRanges = []
            for detpixels in bins:
                if detpixels*analysers*3>len(Ei):
                    warnings.warn('Fitting might be unstable due to {} pixels being fitted using only {} energies ({} free parameters).'.format(detpixels,len(Ei),detpixels*analysers*3))
                    
                if plot: # pragma: no cover
                    EiX = np.linspace(Ei[0],Ei[-1],len(Ei))
                    if not os.path.exists(savelocation+'/{}_pixels'.format(detpixels)):
                        os.makedirs(savelocation+'/{}_pixels'.format(detpixels)) 
                    colors=np.zeros((3,detpixels))
                    if pixels==1:
                        colors[:,0]=[0.65,0.2,0.45]
                    else:
                        colors[0]=np.linspace(0.3,1.0,detpixels)
                        colors[1]=np.linspace(0.2,0.2,detpixels)
                        colors[2]=np.linspace(0.8,0.1,detpixels)
                    plt.suptitle('{} pixels'.format(detpixels))

                fittedParameters=np.zeros((detectors,analysers,detpixels,4))
                activePixelDetector=[]
                for i in range(detectors):
                    activePixelAnalyser = []
                    if plot: # pragma: no cover
                        plt.clf()
                        plt.title('Detector {}, {} pixels'.format(i,detpixels))
                        x =np.linspace(0,detpixels,len(Ei))
                    for j in range(analysers):

                        center = int(round(sortedPeakPos[i,j]))
                        width = activePixels[i,j].sum()
                        pixelAreas = np.linspace(-width/2.0,width/2.0,detpixels+1,dtype=int)+center+1 #Add 1 such that the first pixel is included 20/10-17
                        
                        for k in range(detpixels):
                            binPixelData = Data[i,:,pixelAreas[k]:pixelAreas[k+1]].sum(axis=1)
                            guess = [np.max(binPixelData), Ei[np.argmax(binPixelData)],0.1,0]
                            try:
                                res = scipy.optimize.curve_fit(Gaussian,Ei,binPixelData,p0=guess)
                            except:
                                if not os.path.exists(savelocation+'/{}_pixels'.format(detpixels)):
                                    os.makedirs(savelocation+'/{}_pixels'.format(detpixels))
                                if not plot:
                                    plt.ioff
                                plt.figure()
                                plt.scatter(Ei,binPixelData)
                                plt.plot(Ei,Gaussian(Ei,guess[0],guess[1],guess[2],guess[3]))
                                plt.savefig(savelocation+'/{}_pixels/Detector{}_{}.png'.format(detpixels,i,k),format='png',dpi=300)
                                plt.close()

                            fittedParameters[i,j,k]=res[0]
                            if plot: # pragma: no cover
                                plt.plot(EiX,Gaussian(EiX,*fittedParameters[i,j,k]),color='black')
                                plt.scatter(Ei,binPixelData,color=colors[:,k])
                        activePixelAnalyser.append(np.linspace(-width/2.0,width/2.0,detpixels+1,dtype=int)+center+1)
                    activePixelDetector.append(activePixelAnalyser)
                    if plot: # pragma: no cover
                        plt.grid('on')
                        plt.xlabel('Ei [meV]')
                        plt.ylabel('Weight [arb]')
                        plt.tight_layout(rect=(0,0,1,0.95))
                        plt.savefig(savelocation+'/{}_pixels/Detector{}.png'.format(detpixels,i),format='png',dpi=300)
                        print('Saving: {}'.format(savelocation+'/{}_pixels/Detector{}.png'.format(detpixels,i)))

                # Perform A4 calibration
                A4FileValue = np.array(A4FileInstrument.get('detector/polar_angle'))
                EiFile = np.array(A4FileInstrument.get('monochromator/energy'))[0]
                A4FileIntensity = np.array(A4FileInstrument.get('detector/data'))

                factorsqrtEK = 0.694692
                ki = np.sqrt(EiFile)*factorsqrtEK

                Qvec = 1.8049 # Angstrom <----------------------CHANGE!

                # q = 2 k sin(theta)
                theta = np.arcsin(Qvec/(2*ki))
 
                A4 = np.array(self.A4)
                A4=A4.reshape(A4.shape[0]*A4.shape[1],A4.shape[2],order='C')
                EPrDetector = len(self.wedges[0].detectors[0].split)+1

                
                pixelList = np.array(activePixelDetector).reshape(A4.shape[0],EPrDetector,detpixels+1).astype(int)
                PixelEdge = np.array([[pixelList[:,:,i],pixelList[:,:,i+1]] for i in range(detpixels)]).transpose((2,3,0,1))
                PixelEnergy = fittedParameters[:,:,:,1].reshape(A4.shape[0],EPrDetector*detpixels)

                ## Find detector analyser combi corresponding to energy
                SoftwarePixel = np.array([np.argmin(np.abs(x-EiFile)) for x in PixelEnergy])

                MeanA4Instr = np.zeros((A4.shape[0],EPrDetector*detpixels))
                MeanIntensity = np.zeros((len(A4FileValue),A4.shape[0],EPrDetector*detpixels))
                for i in range(A4.shape[0]): # For each detector
                    for j in range(EPrDetector):
                        for k in range(detpixels):
                            MeanIntensity[:,i,j*detpixels+k] = np.sum(A4FileIntensity[:,i,PixelEdge[i,j,k,0]:PixelEdge[i,j,k,1]],axis=1)
                            MeanA4Instr[i,j*detpixels+k] = np.mean(A4[i,PixelEdge[i,j,k,0]:PixelEdge[i,j,k,1]])
                            
                x = A4FileValue
                A4FitValue = np.zeros((A4.shape[0]))

                
                if plot==True:
                    plt.clf()
                for i in range(104):
                    y = MeanIntensity[:,i,SoftwarePixel[i]]
                    if plot==True:
                        plt.scatter(x,y)
                    
                    guess=[np.max(y),x[np.argmax(y)],3,0]
                    try:
                        fit = scipy.optimize.curve_fit(Gaussian,x,y,p0=[guess])
                    except:
                        A4FitValue[i]=guess[1]
                    else:
                        A4FitValue[i] = fit[0][1]

                if plot==True: # pragma: no cover
                    if not os.path.exists(savelocation+'A4'):
                        os.makedirs(savelocation+'A4')
                    plt.savefig(savelocation+'A4'+'/A4_{}.png'.format(detpixels),format='png',dpi=300)

                A4FitValue+=2*theta*180.0/np.pi # offset relative to expected from powder line

                if plot==True: # pragma: no cover
                    plt.clf()
                    plt.scatter(range(A4.shape[0]),A4FitValue)
                    plt.scatter(range(A4.shape[0]),MeanA4Instr[:,int(np.round(np.mean(SoftwarePixel)))]*180.0/np.pi)
                    plt.legend(['File','Geometry'])
                    plt.savefig(savelocation+'A4'+'/Points_{}.png'.format(detpixels),format='png',dpi=300)

                    diff = A4FitValue-MeanA4Instr[:,int(np.round(np.mean(SoftwarePixel)))]*180.0/np.pi#+2*theta*180.0/np.pi
                    plt.clf()
                    plt.scatter(range(A4.shape[0]),diff)
                    plt.savefig(savelocation+'A4'+'/diff_{}.png'.format(detpixels),format='png',dpi=300)

                fitParameters.append(fittedParameters)
                activePixelRanges.append(np.array(activePixelDetector))
                tableString = 'Normalization for {} pixel(s) using VanData {} and A4Data{}\nPerformed {}\nDetector,Energy,Pixel,Amplitude,Center,Width,Background,lowerBin,upperBin,A4Offset\n'.format(detpixels,Vanadiumdatafile,A4datafile,datetime.datetime.now())
                for i in range(len(fittedParameters)):
                    for j in range(len(fittedParameters[i])):
                        for k in range(len(fittedParameters[i][j])):
                            tableString+=str(i)+','+str(j)+','+str(k)+','+','.join([str(x) for x in fittedParameters[i][j][k]])
                            tableString+=','+str(activePixelRanges[-1][i][j][k])+','+str(activePixelRanges[-1][i][j][k+1])
                            tableString+=','+str(A4FitValue[i])+'\n'
                tableName = 'Normalization_{}.calib'.format(detpixels)
                print('Saving {} pixel data to {}'.format(detpixels,savelocation+tableName))
                file = open(savelocation+tableName,mode='w')

                file.write(tableString)
                file.close()
        VanFile.close()
        A4File.close()

def parseXML(Instr,fileName):
    import xml.etree.ElementTree as ET


    tree = ET.parse(fileName)
    instr_root = tree.getroot()

    
    
        
    for attrib in instr_root.keys():
        if attrib=='position':
            Instr.position = np.array(instr_root.attrib[attrib].split(','),dtype=float)
        Instr.settings[attrib]=instr_root.attrib[attrib]
    
    
    Instr._wedges=[]
    for wedge in instr_root.getchildren():
        
        if wedge.tag in dir(Wedge):
            Wedgeclass_ = getattr(Wedge, wedge.tag)
        else:
            raise ValueError("Element is supposed to be a Wedge, but got '{}'.".format(wedge.tag))
        wedgeSettings = {}
        
        for attrib in wedge.keys():
            if attrib=='concept':
                wedgeSettings[attrib]=np.array(wedge.attrib[attrib].strip().split(','),dtype=str)
            else:        
                wedgeSettings[attrib]=np.array(wedge.attrib[attrib].strip().split(','),dtype=float)
            
        temp_wedge = Wedgeclass_(**wedgeSettings)
        
        
        
        
        for item in wedge.getchildren():
            if item.tag in dir(Detector):
                class_ = getattr(Detector, item.tag)
            elif item.tag in dir(Analyser):
                class_ = getattr(Analyser,item.tag)
            else:
                raise ValueError("Item '{}' not recognized as MJOLNIR detector or analyser.".format(item.tag))
            
            itemSettings = {}
            for attrib in item.keys():
                attribVal = item.get(attrib).strip().split(',')
                if len(attribVal)==1:
                    if(attrib=='split'):
                        try:
                            val=float(attribVal[0])
                        except ValueError:
                            val=[]
                        itemSettings[attrib]=val
                    else:
                        itemSettings[attrib]=float(attribVal[0])
                else:
                    if(attrib=='split'):
                        #print(type(attribVal))
                        itemSettings[attrib]=attribVal
                    else:
                        itemSettings[attrib]=np.array(attribVal,dtype=float)    
            try:
                temp_item = class_(**itemSettings)
            except TypeError as e:
                print(e.args[0])
                raise ValueError('Item {} misses argument(s):{}'.format(class_,e.args[0].split(':')[0]))
            except AttributeError as e:
                raise AttributeError('Error in passing {} with attributes {}'.format(class_,itemSettings))
            except ValueError:
                raise ValueError('Item {} not initialized due to error.'.format(class_))
            #print(temp_item)
            temp_wedge.append(temp_item)
            #print()

        #print(str(temp_wedge))
        Instr.append(temp_wedge)
    #print(str(Instr))
   

def getNX_class(x,y,attribute):
    try:
        variableType = y.attrs['NX_class']
    except:
        variableType = ''
    if variableType==attribute:
        return x

def getInstrument(file):
    location = file.visititems(lambda x,y: getNX_class(x,y,b'NXinstrument'))
    return file.get(location)



def Gaussian(x,A,mu,sigma,b):
    return A*np.exp(-np.power(mu-x,2.0)*0.5*np.power(sigma,-2.0))+b


def findPeak(data):
    return [np.argmax(data,axis=1),np.max(data,axis=1)]


def convertToHDF(fileName,title,sample,fname,CalibrationFile=None): # pragma: no cover
    """Convert McStas simulation to h5 format"""
    def addMetaData(entry,title):
        dset = entry.create_dataset('start_time',(1,),dtype='<S70')
        dset[0] = b'2018-03-22T16:44:02+01:00'

        dset = entry.create_dataset('end_time',(1,),dtype='<S70')
        dset[0] = b"2018-03-22T18:44:02+01:00"

        dset = entry.create_dataset('title',(1,),dtype='<S70')
        dset[0] = np.string_(title)

        dset = entry.create_dataset('proposal_id',(1,),dtype='<S70')
        dset[0] = b"2018-00666"

        us = entry.create_group('proposal_user')
        us.attrs['NX_class'] = np.string_('NXuser')
        dset = us.create_dataset('name',(1,),dtype='S70')
        dset[0] = b"Jakob Lass"

    def addMono(inst):
        mono = inst.create_group('monochromator')
        mono.attrs['NX_class'] = np.string_('NXmonochromator')

        dset = mono.create_dataset('type',(1,),dtype='S70')
        dset[0] = b"Pyrolithic Graphite"
        
        dset = mono.create_dataset('d_spacing',(1,),'float32')
        dset[0] = 3.354

    def addDetector(inst):
        det = inst.create_group('detector')
        det.attrs['NX_class'] = np.string_('NXdetector')

    def readDetSequence():
        detlist = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        fin = open(dir_path+'/'+'detsequence.dat','r')
        for line in fin:
            detlist.append(line.strip())
        fin.close()
        return detlist

    def readDetFile(fname):
        detdata = np.zeros((452),dtype='int32')
        f = open(fname,'r')
        psddata = f.readlines()
        f.close()
        idx = 0
        for line in psddata:
            if line.find('EI=') > 0:
                l = line.split('=')
                ei = float(l[1])
            if line.find('A3=') > 0:
                l = line.split('=')
                a3 = float(l[1])
            if line.find('A4=') > 0:
                l = line.split('=')
                a4 = float(l[1])
            if line.find('variables:') > 0:
                idx = idx + 1
                break
            idx = idx + 1
        detind = 0

        for i in range(idx+1,452+idx-1):
            l = psddata[i].split()

            detdata[detind] = int(round(10000.*float(l[1])))
            detind = detind + 1
        return detdata,a3,a4,ei

    def readScanPointData(dir,detlist,Numpoints):
        frame = np.zeros((104,452),dtype='int32')
        i = 0
        for detfile in detlist:
            detdata, a3, a4, ei = readDetFile(dir +'/' + str(Numpoints) + '/' + detfile)
            frame[i] = detdata
            i = i + 1
        return frame,a3,a4,ei

    def readScanData(dir,Numpoints):
        detlist = readDetSequence()
        data = np.zeros((Numpoints,104,452),dtype='int32')
        a3 = []
        a4 = []
        ei = []
        for n in range(Numpoints):
            frame, a3n, a4n, ein = readScanPointData(dir,detlist,n)
            a3.append(a3n)
            a4.append(a4n)
            ei.append(ein)
            data[n] = frame
        return data,a3,a4,ei
        
    def addSample(entry,name):
        sam = entry.create_group('sample')
        sam.attrs['NX_class'] = np.string_('NXsample')
        dset = sam.create_dataset('name',(1,),dtype='S70')
        dset[0] = np.string_(name)

        ub = np.zeros((3,3,),dtype='float32')
        ub[0,0] = 1.
        ub[1,1] = 1.
        ub[2,2] = 1.
        dset = sam.create_dataset('orientation_matrix',data=ub)

        normal = np.zeros((3,),dtype='float32')
        normal[2] = 1.0
        dset = sam.create_dataset('plane_normal',data=normal)

        cell = np.zeros((6,),dtype='float32')
        cell[0] = 4.95
        cell[1] = 4.95
        cell[2] = 4.95
        cell[3] = 90.
        cell[4] = 90.
        cell[5] = 90.
        dset = sam.create_dataset('unit_cell',data=cell)

        

    def isVaried(data):
        if len(data)>1 and data[0]!=data[1]:
            return True
        else:
            return False

    def makeTheta(ei):
        theta = []
        tth = []
        for e in ei:
            k = np.sqrt(float(e)/2.072)
            fd = np.pi/(k*3.354)
            th = np.degrees(np.arcsin(fd))
            theta.append(th)
            tth.append(2.*th)
        return theta,tth

    def storeScanData(entry,data,a3,a4,ei):
        nxdata = entry.create_group('data')
        nxdata.attrs['NX_class'] = np.string_('NXdata')
        
        det = entry['CAMEA/detector']
        dset = det.create_dataset('data',data=data )
        dset.attrs['target'] = np.string_('/entry/CAMEA/detector/data')
        nxdata['data'] = dset

        online = det.create_dataset('online',data=np.ones((data.shape[1],),dtype=bool))
        online.attrs['units']=np.string_('Boolean for detector state')

        sam = entry['sample']

        scanType='Unknown'
        if isVaried(a3):
            dset = sam.create_dataset('rotation_angle',data=a3)
            nxdata['rotation_angle'] = dset
            scanType = 'a3Scan'
        else:
            dset = sam.create_dataset('rotation_angle',(1,),dtype='float32')

        dset.attrs['units'] = np.string_('degrees')

        if isVaried(a4):
            dset = det.create_dataset('polar_angle',data=a4)
            nxdata['polar_angle'] = dset
            scanType = 'a4Scan'
        else:
            dset = det.create_dataset('polar_angle',(1,),dtype='float32',data=a4[0])
        dset.attrs['units'] = np.string_('degrees')
        

        mono = entry['CAMEA/monochromator']
        theta,tth = makeTheta(ei)

        if isVaried(ei):
            dset = mono.create_dataset('energy',data=ei)
            nxdata['incident_energy'] = dset
            mono.create_dataset('rotation_angle',data=theta);
            sam.create_dataset('polar_angle',data=tth)
            scanType = 'EiScan'

        else:
            dset = mono.create_dataset('energy',(1,),dtype='float32')
            dset[0] = ei[0]
            dset = mono.create_dataset('rotation_angle',(1,),dtype='float32')
            dset[0] = theta[0]
            dset = sam.create_dataset('polar_angle',(1,),dtype='float32')
            dset[0] = tth[0]
        dset = entry['CAMEA/monochromator/rotation_angle']    
        dset.attrs['units'] = np.string_('degrees')
        dset = entry['sample/polar_angle']    
        dset.attrs['units'] = np.string_('degrees')

        makeMonitor(entry,Numpoints)
        entry['control'].create_dataset('scan_Type',data=scanType)
        
    def makeMonitor(entry,Numpoints):
        control = entry.create_group('control')
        control.attrs['NX_class'] = np.string_('NXmonitor')
        mons = [10000]*Numpoints
        control.create_dataset('data',data=mons,dtype='int32')
        dset = control.create_dataset('preset',(1,),dtype='int32')
        dset[0] = 10000
        dset = control.create_dataset('mode',(1,),dtype='S70')
        dset[0] = b"monitor"
        time = [36.87]*Numpoints
        control.create_dataset('time',data=time,dtype='float32')


    f = hdf.File(fileName,'w')
    f.attrs['file_name'] = np.string_(fileName)
    f.attrs['file_time'] = np.string_(b'2018-03-22T16:44:02+01:00')
    
    entry = f.create_group('entry')
    entry.attrs['NX_class'] = np.string_('NXentry')

    addMetaData(entry,np.string_(title))
    
    #------------ Instrument
    inst = entry.create_group(b'CAMEA')
    inst.attrs['NX_class'] = np.string_('NXinstrument')
    
    if not CalibrationFile is None:
        calib = entry.create_group(b'calibration')
        if not isinstance(CalibrationFile,list):
            CalibrationFile=[CalibrationFile]
        for i in range(len(CalibrationFile)):
            calibrationData = np.genfromtxt(CalibrationFile[i],skip_header=3,delimiter=',')
            binning = CalibrationFile[i].split('/')[-1].split('_')[-1].split('.')[0]
            calib.create_dataset('{}_pixels'.format(binning),data=calibrationData,dtype='float32')
    
    addMono(inst)
    
    addDetector(inst)
    
    addSample(entry,np.string_(sample))
    import os
    Numpoints = sum(os.path.isdir(fname+i) for i in os.listdir(fname))
    data,a3,a4,ei = readScanData(fname,Numpoints)
    storeScanData(entry,data,a3,a4,ei)

    f.close()


# _________________________TESTS____________________________________________



def test_Instrument_init():
    Instr = Instrument()

    assert(np.all(Instr.position==(0,0,0)))

    Det = Detector.Detector(position=(1.0,1,0),direction=(1,0,0))
    Ana = Analyser.Analyser(position=(0.5,0,0),direction=(1,0,1))
    
    wedge = Wedge.Wedge(detectors=[Det,Det],analysers=Ana)

    Instr.wedges=[wedge,wedge]

    assert(Instr.settings['Initialized']==False)



def test_Instrument_error():
    
    try:
        Instr = Instrument(fileName='wrongDummyFile.bin')
        assert False
    except ValueError:
        assert True

    Instr = Instrument()

    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))

    try:
        Instr.wedges=Ana
        assert False
    except AttributeError:
        assert True

    try:
        Instr.wedges=[Ana,Ana]
        assert False
    except AttributeError:
        assert True

    try:
        Instr.append("Wrong object type")
        assert False
    except AttributeError:
        assert True
    
    try:
        Instr.append(["List of",3.0,"wrong objects"])
        assert False
    except AttributeError:
        assert True

    try:
        Instr.settings = {'Name','New dictionary'}
        assert False
    except NotImplementedError:
        return True


def test_Instrument_warnings():
    Instr = Instrument()

    wedge = Wedge.Wedge(position=(0.5,0,0))

    Instr.wedges = wedge

    with warnings.catch_warnings(record=True) as w: # From https://docs.python.org/3.1/library/warnings.html
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Trigger a warning.
        Instr.wedges = wedge
        # Verify some things
        assert len(w) == 1
        assert issubclass(w[0].category, UserWarning)
        assert 'The list of wedges is not empty! Appending new wedges(s)' in str(w[0].message)


def test_Instrument_append():
    Instr = Instrument()

    wedge = Wedge.Wedge(position=(0.5,0,0))

    Instr.append([wedge,wedge])
    Instr.append(wedge)

    assert(len(Instr.wedges)==3)


def test_Instrument_plot():
    Instr = Instrument()

    wedge = Wedge.Wedge(position=(0.5,0,0))

    Det = Detector.TubeDetector1D(position=(1.0,1,0),direction=(1,0,0))
    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))

    wedge.append([Det,Ana])
    Instr.append(wedge)
    plt.ioff()
    fig = plt.figure()
    ax = fig.gca(projection='3d')

    Instr.plot(ax)

def test_Instrument_Setting(): 
    Instr = Instrument()
    Instr.settings['SettingVersion']=1.0
    assert(Instr.settings['SettingVersion']==1.0)


def test_Instrument_Initialization():
    Instr = Instrument()

    wedge = Wedge.Wedge(position=(0.5,0,0),concept='ManyToMany')
    pixels=33
    split = [12]
    Det = Detector.TubeDetector1D(position=(1.0,1,0),direction=(1,0,0),pixels=pixels,split=split)
    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))
    

    wedge.append([Det,Det,Ana,Ana,Ana])

    try:
        Instr.initialize()
        assert False
    except ValueError:
        assert True

    try:
        print(Instr.A4)
        assert False
    except RuntimeError:
        assert True

    try:
        print(Instr.Ef)
        assert False
    except RuntimeError:
        assert True

    Instr.append(wedge)
    try:
        Instr.initialize()
        assert False
    except ValueError:
        assert True
    Instr.wedges[0].detectors[0].split = [12,20]
    Instr.initialize()

    assert(len(Instr.A4)==1)
    assert(len(Instr.A4[0])==2)
    assert(len(Instr.A4[0][0])==pixels)
    assert(len(Instr.A4)==len(Instr.Ef))
    assert(len(Instr.A4[0])==len(Instr.Ef[0]))
    assert(len(Instr.A4[0][0])==len(Instr.Ef[0][0]))
    assert(Instr.settings['Initialized']==True)

    try:
        Instr.A4 = []
        assert False
    except NotImplementedError:
        assert True

    try:
        Instr.Ef = []
        assert False
    except NotImplementedError:
        assert True



def test_Instrument_saveload():
    import os
    Instr = Instrument(position=(0,1,0))
    Instr2 = Instrument()

    wedge = Wedge.Wedge(position=(0.5,0,0))

    Det = Detector.TubeDetector1D(position=(1.0,1,0),direction=(1,0,0))
    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))

    wedge.append([Det,Ana])
    Instr.append(wedge)

    tempFile = 'temp.bin'
    Instr.save(tempFile)
    Instr2.load(tempFile)
    os.remove(tempFile)
    

    assert(Instr==Instr2)



def test_parseXML(): # Improve this test!

    tempFileName = '__temp__.xml'
        
    Instr = Instrument()
    Instr.settings['Author'] = 'Jakob Lass'

    wedge = Wedge.Wedge(position=(0.5,0,0))

    Det = Detector.TubeDetector1D(position=(1.0,1,0),direction=(1,0,0))
    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))

    wedge.append([Det,Ana])
    Instr.append([wedge,wedge])
    Instr.append(wedge)
    Instr.saveXML(tempFileName)
        
    InstrLoaded = Instrument(fileName=tempFileName)
    os.remove(tempFileName)

    assert(Instr==InstrLoaded)


def test_XML_errors():

    fileString = ""
    fileString+="<?xml version='1.0'?>"
    fileString+="<Instrument Initialized='False' Author='Jakob Lass' Date ='16/03/18' position='0.0,0.0,0.0'>"
    fileString+="<Wedge position='0.0,0.0,0.0' concept='ManyToMany'>"
    fileString+="<FlatAnalyser direction='0.707,0.0,0.707' d_spacing='3.35' mosaicity='60' width='0.05' height='0.1'></FlatAnalyser>"
    fileString+="<TubeDetector1D position='1.198,0.0580,0.71' direction='0.998,0.04841,0.0' pixels='456' length='0.883' diameter='0.02' split='57, 114, 171, 228, 285, 342, 399'></TubeDetector1D>"
    fileString+="</Wedge>"
    fileString+="</Instrument>"

    temp_file = 'Tempfile.xml'
    f = open(temp_file,'w')
    f.write(fileString)
    f.close()

    try:
        Instr = Instrument(fileName=temp_file)
        del Instr
        assert False
    except ValueError:
        assert True

    fileString = ""
    fileString+="<?xml version='1.0'?>"
    fileString+="<Instrument Initialized='False' Author='Jakob Lass' Date ='16/03/18' position='0.0,0.0,0.0'>"
    fileString+="<Wedge position='0.0,0.0,0.0' concept='ManyToMany'>"
    fileString+="<FlatAnalyser position='0.0580,0.71' direction='0.707,0.0,0.707' d_spacing='3.35' mosaicity='60' width='0.05' height='0.1'></FlatAnalyser>"
    fileString+="<TubeDetector1D position='1.198,0.0580,0.71' direction='0.998,0.04841,0.0' pixels='456' length='0.883' diameter='0.02' split='57, 114, 171, 228, 285, 342, 399'></TubeDetector1D>"
    fileString+="</Wedge>"
    fileString+="</Instrument>"
    f = open(temp_file,'w')
    f.write(fileString)
    f.close()
    try:
        Instr = Instrument(fileName=temp_file)
        assert False
    except AttributeError:
        assert True

    fileString = ""
    fileString+="<?xml version='1.0'?>"
    fileString+="<Instrument Initialized='False' Author='Jakob Lass' Date ='16/03/18' position='0.0,0.0,0.0'>"
    fileString+="<FlatAnalyser position='0.0,0.0,0.0' concept='ManyToMany'>"
    fileString+="<FlatAnalyser position='0.0580,0.71' direction='0.707,0.0,0.707' d_spacing='3.35' mosaicity='60' width='0.05' height='0.1'></FlatAnalyser>"
    fileString+="<TubeDetector1D position='1.198,0.0580,0.71' direction='0.998,0.04841,0.0' pixels='456' length='0.883' diameter='0.02' split='57, 114, 171, 228, 285, 342, 399'></TubeDetector1D>"
    fileString+="</FlatAnalyser>"
    fileString+="</Instrument>"
    f = open(temp_file,'w')
    f.write(fileString)
    f.close()
    try:
        Instr = Instrument(fileName=temp_file)
        assert False
    except ValueError:
        assert True
    os.remove(temp_file)

def test_instrument_string_dummy(): # Todo: Improve test!
    Instr = Instrument()

    string = str(Instr)
    del string
    assert True
    
def test_instrument_create_xml():

    Instr = Instrument()
    filename = 'temp'
    Instr.generateCAMEAXML(filename)

    Instr2 = Instrument(fileName=filename+'.xml')
    os.remove(filename+'.xml')
    assert(len(Instr2.wedges)==8)


def test_Normalization_tables():

    Instr = Instrument(fileName='TestData/CAMEA_Full.xml')
    Instr.initialize()

    NF = 'TestData/VanNormalization.h5'
    AF = 'TestData/A4Normalization.h5'

    try:
        Instr.generateCalibration(Vanadiumdatafile=NF ,A4datafile=AF,savelocation='TestData/',plot=False,tables=[]) # No binning specified 
        assert False
    except AttributeError:
        assert True

    try:
        Instr.generateCalibration(Vanadiumdatafile=NF ,A4datafile=AF,savelocation='TestData/',plot=False,tables=['Nothing?']) # Wrong binning
        assert False
    except AttributeError:
        assert True

    Instr.generateCalibration(Vanadiumdatafile=NF ,A4datafile=AF,savelocation='TestData/',plot=False,tables=['Single']) 
    #Instr.generateCalibration(Vanadiumdatafile=NF ,A4datafile=AF,  savelocation='TestData',plot=False,tables=['PrismaticHighDefinition','PrismaticLowDefinition',2]) 
    


