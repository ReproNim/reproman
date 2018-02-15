# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utils to deal with various file formats
"""

from __future__ import absolute_import

import yaml

from niceman.utils import safe_write


def write_config_key(stream, envconfig, key, intro_comment=""):
    """Writes the YAML representation of a single key

    This writes a single key of a dict to an output stream and then removes
    the key from the dict.

    Parameters
    ----------
    stream
        Output Stream
    envconfig : dict
    key
        Key from the dictionary
    intro_comment : str, optional
        Introduction comment for the key

    """
    if key in envconfig:
        mini_config = dict()
        mini_config[key] = envconfig.pop(key)
        if intro_comment:
            safe_write(stream, "\n# %s\n\n" % intro_comment)
        write_config(stream, mini_config)


def write_config(stream, rec):
    """TODO"""
    return safe_write(
        stream,
        yaml.safe_dump(
            rec, encoding="utf-8", allow_unicode=True,
            default_flow_style=False
        )
    )
