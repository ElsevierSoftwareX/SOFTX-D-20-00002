import sys
sys.path.append('.')
sys.path.append('..')
sys.path.append('../..')
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.gridspec

import warnings

from matplotlib import rc
rc('text', usetex=True)
plt.rc('text.latex', preamble=r'\usepackage{amsmath}')
import scipy.optimize
import pyperclip




class FittingFunction(object):
    def __init__(self,function):
        self.function = function
        self.__name__ = type(self).__name__
        self.executable = False
        self.fitError = False
    
    def __call__(self, x):
        return self.function(x,*self.parameters)

    @property
    def function(self):
        return self._function

    @function.getter
    def function(self):
        return self._function

    @function.setter
    def function(self,function):
        self._function = function
        self.parameterLength = self.function.__code__.co_argcount-2
        self.parameters = np.array([np.NaN]*self.parameterLength)
        self.parameterNames = np.array(self._function.__code__.co_varnames[2:])

    
    @property
    def parameters(self):
        return self._parameters

    @parameters.getter
    def parameters(self):
        return self._parameters

    
    @parameters.setter
    def parameters(self,parameters):
        self._parameters = parameters
        if np.sum(np.isnan(self._parameters))==0:
            self.executable=True
        else:
            self.executable=False
        
    

    def setParameter(self,event,index):
        raise NotImplementedError('The setParameter()-method is not yet implemented!')
    
highlighter = '\\boldsymbol{'
ender= '}'
def executable(func):
    def newFunc(self,*args,**kwargs):
        returnval = func(self,*args,**kwargs)
        if np.sum(np.isnan(self.parameters))==0:
            self.executable=True
        else:
            self.executable=False
        return returnval
    return newFunc

class Gaussian(FittingFunction):
    def func(self,x,A,mu,sigma,B):
        return A * np.exp(-np.power(x-mu,2.0)/(2*sigma**2))+B
    
    def __init__(self):
        super(Gaussian,self).__init__(self.func)
        self.format=['','\\','\\','']
        self.variableNames = [self.format[i]+self.parameterNames[i] for i in range(len(self.format))]
    @executable
    def setParameter(self,event,index):
        if index == 0:
            if not np.isnan(self.parameters[3]):
                self.parameters[0] = event.ydata-self.parameters[3]
            else:
                self.parameters[0] = event.ydata
            self.parameters[1] = event.xdata
            return 2
        elif index == 1:
            self.parameters[1] = event.xdata
            return 2
        elif index == 2:
            self.parameters[2] = np.abs(self.parameters[1]-event.xdata)/(np.sqrt(2*np.log(2)))
            return 3
        elif index == 3:
            if np.isnan(self.parameters[3]):
                self.parameters[0]-= event.ydata
            else:
                self.parameters[0]-= event.ydata-self.parameters[3]
            self.parameters[3] = event.ydata
            return 0


    def latex(self,highlight=None):
        if not highlight is None:
            if highlight==0:
                highlight = [0,1]
            highlight = np.array(highlight).reshape(-1)
            for i in highlight:
                self.variableNames[i] = highlighter+self.variableNames[i]+ender
        string = '$f(x, '
        string+=', '.join([x for x in self.variableNames])+') = '
        string+='{}'.format(self.variableNames[0])+'\\cdot \mathrm{exp}^{\left(-\\frac{\left(x-'+'{}'.format(self.variableNames[1])\
        +'\\right)^2}{2\\cdot '+'{}'.format(self.variableNames[2])+'^2}\\right)}+'+'{}'.format(self.variableNames[3])+'$'
        if not highlight is None:
            for i in highlight:
                self.variableNames[i] = self.variableNames[i][len(highlighter):-len(ender)]
        return string
    

class Lorentz(FittingFunction):
    def func(self,x,A,x_0,gamma,B):
        return A * np.power(gamma,2.0)/(np.power(x-x_0,2.0)+np.power(gamma,2.0))+B
    
    def __init__(self):
        super(Lorentz,self).__init__(self.func)
        self.format = ['','','\\','']    
        self.variableNames = [self.format[i]+self.parameterNames[i] for i in range(len(self.format))]
        self.currentFitParameter = 0
    @executable
    def setParameter(self,event,index):
        if index == 0:
            self.parameters[0] = event.ydata
            self.parameters[1] = event.xdata
            return 2
        elif index == 1:
            self.parameters[1] = event.xdata
            return 2
        elif index == 2:
            self.parameters[2] = np.abs(self.parameters[1]-event.xdata)
            return 3
        elif index == 3:
            if np.isnan(self.parameters[3]):
                self.parameters[0]-= event.ydata
            else:
                self.parameters[0]-= event.ydata-self.parameters[3]
            self.parameters[3] = event.ydata
            return 0     

    def latex(self,highlight=None):
        if not highlight is None:
            if highlight==0:
                highlight = [0,1]
            highlight = np.array(highlight).reshape(-1)
            for i in highlight:
                self.variableNames[i] = highlighter+self.variableNames[i]+ender
        string = '$f(x, '
        string+=', '.join([x for x in self.variableNames])+') = '
        string+='{}'.format(self.variableNames[0])+'\\cdot\\frac{'+'{}'.format(self.variableNames[2])\
        +'^2}{\left(x-'+'{}'.format(self.variableNames[1])+'\\right)^2+'+'{}'.format(self.variableNames[2])+'^2}+'\
        +'{}'.format(self.variableNames[3])+'$'
        
        if not highlight is None:
            for i in highlight:
                self.variableNames[i] = self.variableNames[i][len(highlighter):-len(ender)]

        return string
    

