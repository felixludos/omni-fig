Config System
=============

.. role::  raw-html(raw)
    :format: html

The original motivation for this package was to design a system that would read arguments from files, the terminal, or directly as python objects (eg. in a jupyter notebook) and would structure so that the arguments are always used in the code where they need to be. This is accomplished chiefly by a hierarchical structure in the config much like a tree where each branch corresponds to the a dict or list of arguments (or other branches).

When reading (aka *pulling*) arguments from the config, if an argument is not found in the current branch, it will automatically defer to the higher branches (aka *parent* branch) as well, which allows users to define more or less "global" arguments depending on which node actually contains the argument.

It should be noted that despite the hierarchical structure of the config object, it can ultimately always be exported into a simple yaml file - so it should not contain any values that are primitives (:code:`str`, :code:`bool`, :code:`int`, :code:`float`, :code:`None`) aside from the branches that behave either as a :code:`dict` or :code:`list`. Using the registries, the config can implicitly contain specifications for arbitrarily complex components such as objects and functions (see :ref:`registry:Registry` for more details and an example).

Probably, the next most important feature of the config object is that a config object can be updated with other configs, and thereby "inherit" arguments from other config files. This inheritance behaves analogously to python's class inheritance in that each config can have arbitrarily many parents and the full inheritance tree is linearized using the "C3" linearization algorithm (so no cycles are permitted). The configs are updated in reverse order of precedence (so that the higher precedence config file can override arguments in the lower precedence files).

Generally, arguments are read from the config object using :func:`pull` and individually updated or set using :func:`push`.Both :func:`pull` and :func:`push` supports *deep* gets and sets, which means you can get and set arguments arbitrarily deep in the config hierarchy using "." to "dereference" (aka "go into") a branch. When pulling, additional default values can be provided to process if the key is not found. This is especially useful in conjunction with another feature called aliasing, where arguments can reference each other (see the example below).

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


When this yaml file is loaded (eg. :code:`config = omnifig.get_config('myconfig')`), we could use it like so:

.. code-block:: python

    assert config.pull('favorites.language') == 'Python'
    assert config.pull('favorites.0') == 'Innvoation'
    assert config.pull('app.color') == 'red'
    assert config.pull('app.publisher', 'unknown') == 'unknown'
    assert config.pull('jacket.color', '<>wallpaper.color') == 'red'
    assert config.pull('favorites.activity') == 'Innovation'
    assert config.pull('jacket.price', '<>price', '<>total_cost', 'too much') == 'too much'
    assert config.pull('trip.0.location') == 'London'
    assert config.pull('trip.1.nights', 4) == 2

While this example should give you a sense for what kind of features the config system offers, a comprehensive list of features follows.

Keys
----

In addition to the behavior described above, the keys (or indices) in a config branch have the following features (where :code:`{}` refers to any value):

- :func:`push`/:func:`pull` :code:`'_{}'` - protected argument :raw-html:`&rarr;` not visible to child branches when they defer to parents
- :func:`push`/:func:`pull` :code:`'__{}'` - volatile argument :raw-html:`&rarr;` is not exported when saving config to yaml (can be used for non-yamlifiable data)
- :func:`push`/:func:`pull` :code:`({1},{2}, ...)` - *deep* key :raw-html:`&rarr;` :code:`[{1}][{2}]`
- :func:`push`/:func:`pull` :code:`'{1}.{2}'` - *deep* key as str :raw-html:`&rarr;` :code:`['{1}']['{2}']`
- :func:`push`/:func:`pull` :code:`'{1}.{2}'` - *deep* key through list :raw-html:`&rarr;` :code:`['{1}'][{2}]` (where :code:`{2}` is an int and :code:`self['{1}']` is a list)
- :func:`push` :code:`'{1}.{2}'` where :code:`'{1}'` is missing - *deep* push :raw-html:`&rarr;` automatically creates a new branch :code:`'{1}'` in config and then pushes :code:`'{2}'` to that new branch

Values
------

The values of arguments also have a few special features worth noting:

- :code:`'<>{}'` - local alias :raw-html:`&rarr;` use value of key :code:`{}` starting search for the key here
- :code:`'<o>{}'` - origin alias :raw-html:`&rarr;` use value of key :code:`{}` starting search for the key at origin (this only makes a difference when chaining aliases, origin refers to the branch where :func:`pull` was called)
- :code:`_x_` - remove key if encountered (during update) :raw-html:`&rarr;` remove corresponding key it it appears in the config being updated
- :code:`__x__` - cut deferring chain of key :raw-html:`&rarr;` behave as though this key didn't exist (and don't defer to parent)


Code
----

.. automodule:: omnifig.config
    :members:
    :undoc-members:
    :show-inheritance:
    :private-members:
    :special-members:
    :exclude-members: __module__,_getref,__new__,__weakref__,__dict__,load_config_from_path,process_single_config,merge_configs,Config_Printing,_Silent_Config,_set_silent,_get_silent,_get_printer,get_prefix,_send_prefix,_receive_prefix,_swap_prefix,_store_prefix,_pop_prefix,_append_prefix,__repr__,__str__,__setitem__,__getitem__,__contains__,get_nodefault,set_nodefault,contains_nodefault,_single_get,_process_val,_push,_pull,__init__,__len__,_next_idx,__next__,_record_action
    :member-order: bysource

