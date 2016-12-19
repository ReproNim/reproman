# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Functions to read and manipulate reprozip yaml files

"""
import yaml
import io


def read_reprozip_yaml(filename):
    """Parses a ReproZip YAML file into a configuration object

    Given the path to a ReproZip YAML file, it parses the file and
    stores the resulting environment configuration into an object.

    Parameters
    ----------
    filename : str
        Path to the ReproZip YAML file

    Return
    ------
    dict
        The environment configuration

    """
    with io.open(filename, encoding='utf-8') as fp:
        config = yaml.safe_load(fp)
        return config


def identify_packages(config):
    """Identifies packages in the current environment from a ReproZip config

    Given a ReproZip configuration, it analyzes the current environment to
    find details about the source packages, and places the results back into
    the configuration object.

    Parameters
    ----------
    config : dict
        ReproZip configuration (input/output)

    Return
    ------
    dict
        A reference to the input dict

    """
    # Immediately clone the configuration
    files = get_system_files(config)

    # clear out current package assignment
    config['packages'] = {}

    # TODO: Identify files here

    # set any files not identified
    config['other_files'] = files

    return config


def get_system_files(config):
    """Pulls the system files from a ReproZip configuration into a set

    Given a ReproZip configuration (read into a dictionary) it pulls
    the list of files from "packages" and "other files" sections into a
    set. It excludes files from "input_output".

    Parameters
    ----------
    config : dict
        ReproZip configuration

    Return
    ------
    set
        System fles from the configuration
    """

    files = set()

    if 'packages' in config:
        for package in config['packages']:
            if 'files' in package:
                files.update(package['files'])

    if 'other_files' in config:
        files.update(config["other_files"])

    return files