Jupyter Environments
================================================================================

.. TODO: vignette A3


You can also use ``omni-fig`` in an interactive programming environment such as Jupyter or IPython. This is useful for quickly prototyping and debugging scripts. First, to load a project, use the :func:`fig.initialize() <omnifig.top.initialize>` function. Once the project is initialized you can create a config with any of the registered configs using :func:`fig.create_config() <omnifig.top.create_config>`. Additionally, you can run any registered scripts with :func:`fig.run_script() <omnifig.top.run_script>`, or :func:`fig.run() <omnifig.top.run>` if the script is already specified in the config.

Remember that when running a :ref:`script <script>`, the first positional argument is the config, however you can manually include additional positional keyword arguments which are passed to the script as well. Alternatively, for additional convenience, you can use the :func:`fig.quick_run() <omnifig.top.quick_run>` function to create a config object and run a script in one line.
