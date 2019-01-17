# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##


from collections import OrderedDict
import logging
import pytest
from mock import patch, call, MagicMock

from niceman.api import create
from niceman.cmdline.main import main
from niceman.utils import swallow_logs
from niceman.resource.base import ResourceManager
from niceman.tests.utils import assert_in
from niceman.support.exceptions import ResourceError

from ..create import parse_backend_parameters


def test_create_interface():
    """
    Test creating an environment
    """

    with patch('docker.Client') as client, \
        patch('niceman.resource.ResourceManager._save'), \
        patch('niceman.resource.ResourceManager._get_inventory'), \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [],
            pull=lambda repository, stream: [
                b'{ "status" : "status 1", "progress" : "progress 1" }',
                b'{ "status" : "status 2", "progress" : "progress 2" }'
            ],
            create_container=lambda name, image, stdin_open, tty, command: {
                'Id': '18b31b30e3a5'
            }
        )

        args = ['create',
                '--resource-type', 'docker-container',
                '--backend', 'engine_url=tcp://127.0.0.1:2376',
                '--',
                'my-test-resource'
        ]
        with patch("niceman.interface.create.get_manager",
                   return_value=ResourceManager()):
            main(args)

        calls = [
            call(base_url='tcp://127.0.0.1:2376'),
            call().start(container='18b31b30e3a5')
        ]
        client.assert_has_calls(calls, any_order=True)

        assert_in("status 1 progress 1", log.lines)
        assert_in("status 2 progress 2", log.lines)
        assert_in("Created the environment my-test-resource", log.lines)


def test_create_missing_required():
    with pytest.raises(ResourceError) as exc:
        # SSH requires host.
        with patch("niceman.interface.create.get_manager",
                   return_value=ResourceManager()):
            create("somessh", "ssh", [])
    assert "host" in str(exc.value)


def test_parse_backend_parameters():
    for value, expected in [(["a=b"], {"a": "b"}),
                            (["a="], {"a": ""}),
                            (["a=c=d"], {"a": "c=d"}),
                            (["a-b=c d"], {"a-b": "c d"}),
                            ({"a": "c=d"}, {"a": "c=d"})]:
        assert parse_backend_parameters(value) == expected

    # We leave any mapping be, including not converting an empty mapping to an
    # empty dict.
    assert isinstance(parse_backend_parameters(OrderedDict({})),
                      OrderedDict)
