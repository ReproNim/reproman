# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""High-level interface generation

"""

__docformat__ = 'restructuredtext'

import attr
from importlib import import_module
import sys
import re
import textwrap

from ..ui import ui
from ..dochelpers import exc_str
from ..resource import ResourceManager
from ..resource import Resource
from ..support.exceptions import ResourceError
from logging import getLogger
lgr = getLogger('niceman.interface')


def get_api_name(intfspec):
    """Given an interface specification return an API name for it"""
    if len(intfspec) > 3:
        name = intfspec[3]
    else:
        name = intfspec[0].split('.')[-1]
    return name


def get_cmdline_command_name(intfspec):
    """Given an interface specification return a cmdline command name"""
    if len(intfspec) > 2:
        name = intfspec[2]
    else:
        name = intfspec[0].split('.')[-1].replace('_', '-')
    return name


def get_interface_groups():
    from .. import interface as _interfaces

    grps = []
    # auto detect all available interfaces and generate a function-based
    # API from them
    for _item in _interfaces.__dict__:
        if not _item.startswith('_group_'):
            continue
        grp_name = _item[7:]
        grp = getattr(_interfaces, _item)
        grps.append((grp_name,) + grp)
    return grps


def dedent_docstring(text):
    """Remove uniform indentation from a multiline docstring"""
    # Problem is that first line might often have no offset, so might
    # need to be ignored from dedent call
    if text is None:
        return None
    if not text.startswith(' '):
        lines = text.split('\n')
        if len(lines) == 1:
            # single line, no indentation, nothing to do
            return text
        text2 = '\n'.join(lines[1:])
        return lines[0] + "\n" + textwrap.dedent(text2)
    else:
        return textwrap.dedent(text)


def alter_interface_docs_for_api(docs):
    """Apply modifications to interface docstrings for Python API use."""
    # central place to alter the impression of docstrings,
    # like removing cmdline specific sections
    if not docs:
        return docs
    docs = dedent_docstring(docs)
    # clean cmdline sections
    docs = re.sub(
        '\|\| CMDLINE \>\>.*\<\< CMDLINE \|\|',
        '',
        docs,
        flags=re.MULTILINE | re.DOTALL)
    # clean cmdline in-line bits
    docs = re.sub(
        '\[CMD:\s[^\[\]]*\sCMD\]',
        '',
        docs,
        flags=re.MULTILINE | re.DOTALL)
    docs = re.sub(
        '\[PY:\s([^\[\]]*)\sPY\]',
        lambda match: match.group(1),
        docs,
        flags=re.MULTILINE)
    docs = re.sub(
        '\|\| PYTHON \>\>(.*)\<\< PYTHON \|\|',
        lambda match: match.group(1),
        docs,
        flags=re.MULTILINE | re.DOTALL)
    docs = re.sub(
        '\|\| REFLOW \>\>\n(.*)\<\< REFLOW \|\|',
        lambda match: textwrap.fill(match.group(1)),
        docs,
        flags=re.MULTILINE | re.DOTALL)
    return docs


def alter_interface_docs_for_cmdline(docs):
    """Apply modifications to interface docstrings for cmdline doc use."""
    # central place to alter the impression of docstrings,
    # like removing Python API specific sections, and argument markup
    if not docs:
        return docs
    docs = dedent_docstring(docs)
    # clean cmdline sections
    docs = re.sub(
        '\|\| PYTHON \>\>.*\<\< PYTHON \|\|',
        '',
        docs,
        flags=re.MULTILINE | re.DOTALL)
    # clean cmdline in-line bits
    docs = re.sub(
        '\[PY:\s[^\[\]]*\sPY\]',
        '',
        docs,
        flags=re.MULTILINE | re.DOTALL)
    docs = re.sub(
        '\[CMD:\s([^\[\]]*)\sCMD\]',
        lambda match: match.group(1),
        docs,
        flags=re.MULTILINE)
    docs = re.sub(
        '\|\| CMDLINE \>\>(.*)\<\< CMDLINE \|\|',
        lambda match: match.group(1),
        docs,
        flags=re.MULTILINE | re.DOTALL)
    # remove :role:`...` RST markup for cmdline docs
    docs = re.sub(
        r':\S+:`[^`]*`[\\]*',
        lambda match: ':'.join(match.group(0).split(':')[2:]).strip('`\\'),
        docs,
        flags=re.MULTILINE | re.DOTALL)
    # remove None constraint. In general, `None` on the cmdline means don't
    # give option at all, but specifying `None` explicitly is practically
    # impossible
    docs = re.sub(
        ',\sor\svalue\smust\sbe\s`None`',
        '',
        docs,
        flags=re.MULTILINE | re.DOTALL)
    # capitalize variables and remove backticks to uniformize with
    # argparse output
    docs = re.sub(
        '`\S*`',
        lambda match: match.group(0).strip('`').upper(),
        docs)
    # clean up sphinx API refs
    docs = re.sub(
        '\~niceman\.api\.\S*',
        lambda match: "`{0}`".format(match.group(0)[13:]),
        docs)
    # Remove RST paragraph markup
    docs = re.sub(
        r'^.. \S+::',
        lambda match: match.group(0)[3:-2].upper(),
        docs,
        flags=re.MULTILINE)
    docs = re.sub(
        '\|\| REFLOW \>\>\n(.*)\<\< REFLOW \|\|',
        lambda match: textwrap.fill(match.group(1)),
        docs,
        flags=re.MULTILINE | re.DOTALL)
    return docs


def update_docstring_with_parameters(func, params, prefix=None, suffix=None):
    """Generate a useful docstring from a parameter spec

    Amends any existing docstring of a callable with a textual
    description of its parameters. The Parameter spec needs to match
    the number and names of the callables arguments.
    """
    from inspect import getargspec
    # get the signature
    ndefaults = 0
    args, varargs, varkw, defaults = getargspec(func)
    if not defaults is None:
        ndefaults = len(defaults)
    # start documentation with what the callable brings with it
    doc = prefix if prefix else u''
    if len(args) > 1:
        if len(doc):
            doc += '\n'
        doc += "Parameters\n----------\n"
        for i, arg in enumerate(args):
            if arg == 'self':
                continue
            # we need a parameter spec for each argument
            if not arg in params:
                raise ValueError("function has argument '%s' not described as a parameter" % arg)
            param = params[arg]
            # validate the default -- to make sure that the parameter description is
            # somewhat OK
            defaults_idx = ndefaults - len(args) + i
            if defaults_idx >= 0:
                if not param.constraints is None:
                    param.constraints(defaults[defaults_idx])
            orig_docs = param._doc
            param._doc = alter_interface_docs_for_api(param._doc)
            doc += param.get_autodoc(
                arg,
                default=defaults[defaults_idx] if defaults_idx >= 0 else None,
                has_default=defaults_idx >= 0)
            param._doc = orig_docs
            doc += '\n'
    doc += suffix if suffix else u""
    # assign the amended docs
    func.__doc__ = doc
    return func


def backend_help(resource_type=None):
    """
    Helper function for displaying backend help listing for interface commands.

    To use, add this to the interface argparse parameters:

        backend=Parameter(
            args=("-b", "--backend"),
            nargs="+",
            doc=backend_help()
        )

    """
    types = ResourceManager._discover_types() if not resource_type else [resource_type]

    help_message = "One or more backend parameters in the form KEY=VALUE. Options are: "
    help_args = []

    for module_name in types:
        class_name = ''.join([token.capitalize() for token in module_name.split('_')])
        try:
            module = import_module('niceman.resource.{}'.format(module_name))
        except ImportError as exc:
            raise ResourceError(
                "Failed to import resource {}: {}.  Known ones are: {}".format(
                    module_name,
                    exc_str(exc),
                    ', '.join(ResourceManager._discover_types()))
            )
        cls = getattr(module, class_name)
        if not issubclass(cls, Resource):
            lgr.debug(
                "Skipping %s.%s since not a Resource. Consider moving away",
                module, class_name
            )
            continue
        args = attr.fields(cls)
        for arg in args:
            if 'doc' in arg.metadata:
                help_args.append('"{}" ({})'.format(arg.name, arg.metadata['doc']))

    return help_message + ", ".join(help_args)


def backend_set_config(backend, env_resource, config):
    """
    Set config settings based and env_resource properties based on
    backend parameters passed through command line.
    """
    config = config.copy()
    for backend_arg in backend:
        key, value = backend_arg.split("=")
        if hasattr(env_resource, key):
            config[key] = value
            setattr(env_resource, key, value)
        else:
            raise NotImplementedError("Bad --backend parameter '{}'".format(key))
    return config


class Interface(object):
    """Base class for interface implementations"""

    @classmethod
    def setup_parser(cls, parser):
        # XXX needs safety check for name collisions
        # XXX allow for parser kwargs customization
        parser_kwargs = {}
        from inspect import getargspec
        # get the signature
        ndefaults = 0
        args, varargs, varkw, defaults = getargspec(cls.__call__)
        if not defaults is None:
            ndefaults = len(defaults)
        for i, arg in enumerate(args):
            if arg == 'self':
                continue
            param = cls._params_[arg]
            defaults_idx = ndefaults - len(args) + i
            cmd_args = param.cmd_args
            if cmd_args is None:
                cmd_args = []
            if not len(cmd_args):
                if defaults_idx >= 0:
                    # dealing with a kwarg
                    template = '--%s'
                else:
                    # positional arg
                    template = '%s'
                # use parameter name as default argument name
                parser_args = (template % arg.replace('_', '-'),)
            else:
                parser_args = [c.replace('_', '-') for c in cmd_args]
            parser_kwargs = param.cmd_kwargs
            if defaults_idx >= 0:
                parser_kwargs['default'] = defaults[defaults_idx]
            help = alter_interface_docs_for_cmdline(param._doc)
            if help and help[-1] != '.':
                help += '.'
            if param.constraints is not None:
                parser_kwargs['type'] = param.constraints
                # include value constraint description and default
                # into the help string
                cdoc = alter_interface_docs_for_cmdline(
                    param.constraints.long_description())
                if cdoc[0] == '(' and cdoc[-1] == ')':
                    cdoc = cdoc[1:-1]
                help += '  Constraints: %s' % cdoc
            if defaults_idx >= 0:
                help += " [Default: %r]" % (defaults[defaults_idx],)
            # create the parameter, using the constraint instance for type
            # conversion
            parser.add_argument(*parser_args, help=help,
                                **parser_kwargs)

    @classmethod
    def call_from_parser(cls, args):
        # XXX needs safety check for name collisions
        from inspect import getargspec
        argnames = getargspec(cls.__call__)[0]
        kwargs = {k: getattr(args, k) for k in argnames if k != 'self'}
        try:
            return cls.__call__(**kwargs)
        except KeyboardInterrupt:
            ui.error("\nInterrupted by user while doing magic")
            sys.exit(1)