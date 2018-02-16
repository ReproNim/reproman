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


def get_tracer_session(protocols):
    class FakeSession(object):
        """A fake session attributes and methods of which should not
        actually be used only but isdir.
        If anything else is accessed, it means that we have some assumptions
        """

        def isdir(self, _):
            return False  # TODO: make it parametric

    tracer_classes = []
    for itracer, protocol in enumerate(protocols):
        # Test the loop logic
        class FakeTracer(object):
            _protocol = protocol[:]
            HANDLES_DIRS = False  # ???

            def __init__(self, session):
                assert session
                assert self._protocol, \
                    "No more protocols to go through, but were were asked to"
                self._current_protocol = self._protocol.pop(0)

            def identify_distributions(self, files):
                for item in self._current_protocol:
                    yield item
        FakeTracer.__name__ = "FakeTracer%d" % itracer
        tracer_classes.append(FakeTracer)
    return tracer_classes, FakeSession()


def _check_loop_protocol(protocols, files, tenvs, tfiles):
    tracer_classes, session = get_tracer_session(protocols)
    dists, unknown_files = identify_distributions(
        files, session, tracer_classes=tracer_classes)
    assert not any(t._protocol for t in tracer_classes), "we exhausted the protocol"
    assert dists == tenvs
    assert unknown_files == tfiles


def test_retrace_loop_over_tracers():
    _check_loop_protocol(
        [  # Tracers
            [  # Tracer passes
                [  # what to yield
                    ("Env1", {"thefile"})
                ]
            ]
        ],
        files=["thefile"],
        tenvs=['Env1'],
        tfiles={"thefile"})

    # The 2nd tracer consumes everything
    _check_loop_protocol(
        [  # Tracers
            [  # Tracer passes
                [  # what to yield
                    ("Env1", {"thefile"})
                ],
            ],
            [  # Tracer passes
                [  # what to yield
                    ("Env2", set())
                ],
            ]
        ],
        files=["thefile"],
        tenvs=['Env1', 'Env2'],
        tfiles=set())

    # The fancy multi-yield and producing stuff
    _check_loop_protocol(
        [  # Tracers
            [  # Tracer passes
                [  # what to yield
                    ("Env1", {"file2", "file3"}),
                ],
                [
                    ("Env3", {"file3"})  # consume file4
                ],
                []  # finale
            ],
            [  # Tracer passes
                [  # what to yield
                    ("Env2", {"file3", "file4", "file5"}),
                    ("Env2.1", {"file3", "file4"})
                ],
                [

                ],
                []  # finale
            ]
        ],
        files=["file1", "file2"],
        tenvs=['Env1', 'Env2', 'Env2.1', 'Env3'],
        tfiles={'file3'})