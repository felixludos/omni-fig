.. _highlight-config-access:

Accessing Config Values
================================================================================

Once the config object is :ref:`created <Composing Config Files>`, the primary way to access values in the config is via the :meth:`pull() <omnifig.abstract.AbstractConfig.pull>` (while you can update individual values using :meth:`push() <omnifig.abstract.AbstractConfig.push>`). Optionally, you can provide a default value to be returned if the query is not found. If no default value is provided, a :exc:`SearchFailed <omnifig.abstract.AbstractConfig.SearchFailed>` error is raised (which is subclass of :exc:`KeyError`). Additionally, the :meth:`pulls() <omnifig.abstract.AbstractConfig.pulls>` method allows you to provide any number of fallback queries.

When reading (aka *pulling*) arguments from the config, if an argument is not found in the current branch and the query is not hidden (i.e. it does not begin with :code:`_`), it will automatically defer to the higher branches (aka *parent* branch) as well, which allows users to define more or less "global" arguments depending on how deep the node containing the argument actually is. Although this behavior can be changed using the ``ask_parents`` key in the :ref:`config settings <Config Settings>`.

For example, given the config object that is loaded from the this yaml file (registered as ``myconfig``):

.. code-block:: yaml

    favorites:
        games: [Innovation, Triumph and Tragedy, Inis, Nations]
        language: Python
        activity: <>games.0

    wallpaper:
        color: red

    jacket:
        size: 30

    nights: 2
    trip:
        - location: London
          nights: 3
        - location: Berlin
        - location: Moscow
          nights: 4

    app:
        price: 1.99
        color: <>wallpaper.color


When this yaml file is loaded (e.g. :code:`config = fig.create_config('myconfig')`), we could use it like so:

.. code-block:: python

    assert config.pull('favorites.language') == 'Python'
    assert config.pull('favorites.0') == 'Innvoation'
    assert config.pull('app.color') == 'red'
    assert config.pull('favorites.activity') == 'Innovation'
    assert config.pull('trip.0.location') == 'London'
    assert config.pull('trip.1.nights', 4) == 2
    assert config.pull('app.publisher', 'unknown') == 'unknown' # default

    assert config.pulls('jacket.color', 'wallpaper.color') == 'red'
    assert config.pulls('jacket.price', 'price', 'total_cost', default='too much') == 'too much'

While this example should give you a sense for what kind of features the config system offers, a more comprehensive list of how queries in the config are resolved and the values are processed.

See the feature slide :ref:`B5 <vignette-config-access>`.

Queries
-------

In addition to the behavior described above, the keys (or indices) in a config branch have the following features (where :code:`{}` refers to any value):

* :code:`'_{}'` - hidden query - is not visible to child branches when they defer to parents
* :func:`push`/:func:`pull` :code:`'{1}.{2}'` - *deep* query - equivalent to :code:`['{1}']['{2}']`
* :func:`push` :code:`'{1}.{2}'` where :code:`'{1}'` is missing - *deep* push - automatically creates a new branch :code:`'{1}'` in config and then pushes :code:`'{2}'` to that new branch

Values
------

The values of arguments also have a few special features worth noting:

* :code:`'<>{}'` - local alias - defer to value of :code:`{}` starting search for the key here
* :code:`'<o>{}'` - (advanced feature) origin alias - defer to value of :code:`{}` starting search at origin (this only makes a difference when chaining aliases, origin refers to the branch where :func:`pull` was called)
* :code:`'_x_'` - remove key if encountered (during update) - remove corresponding key it it appears in the config being updated
* :code:`__x__` - cut deferring chain of key - behaves as though this key didn't exist (and doesn't defer to parent)


Currently there are no escape sequences, so any values starting with :code:`<>` or :code:`<o>` will be treated as aliases and values that are :code:`_x_` or :code:`__x__` will not be processed as regular strings. However, if necessary, you can easily implement a component to escape these values using the automatic :ref:`object instantiation <Automatic Instantiation>`, like so:

.. code-block:: python

    @fig.autocomponent('escaped-str')
    def escape_str(value):
        return value

    cfg = fig.create_config(special={'_type': 'escaped-str', 'value':'<>some-value'})

    assert cfg.pull('special') == '<>some-value'




