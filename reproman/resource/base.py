# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to manage compute resources."""

import attr
from importlib import import_module
import abc
from configparser import NoSectionError

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
lgr = logging.getLogger('reproman.resource.base')


def discover_types():
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
        l.append(f_[:-3].replace('_', '-'))
    return sorted(l)


def get_resource_class(name):
    if '_' in name:
        known = discover_types()
        hyph_name = name.replace('_', '-')
        if name not in known and hyph_name in known:
            raise ResourceError(
                "'{}' not a known backend. Did you mean '{}'?"
                .format(name, hyph_name))
    module_name = name.replace('-', '_')
    try:
        module = import_module('reproman.resource.{}'.format(module_name))
    except Exception as exc:
        # Typically it should be an ImportError, but let's catch and recast
        # anything just in case.
        import difflib
        try:
            msg = exc_str(exc)
            known = discover_types()
            suggestions = difflib.get_close_matches(name, known)
            if module_name not in known:
                msg += (
                    ". {}: {}"
                    .format("Similar backends" if suggestions else "Known backends",
                            ', '.join(suggestions or known)))
        except Exception as exc2:
            msg += ".  Failed to discover resource types: " + exc_str(exc2)
        raise ResourceError(
            "Failed to import resource: {}".format(msg)
        )

    class_name = ''.join([token.capitalize() for token in name.split('-')])
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ResourceError(
            "Failed to find {} in {}: {}"
            .format(class_name, module, exc_str(exc)))
    return cls


def get_required_fields(cls):
    """Return the mandatory fields for a resource class.
    """
    return {f.name for f in attr.fields(cls) if f.default is attr.NOTHING}


def get_resource_backends(cls):
    """Return name to documentation mapping of `cls`s backends.
    """
    return {b.name: b.metadata["doc"] for b in attr.fields(cls)
            if "doc" in b.metadata}


