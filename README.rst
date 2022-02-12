=====
eyepy
=====

.. image:: https://badge.fury.io/py/eyepie.svg
    :target: https://badge.fury.io/py/eyepie

.. image:: https://travis-ci.com/MedVisBonn/eyepy.svg?branch=master
    :target: https://travis-ci.com/MedVisBonn/eyepy

.. image:: https://readthedocs.org/projects/eyepy/badge/?version=latest
        :target: https://eyepy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


This software is under active development and things might change without
backwards compatibility. If you want to use eyepy in your project make sure to
pin the version in your requirements file.


Features
--------

* Read the HEYEX XML export
* Read the HEYEX VOL export
* Read B-Scans from a folder
* Read the public OCT Dataset from Duke University
* Plot OCT Scans
* Compute Drusen from BM and RPE segmentations


Getting started
---------------

Installation
^^^^^^^^^^^^
To install the latest version of eyepy run :code:`pip install -U eyepie`. It is :code:`eyepie` and not :code:`eyepy` for
installation with pip.

Import Data
^^^^^^^^^^^^

.. code-block:: python

   import eyepy as ep

   # Load an HEYEX XML export
   ev = ep.import_heyex_xml("path/to/folder")

   # Load an HEYEX VOL export
   ev = ep.import_heyex_vol("path/to/file.vol")

The EyeVolume object
^^^^^^^^^^^^^^

When loading data as described above an EyeVolume object is returned. You can use
this object to perform common actions on the OCT volume such as:

+ Iterating over the volume to retrieve EyeBscan objects :code:`for bscan in ev:`
+ Plotting a localizer (NIR) image associated to the OCT :code:`ev.plot(localizer=True)`
+ Accessing an associated localizer image :code:`ev.localizer`
+ Reading Meta information from the loaded data if available :code:`ev.meta["scale_x"]`

All B-scans of the volume are assembled into a 3D numpy array which is accessible via the :code:`data` attribute like :code:`ev.data`. The shape of this numpy array is (Number of B-scans, B-scan height, B-scan width).
