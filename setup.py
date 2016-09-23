#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproNim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import platform

from glob import glob
from os.path import sep as pathsep

from setuptools import setup, find_packages

# manpage build imports
from distutils.command.build_py import build_py
from setup_support import BuildManPage, BuildRSTExamplesFromScripts
from setup_support import get_version

# repronim version to be installed
version = get_version()

# Only recentish versions of find_packages support include
# repronim_pkgs = find_packages('.', include=['repronim*'])
# so we will filter manually for maximal compatibility
repronim_pkgs = [pkg for pkg in find_packages('.') if pkg.startswith('repronim')]

requires = {
    'core': [
        'appdirs',
        'attrs',
        'humanize',
        'mock',  # mock is also used for auto.py, not only for testing
        'pyyaml',
        'six>=1.8.0',
        'tqdm',
    ],
    'debian': [
        'python-debian',
    ],
    'meta': [
        'rdflib',
    ],
    'tests': [
        'mock',
        'nose>=1.3.4',
    ]
}
requires['full'] = sum(list(requires.values()), [])


# configure additional command for custom build steps
class ReproNimBuild(build_py):
    def run(self):
        self.run_command('build_manpage')
        #self.run_command('build_examples')
        build_py.run(self)

cmdclass = {
    'build_manpage': BuildManPage,
    #'build_examples': BuildRSTExamplesFromScripts,
    'build_py': ReproNimBuild
}

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
