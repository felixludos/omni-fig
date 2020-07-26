
.. role:: py(code)
   :language: python



.. raw:: html

    <img align="right" width="150" height="150" src="assets/logo_border.png" alt="omni-fig">

--------
omni-fig
--------

.. image:: https://readthedocs.org/projects/omnifig/badge/?version=latest
    :target: https://omnifig.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.com/felixludos/omni-fig.svg?branch=master
    :target: https://travis-ci.com/felixludos/omni-fig
    :alt: Test Status

.. setup-marker-do-not-remove

.. role:: py(code)
   :language: python

A universal configuration system for managing scripts and their arguments for several different kinds of execution environments.

This also includes a registration system for module components and modifiers to enable automatically creating any component (or modification thereof) without having to deal with import statements.


Install
=======

.. install-marker-do-not-remove

Everything is tested with Python 3.7 on Ubuntu 18.04, but there is no reason it shouldn't also work for Windows.

You can clone this repo and install the local version for development:

.. code-block:: bash

    git clone https://github.com/felixludos/omni-fig
    pip install -e ./omni-fig

.. end-install-marker-do-not-remove

Quickstart
==========

.. quickstart-marker-do-not-remove

[todo]

.. end-quickstart-marker-do-not-remove


TODO
====

Features that could be added/improved:

- make sure json strings can be passed from the terminal
- add the "py_info" arg to integrate branch project meta data automatically
- make sure updating config objects works as expected
- fill in UNIT TESTS !! (especially for config system!)

Contributions and suggestions are always welcome.

.. end-setup-marker-do-not-remove