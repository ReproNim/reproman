# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from unittest.mock import patch
import os.path as op
import pytest

from reproman.config import ConfigManager
from reproman.resource.base import ResourceManager
from reproman.resource.base import Resource
from reproman.resource.base import backend_check_parameters
from reproman.resource.base import get_resource_class
from reproman.resource.shell import Shell
from reproman.support.exceptions import MissingConfigError
from reproman.support.exceptions import MultipleResourceMatches
from reproman.support.exceptions import ResourceAlreadyExistsError
from reproman.support.exceptions import ResourceError
from reproman.tests.skip import mark


def test_resource_manager_factory_missing_type(resman):
    with pytest.raises(MissingConfigError):
        resman.factory({})


def test_resource_manager_factory_unkown(resman):
    with pytest.raises(ResourceError):
        resman.factory({"type": "not really a type"})


def test_resource_manager_factory_missing_required(resman):
    with pytest.raises(ResourceError):
        resman.factory({"type": "shell"})


@pytest.mark.parametrize("type_", ["shell", "ssh"])
def test_resource_manager_factory_invalid_param(resman, type_):
    config = {
        "type": type_,
        "id": "id",
        "name": "name",
        # All of the below are invalid in the case of shell. For ssh,
        # "other" is invalid.
        "host": "host",
        "port": "port",
        "other": "doesntmatter",
    }

    with pytest.raises(ResourceError):
        resman.factory(config)

    res = resman.factory(config, strict=False)
    assert isinstance(res, Resource)


def test_backend_check_parameters_no_known():
    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(Shell, {"name": "name", "unknown_key": "value"})
    assert "no known parameters" in str(exc.value)


@mark.skipif_no_docker_dependencies
def test_backend_check_parameters_nowhere_close():
    from reproman.resource.docker_container import DockerContainer

    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(DockerContainer, {"name": "name", "unknown_key": "value"})
    assert "Known backend parameters" in str(exc.value)


@mark.skipif_no_docker_dependencies
def test_backend_check_parameters_close_match():
    from reproman.resource.docker_container import DockerContainer

    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(DockerContainer, {"name": "name", "imagee": "value"})
    assert "Did you mean?" in str(exc.value)


@mark.skipif_no_docker_dependencies
def test_backend_check_parameters_missing_required():
    from reproman.resource.docker_container import DockerContainer

    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(DockerContainer, {"imagee": "value"})
    assert "Missing required" in str(exc.value)


def test_resource_manager_empty_init(tmpdir):
    inventory = op.join(str(tmpdir), "inventory.yml")
    manager = ResourceManager(inventory)
    assert not manager.inventory


def test_resource_manager_inventory_undefined():
    with pytest.raises(MissingConfigError):
        ResourceManager("")


def test_resource_manager_save(tmpdir):
    inventory = op.join(str(tmpdir), "subdir", "inventory.yml")
    manager = ResourceManager(inventory)
    manager.inventory = {
        "plain": {"name": "plain", "type": "foo-type", "id": "foo_id"},
        "with-secret": {"name": "with-secret", "type": "bar-type", "secret_access_key": "SECRET", "id": "bar_id"},
        "null-id": {"name": "null-id", "id": None, "type": "baz-type"},
    }
    manager.save_inventory()
    assert op.exists(inventory)
    with open(inventory) as fh:
        content = fh.read()
    assert "plain" in content
    assert "with-secret" in content
    assert "SECRET" not in content
    assert "null-id" not in content

    # Reload that inventory, add another item, and save again.
    manager_reborn = ResourceManager(inventory)
    manager_reborn.inventory["added"] = {"name": "added", "type": "added-type", "id": "added-id"}
    manager_reborn.save_inventory()
    with open(inventory) as fh:
        content_reread = fh.read()
    for line in content:
        assert line in content_reread
    assert "added" in content_reread


def test_get_resources_empty_resref():
    with pytest.raises(ValueError):
        ResourceManager().get_resource("")


