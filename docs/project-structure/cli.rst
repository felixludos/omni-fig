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

