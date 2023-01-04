Registries
==========

At the heart of good code organization is a flexible yet powerful way to add new features or functionality to a past, current, and even future projects. ``omni-fig`` accomplishes this by relying on registries to manage all of the most important pieces of code that may be explicitly addressed/referred to in the config.

The first registry registers all scripts which are essentially the top level interface for how a user is to interact with the code (by calling scripts). These scripts can be called from the terminal (see :ref:`common:Running Scripts` for more details and examples) or executed in environments like jupyter notebooks or an IDE debugger (eg. Pycharm).

Next, is the component registry. A component is any atomic piece of code that might be specified in the config. As the config object is a yaml file, there are no python classes or objects there in (aside from dicts, lists and primitives). Instead, if the user wants to use a user defined class or function, it can be registered as a component, and then the component can be referred to in the config with the key ``_type``.

Finally, modifiers can be registered and used to wrap existing components to further customize the behavior of components dynamically from the config. There are two special kinds of modifiers: :func:`AutoModifier` and :func:`Modification`. An :func:`AutoModifier` essentially acts as a child class of whatever component it is wrapping. Meanwhile a :func:`Modification` is used to wrap or modify a component after it has been created. The example below (and elsewhere) will hopefully help elucidate how modifiers can be used with components.

For an extended example in how all three registries might be used for a simple project where we sample from a guassian distribution and then record the particularly low probability events, which might be implemented and registered like so:

.. code-block:: python

    import sys
    import random
    import omnifig as fig

    @fig.script('sample-low-prob')
    def sample_low_prob(config): # config object

        mylogger = config.pull('logger') # create a logger object according to specifications in the config

        num_events = config.pull('num_events', 10) # default value is 10 if "num_events" is not specified in the config

        interest_criterion = config.pull('criterion', 5.)
        important_criterion = config.pull('important_criterion', 5.2)

        mu, sigma = config.pull('mu',0.), config.pull('sigma', 1.)
        sigma = max(sigma, 1e-8) # ensure sigma is positive

        print('Sampling...')

        events = []
        count = 0
        while len(events) < num_events:
            x = random.gauss(mu, sigma)
            if abs(x) > interest_criterion:
                mylogger.log_line(f'Found important {x:.2f}\n', important=abs(x)>important_criterion)
                events.append(x)
            count += 1

        mylogger.log_line(f'Finding {num_events} low prob samples required {count} samples.\n',
                          include_credits=True, important=True)

        mylogger.close()

        return events

In this example project, we may require a logger (called ``logger`` above) to print information to ``stdout`` or a file, and we can register components to implement the different choices and corresponding arguments.

.. code-block:: python

    @fig.autocomponent('stdout') # automatically pulls all arguments in signature before creating
    def _get_stdout(): # in this case, we don't need any arguments
        return sys.stdout

    @fig.autocomponent('file')
    def _get_file(path):
        return open(path, 'a+')

    @fig.component('mylogger')
    class Logger(fig.Configurable): # Subclassing Configurable allows automatically fills in the arguments
        def __init__(self, always_log=False, print_stream=None, credits=None): # arguments pulled from the config object
            self.always_log = always_log # value defaults to False if not found in the config
            self.print_stream = print_stream # values can also be components themselves
            if credits is None:
                credits = []
            self.credits = credits # pulled values can also be dicts or lists (with defaults)
            if not isinstance(self.credits, list):
                self.credits = list(self.credits)

        def log_line(self, line, stream=None, important=False, include_credits=False):
            if stream is None:
                stream = self.print_stream
            if stream is not None and (important or self.always_log):
                stream.write(line)
                if include_credits and len(self.credits):
                    stream.write('Credits: {}\n'.format(', '.join(self.credits)))

        def close(self):
            if self.print_stream is not None:
                self.print_stream.close()

This example shows how :func:`Component` and :func:`AutoComponent` may be used with both classes and functions. The config (eg. registered as ``myconfig1``) may contain something like:

