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
    filename : basestring
        Path to the ReproZip YAML file

    Return
    ------
    dict
        The environment configuration

    """
    with io.open(filename, encoding='utf-8') as fp:
        config = yaml.safe_load(fp)
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