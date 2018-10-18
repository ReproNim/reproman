# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op
import pytest

from niceman.resource.base import ResourceManager
from niceman.resource.base import backend_check_parameters
from niceman.resource.shell import Shell
from niceman.resource.docker_container import DockerContainer
from niceman.support.exceptions import MissingConfigError
from niceman.support.exceptions import MultipleResourceMatches
from niceman.support.exceptions import ResourceAlreadyExistsError
from niceman.support.exceptions import ResourceError


def test_resource_manager_factory_missing_type():
    with pytest.raises(MissingConfigError):
        ResourceManager.factory({})


def test_resource_manager_factory_unkown():
    with pytest.raises(ResourceError):
        ResourceManager.factory({"type": "not really a type"})


def test_backend_check_parameters_no_known():
    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(Shell,
                                 {"name": "name",
                                  "unknown_key": "value"})
    assert "no known parameters" in str(exc.value)


def test_backend_check_parameters_nowhere_close():
    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(DockerContainer,
                                 {"name": "name",
                                  "unknown_key": "value"})
    assert "Known backend parameters" in str(exc.value)


def test_backend_check_parameters_close_match():
    with pytest.raises(ResourceError) as exc:
        backend_check_parameters(DockerContainer,
                                 {"name": "name",
                                  "imagee": "value"})
    assert "Did you mean?" in str(exc.value)


def test_backend_check_parameters_missing_required():
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
        "plain": {"name": "plain",
                  "type": "foo-type",
                  "id": "foo_id"},
        "with-secret": {"name": "with-secret",
                        "type": "bar-type",
                        "secret_access_key": "SECRET",
                        "id": "bar_id"},
        "null-id": {"name": "null-id",
                    "id": None,
                    "type": "baz-type"}}
    manager._save()
    assert op.exists(inventory)
    with open(inventory) as fh:
        content = fh.read()
    assert "plain" in content
    assert "with-secret" in content
    assert "SECRET" not in content
    assert "null-id" not in content

    # Reload that inventory, add another item, and save again.
    manager_reborn = ResourceManager(inventory)
    manager_reborn.inventory["added"] = {"name": "added",
                                         "type": "added-type",
                                         "id": "added-id"}
    manager_reborn._save()
    with open(inventory) as fh:
        content_reread = fh.read()
    for line in content:
        assert line in content_reread
    assert "added" in content_reread


def test_get_resources():
    manager = ResourceManager()
    manager.inventory = {
        "myshell": {"name": "myshell",
                    "type": "shell",
                    "id": "myshell-id"},
        "ambig-id0": {"name": "ambig-id0",
                      "type": "shell",
                      "id": "ambig-id"},
        "ambig-id1": {"name": "ambig-id1",
                      "type": "shell",
                      "id": "ambig-id"},
        "id-name-same": {"name": "id-name-same",
                         "type": "shell",
                         "id": "uniq-id"},
        "same-id": {"name": "same-id",
                    "type": "shell",
                    "id": "id-name-same"}
    }

    with pytest.raises(ResourceError):
        manager.get_resource("not there")

    resource_uniq = manager.get_resource("myshell")
    assert resource_uniq.name == "myshell"
    # We can get the same resource by ID.
    assert resource_uniq.id == "myshell-id"

    with pytest.raises(MultipleResourceMatches):
        manager.get_resource("ambig-id")

    # We get an exception if both if there is an name-ID collision...
    with pytest.raises(MultipleResourceMatches):
        manager.get_resource("id-name-same")
    # ... but we can disambiguate with resref_type.
    assert manager.get_resource("id-name-same", "name").id == "uniq-id"
    assert manager.get_resource("id-name-same", "id").id == "id-name-same"


def test_create_conflict():
    manager = ResourceManager()
    manager.inventory = {"already-exists": {"name": "already-exists",
                                            "type": "shell"}}
    with pytest.raises(ResourceAlreadyExistsError):
        manager.create("already-exists", "type-doesnt-matter")
