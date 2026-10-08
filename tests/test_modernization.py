"""Regression tests for command options and resource lifetime."""
from pathlib import Path
from unittest import mock

import pytest
from setuptools import Distribution
from setuptools_pyecore.command import PyEcoreCommand


def test_default_output_is_not_last_output():
    cmd = PyEcoreCommand(Distribution())
    cmd.output = 'default=generated alpha=elsewhere'
    cmd.finalize_options()
    assert cmd.output['unknown'] == Path('generated')
    assert cmd.output['alpha'] == Path('elsewhere')


def test_resource_removed_when_generator_fails():
    cmd = PyEcoreCommand(Distribution())
    with mock.patch('pyecore.resources.ResourceSet') as factory:
        rset = factory.return_value
        resource = rset.get_resource.return_value
        with pytest.raises(RuntimeError, match='generation failed'):
            with cmd._load_ecore_model(Path('model.ecore')):
                raise RuntimeError('generation failed')
        rset.remove_resource.assert_called_once_with(resource)


@pytest.mark.parametrize('option', ['output', 'user_modules'])
def test_invalid_mapping_has_actionable_error(option):
    from setuptools.errors import OptionError
    cmd = PyEcoreCommand(Distribution())
    setattr(cmd, option, 'missing_equals')
    with pytest.raises(OptionError, match='model=value'):
        cmd.finalize_options()


def test_quoted_output_path():
    cmd = PyEcoreCommand(Distribution())
    cmd.output = 'default="generated é ; $"'
    cmd.finalize_options()
    assert cmd.output['anything'] == Path('generated é ; $')


def test_invalid_options_preserve_command_state():
    from setuptools.errors import OptionError
    cmd = PyEcoreCommand(Distribution())
    cmd.ecore_models = 'a b'
    cmd.output = 'default=generated'
    cmd.user_modules = 'missing_equals'
    with pytest.raises(OptionError):
        cmd.finalize_options()
    assert cmd.ecore_models == 'a b'
    assert cmd.output == 'default=generated'
    assert cmd.user_modules == 'missing_equals'


@pytest.mark.parametrize('value, expected', [('yes', 1), ('no', 0)])
def test_historic_boolean_config_alias(value, expected):
    cmd = PyEcoreCommand(Distribution())
    setattr(cmd, 'auto-register-package', value)
    assert cmd.auto_register_package == expected


def test_historic_model_config_aliases():
    cmd = PyEcoreCommand(Distribution())
    setattr(cmd, 'ecore-models', 'a')
    setattr(cmd, 'user-modules', 'a=client.mixins')
    cmd.finalize_options()
    assert cmd.ecore_models == ['a']
    assert cmd.user_modules == {'a': 'client.mixins'}
