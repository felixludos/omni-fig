# omni-fig

A universal configuration system for managing scripts and their arguments for several different kinds of execution environments.

Supported execution environments:

- Terminal - most basic environment, just calling a script directly from the terminal (including ipdb debugging)
- Jupyter - running scripts (or individual parts) in a jupyter notebook
- Pycharm - using the pycharm debugger to step through the scripts with the desired configuration.
- Cluster - submitting scripts as jobs on to a remote computing cluster or cloud computing.
