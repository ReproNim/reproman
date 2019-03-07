# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test sequences of interface commands.
"""

import logging
import os
import os.path as op
import pytest

from unittest.mock import patch
import yaml

from reproman.cmdline.main import main
from reproman.cmd import Runner
from reproman.utils import swallow_logs
from reproman.resource.base import ResourceManager
from reproman.support.exceptions import CommandError


def test_create_start_stop(tmpdir):
    tmpdir = str(tmpdir)
    inventory_file = op.join(tmpdir, "inventory.yml")
    rm = ResourceManager(inventory_file)

    # Simple smoke test.  We can't easily test the effects of start/stop with
    # shell because those the start and stop methods are noops.
    with patch("reproman.interface.create.get_manager",
               return_value=rm):
        main(["create", "-t", "shell", "testshell"])

    with open(inventory_file) as ifh:
        inventory = yaml.safe_load(ifh)
    assert inventory["testshell"]["status"] == "available"

    with patch("reproman.interface.start.get_manager",
               return_value=rm):
        main(["start", "testshell"])

    with patch("reproman.interface.stop.get_manager",
               return_value=rm):
        main(["stop", "testshell"])

    with patch("reproman.interface.delete.get_manager",
               return_value=rm):
        main(["delete", "--skip-confirmation", "testshell"])

    with open(inventory_file) as ifh:
        inventory = yaml.safe_load(ifh)
    assert "testshell" not in inventory


@pytest.mark.integration
def test_create_and_start(tmpdir):
    runner = Runner()
    tmpdir = str(tmpdir)
    cfg_file = op.join(tmpdir, "custom.cfg")
    inventory_file = op.join(tmpdir, "inventory.yml")
    with open(cfg_file, "w") as cfg_fh:
        cfg_fh.write("[general]\ninventory_file = {}\n".format(inventory_file))

    def run_reproman(args):
        runner(["reproman", "--config", cfg_file] + args,
               expect_stderr=True)

    run_reproman(["create", "--resource-type=shell", "myshell"])

    with open(inventory_file) as ifh:
        dumped = ifh.read()
    assert "myshell" in dumped
    assert "id" in dumped

    # Running with a different config fails ...
    empty_cfg_file = op.join(tmpdir, "empty.cfg")
    with open(empty_cfg_file, "w"):
        pass

    with swallow_logs(new_level=logging.ERROR) as cml:
        with pytest.raises(CommandError):
            runner(["reproman", "--config", empty_cfg_file,
                    "start", "myshell"])
        if os.environ.get("REPROMAN_LOGTARGET", "stderr") == "stderr":
            assert "ResourceNotFoundError" in cml.out
    # ... but using the same config works.
    run_reproman(["start", "myshell"])
