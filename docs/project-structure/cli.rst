.. _highlight-cli:

Command Line Interface
================================================================================

There are several ways to run scripts that are registered using ``omni-fig``. The most common way is through the command line using the ``fig`` command.

The `fig` command should be used like this:

.. code-block:: bash

    fig [-<meta>] <script> [<configs>...] [--<args>]


* ``script`` - refers to the registered name of the script that should be run. This can be "_" to specify that the script is already specified in the config. When using the `fig` command, the script is a required argument.
* ``meta`` - any :ref:`Behavior` that should be activated to modify the execution of the script (and must use the prefix ``-``. For example, use ``-h`` to see the :ref:`Help` message, or ``-d`` to run the script in :ref:`Debug` mode.
* ``configs`` - is an ordered list of names of registered config files that will be composed and passed to the script function.
* ``args`` - any manually provided arguments to be added to the config object. Here each argument key must be preceded by a ``--`` and optionally followed by a value (which is parsed as yaml syntax), if not value is provided the key is set to :code:`True`.


.. TODO: vignette B2 project organization


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
--------------------


.. TODO: vignette execution environment


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



