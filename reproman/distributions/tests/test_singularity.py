# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op

import pytest

from ...cmd import Runner
from ...distributions.singularity import SingularityTracer
from ...support.external_versions import external_versions
from ...tests.skip import mark


@mark.skipif_no_network
@mark.skipif_no_singularity
@pytest.mark.xfail(
    external_versions["cmd:singularity"] >= '3',
    reason="Pulling with @hash fails with Singularity v3 (gh-406)")
def test_singularity_trace(tmpdir):
    tmpdir = str(tmpdir)
    # Download and set up singularity image file
    runner = Runner(cwd=tmpdir)
    expected_md5sum = "ed9755a0871f04db3e14971bec56a33f"
    location = 'vsoch/hello-world@' + expected_md5sum
    runner.run(['singularity', 'pull', '--name', 'img', 'shub://' + location])

    # Test tracer class
    tracer = SingularityTracer()

    for path in [op.join(tmpdir, "img"), "shub:/" + location]:
        files = [path, 'non-existent-image']
        dist, remaining_files = next(tracer.identify_distributions(files))
        img_info = dist.images[0]
        assert img_info.md5 == expected_md5sum
        assert img_info.bootstrap == 'docker'
        assert img_info.maintainer == 'vanessasaur'
        assert img_info.deffile == 'Singularity'
        assert img_info.schema_version == '1.0'
        assert img_info.build_date == '2017-10-15T12:52:56+00:00'
        assert img_info.build_size == '333MB'
        assert img_info.singularity_version == '2.4-feature-squashbuild-secbuild.g780c84d'
        assert img_info.base_image == 'ubuntu:14.04'
        assert 'non-existent-image' in remaining_files
