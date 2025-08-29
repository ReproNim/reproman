# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
# Test string to read

import logging
from unittest import mock
import os
import pytest
import re
import uuid
from pytest import raises

from ...support.exceptions import CommandError
from ...utils import merge_dicts
from ...utils import swallow_logs
from ...tests.utils import assert_in
from ...tests.skip import mark
from reproman.tests.fixtures import get_docker_fixture
from ...consts import TEST_SSH_DOCKER_DIGEST

# Skip entire module if no SSH is available.
pytestmark = mark.skipif_no_ssh

setup_ssh = get_docker_fixture(
    TEST_SSH_DOCKER_DIGEST,
    portmaps={49000: 22},
    custom_params={"host": "localhost", "user": "root", "port": 49000},
    scope="module",
)


def test_setup_ssh(setup_ssh):
    # Rudimentary smoke test for setup_ssh so we have
    # multiple uses for the setup_ssh
    assert "port" in setup_ssh["custom"]
    assert setup_ssh["custom"]["host"] == "localhost"


# https://github.com/ReproNim/reproman/issues/587
@pytest.mark.xfail(reason="RSA key treated as DSA", run=False)
def test_ssh_class(setup_ssh, resource_test_dir, resman):
    with swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting to test SSH server.
        # TODO: Add a test using a SSH key pair.
        config = dict(name="ssh-test-resource", type="ssh", **setup_ssh["custom"])
        resource = resman.factory(config)
        updated_config = merge_dicts(resource.create())
        config.update(updated_config)
        assert re.match(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$", resource.id) is not None
        assert resource.status == "N/A"

        # Test bad password handling.
        with mock.patch("getpass.getpass") as getpass:
            getpass.return_value = "root"
            resource.connect(password="incorrect")

        assert resource.status == "ONLINE"

        # Test running commands in a resource.
        resource.add_command(["apt-cache", "--help"])
        resource.add_command(["ls", "/"])
        resource.execute_command_buffer()

        assert_in("Running command '['apt-cache', '--help']'", log.lines)
        assert_in("Running command '['ls', '/']'", log.lines)
        # TODO: Figure out why PY3 logger is not picking up STDOUT from SSH server.

        # Test SSHSession methods
        session = resource.get_session()

        assert session.exists("/etc/hosts")
        assert session.exists("/no/such/file") is False

        # Copy this file to /root/test_ssh.py on the docker test container.
        session.put(__file__, "remote_test_ssh.py")
        assert session.exists("remote_test_ssh.py")

        tmp_path = "{}/{}".format(resource_test_dir, uuid.uuid4().hex)
        session.get("/etc/hosts", tmp_path)
        assert os.path.isfile(tmp_path)

        file_contents = session.read("remote_test_ssh.py")
        file_contents = file_contents.splitlines()
        assert file_contents[7] == "# Test string to read"

        path = "/tmp/{}".format(str(uuid.uuid4()))
        assert session.isdir(path) is False
        session.mkdir(path)
        assert session.isdir(path)

        path = "/tmp/{}/{}".format(str(uuid.uuid4()), str(uuid.uuid4()))
        assert session.isdir(path) is False
        session.mkdir(path, parents=True)
        assert session.isdir(path)

        assert not session.isdir("not-a-dir")
        assert not session.isdir("/etc/hosts")

        with raises(CommandError):
            session._execute_command("non-existent-command", cwd="/path")


# https://github.com/ReproNim/reproman/issues/587
@pytest.mark.xfail(reason="RSA key treated as DSA", run=False)
def test_ssh_resource(setup_ssh, resman):

    config = {
        "name": "ssh-test-resource",
        "type": "ssh",
        "host": "localhost",
        "user": "root",
        "port": 49000,
    }
    resource = resman.factory(config)
    resource.connect(password="root")

    with pytest.raises(NotImplementedError):
        resource.start()
    with pytest.raises(NotImplementedError):
        resource.stop()

    resource.delete()
    assert resource._connection is None

    # resource.get_session()
    # assert type(resource._transport) == paramiko.Transport
