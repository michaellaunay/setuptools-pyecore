"""Implementation of the setuptools command 'pyecore'."""
import collections
import contextlib
import logging
import pathlib
import shlex

import pyecore.resources
import pyecoregen.ecore
import setuptools
from setuptools._distutils import log as logger
from setuptools.errors import OptionError


class PyEcoreCommand(setuptools.Command):
    """A setuptools command for generating Python code from Ecore models.

    An extra command for setuptools to generate static Python classes from Ecore models. The pyecore
    command wraps pyecoregen - the real Python code generator for Ecore models. It searches for
    Ecore models starting from the base directory and generates a Python package for each found
    Ecore model.

    :cvar _ECORE_FILE_EXT: File extension of Ecore XMI file
    :cvar description: Description of ecore command
    :cvar user_options: Options which can be passed by the user
    :cvar boolean_options: Subset of user options which are binary
    """

    _ECORE_FILE_EXT = 'ecore'

    description = 'generate Python code from Ecore models'

    user_options = [
        ('ecore-models=', 'e', 'specify Ecore models to generate code for'),
        ('output=', 'o', 'specify directories where output is generated'),
        ('user-modules=', None, 'dotted names of modules with user-provided mixins to import from '
                                'generated classes'),
        ('auto-register-package', None, 'Generate package auto-registration for the PyEcore '
                                        '\'global_registry\''),
    ]

    boolean_options = ['auto-register-package']

    def initialize_options(self):
        """Set default values for all the options that this command supports. Note that these
        defaults may be overridden by other commands, by the setup script, by config files, or by
        the command-line.
        """
        self.ecore_models = None
        self.output = ''
        self.user_modules = ''
        self.auto_register_package = 0

    def finalize_options(self):
        """Set final values for all the options that this command supports. This is always called
        as late as possible, ie. after any option assignments from the command-line or from other
        commands have been done.
        """
        # Parse into local state so an invalid option does not leave a partly
        # finalized command that cannot be corrected and retried.
        models = shlex.split(self.ecore_models, comments=True) if self.ecore_models else None
        output_paths = collections.defaultdict(lambda: None)
        for token in shlex.split(self.output, comments=True):
            model, output = self._split_mapping(token)
            if model and output:
                output_path = pathlib.Path(output).relative_to('.')
                if model == 'default':
                    output_paths.default_factory = lambda path=output_path: path
                else:
                    output_paths[model] = output_path
            else:
                logger.warn('Ignoring invalid output specifier {!r}.', token)

        user_modules = {}
        for token in shlex.split(self.user_modules, comments=True):
            model, user_module = self._split_mapping(token)
            if model and user_module:
                user_modules[model] = user_module
            else:
                logger.warn('Ignoring invalid user module specifier {!r}.', token)

        self.ecore_models = models
        self.output = output_paths
        self.user_modules = user_modules

    @staticmethod
    def _split_mapping(token):
        if '=' not in token:
            raise OptionError(f'Expected model=value, got {token!r}')
        return token.split('=', 1)

    def _configure_logging(self):
        """Configure logging using global verbosity level of distutils."""
        loglevel_map = collections.defaultdict(lambda: logging.WARNING)
        loglevel_map.update({
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG
        })
        logging.basicConfig(
            format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
            level=loglevel_map[self.distribution.verbose]
        )

    def _find_ecore_xmi_files(self, base_path=pathlib.Path('.')):
        """Search for all Ecore XMI files starting from base directory and returns a list of them.

        :param base_path: base path to search for Ecore XMI files
        :return: a list of all found Ecore XMI files
        """
        pattern = '*.{}'.format(self._ECORE_FILE_EXT)
        logger.debug('searching for Ecore XMI files in \'{!s}\''.format(str(base_path)))
        return sorted(base_path.rglob(pattern))

    @staticmethod
    @contextlib.contextmanager
    def _load_ecore_model(ecore_model_path):
        """Load a single Ecore model from a Ecore XMI file and return the root package.

        :param ecore_model_path: path to Ecore XMI file
        :return: root package of the Ecore model
        """
        rset = pyecore.resources.ResourceSet()
        logger.debug('loading \'{!s}\''.format(str(ecore_model_path)))
        resource = rset.get_resource(ecore_model_path.as_posix())
        try:
            yield resource.contents[0]
        finally:
            rset.remove_resource(resource)

    def run(self):
        """Perform all tasks necessary to generate Python packages representing the classes from
        Ecore models. This process is controlled by the user options passed on the command line or
        set internally to default values.
        """
        self._configure_logging()

        # find Ecore XMI files
        ecore_xmi_files = self._find_ecore_xmi_files()

        # load each Ecore model
        for ecore_xmi_file in ecore_xmi_files:
            with self._load_ecore_model(ecore_xmi_file) as resource:
                if self.ecore_models is None or resource.name in self.ecore_models:
                    # configure EcoreGenerator
                    kwargs = {}
                    if self.auto_register_package:
                        kwargs['auto_register_package'] = True
                    if resource.name in self.user_modules:
                        kwargs['user_module'] = self.user_modules[resource.name]

                    if self.output[resource.name]:
                        output_dir = self.output[resource.name]
                    else:
                        output_dir = ecore_xmi_file.parent

                    #  generate Python classes
                    logger.info(
                        'running pyecoregen to generate code for {!r} metamodel'.format(resource.name)
                    )
                    pyecoregen.ecore.EcoreGenerator(**kwargs).generate(
                        resource,
                        output_dir.as_posix()
                    )
                else:
                    logger.debug('skipping {!r} metamodel'.format(resource.name))


def _config_alias(attribute, *, boolean=False):
    """Support historic dashed setup.cfg keys with modern setuptools."""
    def get(command):
        return getattr(command, attribute)

    def set_(command, value):
        if boolean and isinstance(value, str):
            from setuptools._distutils.util import strtobool
            value = strtobool(value)
        setattr(command, attribute, value)

    return property(get, set_)


# Modern setuptools preserves dashes in custom command sections. CLI options
# still normalize to underscores; these descriptors preserve old config files.
setattr(PyEcoreCommand, 'ecore-models', _config_alias('ecore_models'))
setattr(PyEcoreCommand, 'user-modules', _config_alias('user_modules'))
setattr(PyEcoreCommand, 'auto-register-package',
        _config_alias('auto_register_package', boolean=True))