def test_get_resources():
    manager = ResourceManager()
    manager.inventory = {
        "myshell": {"name": "myshell", "type": "shell", "id": "0-myshell-id"},
        "ambig-id0": {"name": "ambig-id0", "type": "shell", "id": "ambig-id"},
        "ambig-id1": {"name": "ambig-id1", "type": "shell", "id": "ambig-id"},
        "id-name-same": {"name": "id-name-same", "type": "shell", "id": "0-uniq-id"},
        "same-id": {"name": "same-id", "type": "shell", "id": "id-name-same"},
        "00": {"name": "00", "type": "shell", "id": "00s-id"},
        "partial-is-other": {"name": "partial-is-other", "type": "shell", "id": "00-rest-of-id"},
    }

    with pytest.raises(ResourceError):
        manager.get_resource("not there")

    resource_uniq = manager.get_resource("myshell")
    assert resource_uniq.name == "myshell"
    # We can get the same resource by ID.
    assert manager.get_resource(resource_uniq.id).name == resource_uniq.name
    # ... or by a unique partial prefix match on ID.
    assert manager.get_resource("0-m").name == resource_uniq.name

    with pytest.raises(MultipleResourceMatches):
        manager.get_resource("ambig-id")

    # We get an exception if both if there is an name-ID collision...
    with pytest.raises(MultipleResourceMatches):
        manager.get_resource("id-name-same")
    # ... but we can disambiguate with resref_type.
    assert manager.get_resource("id-name-same", "name").id == "0-uniq-id"
    assert manager.get_resource("id-name-same", "id").id == "id-name-same"

    # Ambiguous prefix match on ID:
    with pytest.raises(MultipleResourceMatches):
        manager.get_resource("0-")

    # When a name matches the partial ID match, we prefer the name.
    assert manager.get_resource("00").id == "00s-id"
    # We could do partial match on ID if we specify resref type, though.
    assert manager.get_resource("00-r", "id").id == "00-rest-of-id"

    # ... but it still must be unique.
    with pytest.raises(MultipleResourceMatches):
        assert manager.get_resource("00", "id")


def test_create_conflict():
    manager = ResourceManager()
    manager.inventory = {"already-exists": {"name": "already-exists", "type": "shell"}}
    with pytest.raises(ResourceAlreadyExistsError):
        manager.create("already-exists", "type-doesnt-matter")


def test_create_includes_config(tmpdir):
    tmpdir = str(tmpdir)
    manager = ResourceManager(op.join(tmpdir, "inventory.yml"))
    # We load items from the config.
    config_file = op.join(tmpdir, "reproman.cfg")
    with open(config_file, "w") as cfh:
        cfh.write("[ssh]\nhost = myhost\n")
    config = ConfigManager(filenames=[config_file], load_default=False)
    with patch.object(manager, "config_manager", config):
        with patch.object(manager, "factory") as factory:
            manager.create("myssh", "ssh")
            factory.assert_called_with({"host": "myhost", "name": "myssh", "type": "ssh"})


def test_get_resource_class():
    from reproman.resource.shell import Shell

    assert get_resource_class("shell") == Shell

    # If we can't find the resource, we suggest near-hits.
    with pytest.raises(ResourceError) as exc:
        get_resource_class("shll")
    assert "shell" in str(exc.value)

    # We raise a resource error if some other failure happens while trying to
    # discover resource types.
    with pytest.raises(ResourceError) as exc:

        def fail():
            raise Exception("some failure")

        with patch("reproman.resource.base.discover_types", fail):
            get_resource_class("shll")
    assert "Failed to discover" in str(exc.value)

    # We raise a resource error if we can find a module in reproman/resource/
    # but it doesn't have a corresponding resource class.
    with pytest.raises(ResourceError) as exc:
        get_resource_class("base")
    assert "Failed to find" in str(exc.value)

    # We recognize when s/_/-/ would give an existing class and provide an
    # informative error.
    with pytest.raises(ResourceError) as exc:
        get_resource_class("docker_container")
    assert "docker-container" in str(exc.value)
