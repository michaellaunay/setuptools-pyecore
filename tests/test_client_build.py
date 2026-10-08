"""Isolated sdist/wheel builds and installed clients without generation tools."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.parse import unquote, urlparse
import zipfile

import pytest


def run(argv, cwd, logs):
    process = subprocess.run(list(map(str, argv)), cwd=cwd, capture_output=True, text=True)
    logs.append({'argv': list(map(str, argv)), 'returncode': process.returncode,
                 'stdout': process.stdout, 'stderr': process.stderr})
    (cwd.parent / 'client-commands.json').write_text(json.dumps(logs, indent=2))
    assert process.returncode == 0, process.stdout + process.stderr
    return process


@pytest.mark.parametrize('generator', ['command', 'explicit'])
def test_client_build_without_plugin(tmp_path, generator, request):
    client = tmp_path / 'client é ; $'
    shutil.copytree(Path(__file__).parent / 'fixtures/client', client)
    logs = []
    if generator == 'command':
        run([sys.executable, '-I', 'setup.py', 'pyecore'], client, logs)
    else:
        run([sys.executable, '-I', '-m', 'pyecoregen.cli',
             '-e', 'models/A.ecore', '-o', 'src/client'], client, logs)
    generated = client / 'src/client/a/a.py'
    assert generated.is_file()
    original = generated.read_bytes()
    # build's default path builds the sdist, then the wheel FROM that sdist.
    # Fixture backend asserts that all generation/runtime tools are absent.
    run([sys.executable, '-I', '-m', 'build'], client, logs)
    assert generated.read_bytes() == original
    wheel, = (client / 'dist').glob('*.whl')
    sdist, = (client / 'dist').glob('*.tar.gz')
    with tarfile.open(sdist) as archive:
        member, = [m for m in archive.getmembers() if m.name.endswith('/src/client/a/a.py')]
        assert archive.extractfile(member).read() == original
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read('client/a/a.py') == original
        assert 'client/a/__init__.py' in archive.namelist()

    # Fresh client runtime: install the qualified local PyEcore origin explicitly.
    # No plugin or generator is needed to use the produced distribution.
    runtime = tmp_path / 'runtime'
    run([sys.executable, '-I', '-m', 'venv', '--without-pip', runtime], client, logs)
    python = runtime / 'bin/python'
    origin = json.loads(metadata.distribution('pyecore').read_text('direct_url.json'))
    assert origin['url'].startswith('file:'), origin
    core = Path(unquote(urlparse(origin['url']).path))
    assert core.exists(), core
    run([sys.executable, '-I', '-m', 'pip', '--python', python,
         'install', wheel.resolve().as_uri(), core.resolve().as_uri()], client, logs)
    code = '''
from importlib.util import find_spec
assert find_spec('setuptools_pyecore') is None
assert find_spec('pyecoregen') is None
from client.a import Root, A
obj = Root(visible=True, a=[A(tob='é')])
assert obj.visible is True
assert obj.a[0].tob == 'é'
assert obj.a[0].eContainer() is obj
import client.a, pyecore
print(client.a.__file__)
print(pyecore.__file__)
'''
    # The cwd contains sources, but -I excludes them from imports.
    code += '\nimport importlib.metadata as md, json\n'
    code += 'assert json.loads(md.distribution("pyecore").read_text("direct_url.json"))["url"] == ' + repr(core.resolve().as_uri()) + '\n'
    run([python, '-I', '-c', code], client, logs)
    request.node.user_properties.append(('client_commands', json.dumps(logs)))


def test_missing_local_core_fails_offline(tmp_path, request):
    empty = tmp_path / 'empty-wheelhouse'
    empty.mkdir()
    env = dict(__import__('os').environ)
    env.pop('PIP_FIND_LINKS', None)
    env.pop('PIP_CONSTRAINT', None)
    env.pop('PIP_BUILD_CONSTRAINT', None)
    argv = [sys.executable, '-I', '-m', 'pip', 'download', '--no-index',
            '--no-deps', '--find-links', str(empty), '--dest', str(tmp_path), 'pyecore']
    process = subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert process.returncode != 0
    assert 'No matching distribution found for pyecore' in process.stderr
    assert not list(tmp_path.glob('*.whl'))
    request.node.user_properties.append(('offline_missing_core', json.dumps({
        'argv': argv, 'returncode': process.returncode,
        'stdout': process.stdout, 'stderr': process.stderr})))
