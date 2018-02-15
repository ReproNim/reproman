# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main
from niceman.formats import Provenance

import logging

from niceman.utils import swallow_logs, swallow_outputs, make_tempfile
from niceman.tests.utils import assert_in, skip_if_no_apt_cache

from ..retrace import identify_distributions

def test_retrace(reprozip_spec2):
    """
    Test installing packages on the localhost.
    """
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['retrace',
                '--spec', reprozip_spec2,
                ]
        main(args)
        assert_in("reading spec file " + reprozip_spec2, log.lines)


def test_retrace_to_output_file(reprozip_spec2):
    with make_tempfile() as outfile:
        args = ['retrace',
                '--spec', reprozip_spec2,
                '--output-file', outfile]
        main(args)

        ## Perform a simple check of whether the output file can be
        ## loaded.
        provenance = Provenance.factory(outfile)
        assert len(provenance.get_distributions()) == 1


@skip_if_no_apt_cache
def test_retrace_normalize_paths():
    # Retrace should normalize paths before passing them to tracers.
    with swallow_outputs() as cm:
        main(["retrace", "/sbin/../sbin/iptables"])
        assert "name: debian" in cm.out


def test_retrace_loop_over_tracers():
    def get_tracer_session(protocol):
        # Test the loop logic
        class FakeTracer(object):
            _protocol = protocol
            HANDLES_DIRS = False  # ???
            def __init__(self, session):
                assert session
                self._current_protocol = self._protocol.pop(0)

            def identify_distributions(self, files):
                for item in self._current_protocol:
                    yield item

        class FakeSession(object):
            """A fake session attributes and methods of which should not
            actually be used only but isdir.
            If anything else is accessed, it means that we have some assumptions
            """
            def isdir(self, _):
                return False   # TODO: make it parametric

        return [FakeTracer], FakeSession()

    tracer_classes, session = get_tracer_session([[("TheEnvironment1", {"thefile"})]])
    dists, unknown_files = identify_distributions(["thefile"], session, tracer_classes=tracer_classes)
    assert not any(t._protocol for t in tracer_classes), "we exhausted the protocol"
    assert dists == ['TheEnvironment1']
    assert unknown_files == {"thefile"}