.. code-block:: yaml

    num_events: 5

    logger:
      _type: mylogger
      credits: [Gauss, Hamilton, Fourier]
      print_stream._type: stdout    # "." is treated like a sub-dict

Or (say, ``myconfig2``):

.. code-block:: yaml

    always_log: True  # as this argument is in a parent dict of "logger" it will still be found within "logger".
    logger:
      _type: mylogger
      print_stream:
        _type: file
        path: 'log_file.txt'    # "." is treated like a sub-dict

Additionally, components can be modified in the config using :func:`Modifier`, :func:`AutoModifier`, and :func:`Modification`. Modifiers essentially act as additional decorators that can dynamically be specified in the config to change the bahavior of components before (eg. :func:`Modifier` or :func:`AutoModifier`) or after (:func:`Modification`) creating the component.

To add on to our previous example:

.. code-block:: python

    @fig.modifier('multi')
    class MultiStream(fig.Configurable):
        # use this decorator to search for arguments in multiple places in the config
        @fig.config_aliases(print_stream=['print_streams'])
        def __init__(self, print_stream=(), **kwargs):
            if not isinstance(print_stream, (list, tuple)):
                print_stream = [print_stream]

            super().__init__(print_stream=print_stream, **kwargs) # initialize original component class

            self.print_streams = streams

        def log_line(self, line, stream=None, important=False, include_credits=False):

            if stream is not None:
                return super().log_line(line, stream=stream, important=important, include_credits=include_credits)
            for stream in self.print_streams:
                return super().log_line(line, stream=stream, important=important, include_credits=include_credits)

        def close(self):
            for stream in self.print_streams:
                stream.close()

    @fig.modifier('remove-credits')
    class RemoveNames(fig.Configurable):
        def __init__(self, remove_names=None, credits=None, **kwargs):
            if credits is not None and remove_names is not None:
                for name in remove_names:
                    if name in credits:
                        credits.remove(name)
                        print(f'Removed {name} from credits')
            super().__init__(credits=credits, **kwargs)

And some associated configs might include (``config3``):

.. code-block:: yaml

    parents: [config1] # all these registered configs will be loaded and merged with this one

    path: 'backup-log.txt'

    logger:
      _mod: multi

      print_streams:
      - _type: file
      - _type: stdout

Or, finally (``config4``):

.. code-block:: yaml

    parents: [config2, config3]

    remove_names: [Fourier]

    logger._mod: [multi, remove-credits]

Now, if your head isn't spinning from the complicated merging and defaulting of configs, then perhaps you can figure out what path we will actually end up using as our log file when using ``config4``?

The answer is ``backup-log.txt`` because the :func:`AutoModifier` ``multi`` starts from the ``logger.print_streams`` branch, which does not get merged with the ``logger.print_stream`` branch (which contains :code:`path : 'log_file.txt'`), so when defaulting towards the root, ``log_file.txt`` is not encountered. For more information, the code for this example can be found in ``examples/gauss_fun``.

Another part of this example that warrants careful consideration is how the :func:`AutoModifier` ``multi`` is used. The trick is that an :func:`AutoModifier` actually dynamically creates a new child class of the registered :func:`AutoModifier` type and the original type of the component (for that reason :func:`AutoModifier` must be a class, not a function, and they only work on components that are classes). In this case, the dynamically created type will be called ``MultiStream_Logger`` with the method resolution order (MRO) :code:`[MultiStream, Logger, object]`.

Note that the :func:`AutoModifier` can be paired with, in principle, any component (although some will raise errors), which effectively means an :func:`AutoModifier` allows changing the behavior of any component, even ones that haven't even been written yet. While :func:`AutoModifier` is one of the most powerful features of the registry system in ``omni-fig``, they are consequently also rather advanced, so particular care must be taken when using them.


.. automodule omnifig.decorators


Artifacts
---------

[artifacts info]


Configurable
------------

[configurable info]


