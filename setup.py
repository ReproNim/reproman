#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproNim package for the
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

    Leading directory (repronim) gets stripped
    """
    return [
        f.split(pathsep, 1)[1] for f in findall(opj('repronim', subdir))
        if splitext(f)[-1].lstrip('.') in extensions
    ]

# repronim version to be installed
version = get_version()

# Only recentish versions of find_packages support include
# repronim_pkgs = find_packages('.', include=['repronim*'])
# so we will filter manually for maximal compatibility
repronim_pkgs = [pkg for pkg in find_packages('.') if pkg.startswith('repronim')]

requires = {
    'core': [
        'appdirs',
        'humanize',
        'mock',  # mock is also used for auto.py, not only for testing
        'six>=1.8.0',
        'tqdm',
    ],
    'tests': [
        'mock',
        'nose>=1.3.4',
    ]
}

requires['full'] = sum(list(requires.values()), [])

# Now add additional ones useful for development
requires.update({
    'devel-docs': [
        # used for converting README.md -> .rst for long_description
        'pypandoc',
        # Documentation
        'sphinx',
        'sphinx-rtd-theme',
    ],
    'devel-utils': [
        'nose-timer',
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
    name="repronim",
    author="The ReproNim Team and Contributors",
    author_email="team@repronim.org",
    version=version,
    description="Tools for Reproducible Neuroimaging",
    packages=repronim_pkgs,
    install_requires=requires['core'],
    extras_require=requires,
    entry_points={
        'console_scripts': [
            'repronim=repronim.cmdline.main:main',
        ],
    },
    cmdclass=cmdclass,
    package_data={
        'repronim': []
    }
)
