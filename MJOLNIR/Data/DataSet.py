import sys, os
sys.path.append('.')
sys.path.append('..')
sys.path.append('../..')
import scipy
from scipy.ndimage import filters
import matplotlib.pyplot as plt
import numpy as np
import pickle as pickle
from MJOLNIR.Geometry import GeometryConcept,Analyser,Detector,Wedge,Instrument
import h5py as hdf
import scipy.optimize
import datetime
import warnings

dataLocation = 'entry/data/data'#'entry/Detectors/Detectors'
EiLocation = 'entry/data/incident_energy' # 'entry/Ei'
monLocation = 'entry/control/data'#'entry/Monitor'


NumberOfSigmas= 3 # Defining the active area of a peak on a detector as \pm n*sigma



class DataSet(object):
    def __init__(self, instrument=None,datafiles=None,normalizationfiles=None, templocation='_temp/', **kwargs):
        """DataSet object to hold all informations about data.
        
        Kwargs:
            
            instrument (Instrument): Instrument object describing the data (default None).

            datafiles (list of strings): List of datafiles to be used in conversion.

            normalizationfiles (string or list of strings): Location of Vanadium normalization file(s).

            templocation (string): Location of temporary files (default _temp/.

        Raises:
            ValueError,NotImplementedError
        
        """
        
        self._instrument = None
        self._datafiles = []
        self._normalizationfiles = []
        if instrument is not None:
            self.instrument = instrument


        if datafiles is not None:
            self.datafiles = datafiles

        if normalizationfiles is not None:
            self.normalizationfiles = normalizationfiles
        


        self._settings = {}
        

        if templocation is not None:
            self.templocation=templocation
            
        
        
        # Add all other kwargs to settings
        for key in kwargs:
            self.settings[key]=kwargs[key]
        

    @property
    def instrument(self):
        return self._instrument

    @instrument.getter
    def instrument(self):
        return self._instrument

    @instrument.setter
    def instrument(self,instrument):
        if not issubclass(type(instrument),Instrument.Instrument):
            raise ValueError('Instrument provided is not of instrument type!')
        else:
            self._instrument = instrument


    @property
    def datafiles(self):
        return self._datafiles

    @datafiles.getter
    def datafiles(self):
        return self._datafiles

    @datafiles.setter
    def datafiles(self,datafiles):
        self._datafiles = IsListOfStrings(datafiles)

    @property
    def normalizationfiles(self):
        return self._normalizationfiles

    @normalizationfiles.getter
    def normalizationfiles(self):
        return self._normalizationfiles

    @normalizationfiles.setter
    def normalizationfiles(self,normalizationfiles):
        self._normalizationfiles = IsListOfStrings(normalizationfiles)

    @property
    def templocation(self):
        return self._templocation

    @templocation.getter
    def templocation(self):
        return self._templocation

    @templocation.setter
    def templocation(self,templocation):
        if isinstance(templocation,str):
            if not templocation[-1]=='/':
                templocation+='/'
            self._templocation=templocation
        else:
            raise AttributeError('Temporary location ({}) is not a string!'.format(templocation))


    @property
    def settings(self):
        return self._settings

    @settings.getter
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self,*args,**kwargs):
        raise NotImplementedError('Settings cannot be overwritten.')    

    def load(self,filename):
        """Method to load an object from a pickled file."""
        try:                                # Opening the given file with an error catch
            fileObject = open(filename, 'rb')
        except IOError as e:                        # Catch all IO-errors
            print("Error in opening file:\n{}".format(e))
        else:
            tmp_dict = pickle.load(fileObject)
            
            fileObject.close()
            # TODO: Make checks that the object loaded is of correct format?
            self=tmp_dict

    def save(self, filename):
        try:                                # Opening the given file with an error catch
            fileObject = open(filename, 'wb')
        except IOError as e:                        # Catch all IO-errors
            print("Error in opening file:\n{}".format(e))
        else:
                pickle.dump(self, fileObject)
                fileObject.close()  

    def initialize(self):
        ## Needed things for initialization: Instrument(?!), datafiles, normalizationfiles(?)
        if not '_instrument' in self.__dict__:
            raise RuntimeError("DataSet object does not contain an instrument!")
        elif not '_datafiles' in self.__dict__:
            raise RuntimeError("DataSet object does not contain data files!")
        elif not '_normalizationfiles' in self.__dict__:
            raise RuntimeError("DataSet object does not contain normalization files!")

        if self.instrument.settings['Initialized']==False:
            self.instrument.initialize()

    def __eq__(self, other): 
        return np.logical_and(set(self.__dict__.keys()) == set(other.__dict__.keys()),self.__class__ == other.__class__)

    def __str__(self):
        string = '{} with settings:\n'.format(self.__class__)
        for attrib in self.settings:
            string+='{}:\t{}\n'.format(attrib,self.settings[attrib])
        for attrib in self.__dict__:
            if attrib=='_settings':
                continue
            string+='{}:\t{}\n'.format(attrib,self.__dict__[attrib])
        string+='\n'    
        return string


    def EnergyCalibration(self,datafile,savelocation,tables=['Single','PrismaticLowDefinition','PrismaticHighDefinition','Unbinned'],InstrumentType='CAMEA',plot=False):
        """Method to generate look-up tables for normalization. Saves calibration file(s) as 'EnergyCalibration_Np.calib', where Np is the number of pixels.
        
        Generates 4 different tables:

        - Unbinned (452 pixels/detector)
            .. warning::
                Does not support unbinned normalization! Raises warning at current time.

        - Prismatic High Definition (8 pixels/energy or 64 pixels/detector)

        - Prismatic Low Definition (3 pixels/energy or 24 pixels/detector)

        - Single (1 pixel/energy or 8 pixels/detector)

        Arguments:

            datafile (string): String to data single data file used for normalization (required).

            savelocation (string): String to save location folder (required)

            tables (list): List of needed conversion tables (Default: ['Single','PrismaticLowDefinition','PrismaticHighDefinition','Unbinned'], increasing number of pixels).

            InstrumentType (string): Type of instrument (default CAMEA).

            plot (boolean): Set to True if pictures of all fit are to be stored in savelocation


        .. note::
            Assumes that file contains a scan over  Ei.

        .. warning::
            At the moment, the active detector area is defined by NumberOfSigmas (currently 3) times the Guassian width of Vanadium peaks.

        """
        if self.instrument.settings['Initialized']==False:
            self.initialize()


        if InstrumentType=='CAMEA':

            NormFile = hdf.File(datafile)

            if savelocation[-1]!='/':
                savelocation+='/'
            
            Data = np.array(NormFile.get(dataLocation)).transpose(1,0,2)
            Ei = np.array(NormFile.get(EiLocation))
            analysers = 8
            pixels = len(self.instrument.A4[0][0]) # <------------------- Change!
            detectors = len(self.instrument.A4[0])*len(self.instrument.A4)
            detectorsorInWedge = len(self.instrument.A4[0])
            wedges = len(self.instrument.A4)

            if pixels!=Data.shape[2]:
                raise ValueError('The number of pixels ({}) in the data file does not match instrument description ({})!'.format(pixels,Data.shape[2]))

            bins = []
            for table in tables:
                if table=='Unbinned':
                    bins.append(pixels)
                elif table=='PrismaticHighDefinition':
                    bins.append(8)
                elif table==table=='PrismaticLowDefinition':
                    bins.append(3)
                elif table==table=='Single':
                    bins.append(1)
                else:
                    raise AttributeError("Provided table attribute ({}) not recognized, should be 'Unbinned','PrismaticHighDefinition','PrismaticLowDefinition', and or'Single'")
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

            

            if plot:
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
                    #if i ==7:
                    #    print(guess)
                    res = scipy.optimize.curve_fit(Gaussian,np.arange(ESummedData.shape[1]),dataSubtracted[i,:],p0=[guess])
                    #if np.abs(res[0][1]-guess[1])>10:
                    #    print('Peak in detector {} with analyser {}, guess {}, diff {}'.format(i,j,guess[1],np.abs(res[0][1]-guess[1])))
                    peakPos[i,j] = res[0][1]
                    peakVal[i,j] = res[0][0]
                    peakWidth[i,j]= res[0][2]

                    # Generate peak as the one fitted and subtract it from signal
                    x=np.arange(pixels)
                    y = Gaussian(x,peakVal[i,j],peakPos[i,j],peakWidth[i,j],peakBackg[i,j])
                    #dataSubtracted[i]-=y
                    peak = y>peakVal[i,j]*0.05
                    dataSubtracted[i,peak]= 0

            if plot:
                plt.clf()
                #figman = plt.get_current_fig_manager()
                #figman.window.setGeometry(1366, 24, 1920, 1176)
                plt.suptitle('Fits')
                x = np.arange(pixels)
                for k in range(wedges):
                    for i in range(detectorsorInWedge):
                        y=np.zeros_like(x,dtype=float)
                        plt.subplot(4, 4, i+1)
                        plt.scatter(np.arange(pixels),ESummedData[i+13*k],s=4)
                        #	plt.scatter(peakPos[i],peakVal[i])
                        for j in range(analysers):
                            y += Gaussian(x,peakVal[i+13*k,j],peakPos[i+13*k,j],peakWidth[i+13*k,j],peakBackg[i+13*k,j])
                            plt.plot([peakPos[i+13*k,j],peakPos[i+13*k,j]],[0,np.max(ESummedData[i+13*k])*1.1])
                        plt.plot(x,y,'k')
                        plt.xlabel('Pixel')
                        plt.ylabel('Intensity [arg]')
                        plt.title('Detector {}'.format(i))
                        #plt.legend(['Fit','Data'])
                        plt.ylim(0,np.max(ESummedData[i+13*k])*1.1)

                    plt.tight_layout()
                    plt.savefig(savelocation+'/Raw/Fit_wedge_'+str(k)+'.png',format='png', dpi=150)

            
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
            #amplitudes= np.array([peakVal[i,argSort[i]] for i in range(detectors)])
            widths    = np.array([peakWidth[i,argSort[i]] for i in range(detectors)])
            #backgrounds=np.array([peakBackg[i,argSort[i]] for i in range(detectors)])
            
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
                if plot:
                    plt.clf()
                    plt.title('Detector {} Active pixels'.format(i))
                    plt.scatter(x,ESummedData[i],s=4,color='black')
                for j in range(analysers):
                    activePixels[i,j] = np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])
                    if plot: plt.scatter(x[np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])],
                        ESummedData[i,np.logical_and(x>lowerPixel[i,j],x<upperPixel[i,j])],s=4,color='red')
                if plot:
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
                if detpixels==pixels:
                    warnings.warn('Skipping full no binning option.') #<----------------------------- TODO
                    continue
                elif detpixels*analysers*3>len(Ei):
                    warnings.warn('Fitting might be unstable due to {} pixels being fitted using only {} energies ({} free parameters).'.format(detpixels,len(Ei),detpixels*analysers*3))
                    
                if plot:
                    EiX = np.linspace(Ei[0],Ei[-1],200)
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
                    if plot:
                        plt.clf()
                        plt.title('Detector {}, {} pixels'.format(i,detpixels))
                        x=np.linspace(0,detpixels,200)
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
                                raise ValueError('Fitting not converged, probably due to too few points.')



                            fittedParameters[i,j,k]=res[0]
                            if plot:
                                plt.plot(EiX,Gaussian(EiX,*fittedParameters[i,j,k]),color='black')
                                plt.scatter(Ei,binPixelData,color=colors[:,k])
                        activePixelAnalyser.append(np.linspace(-width/2.0,width/2.0,detpixels+1,dtype=int)+center+1)
                    activePixelDetector.append(activePixelAnalyser)
                    if plot:
                        plt.grid('on')
                        plt.xlabel('Ei [meV]')
                        plt.ylabel('Weight [arb]')
                        plt.tight_layout(rect=(0,0,1,0.95))
                        plt.savefig(savelocation+'/{}_pixels/Detector{}.png'.format(detpixels,i),format='png',dpi=300)


                fitParameters.append(fittedParameters)
                activePixelRanges.append(np.array(activePixelDetector))
                tableString = 'Normalization for {} pixel(s) using data {}\nPerformed {}\nDetector,Energy,Pixel,Amplitude,Center,Width,Background,lowerBin,upperBin\n'.format(detpixels,datafile,datetime.datetime.now())
                for i in range(len(fittedParameters)):
                    for j in range(len(fittedParameters[i])):
                        for k in range(len(fittedParameters[i][j])):
                            tableString+=str(i)+','+str(j)+','+str(k)+','+','.join([str(x) for x in fittedParameters[i][j][k]])
                            tableString+=','+str(activePixelRanges[-1][i][j][k])+','+str(activePixelRanges[-1][i][j][k+1])+'\n'
                
                tableName = 'EnergyNormalization_{}.calib'.format(detpixels)
                print('Saving {} pixel data to {}'.format(detpixels,savelocation+tableName))
                file = open(savelocation+tableName,mode='w')

                file.write(tableString)
                file.close()





            

