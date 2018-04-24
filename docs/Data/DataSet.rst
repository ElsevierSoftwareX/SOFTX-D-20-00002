.. :DataModule:

Data Module
===========

.. currentmodule:: Data



.. autosummary::
   :nosignatures:

    DataSet.DataSet
    DataSet.DataSet.convertDatafile
    DataSet.DataSet.cut1D
    DataSet.DataSet.plotCut1D
    DataSet.DataSet.cutQE
    DataSet.DataSet.plotCutQE
    DataSet.binData3D
    DataSet.calculateGrid3D
    DataSet.cut1D
    DataSet.plotCut1D
    DataSet.binEdges
    DataSet.cutQE
    DataSet.plotCutQE

.. automodule:: Data
   :members: 

Data Set Object
^^^^^^^^^^^^^^^

Object to take care of all data conversion and treatment taking it from raw hdf5 files obtained at the instrument into rebinned data sets converted to S(q,omega). 

.. automodule:: DataSet

.. _DataSet:

.. autoclass:: DataSet
    :members:



DataSet bin data
^^^^^^^^^^^^^^^^
.. autofunction:: binData3D


DataSet calculated 3D grid
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. autofunction:: calculateGrid3D


DataSet cut1D
^^^^^^^^^^^^^
.. autofunction:: cut1D

DataSet plotCut1D
^^^^^^^^^^^^^^^^^
.. autofunction:: plotCut1D

DataSet binEdges
^^^^^^^^^^^^^^^^
.. autofunction:: binEdges


DataSet cutQE
^^^^^^^^^^^^^
.. autofunction:: cutQE

DataSet plotCutQE
^^^^^^^^^^^^^^^^^
.. autofunction:: plotCutQE
