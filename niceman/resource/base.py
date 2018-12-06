# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to manage compute resources."""

import attr
from importlib import import_module
import abc
from six import add_metaclass
from six.moves.configparser import NoSectionError

import yaml
from glob import glob
import os
import os.path as op

from ..dochelpers import exc_str
from ..support.exceptions import ResourceError
from ..support.exceptions import ResourceNotFoundError
from ..support.exceptions import ResourceAlreadyExistsError
from ..support.exceptions import MultipleResourceMatches
from ..support.exceptions import MissingConfigError


import logging
lgr = logging.getLogger('niceman.resource.base')


def get_required_fields(cls):
    """Return the mandatory fields for a resource class.
    """
    return {f.name for f in attr.fields(cls) if f.default is attr.NOTHING}


def get_resource_backends(cls):
    """Return name to documentation mapping of `cls`s backends.
    """
    return {b.name: b.metadata["doc"] for b in attr.fields(cls)
            if "doc" in b.metadata}


def backend_check_parameters(cls, keys):
    """Check whether any backend parameter keys are unknown.

    Parameters
    ----------
    cls : Resource object
    keys : iterable
        Backend parameter keys to check.

    Raises
    ------
    ResourceError on the first unknown key encountered.
    """
    required_params = get_required_fields(cls)
    for req_param in required_params:
        if req_param not in keys:
            raise ResourceError(
                "Missing required backend parameter: " + req_param)
    known = get_resource_backends(cls)
    for key in keys:
        if key not in known and key not in required_params:
            if known:
                import difflib

                suggestions = {s: known[s]
                               for s in difflib.get_close_matches(key, known)}
                if suggestions:
                    title = "Did you mean?"
                    params = suggestions
                else:
                    title = "Known backend parameters:"
                    params = known
                help_msg = "\n  {}\n{}\n".format(
                    title,
                    "\n".join(["    {} ({})".format(bname, bdoc)
                               for bname, bdoc in sorted(params.items())]))
                msg = "Bad --backend parameter '{}'{}".format(key, help_msg)
            else:
                msg = "Resource {} has no known parameters".format(cls)
            raise ResourceError(msg)


