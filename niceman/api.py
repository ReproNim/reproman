# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Python NICEMAN API exposing user-oriented commands (also available via CLI)"""


def _generate_func_api():
    """Auto detect all available interfaces and generate a function-based
       API from them
    """
    from importlib import import_module
    from .interface.base import update_docstring_with_parameters
    from .interface.base import get_interface_groups
    from .interface.base import get_api_name
    from .interface.base import alter_interface_docs_for_api

    for grp_name, grp_descr, interfaces in get_interface_groups():
        for intfspec in interfaces:
            # turn the interface spec into an instance
            mod = import_module(intfspec[0], package='niceman')
            intf = getattr(mod, intfspec[1])
            spec = getattr(intf, '_params_', dict())

            # FIXME no longer using an interface class instance
            # convert the parameter SPEC into a docstring for the function
            update_docstring_with_parameters(
                intf.__call__, spec,
                prefix=alter_interface_docs_for_api(
                    intf.__doc__),
                suffix=alter_interface_docs_for_api(
                    intf.__call__.__doc__)
            )
            globals()[get_api_name(intfspec)] = intf.__call__

# Invoke above helpers
_generate_func_api()

# Be nice and clean up the namespace properly
del _generate_func_api
