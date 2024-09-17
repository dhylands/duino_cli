import os
from setuptools import setup

import sys
if sys.version_info < (3,9):
    print('DuinoCli requires Python 3.9 or newer.')
    sys.exit(1)

from DuinoCli.version import __version__

here = Path(__file__).parent
long_description = (here / "README.md").read_text()

setup(
    name = 'DuinoCli',
    version = __version__,
    author = 'Dave Hylands',
    author_email = 'dhylands@gmail.com',
    description = ('A CLI interface for working with Arduino projects.'),
    license = 'MIT',
    keywords = 'cmd cli',
    url = 'https://github.com/dhylands/DuinoCli',
    download_url = f'https://github.com/dhylands/DuinoCli/shell/tarball/v0.0.1',
    packages=['rshell', 'tests'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: System :: Shells',
        'Topic :: Terminals :: Serial',
        'Topic :: Utilities',
    ],
    install_requires=[
        'pyserial',
        'pyudev >= 0.16',
    ],
    entry_points = {
        'console_scripts': [
            'pyboard=rshell.pyboard:main',
            'rshell=rshell.command_line:main'
        ],
    },
    extras_require={
        ':sys_platform == "win32"': [
            'pyreadline']
    }
)
