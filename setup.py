"""
Setup file for the duinp_cli module.
"""

from pathlib import Path
import sys
from setuptools import setup
from duino_cli.version import __version__

if sys.version_info < (3, 9):
    print('duino_cli requires Python 3.9 or newer.')
    sys.exit(1)

here = Path(__file__).parent
long_description = (here / "README.md").read_text()

setup(
        name='duino_cli',
        version=__version__,
        author='Dave Hylands',
        author_email='dhylands@gmail.com',
        description=('A CLI interface for working with Arduino projects.'),
        license='MIT',
        keywords='cmd cli arduino',
        url='https://github.com/dhylands/duino_cli',
        download_url=f'https://github.com/dhylands/duino_cli/shell/tarball/v{__version__}',
        packages=['duino_cli'],
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
        install_requires=['pyserial', 'duino_bus'],
        entry_points={
                'console_scripts': ['cli=duino_cli.command_line:main'],
                'duino_cli.plugin': ['core=duino_cli.core_plugin:CorePlugin']
        },
        extras_require={':sys_platform == "win32"': ['pyreadline']}
)
