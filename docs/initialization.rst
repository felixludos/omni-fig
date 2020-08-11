Initialization
==============

It is strongly encouraged to *initialize* omni-fig before running any scripts. When calling a script from the terminal using the ``fig`` command, omni-fig will initialize automatically, but when running in a separate environment (such as in a jupyter notebook), it is suggested to call :func:`omnifig.initialize()` after importing the package. More info about :func:`initialize` can be found in :ref:`scripts:Running Scripts`.

The initialization process:

    1. runs the initial "princeps" file (if one is specified)
    2. loads the profile (if one exists)
    3. loads any active projects listed in the profile
    4. recursively loads all related projects
    5. loads the profile in the current working directory (if there is one and it hasn't been loaded yet)

Princeps File
-------------

The *princeps* file is an optional startup file that can be run to change global settings in ``omni-fig``, to change the profile type, to register new project types, or to make other advanced customizations in how ``omni-fig`` runs.

The *princeps* file is specified by defining an environment variable ``FIG_PRINCEPS_PATH`` which contains the absolute path to a python file.

For most use cases it should not be necessary to specify a *princeps* file, and running one can also be disabled all together - so it is generally discouraged to use a princeps file unless absolutely necessary.

Profiles
--------

Generally, every OS image or file system should use it's own *profile*. The profile is specified by defining an environment variable ``FIG_PROFILE`` which contains the absolute path to a yaml file.

While using a profile is completely optional, it is highly recommended as the profile is the primary way to specify the location of all of your projects that you may want to load. Additionally, the profile can be used to change the global settings of ``omni-fig`` to tailor the behavior to the specific machine/OS. Since the profile is meant to act globally for the whole file system, all paths should be absolute.

The most important contents of the profile file (all of which are optional):

- ``projects`` - dictionary from project name to absolute path to the project directory
- ``active_project`` - list of names of projects that should automatically be loaded (the paths to these projects must be in the ``projects`` table
- ``config_paths`` - list of absolute paths to config (yaml) files or directories that should be registered when loading
- ``src_paths`` - list of absolute paths to python files that should be run when loading
- ``default_ptype`` - name of the registered project type that should be used to load projects (default: ``default``)
- ``global_settings`` - dictionary of setting names and values to be set during loading
- ``autoload_local`` - bool to specify whether the project in the current working directory should be loaded (default: ``True``)

.. automodule:: omnifig.profiles
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,mtype
    :member-order: bysource

Projects
--------

For ``omni-fig`` to recognize a directory as a project, it must contain a yaml file named ``.fig.yml`` (or similarly, see code for all options). This yaml file should contain all project specific information (similar to profiles) that may be useful for running code or interacting with other projects. The most important information contained in the project yaml file:

- ``related`` - a list of project names that should be loaded before loading this one (all the paths to all related projects must be found in the profile's ``projects`` table)
- ``src`` - the relative path to the python file that should be run in order to fully load all components of this project
- ``name`` - while not enforced, it is strongly encouraged that project info files contain their own name (ideally the same as is used in the profile's ``projects`` table)
- ``project_type`` - the registered name of the project type to use when instantiating this project
- ``ptype_src_file`` - a python file to run before trying to load this project (for example, as it might define and register the desired project type)
- ``py_info`` - relative path to a python file that defines project meta data (this is particularly useful for projects that are packages, as the meta data is potentially already specified in various places, like ``requirements.txt``) (``omni-fig`` itself is a good example, see this project's ``.fig.yml`` file and the associated ``omnifig/_info.py`` file)

The directory that contains the project info file (``.fig.yml``) is defined as the "project directory". All paths in the info file should be relative to the project directory. By default, if there is a directory called ``config`` or ``configs`` in the project directory, then that directory will automatically be registered as a config directory (ie. all yaml files inside will be registered while preserving the folder hierarchy) - see the unit tests (in ``test/`` for an example).

When a project is loaded, first the desired type is identified. As a result, you can subclass the :class:`Project` class and override the behavior of project objects. Note that this is a fairly advanced featured and should be used only when absolutely necessary (atm I'm not sure why I added this feature in the first place).

.. automodule:: omnifig.projects
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,__str__,__repr__
    :member-order: bysource


Meta Rules
----------

Meta rules allows changing any script's behavior before it is run, primarily by making changes in the loaded config or changing the run mode that will be used for execution. Meta rules can be activated from the command line using the registered code (usually a single letter) preceded by a single "-". A meta rule can also be provided with additional required arguments (ie. strings), but the number of arguments must be specified when registering. If a meta rule is activated it should appear in the meta config (under the branch ``_meta`` in the config object).

Before a script is executed, all registered meta rules are executed in order of priority (low to high). Since all meta rules are always executed, each rule is expected to check the meta config object whether it has been activated and act accordingly. Note that every meta rule is given the loaded config (and separately the meta config) and returns the config after making whatever changes are desired.

.. automodule:: omnifig.rules
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,_Rules_Registry,view_meta_rules,meta_rule_fns
    :member-order: bysource


Help Rule
*********

As a particularly useful example of how meta rules can be used, the "help rule" implements the help messages for the ``fig`` command, which includes printing out a list of all registered scripts (after the relevant projects are loaded) as well as descriptions (if they are provided).

Note that by subclassing and reregistering this rule, the help message and behavior can easily be augmented.

.. automodule:: omnifig.help
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__
    :member-order: bysource



Run Modes
---------

The run mode is a component that is created using the meta config object. Aside from any user defined functionality, the run mode responsible for identifying the script that should be run (by default saved to ``script_name`` in the meta config), find the corresponding function (usually using :meth:`self.get_script_info`), execute it with the provided config, and finally return the output.

.. automodule:: omnifig.modes
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__
    :member-order: bysource

Debug Mode
**********

The debug mode serves as a good example for how run modes can be used. During development of new scripts and components it can be invaluable to use a debugger (such as in pycharm) to step through the code and see exactly where bugs might be lurking. Alternatively, when running in the terminal, you can still debug your script using the ``ipdb.post_mortem()`` debugger.

The debug mode is activated using a meta rule (``-d`` => ``debug``), which then changes the run mode to the debug run mode (registered under ``run_mode/debug``. Finally, the debugger also automatically updates the config to include a ``debug`` config (registered as ``debug``)

.. automodule:: omnifig.debug
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__
    :member-order: bysource


Utilities
---------

While this doesn't include all of the utilities used for organization and managing projects and scripts,
this should give you a sense for where some of the functionality from behind the scenes actually originates.

Generally, it should not be necessary for a user to call any of these utilities, but they may be useful to
add or change the behavior of ``omni-fig``.

.. automodule:: omnifig.external
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,_Config_Registry
    :member-order: bysource


.. automodule:: omnifig.loading
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,__init__,__enter__,__exit__
    :member-order: bysource

