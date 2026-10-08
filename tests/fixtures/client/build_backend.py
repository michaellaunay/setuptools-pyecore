"""Fixture guard: isolated builds must not depend on generation tools."""
from importlib.util import find_spec

assert find_spec('setuptools_pyecore') is None, 'plugin leaked into isolated build'
assert find_spec('pyecoregen') is None, 'generator leaked into isolated build'
assert find_spec('pyecore') is None, 'runtime leaked into isolated build'
from setuptools.build_meta import *
