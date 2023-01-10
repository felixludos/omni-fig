Config Settings
================================================================================

.. TODO: vignette A5 - config settings

There are a few settings you can choose to affect the behavior of the config object. You can view and change the settings with the property :attr:`cfg.settings`:

* ``silent`` - If ``True``, suppresses all print messages when values from the config are accessed and updated (``False`` by default).
* ``readonly`` - If ``True``, prevents any changes to the config values (``False`` by default).
* ``creator`` - If specified, this must be the name of a registered creator, which will be used to create the config values (defaults to :class:`DefaultCreator <omnifig.config.nodes.ConfigNode.DefaultCreator>`), for more information see the guide about :ref:`creators <Creators>`.
* ``force_create`` - If ``True``, will always :ref:`create <Creating/Processing Values>` new instances of components when pulling config values (``False`` by default).
* ``allow_create`` - If ``False``, only instances of components that have already been instantiated are returned when pulling config values (``True`` by default).
* ``ask_parents`` - If ``True``, missing keys will check in the parent config node (recursively) before raising a :exc:`SearchFailed <omnifig.abstract.AbstractConfig.SearchFailed>` error (``True`` by default).
* ``allow_cousins`` - (advanced feature) If ``True``, missing keys will check in the parent's parent config node (recursively) with the current node's key prepended before raising a :exc:`SearchFailed <omnifig.abstract.AbstractConfig.SearchFailed>` error (``False`` by default).





