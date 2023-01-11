.. _behaviors-info:

Behaviors
================================================================================

.. TODO: vignette A2

One of the key features of ``omni-fig`` to provide additional control and customization over how your scripts are run is the ability to specify *behaviors*. Behaviors are classes with a variety of callbacks at different stages of the :ref:`execution sequence <Execution Sequence>`. Behaviors are usually activated by including a flag in the command line arguments, but can also be activated directly through in the config under the ``_meta`` branch.

A comprehensive documentation of the callbacks are found in :class:`AbstractBehavior <omnifig.abstract.AbstractBehavior>`, but most common callbacks are:

* :meth:`parse_argv <omnifig.abstract.AbstractBehavior.parse_argv>`: called before the :code:`sys.argv` is parsed (and commonly used to check whether or not the behavior should be activated (see :meth:`parse_argv <omnifig.behaviors.base.Behavior.parse_argv>`).

* :meth:`validate_project <omnifig.abstract.AbstractBehavior.validate_project>`: called after the project is loaded, and can be used to switch to a different project.

* :meth:`include <omnifig.abstract.AbstractBehavior.include>`: called after the project is validated, to select which behaviors should be run.

* :meth:`pre_run <omnifig.abstract.AbstractBehavior.pre_run>`: called before the script is run

* :meth:`handle_exception <omnifig.abstract.AbstractBehavior.handle_exception>`: called when an exception is raised during the script execution

* :meth:`post_run <omnifig.abstract.AbstractBehavior.post_run>`: called after the script is run, including the output of the script. If this callback returns a value, it will be used as the output of the script.

Additionally, ``omni-fig`` comes with a few simple, common behaviors that serve as examples of what you can do with behaviors. For more details check out the :ref:`documentation <behaviors-code>`.

Help
----

The :class:`Help <omnifig.behaviors.help.Help>` behavior provides a simple way to add help messages to your scripts. It is activated by the ``-h`` flag, and will print out the help message for the ``fig`` command. If a script is specified in a command with the help flag, then the :code:`__doc__` of the script function is also included in the help message.

Debug
-----

The :class:`Debug <omnifig.behaviors.debug.Debug>` behavior provides a simple way to add debug messages to your scripts. It is activated by the ``-d`` flag, and will automatically compose the config object with a registered config named ``debug``. This is particularly useful when using IDEs like PyCharm or VS Code where you can define a fixed script execution ``fig -d``, and then you can directly edit the file ``config/debug.yaml`` to specify the script and other config files that should be included.

Note that you can specify which script should be run in the config with the key ``_meta.script_name``.

Quiet
-----

The :class:`Quiet <omnifig.behaviors.quiet.Quiet>` behavior provides a simple way to suppress messages sent to the console. It is activated by the ``-q`` flag.

