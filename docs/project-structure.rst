Project Structure
=================

This guide will walk you through some of the tips and tricks to take full advantage of ``omni-fig`` in your python projects. Keep in mind that most of project structure suggested here is not strictly required, and can easily be adapted to your specific workflow.

Each project has several registries to keep track of all associated config files, scripts, and classes, as well as the project's root directory. The registries keep track of all top-level functionality you want to make accessible to the user.

To create a project, the only thing that is actually required is to have a project info file named ``.omnifig.yml`` in the root directoy (which may be empty). That project info file may contain the following fields (in YAML format):

- ``name``: The name of the project. If not specified, the name will be the name of the directory containing the project info file.

- ``module``: Specifies one or multiple python modules that should be imported when the project is loaded. These should be specified as if you were using an import statement, e.g. ``mymodule.myscript`` instead of ``mymodule/myscript.py``. If there are multiple modules to import, they should be specified as a list of strings.

- ``src``: (advanced feature) Specifies one or multiple paths to python source files (relative to the project root directory) that should be run when the project is loaded. If there are multiple paths to import, they should be specified as a list of strings. Note that the difference between ``module`` and ``src`` is that ``module`` uses import which adds the module/s to ``sys.modules``, while ``src`` does not. If you are unsure which to use, generally if you would use ``import`` in your code, use ``module``, while if you want to specify the file or directory by its path, use ``src``.

- ``related``: (advanced feature) Specifies a list of names of other projects to load when this project is loaded. This is useful if you have a project that is a collection of other projects, and you want to load them all at once. Importantly, the projects must be specified by the same name that is used in the :ref:`profile <Profiles>`.

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


To see exactly what else projects can do, check out the documentation :ref:`here <Projects>`.


Command Line Interface
----------------------

There are several ways to run scripts that are registered using ``omni-fig``. The most common way is through the command line using the ``fig`` command.

The `fig` command should be used like this:

.. code-block:: bash

    fig [-<meta>] <script> [<configs>...] [--<args>]



* ``script`` - refers to the registered name of the script that should be run. This can be "_" to specify that the script is already specified in the config. When using the `fig` command, the script is a required argument.
* ``meta`` - any :ref:`Behavior` that should be activated to modify the execution of the script (and must use the prefix ``-``. For example, use ``-h`` to see the :ref:`Help` message, or ``-d`` to run the script in :ref:`Debug` mode.
* ``configs`` - is an ordered list of names of registered config files that will be composed and passed to the script function.
* ``args`` - any manually provided arguments to be added to the config object. Here each argument key must be preceded by a ``--`` and optionally followed by a value (which is parsed as yaml syntax), if not value is provided the key is set to :code:`True`.

However, the ``fig`` command really just calls :func:`fig.entry() <omnifig.top.entry>`, so you can customize the entry point as well. For example, with a python file ``main.py`` in the project directory that looks like this:

.. code-block:: python

    import omnifig as fig

    if __name__ == '__main__':
        fig.entry()

Now, running something like ``python main.py <script> [<configs>...]`` is equivalent to ``fig <script> [<configs>...]``. This is useful if you want to add additional functionality to the entry point of your project, or if you want to specify the script to run in the python file instead of the command line. For example, given that we registered a script called ``launch-server``, we could create another python file ``launch.py`` that looks like this:

.. code-block:: python

    import omnifig as fig

    if __name__ == '__main__':
        fig.entry('launch-server')

Now running something like ``python launch.py [<configs>...]`` is equivalent to ``fig launch-server [<configs>...]``.

Execution Sequence
******************

Here's a breakdown of exactly what happens when you run the ``fig`` command, which is the main entry point for running scripts.

#. First, the ``omnifig`` package is imported.
#. Then :func:`fig.entry() <omnifig.top.entry>` is called.

    #. The profile is detected and loaded (see :ref:`Profiles`) with :meth:`profile.activate() <omnifig.abstract.AbstractProfile.activate>`.

        #. The current project is detected (see :ref:`Projects`), but not loaded yet.
        #. Any specified active base projects are loaded (see :ref:`Profiles`).

    #. :func:`fig.main() <omnifig.top.main>` is called with the script name (if one is provided to :code:`entry()` and the system arguments :code:`sys.argv`.

        #. The project is loaded, importing any specified modules and running any source files (see :ref:`Projects`) with :meth:`project.activate() <omnifig.workspaces.GeneralProject._activate>`.
        #. All registered behaviors are instantiated (see :ref:`Behaviors`).
        #. The provided arguments are parsed with the project's :class:`ConfigManager.parse_argv <omnifig.config.ConfigManager.parse_argv>` and the behaviors to produce the config object
        #. Using the config object, the project is validated using :meth:`project.validate(config) <omnifig.abstract.AbstractProject.validate>` method (which allows the config or behaviors to switch projects before the script is run).
        #. The script is run with the config object using :meth:`project.run_script(script, config) <omnifig.workspaces.GeneralProject.run_script>`.

            #. If a script was provided manually, that is added to the config object.
            #. :meth:`pre_run() <omnifig.abstract.AbstractBehavior.pre_run>` method is called on all behaviors.
            #. The script is run with the config object
            #. :meth:`post_run() <omnifig.abstract.AbstractBehavior.post_run>` method is called on all behaviors.

        #. The project is cleaned up using :meth:`project.cleanup() <omnifig.abstract.AbstractProject.cleanup>` method.
        #. The output of the script is returned by :func:`fig.main() <omnifig.top.main>`, but not by :func:`fig.entry() <omnifig.top.entry>`.


Scripts, Components, and Modifiers
----------------------------------

Aside from config files, ``omni-fig`` primarily keeps track of three different kinds of top-level deliverables: scripts, components, and modifiers. These are all registered using the corresponding decorators :func:`fig.script() <omnifig.registration.script>`, :func:`fig.component() <omnifig.registration.component>`, and :func:`fig.modifier() <omnifig.registration.modifier>`.

* Scripts are functions that should expect the first positional argument to be the config object.

* Components are classes that are recommended to subclass :class:`fig.Configurable <omnifig.configurable.Configurable>` (see :ref:`Configurable`) to extract all the arguments in :code:`__init__` from the config object automatically. If they do not subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, then they should expect the first positional argument to be the config object.

* Modifiers are classes much like components, except that they are used to modify components by dynamically creating a subclass of the modifier and the component at runtime. Consequently, it is also strongly recommended that modifiers subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, or otherwise they should expect the first positional argument to be the config object.


.. TODO: discuss autocomponents and autoscripts


Registration
------------

[missing]


.. TODO: xray


Configurable
------------

[missing]

:ref:`Configurable <Configurable Mixin>`


.. TODO: profiles and related projects



