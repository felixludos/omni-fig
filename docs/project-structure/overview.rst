.. _project-overview:

Overview
========

This guide will walk you through some of the tips and tricks to take full advantage of ``omni-fig`` in your python projects. Keep in mind that most of project structure suggested here is not strictly required, and can easily be adapted to your specific workflow.

Each project has several registries to keep track of all associated config files, scripts, and classes, as well as the project's root directory. The registries keep track of all top-level functionality you want to make accessible to the user.

To create a project, the only thing that is actually required is to have a project info file named ``.omnifig.yml`` in the root directoy (which may be empty). That project info file may contain the following fields (in YAML format):

- ``name`` - The name of the project. If not specified, the name will be the name of the directory containing the project info file.

- ``module`` - Specifies one or multiple python modules that should be imported when the project is loaded. These should be specified as if you were using an import statement, e.g. ``mymodule.myscript`` instead of ``mymodule/myscript.py``. If there are multiple modules to import, they should be specified as a list of strings.

- ``src`` - (advanced feature) Specifies one or multiple paths to python source files (relative to the project root directory) that should be run when the project is loaded. If there are multiple paths to import, they should be specified as a list of strings. Note that the difference between ``module`` and ``src`` is that ``module`` uses import which adds the module/s to ``sys.modules``, while ``src`` does not. If you are unsure which to use, generally if you would use ``import`` in your code, use ``module``, while if you want to specify the file or directory by its path, use ``src``.

- ``related`` - (advanced feature) Specifies a list of names of other projects to load when this project is loaded. This is useful if you have a project that is a collection of other projects, and you want to load them all at once. Importantly, the projects must be specified by the same name that is used in the :ref:`profile <Profiles>`.

By default, if there is a directory called ``config`` in the project directory, then all yaml files inside will be registered while preserving the directory structure.

So for example, a project directory may look like this:

.. code-block::

    myproject/ - project root directory
    │
    ├── config/ - any YAML config files that should automatically be registered
    │   ├── dir1/
    │   │   ├── myconfig2.yaml - will be registered as 'dir1/myconfig2'
    │   │   └── ...
    │   │
    │   ├── myconfig1.yaml - will be registered as 'myconfig1'
    │   └── debug.yaml - config to be used in :ref:`Debug` mode
    │
    ├── scripts/ - some python module containing all the code
    │   ├── __init__.py - required by python to make this a module
    │   ├── myscript.py
    │   └── ...
    │
    ├── .omnifig.yml - project info file
    └── ...

Where the ``.omnifig.yml`` file may look like this:

.. code-block:: yaml

    name: some-name
    module: scripts


To see exactly what else projects can do, check out the documentation on :ref:`projects <Project Base>` and their :ref:`default behavior <Default Projects>`.

.. TODO: vignette B1 project organization
