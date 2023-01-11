.. _highlight-config-composition:

Composing Config Files
================================================================================


Perhaps the most important feature of the configuration system is that config files can easily be composed to encourage config files to be more modular. Specifically, when loading a config file, it will inherit all values of any config files listed under the key ``_base``. This inheritance behaves analogously to python's class inheritance in that each config can have arbitrarily many parents and the full inheritance tree is linearized using the "C3" linearization algorithm (so no cycles are permitted). The configs are updated in reverse order of precedence (so that the higher precedence config file can override arguments in the lower precedence files).

For example, consider the following config directory structure:

.. code-block:: none

    config/
        base.yaml
        cluster.yaml
        demo.yaml
        model/
            base.yaml
            simple.yaml
            large.yaml
        data/
            base.yaml
            mnist.yaml
            cifar.yaml

Where ``base.yaml`` contains the following:

.. code-block:: yaml

    checkpoint-epochs: 5
    gpu: no

``cluster.yaml`` contains the following:

.. code-block:: yaml

    _base: [base]
    gpu: yes
    num-workers: 8

``model/base.yaml`` contains the following:

.. code-block:: yaml

    _base: [base]
    optim: sgd
    lr: 0.001
    act: relu

``model/simple.yaml`` contains the following:

.. code-block:: yaml

    _base: [model/base]
    model-name: deep-nn
    hidden: [40, 40]

``model/large.yaml`` contains the following:

.. code-block:: yaml

    _base: [model/base]
    model-name: large-nn
    hidden: [300, 300, 300]
    batch-norm: yes
    optim: adam

``data/base.yaml`` contains the following:

.. code-block:: yaml

    _base: [base]
    batch-size: 128
    data-dir: /path/to/all/data

``data/mnist.yaml`` contains the following:

.. code-block:: yaml

    _base: [data/base]
    dataset: mnist
    num-classes: 10

``data/cifar.yaml`` contains the following:

.. code-block:: yaml

    _base: [data/base]
    dataset: cifar
    num-classes: 100

``demo.yaml`` contains the following:

.. code-block:: yaml

    _base: [data/mnist, model/simple]

Then, the following configs would be the result of composing the above config files:

.. code-block:: python

    >>> import omnifig as fig
    >>> print(fig.create_config('cluster', 'model/simple', 'data/mnist'))
    gpu: yes
    num-workers: 8
    checkpoint-epochs: 5
    optim: sgd
    lr: 0.001
    act: relu
    model-name: some-model
    hidden: [40, 40]
    batch-size: 128
    dataset: mnist
    data-dir: /path/to/all/data
    num-classes: 10

    >>> print(fig.create_config('model/large', 'data/cifar'))
    gpu: no
    checkpoint-epochs: 5
    optim: adam
    lr: 0.001
    act: relu
    model-name: large-nn
    hidden: [300, 300, 300]
    batch-norm: yes
    batch-size: 128
    data-dir: /path/to/all/data
    dataset: cifar
    num-classes: 100

    >>> print(fig.create_config('model/large', 'data/cifar', 'cluster'))
    gpu: yes
    num-workers: 8
    checkpoint-epochs: 5
    optim: adam
    lr: 0.001
    act: relu
    model-name: large-nn
    hidden: [300, 300, 300]
    batch-norm: yes
    batch-size: 128
    data-dir: /path/to/all/data
    dataset: cifar
    num-classes: 100

    >>> print(fig.create_config('demo'))
    gpu: no
    checkpoint-epochs: 5
    optim: sgd
    lr: 0.001
    act: relu
    model-name: some-model
    hidden: [40, 40]
    batch-size: 128
    dataset: mnist
    data-dir: /path/to/all/data
    num-classes: 10


See the feature slide :ref:`B4 <vignette-composition>`.
