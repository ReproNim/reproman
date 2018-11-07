#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NICEMAN package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import platform

from os.path import sep as pathsep
from os.path import join as opj
from os.path import splitext
from os.path import dirname

from setuptools import findall
from setuptools import setup, find_packages

# manpage build imports
from setup_support import BuildManPage
from setup_support import BuildRSTExamplesFromScripts
# from setup_support import BuildConfigInfo
from setup_support import get_version


def findsome(subdir, extensions):
    """Find files under subdir having specified extensions

    Leading directory (niceman) gets stripped
    """
    return [
        f.split(pathsep, 1)[1] for f in findall(opj('niceman', subdir))
        if splitext(f)[-1].lstrip('.') in extensions
    ]

# niceman version to be installed
version = get_version()

# Only recentish versions of find_packages support include
# niceman_pkgs = find_packages('.', include=['niceman*'])
# so we will filter manually for maximal compatibility
niceman_pkgs = [pkg for pkg in find_packages('.') if pkg.startswith('niceman')]

requires = {
    'core': [
        'appdirs',
        'attrs>=16.3.0',
        'humanize',
        'mock',  # mock is also used for auto.py, not only for testing
        'pyyaml',
        'six>=1.9',
        'tqdm',
        'fabric>=2.3.1',
        'cryptography>=1.5',
        'pytz',
        'scp',
        'pycrypto',
        'pyOpenSSL==16.2.0',
        'requests',
        'reprozip; sys_platform=="linux" or sys_platform=="linux2"',
        'rpaths',
    ],
    'debian': [
        'python-debian',
        # on Debian systems will come via apt
        #'python-apt>=0.8.9.1',
        # Origin.codename was introduced in 0.8.9
        # unfortunately not on pypi but needed by python-apt
        #'http://archive.ubuntu.com/ubuntu/pool/main/p/python-apt/python-apt_0.9.3.5.tar.xz'
        'chardet',  # python-debian misses dependency on it
    ],
    'docker': [
        'docker-py>=0.3.2',
        'dockerpty',
    ],
    'aws': [
        'boto3',
    ],
    'meta': [
        'rdflib',
    ],
    'tests': [
        'mock',
        'pytest>=3.3.0',
    ]
}

requires['full'] = sum(list(requires.values()), [])

# Now add additional ones useful for development
requires.update({
    'devel-docs': [
        # used for converting README.md -> .rst for long_description
        #  TODO: enable whenever we are ready! otherwise requires installation
        #        of pandoc first via apt-get
        # 'pypandoc',
        # Documentation
        'sphinx',
        'sphinx-rtd-theme',
    ],
    'devel-utils': [
        'line-profiler',
        # necessary for accessing SecretStorage keyring (system wide Gnome
        # keyring)  but not installable on travis, IIRC since it needs connectivity
        # to the dbus whenever installed or smth like that, thus disabled here
        # but you might need it
        # 'dbus-python',
    ],
    'devel-neuroimaging': [
        # Specifically needed for tests here (e.g. example scripts testing)
        'nibabel',
    ]
})
requires['devel'] = sum(list(requires.values()), [])


# let's not build manpages and examples automatically (gh-896)
# configure additional command for custom build steps
#class DataladBuild(build_py):
#    def run(self):
#        self.run_command('build_manpage')
#        self.run_command('build_examples')
#        build_py.run(self)

cmdclass = {
    'build_manpage': BuildManPage,
    # 'build_examples': BuildRSTExamplesFromScripts,
    # 'build_cfginfo': BuildConfigInfo,
    # 'build_py': DataladBuild
}

# PyPI doesn't render markdown yet. Workaround for a sane appearance
# https://github.com/pypa/pypi-legacy/issues/148#issuecomment-227757822
README = opj(dirname(__file__), 'README.md')
try:
    import pypandoc
    long_description = pypandoc.convert(README, 'rst')
except ImportError:
    long_description = open(README).read()

setup(
    name="niceman",
    author="The NICEMAN Team and Contributors",
    author_email="team@niceman.org",
    version=version,
    description="Neuroimaging Computational Environments Manager",
    long_description=long_description,
    packages=niceman_pkgs,
    install_requires=requires['core'],
    extras_require=requires,
    entry_points={
        'console_scripts': [
            'niceman=niceman.cmdline.main:main',
        ],
    },
    cmdclass=cmdclass,
    package_data={
        'niceman': []
    }
)
