Execution Sequence
================================================================================

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

