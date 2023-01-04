.. _common:

Default Behavior
================

There are several ways to run scripts that are registered using ``omni-fig``. The most common way is through the command line using the ``fig`` command or from a different environment (eg. a jupyter notebook) using :func:`run()` or :func:`quick_run()` (depending on if the config has already been loaded or not).

The ``fig`` command should be used:

.. code-block::

    fig [-<meta>] <script> [<configs>...] [--<args>]

- ``script`` - refers to the registered name of the script that should be run. This can be "_" to specify that the script is already specified in the config. When using the ``fig`` command, the script is a required argument.
- ``meta`` - any meta rules that should be activated should use their respective (usually single letter) codes and must always be preceeded by a ``-``.
- ``configs`` - is an ordered list of names of registered config yaml files that should be loaded and merged when creating the config object.
- ``args`` - any manually provided arguments to be added to the config object after loading/merging ``configs``. Here each argument key must be preceded by a ``--`` and optionally followed by a value (which is parsed as yaml syntax), if not value is provided the key is set to :code:`True`.

Another slightly more advanced way to run specific scripts from the terminal is by directly calling a python file that explicitly calls :func:`entry()` or :func:`main()`. Below is an example of the recommended way to do so:

Contents of python file called ``main.py``:

.. code-block:: python

    import omnifig as fig

    if __name__ == '__main__':
        fig.entry('myscript')


Here ``myscript`` must be the name of a registered script (for example when loading the associated project), or it can be left out (in which case calling the python file behaves identically to calling the ``fig`` command).

Now the example command from the terminal to execute ``myscript`` using the meta argument ``d`` (which switches to debug mode by default), a few registered configs (``myconfig1`` and ``myconfig1``), and some manually provided arguments (``myflag`` and ``myvalue``):

.. code-block::

    python main.py -d myconfig1 myconfig2 --myflag --myvalue 1234

Note that if a script name is provided manually (as in ``main.py`` in this example), then no script name (or ``_``) must be specified from the command line.

The equivalent command without using ``main.py`` is:

.. code-block::

    fig -d myscript myconfig1 myconfig2 --myflag --myvalue 1234


.. automodule omnifig.running


Top-level interface
-------------------

By default, these functions provide all the basic and most important features of this package. However, they usually delegate all the real heavy-lifting to the "current" project or profile, so for more fine-grain control over exactly how your code gets organized and additional customization, take a look at the full documentation (particularly the sections about profiles and projects).

.. automodule omnifig.top


Running Scripts
---------------

[running scripts info]


Top-Level Targets
-----------------

[top level info]

