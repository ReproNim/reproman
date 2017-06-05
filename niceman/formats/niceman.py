# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for provenance YAML files following NICEMAN spec.

"""
from __future__ import absolute_import

import attr

import collections
import datetime
from collections import OrderedDict

import yaml

import niceman
from .. import utils
from ..dochelpers import exc_str
from ..distributions import Distribution
from .base import Provenance
from .utils import write_config_key
from .utils import write_config
from niceman.distributions.base import Factory
from niceman.distributions.base import SpecObject

import logging
lgr = logging.getLogger('niceman.formats.niceman')

__version__ = '0.0.1'


class NicemanspecProvenance(Provenance):
    """
    Parser for NICEMAN Spec (YAML specification)
    """

    @classmethod
    def _load(cls, source):
        """
        Load and store the raw spec file.

        Parameters
        ----------
        source : string
            File path or URL
        """
        with open(source, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as exc:
                lgr.error("Failed to load %s: %s", source, exc_str(exc))
                raise  # TODO -- we might want a dedicated exception here

    # def get_operating_system(self):
    #     """
    #     Retrieve the operating system information.
    #
    #     Returns
    #     -------
    #     Dictionary containing name and version of the OS.
    #         os['name']
    #         os['version']
    #     """
    #     raise NotImplementedError()
    #     return self._src['distribution']

    def get_distributions(self):
        """
        Retrieve the information for all the distributions recorded in the
        file.

        Returns
        -------
        list
            List of Distribution sub-class objects.
        """
        dist_objects = []

        """
        TODO: For "compressed" presentation we need to specify somewhere a handler
        in case of e.g. 
        - packages:
           - "full" is a list of dicts(attr structures)
           - a list with strings (e.g. - name[>=version]) where, depending on type
             of the package ('name' for DEBPackage, "url" for VCS), some name serves
             an identified
           - so it is a matter of the datatype of the item (string vs fully blown dict)
        - distributions:
           - "full" is a list of dict(attr structures) per each type of distribution
           - a dict with keys being a "name" of each entry
           
        But that is later -- for now just reading as is, allowing to map those specs
        into structs
        """

        """ATM we will assume that we are getting the "cut" at the level of the environment
        but it could be that the spec is on top of it
        """

        dists_in = self._src['distributions']
        if isinstance(dists_in, dict):
            # normalize compressed presentation into full
            dists_in = [
                dict(name=n, **(fields or {}))
                for n, fields in dists_in.items()
            ]

        distributions = []
        for dist_in in dists_in:
            subclass = dist_in['name'].strip('-0123456789')
            # Uses our factory decided by the 'name'
            # So it is pretty much some kind of a helper factory
            #   get_instance_by_name('niceman.distributions', dist_in['name'])
            # and then populate it.  Could become part of the model spec
            # describing that. ATM it is just a FactoryListOf(Distribution)
            # but we want to say that it is not just any Distribution
            # but the one decided from the 'name' and class for which found
            # among available in a module.
            # We have pretty much the same "factory" construct for Resources
            # ATM.
            # RF: make it generic!
            spec_class = Distribution.factory(subclass)

            spec_args = []
            spec_kwargs = dict()  # name=dist_in['name'])

            # process fields
            spec_attrs = spec_class.__attrs_attrs__  # as is -- list of them
            spec_in = dist_in.copy()  # shallow copy so we could pop

            # now we need to see what fields are present in the spec,
            # and prepare them to be passed into its constructor
            for spec_attr in spec_attrs:
                name = spec_attr.name
                if name not in spec_in:
                    if spec_attr.default is attr.NOTHING:
                        # positional argument -- must be known
                        raise ValueError(
                            "%s requires %r field, but was provided only with following fields: %s"
                            % (spec_class.__name__, name, ', '.join(spec_in.keys()))
                        )
                    else:
                        continue  # skipping

                value_in = spec_in.pop(name)
                # now we need a "factory" for each of those records
                # And those could be specific to their type(s) when "compressed"
                # but in general we should be able to use the same logic,
                # just need to know whom to call
                if isinstance(spec_attr.default, Factory):
                    item_type = spec_attr.metadata.get('type')
                    if item_type:
                        # we can use information of the type for each element we are
                        # getting for this name
                        # TODO: Recurse this whole shebang
                        value_out = spec_attr.default.factory(
                            (item_type(**kw) for kw in value_in)
                        )
                    else:
                        import pdb; pdb.set_trace()
                        value_out = spec_attr.default.factory(**value_in)
                else:
                    value_out = value_in

                if spec_attr.default is attr.NOTHING:
                    spec_args.append(value_out)  # positional arg
                else:
                    spec_kwargs[spec_attr.name] = value_out  # keyword arg

            if spec_in:
                raise ValueError(
                    "Following input fields were not processed since were not known to %s: %s"
                    % (spec_class.__name__, ', '.join(spec_in.keys()))
                )

            distributions.append(
                spec_class(*spec_args, **spec_kwargs)
            )

        # from pprint import pprint; pprint(distributions)
        # import pdb; pdb.set_trace()
        return distributions

    def get_files(self, limit='all'):
        return self._src.get('files', []) + ["TODO"]
        # TODO: we would need to get_distributions first then to traverse
        # all the packages etc...

    # TODO: RF
    #   config must be gone and taken from self
    @classmethod
    def write(cls, output, spec):
        """Writes an environment config to a stream
    
        Parameters
        ----------
        output
            Output Stream
        spec : dict
            Spec (environment) configuration (input).
            ??? Might want to code it in a generic fashion so spec 
            might be at a different level than environment may be.
            E.g. something which would be above and contain environment(s), 
            runs, etc 
    
        """

        # Allow yaml to handle OrderedDict
        # From http://stackoverflow.com/questions/31605131
        if collections.OrderedDict not in yaml.SafeDumper.yaml_representers:
            yaml.SafeDumper.add_representer(
                collections.OrderedDict,
                lambda self, data:
                self.represent_mapping('tag:yaml.org,2002:map', data.items()))

        utils.safe_write(
            output,
            ("# NICEMAN Environment Configuration File\n"
             "# This file was created by NICEMAN {0} on {1}\n").format(
                niceman.__version__, datetime.datetime.now()))

        #c = "\n# Runs: Commands and related environment variables\n\n"
        #write_config_key(output, envconfig, "runs", c)

        out = OrderedDict()
        out['version'] = __version__
        out.update(spec_to_dict(spec))
        write_config(output, out)
        return out