def Gaussian(x,A,mu,sigma,b):
    #A,mu,sigma,b = args
    return A*np.exp(-np.power(mu-x,2.0)*0.5*np.power(sigma,-2.0))+b


def findPeak(data):
    return [np.argmax(data,axis=1),np.max(data,axis=1)]



        
def IsListOfStrings(object):
    if isinstance(object, list):
        isListOfStr = True
        for item in object:
            if not isinstance(item, str):
                isListOfStr=False
                break
        if isListOfStr:
            return object
        else:
            raise ValueError('Data files provided are not a list of strings or string!')
    elif isinstance(object,str):
        return [object]
    else:
        raise ValueError('Data files provided are not a list of strings or string!')
    






#__________________________TESTS_______________________

def test_DataSet_Creation():
    Instr = Instrument.Instrument()

    dataset = DataSet(instrument=Instr,OhterSetting=10.0)
    
    if(dataset.settings['OhterSetting']!=10.0):
        assert False

    try:
        dataset = DataSet(instrument=np.array([1.0]))
        assert False
    except:
        assert True

def test_Dataset_Initialization():
    Instr = Instrument.Instrument()
    emptyDataset = DataSet()
    try:
        emptyDataset.initialize()
        assert False
    except AttributeError:
        assert True
    
    dataset = DataSet(instrument=Instr,OhterSetting=10.0,datafiles='SomeFile',normalizationfiles=['VanData','SecondFile'])
    assert(dataset.datafiles[0]=='SomeFile')
    assert(dataset.normalizationfiles[0]=='VanData')
    assert(dataset.normalizationfiles[1]=='SecondFile')
    assert(len(dataset.normalizationfiles)==2)
    assert(dataset.instrument==Instr)
    assert(dataset.templocation=='_temp/')

    dataset.templocation = 'Other/'
    assert(dataset.templocation== 'Other/')

    try:
        dataset.initialize()
        assert False
    except:
        assert True

    wedge = Wedge.Wedge(position=(0.5,0,0),concept='ManyToMany')
    pixels=33
    split = [12,20]
    Det = Detector.TubeDetector1D(position=(1.0,1,0),direction=(1,0,0),pixels=pixels,split=split)
    Ana = Analyser.FlatAnalyser(position=(0.5,0,0),direction=(1,0,1))
    wedge.append([Det,Det,Ana,Ana,Ana])
    Instr.append(wedge)

    dataset.initialize()

def test_DataSet_Equality():
    D1 = DataSet(datafiles='Here',normalizationfiles=['Van/1.nxs','Van/2.nxs'])
    assert(D1==D1)

def test_DataSet_SaveLoad():
    Instr = Instrument.Instrument()
    D1 = DataSet(datafiles='Here',normalizationfiles = 'Van.nxs',instrument=Instr)
    # D1.normalizationfiles = 'Van.nxs'

    temp = 'temporary.bin'

    D1.save(temp)
    D2 = DataSet()
    D2.load(temp)
    os.remove(temp)
    #print(DataSet.__dict__)
    #print(str(D1))
    #print(str(D2))
    assert(D1==D2) 



