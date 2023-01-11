Profiles
====================

.. TODO: vignette A1

.. TODO: profile keys


Generally, every OS image or file system should use it's own *profile*. The profile is specified by defining an environment variable ``OMNIFIG_PROFILE`` which contains the absolute path to a yaml file.

While using a profile is completely optional, it is highly recommended as the profile is the primary way to specify the location of all of your projects to load them remotely. For example, a project can specify related projects as dependencies, which get loaded automatically when the project is loaded, but only if the paths to those dependency projects are listed in the profile info file. Since the profile is meant to act globally for the whole file system, all paths should be absolute.

The most important contents of the profile file (all of which are optional):

- ``name`` - the name of the profile
- ``projects`` - dictionary from project name to absolute path to the project directory
- ``active-projects`` - list of names of projects that should automatically be loaded (the paths to these projects must be in the ``projects`` table


