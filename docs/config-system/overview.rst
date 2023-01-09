.. _config-overview:

Overview
================================================================================

This section discusses different ways to create and use the config object.

The original motivation for this package was to design a system that would read arguments from files, the terminal, or directly as python objects (eg. in a jupyter notebook) and would structure so that the arguments are always used in the code where they need to be. This is accomplished chiefly by a hierarchical tree-like structure in the config much like a tree where each branch corresponds to the a :code:`dict` or :code:`list` of arguments.



