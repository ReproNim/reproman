#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproMan package for the
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

    Leading directory (reproman) gets stripped
    """
    return [
        f.split(pathsep, 1)[1] for f in findall(opj('reproman', subdir))
        if splitext(f)[-1].lstrip('.') in extensions
    ]

# reproman version to be installed
version = get_version()

# Only recentish versions of find_packages support include
# reproman_pkgs = find_packages('.', include=['reproman*'])
# so we will filter manually for maximal compatibility
reproman_pkgs = [pkg for pkg in find_packages('.') if pkg.startswith('reproman')]

requires = {
    'core': [
        'appdirs',
        'attrs>=16.3.0',
        'etelemetry>=0.2.0',
        'humanize',
        'pyyaml',
        'tqdm',
        # https://github.com/paramiko/paramiko/issues/1839
        'paramiko==2.8.1',
        'fabric>=2.3.1',
        'cryptography>=2.5',
        'pytz',
        'scp',
        'pycrypto',
        'pyOpenSSL==16.2.0',
        'requests',
        'reprozip; sys_platform=="linux" or sys_platform=="linux2"',
        'rpaths',
        'jinja2',
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
    'datalad': [
        'datalad>=0.13.0',
        'datalad-container',
    ],
    'docker': [
        'docker>=3.0.0',
        'dockerpty',
    ],
    'aws': [
        'boto3',
    ],
    'meta': [
        'rdflib',
    ],
    'tests': [
        'pytest>=3.3.0',
        'virtualenv',
    ]
}

# Target to ease testing installation.
requires['full-except-datalad'] = [v for k, vs in requires.items()
                                   for v in vs if k != "datalad"]
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

with open(opj(dirname(__file__), 'README.md')) as f:
    long_description = f.read()

setup(
    name="reproman",
    author="The ReproMan Team and Contributors",
    author_email="team@reproman.org",
    version=version,
    description="Neuroimaging Computational Environments Manager",
    long_description=long_description,
    # following https://packaging.python.org/guides/making-a-pypi-friendly-readme/
    # might need
    # python3 -m pip install --user --upgrade setuptools wheel twine
    long_description_content_type='text/markdown',
    packages=reproman_pkgs,
    python_requires='>=3.6',
    install_requires=requires['core'],
    extras_require=requires,
    entry_points={
        'console_scripts': [
            'reproman=reproman.cmdline.main:main',
        ],
    },
    cmdclass=cmdclass,
    package_data={
        'reproman':
            findsome(opj("distributions", "tests", "files"), {"yml", "yaml"}) +
            findsome("examples", {"trig", "yml", "yaml"}) +
            findsome(opj("formats", "tests", "files"), {"yml", "yaml"}) +
            findsome(opj("interface"), {"shim"}) +
            findsome(opj("interface", "tests"), {"yml", "yaml"}) +
            findsome(opj("interface", "tests", "files"), {"yml", "yaml"}) +
            findsome(opj("support", "jobs", "job_templates", "runscript"),
                     {"sh"}) +
            findsome(opj("support", "jobs", "job_templates", "runscript", "includes"),
                     {"sh"}) +
            findsome(opj("support", "jobs", "job_templates", "submission"),
                     {"template"}) +
            findsome(opj("support", "jobs", "job_templates", "cluster"),
                     {"template"}) +
            findsome(opj("tests", "files"), {"cfg"})
    },
    setup_requires=['setuptools_scm'],
)