class State:
    def __init__(self,parent):
        self.parent = parent

    def button(self, event):
        assert 0, "button not implemented"
    def mouse(self, event):
        assert 0, "mouse not implemented"


class Initial(State):
    def __init__(self,parent):
        super(Initial,self).__init__(parent)
        self.__name__ = 'Initial'
    def button(self,event):
        if event.key in ['ctrl+i','i']:
            return FitInitialization(self.parent)
        return self
    def mouse(self,event):
        return self
        
            
class FitInitialization(State):
    def __init__(self,parent):
        super(FitInitialization,self).__init__(parent)
        self.__name__ = 'Fit\ Initialization\ -\ Click\ to\ choose\ bold\ parameter(s)\ or\ number\ for\ other\ models.'
        self.fitParameterIndex = 0 # Index of current fit parameter
        
        self.ps=' '.join(['{}: {}'.format(i,self.parent.fitObjects[i].__name__) for i in range(len(self.parent.fitObjects))])
        self.parent.updateText(self.fitParameterIndex,title=self.__name__,ps=self.ps)

        
    def button(self,event): # Change fitting function
        if event.key in [str(x) for x in np.arange(len(self.parent.fitObjects))]:
            
            self.parent.fitFunction = self.parent.fitObjects[int(event.key)]()
            self.fitParameterIndex = 0
            self.parent.updateText(self.fitParameterIndex,title=self.__name__,ps=self.ps)
        elif event.key in ['ctrl+i','i']:
            print('Current fit function is: {}({}) with values: {}'.format(self.parent.fitFunction.__name__,\
                  ', '.join([str(x) for x in self.parent.fitFunction.parameterNames]),', '.join([str(x) for x in self.parent.fitFunction.parameters])))
        elif event.key in ['r']:
            self.fitParameterIndex = np.mod(self.fitParameterIndex-1,self.parent.fitFunction.parameterLength)
            self.parent.fitFunction.parameters[self.fitParameterIndex] = np.NaN
            
        elif event.key in ['e']: # Execute fitting
            return Execute(self.parent)
            
        return self            
    def mouse(self,event):
        if not event.inaxes is None: # Only if inside the axis
        
            self.fitParameterIndex = self.parent.fitFunction.setParameter(event,self.fitParameterIndex)
            self.parent.plotFit() # Plot if possible
            
            self.parent.updateText(self.fitParameterIndex,title=self.__name__,ps=self.ps)
        return self

                
class Execute(State):
    def __init__(self,parent):
        super(Execute,self).__init__(parent)
        self.__name__='\mathrm{Fit\ Executed\ - Press\ "i"\ for\ new\ fit\ or\ "ctrl+c"\ to\ copy\ parameters}'
        
        ## Perform fit
        f = lambda *args: self.parent.fitFunction.func.__func__(None,*args)
        xdata = self.parent.xData
        ydata = self.parent.yData
        yerr = self.parent.yErr
        guess = self.parent.fitFunction.parameters

        # Set all nan-values to zero
        guess[np.isnan(guess)]=0.0

        yerr[yerr==0]==1 # Set all zero error values to 1
        fit = scipy.optimize.curve_fit(f,xdata,ydata,p0=guess,sigma=yerr,absolute_sigma=True)
        self.parent.fitFunction.parameters = fit[0]
        self.parent.fitFunction.fitError = fit[1]
        self.parent.plotFit()
        self.parent.updateText(title=self.__name__)
        
    def button(self,event):
        if event.key in ['ctrl+i','i']: # New fitting
            return FitInitialization(self.parent)
        else:
            return self
    
    def mouse(self,event):
        return self
        

    