class ResourceManager(object):
    """Manager of available resources.

    Provides an API for finding existing resources or allocating new ones.
    Typically a NICEMAN process will have a single ResourceManager instance.
    """

    # The keys which are known to be secret and should not be exposed
    SECRET_KEYS = ('access_key_id', 'secret_access_key')

    def __init__(self, inventory_path=None):
        # Import here rather than the module-level to allow more flexibility in
        # overriding the configuration.
        from .. import cfg
        self.config_manager = cfg
        if inventory_path is None:
            self._inventory_path = self.config_manager.getpath(
                'general', 'inventory_file',
                op.join(cfg.dirs.user_config_dir, 'inventory.yml'))
        else:
            self._inventory_path = inventory_path

        self.inventory = self._get_inventory()

    def __iter__(self):
        for r in self.inventory:
            yield r

    @staticmethod
    def factory(config):
        """Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        config : dict
            Configuration parameters for the resource.

        Returns
        -------
        Resource sub-class instance.
        """
        if 'type' not in config:
            raise MissingConfigError("Resource 'type' parameter missing for resource.")

        type_ = config['type']
        module_name = '_'.join(type_.split('-'))
        class_name = ''.join([token.capitalize() for token in type_.split('-')])
        try:
            module = import_module('niceman.resource.{}'.format(module_name))
        except Exception as exc:
            # Typically it should be an ImportError, but let's catch and recast
            # anything just in case.
            try:
                msg = exc_str(exc)
                known = ResourceManager._discover_types()
                if module_name not in known:
                    msg += ". Known ones are: {}".format(", ".join(known))
            except Exception as exc2:
                msg += ".  Failed to discover resource types: " + exc_str(exc2)
            raise ResourceError(
                "Failed to import resource: {}".format(msg)
            )
        cls = getattr(module, class_name)
        try:
            instance = cls(**config)
        except TypeError:
            backend_check_parameters(cls, config)
            # The check didn't raise an exception, so this wasn't related to an
            # unknown backend parameter.
            raise
        return instance

    # TODO: Following methods might better be in their own class
    @staticmethod
    def _discover_types():
        """Discover resource types by inspecting the resource directory files.

        Returns
        -------
        string list
            List of resource identifiers extracted from file names.
        """
        l = []
        for f in glob(op.join(op.dirname(__file__), '*.py')):
            f_ = op.basename(f)
            if f_ in ('base.py',) or f_.startswith('_'):
                continue
            l.append(f_[:-3])
        return sorted(l)

    def _find_resources(self, resref, resref_type):
        def from_name(x):
            return [(name, config) for name, config in self.inventory.items()
                    if x == name]

        def from_id(x):
            return [(name, config) for name, config in self.inventory.items()
                    if x == config.get("id")]

        results_name = None
        results_id = None
        if resref_type == "auto":
            results_name = from_name(resref)
            results_id = from_id(resref)
        elif resref_type == "name":
            results_name = from_name(resref)
        elif resref_type == "id":
            results_id = from_id(resref)
        return results_name, results_id

    def _get_resource_config(self, resref, resref_type="auto"):
        results_name, results_id = self._find_resources(resref, resref_type)
        if results_name and results_id:
            raise MultipleResourceMatches(
                "{} is ambiguous. "
                "Explicitly specify whether it is a name or id".format(resref))
        elif not (results_name or results_id):
            raise ResourceNotFoundError(
                "Resource matching {} not found".format(resref))
        elif results_id and len(results_id) > 1:
            raise MultipleResourceMatches(
                "ID {} matches multiple resources. "
                "Try specifying with the name instead".format(resref))

        name, inventory_config = (results_name or results_id)[0]
        type_ = inventory_config['type']
        try:
            config = dict(self.config_manager.items(type_.split('-')[0]))
        except NoSectionError:
            config = {}
        config.update(inventory_config)
        return config

    def get_resource(self, resref, resref_type="auto"):
        """Return the resource instance for `resref`.

        Parameters
        ----------
        resref : str
            A name or ID that uniquely maps to a resource.
        resref_type : {'auto', 'name', 'id'}, optional
            The default behavior is to infer whether `resref` refers to a
            resource by name or full ID.  If the reference is ambiguous, this
            fails, in which case 'name' or 'id' can be used to disambiguate
            `resref`.

        Returns
        -------
        A Resource object
        """
        return self.factory(self._get_resource_config(resref, resref_type))

    def _get_inventory(self):
        """Return a dict with the config information for all resources.

        Parameters
        ----------
        inventory_path : string
            Path to the inventory file which is declared in the niceman.cfg file.

        Returns
        -------
        inventory : dict
            Hash whose key is resource name and value is the config settings for
            the resource.
        """
        inventory_path = self._inventory_path
        if not inventory_path:
            raise MissingConfigError(
                "No resource inventory path is known to %s" % self
            )

        if not op.isfile(inventory_path):
            inventory = {}
        else:
            with open(inventory_path, 'r') as fp:
                inventory = yaml.safe_load(fp)

        return inventory

    def _save(self):
        """Save the resource inventory.
        """
        # Operate on a copy so there is no side-effect of modifying original
        # inventory.
        #
        # The attribute may not exist yet because _get_inventory calls _save.
        inventory = self.inventory.copy() if hasattr(self, "inventory") else {}

        for key in list(inventory):  # go through a copy of all keys since we modify

            # A resource without an ID has been deleted.
            inventory_item = inventory[key]
            if 'id' in inventory_item and not inventory_item['id']:
                del inventory[key]

            # Remove AWS credentials
            # TODO(yoh): split away handling of credentials.  Resource should
            # probably just provide some kind of an id for a credential which
            # should be stored in a safe credentials storage
            for secret_key in ResourceManager.SECRET_KEYS:
                if secret_key in inventory_item:
                    del inventory_item[secret_key]

        if not op.exists(op.dirname(self._inventory_path)):
            os.makedirs(op.dirname(self._inventory_path))

        with open(self._inventory_path, 'w') as fp:
            yaml.safe_dump(inventory, fp, default_flow_style=False)

    def create(self, name, resource_type, backend_params=None):
        results_name, results_id = self._find_resources(name, "auto")
        if results_name or results_id:
            raise ResourceAlreadyExistsError(
                "Resource with {} {} already exists"
                .format("name" if results_name else "ID", name))

        config = {'name': name, 'type': resource_type}
        if backend_params:
            config.update(backend_params)
        resource = self.factory(config)
        resource.connect()
        resource_attrs = resource.create()
        config.update(resource_attrs)
        self.inventory[name] = config
        self._save()

    def delete(self, resource):
        """Delete `resource` from the inventory.

        Parameters
        ----------
        resource : Resource object
        """
        resource.delete()
        del self.inventory[resource.name]
        self._save()

    def start(self, resource):
        """Start a `resource` in the inventory.

        Parameters
        ----------
        resource : Resource object
        """
        try:
            resource.start()
        except NotImplementedError:
            lgr.info("This resource type does not support the 'start' feature")
            return

        self.inventory[resource.name]['status'] = "running"
        self._save()
        lgr.info("Started the environment %s (%s)", resource.name, resource.id)

    def stop(self, resource):
        """Stop but do not delete a `resource` in the inventory.

        Parameters
        ----------
        resource : Resource object
        """
        try:
            resource.stop()
        except NotImplementedError:
            lgr.info("This resource type does not support the 'stop' feature")
            return

        self.inventory[resource.name]['status'] = "stopped"
        self._save()
        lgr.info("Stopped the environment %s", resource.name)


