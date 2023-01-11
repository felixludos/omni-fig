
Here's a slightly more advanced example of a project using `omni-fig`.

You try running in debug mode using:

```shell
fig -d
```

You can also mix and match differen models and datasets, for example:

```shell
fig train models/basic data/mnist
fig train hard models/super data/cifar
fig train models/basic data/mnist
fig train models/basic data/rotated data/mnist


fig build-model models/basic
fig build-model models/super
```

For debugging, there's also a script called `print-config`, to view what the composed config looks like:

```shell
fig print-config models/basic data/mnist
fig print-config models/basic data/cifar
fig print-config models/super data/cifar
fig print-config hard models/super data/cifar
fig print-config models/basic data/rotated data/mnist
...
```
