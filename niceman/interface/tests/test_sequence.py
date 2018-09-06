# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test sequences of interface commands.
"""

import logging
import os
import os.path as op
import pytest

from niceman.cmd import Runner
from niceman.support.exceptions import CommandError
from niceman.tests.utils import swallow_logs


@pytest.mark.integration
def test_create_and_start(tmpdir):
    runner = Runner()
    tmpdir = str(tmpdir)
    cfg_file = op.join(tmpdir, "custom.cfg")
    inventory_file = op.join(tmpdir, "inventory.yml")
    with open(cfg_file, "w") as cfg_fh:
        cfg_fh.write("[general]\ninventory_file = {}\n".format(inventory_file))

    def run_niceman(args):
        runner(["niceman", "--config", cfg_file] + args,
               expect_stderr=True)

    run_niceman(["create", "--resource-type=shell", "myshell"])

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
            runner(["niceman", "--config", empty_cfg_file,
                    "start", "myshell"])
        if os.environ.get("NICEMAN_LOGTARGET", "stderr") == "stderr":
            assert "ResourceNotFoundError" in cml.out
    # ... but using the same config works.
    run_niceman(["start", "myshell"])
