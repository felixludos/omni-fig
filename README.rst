
.. role:: py(code)
   :language: python



.. raw:: html

    <img align="right" width="150" height="150" src="docs/_static/img/logo_border.png" alt="HumPack">

--------
omni-fig
--------

.. image:: https://readthedocs.org/projects/humpack/badge/?version=latest
    :target: https://humpack.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.com/fleeb24/HumPack.svg?branch=master
    :target: https://travis-ci.com/fleeb24/HumPack

.. setup-marker-do-not-remove

.. role:: py(code)
   :language: python

A universal configuration system for managing scripts and their arguments for several different kinds of execution environments.

Supported execution environments:

- Terminal - most basic environment, just calling a script directly from the terminal (including ipdb debugging)
- Jupyter - running scripts (or individual parts) in a jupyter notebook
- Pycharm - using the pycharm debugger to step through the scripts with the desired configuration.
- Cluster - submitting scripts as jobs on to a remote computing cluster or cloud computing.


Install
=======

.. install-marker-do-not-remove

Everything is tested with Python 3.7 on Ubuntu 18.04, but there is no reason it shouldn't also work for Windows.

You can install this package through pip:

.. code-block:: bash

    pip install omni-fig

Alternatively, you can clone this repo and install the local version for development:

.. code-block:: bash

    git clone https://github.com/felixludos/omni-fig
    pip install -e ./omni-fig

.. end-install-marker-do-not-remove


TODO
====

Features that could be added/improved:

-

- Enable simple conversion from containers to standard python (eg. decontainerify)
- Add security functions to encrypt/decrypt files and directories (collecting/zipping contents in a tar)
- Add Transactionable/Packable replacements for more standard python types (especially tuples)
- Possibly add 1-2 tutorials
- Write more comprehensive unit tests and report test coverage
- Allow packing bound methods of Packable types
- Add option to save class attributes

Contributions and suggestions are always welcome.

.. end-setup-marker-do-not-remove