def classify_keys(cls, keys):
    """Classify `keys` according to the parameters of resource `cls`.

    Parameters
    ----------
    cls : Resource object
    keys : iterable
       Keys to classify.

    Returns
    -------
    A dictionary where each of `keys` is classified into one of the following
    categories:
      - required
        a parameter that must be specified when instantiating the class (either
        by us or the user)
      - opt_user
        a optional parameter that is exposed to the user (i.e. a field that has
        a default value and "doc" metadata)
      - opt_internal
        a unexposed optional parameter (i.e. a field with a default value but
        with no "doc" metadata) that should not be set by the user (e.g.,
        status)
      - unknown
        a parameter that doesn't fall into any of the above categories

    Raises
    ------
    A ResourceError if a required parameter isn't included in `keys`.
    """
    all_fields = {f.name for f in attr.fields(cls)}
    required_params = get_required_fields(cls)
    required_seen = set()
    known = get_resource_backends(cls)
    cats = {"required": [], "opt_user": [], "opt_internal": [], "unknown": []}
    for key in keys:
        if key in required_params:
            required_seen.add(key)
            cat = "required"
        elif key in known:
            cat = "opt_user"
        elif key in all_fields:
            # These are attributes like id and status.
            cat = "opt_internal"
        else:
            cat = "unknown"
        cats[cat].append(key)

    required_missing = required_params.difference(required_seen)
    if required_missing:
        raise ResourceError("Missing required backend parameters: {}"
                            .format(", ".join(sorted(required_missing))))

    return cats


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
    unknown = classify_keys(cls, keys)["unknown"]
    if unknown:
        known = get_resource_backends(cls)
        for key in unknown:
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
    Typically a ReproMan process will have a single ResourceManager instance.
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

    def _filter_config(self, cls, config):
        """Modify `config` to drop invalid parameters for `cls`.

        Parameters
        ----------
        cls : Resource object
        config : dict
             Configuration parameters for a resource.

        Returns
        -------
        A filtered (copy of) config or `config` itself if no modifications were
        needed.
        """
        unknown = classify_keys(cls, config)["unknown"]
        if unknown:
            config = config.copy()
            inv_config = self.inventory.get(config["name"], {})
            for unk_param in unknown:
                msg_extra = ""
                if unk_param in inv_config:
                    msg_extra = (". Consider removing it from {}"
                                 .format(self._inventory_path))
                lgr.warning("%s is not a known %s parameter%s",
                            unk_param, config["type"], msg_extra)
                config.pop(unk_param)
        return config

    def factory(self, config, strict=True):
        """Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        config : dict
            Configuration parameters for the resource.
        strict : optional
            When set to false, drop unknown keys from `config`, after issuing a
            warning, rather than raising a ResourceError.

        Returns
        -------
        Resource sub-class instance.
        """
        if 'type' not in config:
            raise MissingConfigError("Resource 'type' parameter missing for resource.")

        type_ = config['type']
        cls = get_resource_class(type_)

        if not strict:
            config = self._filter_config(cls, config)

        try:
            instance = cls(**config)
        except TypeError:
            if strict:
                # In strict mode, the exception may be due to an unknown
                # backend paraemter. Call backend_check_parameters() to get a
                # more meaningful ResourceError.
                backend_check_parameters(cls, config)
                # Never mind. The check didn't raise an exception, so this
                # wasn't related to an unknown backend parameter.
            raise
        return instance

    def _find_resources(self, resref, resref_type):
        def match_name(inventory_item):
            return resref == inventory_item[0]

        def match_id(inventory_item):
            return resref == inventory_item[1].get("id")

        def match_id_partial(inventory_item):
            return inventory_item[1].get("id", "").startswith(resref)

        def filter_inventory(pred):
            return list(filter(pred, self.inventory.items()))

        results_name = None
        results_id = None
        partial_id = False
        if resref_type in ["auto", "name"]:
            results_name = filter_inventory(match_name)
        if resref_type in ["auto", "id"]:
            results_id = filter_inventory(match_id)
            if not results_id:
                partial_id = True
                results_id = filter_inventory(match_id_partial)
        return results_name, results_id, partial_id

    def _get_resource_config(self, resref, resref_type="auto"):
        if not resref:
            raise ValueError("`resref` cannot be empty")
        results_name, results_id, partial_id = self._find_resources(
            resref, resref_type)
        if results_name and results_id and not partial_id:
            raise MultipleResourceMatches(
                "{} is ambiguous. "
                "Explicitly specify whether it is a name or id".format(resref))
        elif not (results_name or results_id):
            raise ResourceNotFoundError(
                "Resource matching {} not found".format(resref))
        elif results_name:
            # Don't bother with partial ID matches when we have a full name
            # match.
            pass
        elif results_id and len(results_id) > 1:
            raise MultipleResourceMatches(
                "ID {} {}matches {} resources. "
                "Try specifying the {}name instead"
                .format(resref,
                        "partially " if partial_id else "",
                        len(results_id),
                        "full ID or " if partial_id else ""))

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
        return self.factory(self._get_resource_config(resref, resref_type),
                            strict=False)

    def _get_inventory(self):
        """Return a dict with the config information for all resources.

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

    def save_inventory(self):
        """Save the resource inventory.
        """
        # Operate on a copy so there is no side-effect of modifying original
        # inventory.
        #
        # The attribute may not exist yet because _get_inventory calls save_inventory.
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
        results_name, results_id, partial_id = self._find_resources(
            name, "auto")
        if results_name or (results_id and not partial_id):
            raise ResourceAlreadyExistsError(
                "Resource with {} {} already exists"
                .format("name" if results_name else "ID", name))

        try:
            config = dict(
                self.config_manager.items(resource_type.split('-')[0]))
        except NoSectionError:
            config = {}

        config['name'] = name
        config['type'] = resource_type

        if backend_params:
            config.update(backend_params)
        resource = self.factory(config)
        resource.connect()
        # Resource can yield and save inventory info as it needs to throughout
        # the create process.
        for resource_attrs in resource.create():
            config.update(resource_attrs)
            self.inventory[name] = config
            self.save_inventory()

    def delete(self, resource, inventory_only=False):
        """Delete `resource` from the inventory.

        Parameters
        ----------
        resource : Resource object

        inventory_only : boolean
            Flag to indicate that we should only remove the resource record
            from the inventory file
        """
        if not inventory_only:
            resource.delete()
        del self.inventory[resource.name]
        self.save_inventory()

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
        self.save_inventory()
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
        self.save_inventory()
        lgr.info("Stopped the environment %s", resource.name)


class Resource(object, metaclass=abc.ABCMeta):
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
        session : Session object, optional
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
