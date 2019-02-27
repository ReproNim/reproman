# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from reproman.cmdline.main import main

import functools
import uuid
from unittest.mock import patch
import os
import os.path as op
import pytest

import attr

from reproman.api import execute
from reproman.formats.reproman import RepromanProvenance
from reproman.utils import swallow_outputs
from reproman.interface.execute import TracedCommand
from ...resource.base import ResourceManager
from ...tests.utils import assert_is_subset_recur
from ...tests.skip import mark
from ...tests.fixtures import get_docker_fixture
from ...consts import TEST_SSH_DOCKER_DIGEST


docker_container = get_docker_fixture(
    TEST_SSH_DOCKER_DIGEST,
    name='testing-container',
    scope='module',
    seccomp_unconfined=True
)


@mark.skipif_no_ssh
def test_execute_interface(docker_container):

    with patch('reproman.resource.ResourceManager._get_inventory') as get_inventory:
        config = {
            "status": "running",
            "engine_url": "unix:///var/run/docker.sock",
            "type": "docker-container",
            "name": "testing-container",
        }

        get_inventory.return_value = {
            "testing-container": config
        }

        for internal in [False, True]:
            path = '/tmp/{}'.format(str(uuid.uuid4()))
            cmd = ['execute', '--resource', 'testing-container']
            if internal:
                cmd.append('--internal')
            cmd.extend(['mkdir', path])

            manager = ResourceManager()
            with patch("reproman.interface.execute.get_manager",
                       return_value=manager):
                main(cmd)

                session = manager.get_resource("testing-container").get_session()
                assert session.exists(path)

                # on 2nd run mkdir should fail since already exists
                with swallow_outputs() as cmo:
                    with pytest.raises(SystemExit) as cme:
                        main(cmd)
                    assert cme.value.code == 1
                    assert "File exists" in cmo.err


def test_invalid_trace_internal():
    with pytest.raises(RuntimeError):
        execute("doesn't matter", [], internal=True, trace=True)


@pytest.fixture(scope="function")
def trace_info(tmpdir_factory):
    """Return a TracedCommand that uses temporary directories.
    """
    remote_dir = str(tmpdir_factory.mktemp("remote"))
    local_dir = str(tmpdir_factory.mktemp("local"))
    cls = functools.partial(TracedCommand,
                            remote_dir=remote_dir, local_dir=local_dir)
    return {"remote": remote_dir,
            "local": local_dir,
            "class": cls}


@mark.skipif_no_ssh
def test_trace_docker(docker_container, trace_info):
    with patch("reproman.resource.ResourceManager._get_inventory") as get_inv:
        config = {"status": "running",
                  "engine_url": "unix:///var/run/docker.sock",
                  "type": "docker-container",
                  "name": "testing-container"}
        get_inv.return_value = {"testing-container": config}
        manager = ResourceManager()
        with patch("reproman.interface.execute.get_manager",
                   return_value=ResourceManager()):
            with patch("reproman.interface.execute.CMD_CLASSES",
                       {"trace": trace_info["class"]}):
                execute("ls", ["-l"],
                        trace=True, resref="testing-container")
            # Barely more than a smoke test.  The test_trace_docker will look
            # at the generated spec.
            session = manager.get_resource("testing-container").get_session()
            assert session.exists(trace_info["remote"])
            # The tracer didn't doing anything with the local test directory:
            assert not os.listdir(trace_info["remote"])


@pytest.mark.integration
@mark.skipif_no_network
@mark.skipif_no_apt_cache
def test_trace_local(trace_info):
    with patch("reproman.resource.ResourceManager._get_inventory") as get_inv:
        config = {"status": "running",
                  "type": "shell",
                  "name": "testing-local"}
        get_inv.return_value = {"testing-local": config}
        with patch("reproman.interface.execute.get_manager",
                   return_value=ResourceManager()):
            with patch("reproman.interface.execute.CMD_CLASSES",
                       {"trace": trace_info["class"]}):
                execute("ls", ["-l"], trace=True, resref="testing-local")

    local_dir = trace_info["local"]
    assert set(os.listdir(local_dir)) == {"traces", "tracers"}
    trace_dirs = os.listdir(op.join(local_dir, "traces"))
    assert len(trace_dirs) == 1

    prov = RepromanProvenance(op.join(local_dir, "traces",
                                     trace_dirs[0], "reproman.yml"))
    deb_dists = [dist for dist in prov.get_distributions()
                 if dist.name == "debian"]
    assert len(deb_dists) == 1

    expect = {"packages": [{"files": ["/bin/ls"], "name": "coreutils"}]}
    assert_is_subset_recur(expect, attr.asdict(deb_dists[0]), [dict, list])