class Viewer1D:
    initialText = 'Press "i" to initialize fitting procedure.'    
    fitObjects = [Gaussian,Lorentz]
    def __init__(self, XData,YData,YErr,fitFunction=fitObjects[0](),xLabel='',dataLabel='',xID = 0, yID = 0, plotAll = False):
        """Interactive visualization of 1D data with fitting cababilities.
        
        Args:
            
            - XData (list): List of x-valies in shape (n) or (n,m) for n scan points and m scan parameters.
            
            - YData (list): List of y-values in shape (n) or (n,m) or (n,m,l) for n scan points, m and l free.
            
            - YErr (list): List of y errors in same shape as YData.
            
        Kwargs:
            
            - fitFunction (FittingFunction): Custumized object to perform fitting (default Gaussian).
            
            - xLabel (list): X label text in shape (m) for m scan parameters (default '', nothing plotted).
            
            - dataLabel (list): Label to be shown in legend in shape (m) or (m,l), m and l free (default '', nothing plotted)
            
            - xID (int): Index of x axis to be used (default 0)
            
            - yID (int): Index of y axis to be plotted first (default 0)
            
            - plotAll (bool): Boolean deciding whether or not to plot all data (default False)
            
        Raises:
            
            - AttributeError
                
        Example:

        >>> from Mjolnir.Data import DataSet,Viewer1D
        >>> file = 'TestData/ManuallyChangedData/A3.nxs'
        >>> ds = DataSet.DataSet(convertedFiles = file)
        >>> data = ds.extractDetectorData(ID=10)
        >>>
        >>> Y = np.concatenate(data)[:,:5] # Only first 5 energies
        >>> Y_err = np.sqrt(Y) # Calculate errors
        >>> X = np.arange(Y.shape[0])
        >>> 
        >>> xlabel = ['Arbitrary [arb]']
        >>> dataLabel = np.array(['Detector 0: pos 0', 'Detector 0: pos 1', 'Detector 0: pos 2','Detector 0: pos 3', 'Detector 0: pos 4'])
        >>> 
        >>> # Initialize the viewer
        >>> Viewer = Viewer1D.Viewer1D(XData=X,YData=Y,\
        >>> YErr=Y_err,xLabel=xlabel,dataLabel = dataLabel,plotAll=True)

            
        For a walkthrough of the interface see :ref:`Raw plotting and fitting<Raw-plotting-and-fitting>`. 
        """
        ## Make x data into shape (N,M) for N: num of variables, M: scanpoints
        if len(XData.shape) >= 3 or len(XData.shape)==0:
            raise AttributeError('Expected size of xData is 1 or 2 dimensional')
        self.xDataAll = XData
        if len(XData.shape)==1:
            self.xDataAll = np.array(self.xDataAll).reshape(-1,1)
        
        
        if len(YData.shape) >= 4 or len(YData.shape)==0:
            raise AttributeError('Expected size of xData is 1, 2, or 3 dimensional')
        self.yDataAll = YData
        self.yErrAll = YErr
        if len(YData.shape)==1:
            self.yDataAll = np.array(self.yDataAll).reshape(-1,1)
            self.yErrAll = np.array(self.yErrAll).reshape(-1,1)
        elif len(YData.shape)==3: # yDataAll into shape (N,M) as above

            self.yDataAll = np.array(self.yDataAll).reshape(YData.shape[0],-1)
            self.yErrAll = np.array(self.yErrAll).reshape(YData.shape[0],-1)
            
            if not dataLabel is '':
                dataLabel = np.array(dataLabel).reshape(-1)
                dataLabel.dtype = object
                    
        
        if len(xLabel)!=self.xDataAll.shape[1] and xLabel!='':
            raise AttributeError('Provided x-labels do not match number of x-values. ({} labels and {} x-values)'.format(len(xLabel),len(self.xDataAll)))
        if len(dataLabel)!=self.yDataAll.shape[1] and dataLabel!='':
            raise AttributeError('Provided data labels do not match number of y values. ({} labels and {} x-values)'.format(len(dataLabel),len(self.yDataAll)))
        
        
        if xID>self.xDataAll.shape[1]-1:
            raise AttributeError('Provided xId ({}) is outside of x values provided ({})'.format(xID,self.xDataAll.shape[1]))
        self.xID = xID
        if yID>self.yDataAll.shape[1]-1:
            raise AttributeError('Provided yId ({}) is outside of y values provided ({})'.format(yID,self.yDataAll.shape[1]))
        self.yID = yID
        
        
        
        self.xLabel = xLabel
        self.dataLabel = dataLabel
        gs = matplotlib.gridspec.GridSpec(2, 1, height_ratios=[1, 6]) 
        self.figure = plt.figure()
        self.textAx = plt.subplot(gs[0])
        self.textAx.remove()
        self.ax = plt.subplot(gs[1])
        
        if self.yDataAll.shape[1]>10 and plotAll==True:
            warnings.warn('More than 10 plots are being plotted. This may take some time...')
        self.plotAll = plotAll
        
        self.text = self.initialText
        
        
        self.figure.canvas.mpl_connect('key_press_event',lambda event: self.button(event) )
        self.figure.canvas.mpl_connect('button_press_event',self.mouse )
        
        self.initData()
        
        
        self.fitFunction = fitFunction
        self.currentState = Initial(self)
        self.fitPlot = None # No initial plot
        
    @property
    def text(self):
        return self._text

    @text.getter
    def text(self):
        return self._text

    
    @text.setter
    def text(self,text):
        self._text = text
        try:
            self.textObject.remove()
        except:
            pass
        BBox = self.textAx.get_position()
        p0 = BBox.p0
        p1 = BBox.p1
        x = p0[0]-0.05
        y = p1[1]+0.1
        self.textObject = self.figure.text(x,y, self._text, fontsize=10, transform=self.figure.transFigure,horizontalalignment='left',\
                                           verticalalignment='top')
        
    def plotData(self):
        """Plot current data. First destroy previous plot if possible"""
        try:
            self.dataPlot.remove()
        except:
            pass
        self.ax.clear()
        if self.plotAll==False:
            self.dataPlot = self.ax.errorbar(self.xData,self.yData,yerr=self.yErr,fmt='.')
            self.ax.set_ylabel('Int [arb]')
            
            if not self.dataLabel is '':
                self.ax.legend([self.dataLabel[self.yID]])
                self.ax.legend_.draggable(True)
        else:
            for i in range(self.yDataAll.shape[1]):
                self.dataPlot = self.ax.errorbar(self.xData,self.yDataAll[:,i],yerr=self.yErrAll[:,i],fmt='.')

            if not self.dataLabel is '':
                labels = self.dataLabel.copy()
                    
                labels[self.yID] = '*'+labels[self.yID]
                self.ax.legend(labels)
                self.ax.legend_.draggable(True)
                
        if not self.xLabel is '':
                self.ax.set_xlabel(self.xLabel[self.xID])
        
    def plotFit(self):
        """Plot current guess or fit"""
        if self.fitFunction.executable:
            self.removeFitPlot()
            self.y = self.fitFunction(self.x)
            self.fitPlot = self.ax.plot(self.x,self.y)

    def initData(self):
        """Update with new indices both X and Y (+Yerr)"""
        self.xData = self.xDataAll[:,self.xID]
        self.yData = self.yDataAll[:,self.yID]
        self.yErr = self.yErrAll[:,self.yID]
        self.x = np.linspace(np.min(self.xData),np.max(self.xData),201)
        
        
        self.plotData()
            
    def removeFitPlot(self):
        """Try to remove previous fitPlot if it exists"""
        if not self.fitPlot is None:
            try:
                self.fitPlot[0].remove()
            except:
                pass
                
    def button(self,event):
        if event.key in ['up','down','left','right']: # Change xID or yID
            if event.key == 'left':
                if self.xDataAll.shape[1]>1:
                    self.xID = np.mod(self.xID-1,self.xDataAll.shape[1])
                else:
                    return
            elif event.key == 'right':
                if self.xDataAll.shape[1]>1:
                    self.xID = np.mod(self.xID+1,self.xDataAll.shape[1])
                else:
                    return
            elif event.key == 'down':
                self.yID = np.mod(self.yID-1,self.yDataAll.shape[1])
            elif event.key == 'up':
                self.yID = np.mod(self.yID+1,self.yDataAll.shape[1])
            self.initData()

        elif event.key in ['ctrl+c']:
            pyperclip.copy(', '.join([str(x) for x in self.fitFunction.parameters]))
        else:
            self.currentState = self.currentState.button(event)
    def mouse(self,event):
        self.currentState = self.currentState.mouse(event)    
        
    def updateText(self,highlight=None,title=None,ps=None):
        text = '$\mathbf{'+'{}'.format(title)+'}$'+'\nCurrent fitting model: {}\n'.format(self.fitFunction.latex(highlight=highlight))
        for i in range(self.fitFunction.parameterLength):
            if np.isnan(self.fitFunction.parameters[i]):
                val = '   '
            else:
                val = '{:.3e}'.format(self.fitFunction.parameters[i])
            text+='${}$:    {}     '.format(self.fitFunction.variableNames[i],val)
        if not self.fitFunction.fitError is False:
            text+='\n'
            for i in range(self.fitFunction.parameterLength):
                if np.isnan(self.fitFunction.parameters[i]):
                    val = '   '
                else:
                    val = '{:.3e}'.format(np.sqrt(self.fitFunction.fitError[i,i]))
                text+='${}{}{}$:  {}    '.format('\sigma_{',self.fitFunction.variableNames[i],'}',val)
        if not ps is None:
            text+='\n'+ps
        self.text = text