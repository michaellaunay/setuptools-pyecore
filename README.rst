setuptools-pyecore
==================

|Build Status| |Coverage Status| |PyPI Version| |GitHub Version| |License|

.. |Build Status| image:: https://travis-ci.org/pyecore/setuptools-pyecore.svg
   :target: https://travis-ci.org/pyecore/setuptools-pyecore
   :alt: Build Status

.. |Coverage Status| image:: https://coveralls.io/repos/github/pyecore/setuptools-pyecore/badge.svg?branch=master
   :target: https://coveralls.io/github/pyecore/setuptools-pyecore?branch=master
   :alt: Coverage Status

.. |PyPI Version| image:: https://badge.fury.io/py/setuptools-pyecore.svg
   :target: https://pypi.org/project/setuptools-pyecore
   :alt: PyPI Version

.. |GitHub Version| image:: https://badge.fury.io/gh/pyecore%2Fsetuptools-pyecore.svg
   :target: https://github.com/pyecore/setuptools-pyecore/releases
   :alt: GitHub Version

.. |License| image:: https://img.shields.io/github/license/pyecore/setuptools-pyecore.svg
   :target: https://raw.githubusercontent.com/pyecore/setuptools-pyecore/master/LICENSE
   :alt: License

.. contents:: Table of Contents
   :depth: 2

Overview
--------

A ``setuptools`` command for generating Python code from Ecore models.

This is an extension for `setuptools <https://pypi.org/project/setuptools/>`__ integrating the `pyecoregen <https://github.com/pyecore/pyecoregen>`__ code generator into the Python packaging process. It encapsulates ``pyecoregen`` and provides the user a ``setuptools`` command called ``pyecore`` to control the generation process.

In a basic setup the user doesn't have to configure the generation process at all because ``setuptools-pyecore`` discovers Ecore models located in the current working directory and triggers the code generation for each detected Ecore model. Also a meaningful output folder is chosen automatically.

Of course the user has to possibility to customize the generation process. The command line options of ``pyecoregen`` are also available through the ``pyecore`` setuptools command. The user has the choice to pass the options on the command line or configure the code generation in a dedicated section in the ``setup.cfg`` file.

Installation
------------

``setuptools-pyecore`` can be installed in various ways. To run it the following prerequisites have to be fulfilled:

- Python 3.12+
- setuptools

After installation, the used Python environment has a new setuptools command called ``pyecore``.

From Source Code
****************

::

    > git clone https://github.com/pyecore/setuptools-pyecore.git
    > cd setuptools-pyecore
    > pip install .

From PyPI
*********

::

    > pip install setuptools-pyecore

From GitHub Releases
********************

::

    > pip install <setuptools-pyecore_wheel>

Usage
-----

Integration
***********

Generate model sources explicitly **before** creating the sdist or wheel.
The public ``python setup.py pyecore`` command remains supported; there is no
removal or runtime deprecation warning in this release. ``setup_requires`` and
pytest-runner integration are obsolete and should be removed from clients.

Recommended migration without the plugin::

    python -m pyecoregen.cli -e models/library.ecore -o src/myproject
    python -m build

Or, with this plugin already installed in the developer environment::

    python setup.py pyecore
    python -m build

The generation step must precede package discovery. Include the generated Python
sources in the sdist (for example ``recursive-include src *.py`` in MANIFEST.in).
A client can then declare only ``setuptools>=77`` and ``wheel`` in its
``[build-system].requires``, and ``pyecore`` as a runtime dependency. Neither the
plugin nor the generator is required in its isolated build environment. Keep a
minimal setup.py calling setup() only if using the legacy command.

Do not rely on ``setup_requires`` to fetch the plugin implicitly, and do not run
code generation from an import of setup.py or a metadata hook. If a legacy custom
backend intentionally runs the command inside an isolated build, it must explicitly
declare the plugin in build-system.requires; this is separate from the recommended
pre-generation workflow.

For the migration workspace, prepare wheels from the local PyEcore, pymultigen,
pyecoregen and setuptools-pyecore forks. Install those explicit paths and use
``PIP_NO_INDEX=1`` with a prepared wheelhouse and constraints referencing the local
wheels during isolated builds. Installing by package name from an unrestricted
index does not prove local-fork provenance. Missing local dependencies must fail,
not silently download an older PyEcore.

The executable fixture in tests/fixtures/client exercises both generation commands,
builds a wheel from its sdist in an isolated environment without generation tools,
and installs the result with the explicit local PyEcore into a fresh runtime.

Testing::

    python -m pytest tests

Install the ``test`` extra first. Integration tests use build, venv and pip, and
inherit pip's offline wheelhouse/constraints configuration.

Configuration
*************

``setuptools-pyecore`` provides two possibilities to configure the pyecore generator.

All options can be passed on the command line after the ``pyecore`` command:

::

    > python setup.py pyecore --auto-register-package

It's also possible to pass several options to ``pyecoregen`` or execute multiple commands at once:

::

    > python setup.py pyecore --auto-register-package --output "default=gen"
    > python -m build

See ``python setup.py pyecore --help`` for available command line options:

::

    > python setup.py pyecore --help
    ...
    Options for 'PyEcoreCommand' command:
      --ecore-models (-e)      specify Ecore models to generate code for
      --output (-o)            specify directories where output is generated
      --user-modules           dotted names of modules with user-provided mixins
                               to import from generated classes
      --auto-register-package  Generate package auto-registration for the PyEcore
                               'global_registry'
    ...

The ``pyecoregen`` documentation explains all `command line options <https://github.com/pyecore/pyecoregen/blob/master/README.rst>`__ in detail.

Apart from passing options on the command line it's also possible to add a dedicated ``[pyecore]`` section to ``setup.cfg``. The following example section contains all available options:

.. code:: ini

    [pyecore]
    # Specify Ecore models to generate code for; default: None
    #ecore-models = <ecore-model> [<ecore-model> ...]
    # Specify directories where output is generated; default: <ecore-model-dir>
    output = default=gen
    # Dotted names of modules with user-provided mixins to import from generated classes; default: None
    #user-modules = [<ecore-model>=<user module>]
    #               [<ecore-model>=<user module> ...]
    # Generate package auto-registration for the PyEcore 'global_registry' (yes|no); default: no
    auto-register-package = yes

Underscore keys (``ecore_models``, ``user_modules``,
``auto_register_package``) are preferred in new setup.cfg files. Historical
dashed keys remain supported, including yes/no boolean values.

A reference configuration is provided in the ``resources`` directory.

``pyecoregen`` inherits the log level globally configured for ``setuptools``. To set the verbosity to a certain log level pass the global options ``verbose`` or ``quiet`` straight before the ``pyecore`` command on the command line:

::

    > python setup.py --verbose pyecore

Alternatively, you can add these options to the ``[global]`` section of your ``setup.cfg``:

.. code:: ini

    [global]
    # Run verbosely (yes|no); default: yes
    #verbose = yes
    # Run quietly and turns verbosity off (yes|no); default: no
    quiet = yes

Sample
******

Besides the ``setuptools-pyecore`` source code a sample project called ``library`` is provided in the ``samples`` directory. This sample consists of the Ecore model ``library`` and a setup script. During the execution of ``setuptools-pyecore`` a Python package will be generated into the ``library`` package directory representing the classes from the ``library`` Ecore model.

To generate code out of the Ecore model and build a ``library`` wheel package execute the following command:

::

    > python setup.py pyecore
    > python -m build