# TODO: RF into SpecObject._as_dict()
def spec_to_dict(spec):

    out = OrderedDict()
    spec_attrs = spec.__attrs_attrs__  # as is -- list of them
    for attr in spec_attrs:
        value_in = getattr(spec, attr.name, None)
        if not value_in:
            continue
        if isinstance(value_in, Factory):
            # wasn't set, thus "default", thus
            continue
        elif isinstance(value_in, list):
            # might be specs too
            value_out = value_in.__class__(
                spec_to_dict(v) if isinstance(v, SpecObject) else v
                for v in value_in
            )
        elif isinstance(value_in, SpecObject):
            value_out = spec_to_dict(value_in)
        else:
            value_out = value_in
        if value_out in (tuple(), [], {}, None):
            continue  # do not bother saving empty ones

        out[attr.name] = value_out
    return out

"""
        envconfig = dict(spec)  # Shallow copy for destruction

        c = "APT sources"
        write_config_key(output, envconfig, "apt_sources", c)

        c = "Packages"
        write_config_key(output, envconfig, "packages", c)

        c = "Non-Packaged Files"
        write_config_key(output, envconfig, "other_files", c)

        if envconfig:
            utils.safe_write(output, "\n# Other ReproZip keys (not used by NICEMAN) \n\n")
            utils.safe_write(output, yaml.safe_dump(envconfig,
                                                    encoding="utf-8",
                                                    allow_unicode=True))
"""