@add_metaclass(abc.ABCMeta)
class Resource(object):
    """Base class for creating and managing compute resources.
    """

    def __repr__(self):
        return 'Resource({})'.format(self.name)

    def add_command(self, command, env=None):
        """Add a command to the command buffer so that all commands can be
        run at once in a batch submit to the environment.

        Parameters
        ----------
        command : string or list
            Command string or list of command string tokens.

        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        if not hasattr(self, '_command_buffer'):
            self._command_buffer = []  # Each element is a dictionary in the
                                       # form {command=[], env={}}
        self._command_buffer.append({'command': command, 'env': env})

    def execute_command_buffer(self, session=None):
        """Send all the commands in the command buffer to the environment for
        execution.

        Parameters
        ----------
        session : Sesson object, optional
            Session object reflects the resource type. (the default is None,
            which will cause the Session object to be retrieved from the
            Resource object.)
        """
        if not session:
            session = self.get_session(pty=False)
        for command in self._command_buffer:
            lgr.debug("Running command '%s'", command['command'])
            session.execute_command(command['command'], env=command['env'])

    def set_envvar(self, var, value):
        """Save an environment variable for inclusion in the environment

        Parameters
        ----------
        var : string
            Env variable name
        value : string
            Env variable value
        """
        # TODO: This wouldn't work correctly since pretty much each command
        # then should have its desired env recorded since set_envvar
        # could be interleaved with add_command calls
        if not hasattr(self, '_env'):
            self._env = {}

        self._env[var] = value

    def get_updated_env(self, custom_env):
        """Returns an env dictionary with additional or replaced values.

        Parameters
        ----------
        custom_env : dict
            Environment variables to merge into the existing list of declared
            environment variables stored in self._env

        Returns
        -------
        dict
            Environment variables merged with additional custom variables.
        """
        if hasattr(self, '_env'):
            merged_env = self._env.copy()
            if custom_env:
                merged_env.update(custom_env)
            return merged_env

        return custom_env

    @classmethod
    def _generate_id(cls):
        """Utility class method to generate a UUID.

        Returns
        -------
        string
            Newly created UUID
        """
        import uuid
        # just a random uuid for now, TODO: think if we somehow could
        # fingerprint it so to later be able to decide if it is 'ours'? ;)
        return str(uuid.uuid1())

    @abc.abstractmethod
    def get_session(self, pty=False, shared=None):
        """Returns the Session object for this resource.

        Parameters
        ----------
        pty : bool, optional
            Terminal session (the default is False)
        shared : string, optional
            Shared session identifier (the default is None)
        """
        return
