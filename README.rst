
.. role:: py(code)
   :language: python



.. raw:: html

    <img align="right" width="150" height="150" src="assets/logo_border.png" alt="omni-fig">

--------
omni-fig
--------


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

You can clone this repo and install the local version for development:

.. code-block:: bash

    git clone https://github.com/felixludos/omni-fig
    pip install -e ./omni-fig

.. end-install-marker-do-not-remove


TODO
====

Features that could be added/improved:

- make sure json strings can be passed from the terminal

Contributions and suggestions are always welcome.

.. end-setup-marker-do-not-remove