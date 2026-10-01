"""Fail-closed source/frozen validation and allowlisted Windows release packaging.

No provider credentials or user manuscripts are used. Only loopback mock traffic
is allowed during executable checks; the release never includes build logs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import queue
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.build'
RELEASE = ROOT / 'release'
EXE_NAME = 'ManuscriptRevisionClosure.exe'
VERSION = 'v0.6.4.1'
ZIP_NAME = f'manuscript-review-studio-{VERSION}-windows-x64.zip'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def checked(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, timeout: int = 300) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        # Logs may show runner paths in CI, but never enter released receipts.
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
        raise RuntimeError(f'{Path(command[0]).name} failed with exit code {result.returncode}')
    return result.stdout + result.stderr


def source_identity() -> str:
    commit = checked(['git', 'rev-parse', 'HEAD']).strip()
    require(bool(re.fullmatch(r'[0-9a-f]{40}', commit)), 'Invalid source commit')
    require(not os.environ.get('GITHUB_SHA') or os.environ['GITHUB_SHA'] == commit,
            'Checkout does not match workflow commit')
    checked(['git', 'diff', '--exit-code', 'HEAD', '--', '.', ':!release'])
    return commit


def build_metadata() -> dict:
    require(sys.platform == 'win32' and struct.calcsize('P') == 8, 'Build must run with Windows x64 Python')
    installed = {item.metadata['Name']: item.version for item in importlib.metadata.distributions()}
    return {
        'source_commit': source_identity(),
        'repository': 'lensback940701/manuscript-review-studio',
        'release_version': VERSION,
        'built_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'platform': 'Windows-x64',
        'pyinstaller': importlib.metadata.version('PyInstaller'),
        'pypdf': importlib.metadata.version('pypdf'),
        'installed_build_distributions': dict(sorted(installed.items())),
        'requirements_build_sha256': sha256(ROOT / 'requirements-build.txt'),
        'workflow_run_id': os.environ.get('GITHUB_RUN_ID'),
        'workflow_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
    }


def source_tests() -> None:
    WORK.mkdir(exist_ok=True)
    unit = checked([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], timeout=600)
    match = re.search(r'Ran (\d+) tests? in', unit)
    require(match is not None and '\nOK' in unit, 'Unit test summary missing')
    count = int(match.group(1))
    require(count >= 391, 'Expected at least the 391 retained unit tests')
    probes = {}
    for name, expected in [('rc2_0', 23), ('rc2_1', 59)]:
        output = checked([sys.executable, '-B', f'scripts/run_adversarial_probes_{name}.py'])
        result = re.search(r'ADVERSARIAL_PROBES_' + name.upper() + r'_OK count=(\d+)', output)
        require(result is not None and int(result.group(1)) == expected, f'{name} count mismatch')
        probes[name] = {'status': 'PASS', 'count': expected}
    receipt = {'status': 'PASS', 'source_commit': source_identity(), 'unit_test_count': count,
               'unit_tests': 'PASS', 'adversarial': probes, 'python': platform.python_version(),
               'platform': 'Windows-x64' if sys.platform == 'win32' else platform.system()}
    write_json(WORK / 'SOURCE_TEST_RECEIPT.json', receipt)
    print(json.dumps(receipt))


def isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if any(word in key.upper() for word in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD')) or key.upper() in {
            'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'DEEPSEEK_BASE_URL', 'KIMI_BASE_URL', 'GEMINI_BASE_URL'}:
            env.pop(key, None)
    # The frozen child cannot find the build Python, git, or the source tree via PATH.
    system = Path(env.get('SystemRoot', os.environ.get('WINDIR', '')))
    if sys.platform == 'win32':
        env['PATH'] = os.pathsep.join(str(system / item) for item in ('System32', ''))
    env.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONOPTIMIZE': '0', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8',
                'HTTP_PROXY': 'http://127.0.0.1:9', 'HTTPS_PROXY': 'http://127.0.0.1:9',
                'ALL_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': '127.0.0.1,localhost'})
    return env


def gui_smoke(exe: Path, directory: Path, env: dict[str, str]) -> dict:
    lines: queue.Queue[str] = queue.Queue()
    process = subprocess.Popen([str(exe), '--gui-no-browser'], cwd=directory, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding='utf-8', errors='replace',
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    def collect() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line)
    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(url: str, token: str, payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={'X-MRC-Token': token, 'Content-Type': 'application/json'})
        return opener.open(req, timeout=10)
    try:
        deadline = time.monotonic() + 60
        url = ''
        while time.monotonic() < deadline:
            require(process.poll() is None, 'GUI exited before becoming ready')
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                continue
            if line.startswith('Local GUI URL: '):
                url = line.partition('Local GUI URL: ')[2].strip()
                break
        require(bool(url), 'GUI readiness timed out')
        parts = urllib.parse.urlsplit(url)
        require(parts.scheme == 'http' and parts.hostname == '127.0.0.1', 'GUI must bind loopback')
        token = urllib.parse.parse_qs(parts.query)['token'][0]
        base = f'{parts.scheme}://{parts.netloc}'
        with request(base + '/', token) as response:
            html = response.read().decode('utf-8')
            require(response.status == 200 and '<html' in html, 'GUI page not served')
            for mode in ('standard', 'strictness', 'journal_benchmark'):
                require(mode in html, f'GUI mode missing: {mode}')
            require(response.headers.get('Cache-Control') == 'no-store', 'GUI privacy header missing')
        with request(base + '/api/status', token) as response:
            status = json.load(response)
            require(status.get('phase') == 'ready' and status.get('busy') is False, 'GUI initial state is not ready')
        try:
            with request(base + '/api/status', ''):
                raise RuntimeError('GUI accepted unauthenticated status request')
        except urllib.error.HTTPError as error:
            require(error.code == 403, 'Unexpected GUI authentication status')
        with request(base + '/api/close', token, {}) as response:
            require(json.load(response).get('closing') is True, 'GUI close not acknowledged')
        require(process.wait(timeout=20) == 0, 'GUI did not exit cleanly')
        try:
            with request(base + '/api/status', token):
                raise RuntimeError('GUI still serves after shutdown')
        except urllib.error.URLError:
            pass
        return {'status': 'PASS', 'loopback_only': True, 'html_and_all_mode_controls': 'PASS',
                'authenticated_ready_status': 'PASS', 'unauthenticated_request_rejected': True,
                'safe_shutdown_exit_code': 0, 'port_closed_after_shutdown': True,
                'browser_rendering_or_screenshot': 'NOT_RUN_HEADLESS_RUNNER'}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()


def parse_summary(output: str) -> dict:
    for line in reversed(output.splitlines()):
        if line.startswith('{'):
            result = json.loads(line)
            require(str(result.get('status', '')).startswith('PASS'), 'Frozen acceptance summary is not PASS')
            return result
    raise RuntimeError('Frozen acceptance summary missing')


def clean_distribution_paths() -> list[str]:
    """Only tracked, public source/docs; never copy a checkout recursively."""
    tracked = checked(['git', 'ls-files', '-z']).split('\0')
    roots = {'.gitignore', 'README.md', 'README.zh-CN.md', 'LICENSE', 'NOTICE', 'SKILL.md',
             'mrc_standalone.py', 'build_exe.ps1', 'requirements-build.txt'}
    prefixes = ('standalone/', 'scripts/', 'tests/', 'references/', 'agents/', 'docs/', '.github/')
    result = []
    for item in tracked:
        if not item or not (item in roots or item.startswith(prefixes)):
            continue
        path = Path(item)
        if any(part in {'.git', '.venv', '.build', '__pycache__', 'test0829'} for part in path.parts):
            continue
        if path.name.endswith('_GOAL.zh-CN.md') or path.suffix in {'.pyc', '.pyo'}:
            continue
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe distribution path')
        require(not (ROOT / item).is_symlink(), 'Symlinks not allowed in distribution')
        result.append(item)
    for needed in roots:
        require(needed in result, f'Missing public distribution input: {needed}')
    return sorted(result)


def validate_package() -> None:
    require(sys.platform == 'win32', 'Frozen validation requires Windows')
    source = source_identity()
    build = read_json(RELEASE / 'BUILD_RECEIPT.json')
    tests = read_json(WORK / 'SOURCE_TEST_RECEIPT.json')
    exe = RELEASE / EXE_NAME
    digest = sha256(exe)
    require(build['source_commit'] == tests['source_commit'] == source, 'Receipt source identity mismatch')
    require(tests['platform'] == build['platform'] == 'Windows-x64', 'Windows x64 test/build receipts required')
    require(build['sha256'].lower() == digest, 'Built executable hash mismatch')
    require(build['bytes'] == exe.stat().st_size, 'Built executable size mismatch')
    # Verify PE/COFF machine, rather than relying on a runner label alone.
    data = exe.read_bytes()
    pe_offset = struct.unpack_from('<I', data, 0x3c)[0]
    require(data[:2] == b'MZ' and data[pe_offset:pe_offset+4] == b'PE\0\0', 'Not a Windows PE file')
    require(struct.unpack_from('<H', data, pe_offset+4)[0] == 0x8664, 'Executable is not x64')
    with tempfile.TemporaryDirectory(prefix='mrc-standalone-') as folder:
        temp = Path(folder)
        copied = temp / EXE_NAME
        shutil.copy2(exe, copied)
        require([p.name for p in temp.iterdir()] == [EXE_NAME], 'Standalone folder is not otherwise empty')
        env = isolated_env()
        require(checked([str(copied), '--version'], cwd=temp, env=env).strip() == build['standalone_version'],
                'Frozen version does not match receipt')
        gui = gui_smoke(copied, temp, env)
        env['MRC_FROZEN_EXE'] = str(copied)
        env['MRC_BUILD_RECEIPT'] = str(RELEASE / 'BUILD_RECEIPT.json')
        frozen = parse_summary(checked([sys.executable, '-B', str(ROOT / 'tests/run_frozen_acceptance_0_6_4.py')],
                                       cwd=temp, env=env, timeout=900))
        multimode = parse_summary(checked([sys.executable, '-B', str(ROOT / 'tests/run_frozen_multimode_acceptance.py')],
                                          cwd=temp, env=env, timeout=600))
        require(frozen['frozen_exe_sha256'] == multimode['frozen_exe_sha256'] == digest, 'Tested executable hash mismatch')
        require(sha256(copied) == digest, 'Executable changed during validation')
    validation = {
        'status': 'PASS_WINDOWS_FROZEN_AND_SOURCE_VALIDATION', 'source_commit': source,
        'release_version': VERSION, 'validated_at_utc': datetime.now(timezone.utc).isoformat(),
        'exe_sha256': digest, 'exe_bytes': exe.stat().st_size,
        'build_receipt_sha256': sha256(RELEASE / 'BUILD_RECEIPT.json'),
        'source_tests': tests, 'standalone_empty_directory': True,
        'python_removed_from_child_path': True, 'gui_startup_shutdown': gui,
        'frozen_mock_acceptance': frozen, 'frozen_multimode_mock_acceptance': multimode,
        'real_provider_requests': 0, 'real_manuscripts_used': 0,
        'limitations': [
            'Loopback synthetic mock acceptance is not live-provider validation.',
            'GUI HTTP service and controls were verified; interactive browser rendering, native dialogs and screenshots were not tested.',
            'The executable is not code-signed; Windows SmartScreen may warn for an unfamiliar binary.',
            'Direct frozen injection of artificial internal invalid schemas is not performed; source tests cover that boundary.',
        ],
    }
    write_json(RELEASE / 'VALIDATION_RECEIPT.json', validation)
    package(source, build, validation)
    print(json.dumps({'status': validation['status'], 'source_commit': source,
                      'exe_sha256': digest, 'zip': ZIP_NAME}))


def third_party_licenses() -> Path:
    sections = []
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    require(python_license.is_file(), 'Python runtime license missing')
    sections.append('Python runtime ' + platform.python_version() + '\n\n' + python_license.read_text(encoding='utf-8'))
    for package_name in ('pypdf', 'PyInstaller'):
        distribution = importlib.metadata.distribution(package_name)
        found = []
        for item in distribution.files or []:
            if Path(str(item)).name.casefold().startswith(('license', 'copying')):
                path = Path(distribution.locate_file(item))
                if path.is_file() and path.suffix.casefold() not in {'.py', '.pyc'}:
                    found.append(path.read_text(encoding='utf-8', errors='replace'))
        require(bool(found), package_name + ' license text missing')
        sections.append(package_name + ' ' + distribution.version + '\n\n' + '\n\n'.join(found))
    destination = WORK / 'THIRD_PARTY_LICENSES.txt'
    destination.write_text(('\n\n' + '=' * 72 + '\n\n').join(sections) + '\n', encoding='utf-8')
    return destination


def package(source: str, build: dict, validation: dict) -> None:
    publish = WORK / 'publish'
    require(not publish.exists(), 'Publish directory already exists; use a fresh build')
    publish.mkdir(parents=True)
    distribution = {name: ROOT / name for name in clean_distribution_paths()}
    distribution['release/THIRD_PARTY_LICENSES.txt'] = third_party_licenses()
    # Fresh assets only, never historical release/ contents.
    for name in [EXE_NAME, EXE_NAME + '.sha256', 'BUILD_RECEIPT.json', 'VALIDATION_RECEIPT.json']:
        distribution['release/' + name] = RELEASE / name
        shutil.copy2(RELEASE / name, publish / name)
    release_docs = {'LICENSE': 'LICENSE', 'NOTICE': 'NOTICE', 'THIRD_PARTY_NOTICES.md': 'docs/THIRD_PARTY_NOTICES.md'}
    for target, original in release_docs.items():
        distribution['release/' + target] = ROOT / original
    for name, label in [('STANDALONE.md', 'English application guide'),
                        ('STANDALONE.zh-CN.md', '中文应用使用指南')]:
        pointer = WORK / name
        pointer.write_text(f'# {label}\n\n[{label}](../docs/{name})\n', encoding='utf-8')
        distribution['release/' + name] = pointer
    manifest = {'source_commit': source, 'release_version': VERSION,
                'files': {name: {'sha256': sha256(path), 'bytes': path.stat().st_size}
                          for name, path in sorted(distribution.items())}}
    write_json(WORK / 'DISTRIBUTION_MANIFEST.json', manifest)
    distribution['DISTRIBUTION_MANIFEST.json'] = WORK / 'DISTRIBUTION_MANIFEST.json'
    with zipfile.ZipFile(publish / ZIP_NAME, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(distribution.items()):
            archive.write(path, name)
    with zipfile.ZipFile(publish / ZIP_NAME) as archive:
        require(archive.testzip() is None, 'ZIP CRC verification failed')
        require(set(archive.namelist()) == set(distribution), 'Unexpected ZIP files')
        for name, entry in manifest['files'].items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == entry['sha256'], 'ZIP content mismatch')
    notes = (
        f'# Windows x64 release {VERSION}\n\n'
        f'Source commit: `{source}`. Runtime compatibility version: `{build["standalone_version"]}`.\n\n'
        f'Download `{ZIP_NAME}` for the full offline distribution. Extract all files, then double-click '
        '`release/ManuscriptRevisionClosure.exe`. No Python installation is required. '
        'English and Chinese guides are in `docs/STANDALONE.md` and `docs/STANDALONE.zh-CN.md`. '
        'The standalone EXE asset can also run by itself.\n\n'
        f'Windows source tests: {validation["source_tests"]["unit_test_count"]}; '
        'retained adversarial probes: 23 + 59. Frozen synthetic mock acceptance and copied-EXE '
        'GUI startup, authenticated status, mode controls and safe shutdown passed. '
        'See the attached validation receipt for exact case counts and limits.\n\n'
        f'EXE SHA-256: `{validation["exe_sha256"]}`. SHA256SUMS covers all download assets.\n\n'
        'No live-provider requests or real manuscripts were used. Headless CI does not validate browser '
        'rendering/native dialogs, and this EXE is unsigned. Source code (zip/tar.gz) generated by GitHub '
        'does not include the compiled EXE.\n\n'
        '中文：下载完整 Windows ZIP，全部解压后双击 release/ManuscriptRevisionClosure.exe。无需安装 Python。'
        '新版包含三种模式与期刊样本门槛修复；验证使用本机模拟接口，不代表真实模型服务实测。'
        '未签名的程序可能触发 Windows SmartScreen 提示。\n'
    )
    (publish / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')
    sums = ''.join(f'{sha256(path)}  {path.name}\n' for path in sorted(publish.iterdir()) if path.is_file())
    (publish / 'SHA256SUMS').write_text(sums, encoding='ascii')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['metadata', 'source-tests', 'validate-package'])
    args = parser.parse_args()
    if args.command == 'metadata':
        print(json.dumps(build_metadata()))
    elif args.command == 'source-tests':
        source_tests()
    else:
        validate_package()


if __name__ == '__main__':
    main()
