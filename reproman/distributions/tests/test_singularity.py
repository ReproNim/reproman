# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
import tempfile

from ...cmd import Runner
# from ...distributions.singularity import SingularityDistribution
# from ...distributions.singularity import SingularityImage
from ...distributions.singularity import SingularityTracer
from ...tests.utils import skip_if_no_singularity, skip_if_no_network


@skip_if_no_network
@skip_if_no_singularity
def test_singularity_trace():

    # Download and set up singularity image file
    runner = Runner()
    runner.run(['singularity', 'pull',
        'shub://vsoch/hello-world@42e1f04ed80217895f8c960bdde6bef4d34fab59'])
    image_file = tempfile.mktemp()
    os.rename('vsoch-hello-world-master-latest.simg', image_file)

    # Test tracer class
    tracer = SingularityTracer()

    files = [image_file, 'non-existant-image']
    dist, remaining_files = next(tracer.identify_distributions(files))

    assert dist.images[0].md5 == 'ed9755a0871f04db3e14971bec56a33f'
    assert dist.images[0].bootstrap == 'docker'
    assert dist.images[0].maintainer == 'vanessasaur'
    assert dist.images[0].deffile == 'Singularity'
    assert dist.images[0].schema_version == '1.0'
    assert dist.images[0].build_date == '2017-10-15T12:52:56+00:00'
    assert dist.images[0].build_size == '333MB'
    assert dist.images[0].singularity_version == '2.4-feature-squashbuild-secbuild.g780c84d'
    assert dist.images[0].base_image == 'ubuntu:14.04'
    assert 'non-existant-image' in remaining_files

    # Clean up test files
    os.remove(image_file)

    # Run tracer against a Singularity Hub url
    files = ['shub:/GodloveD/lolcow@a59d8de3121579fe9c95ab8af0297c2e3aefd827']
    dist, remaining_files = next(tracer.identify_distributions(files))
    assert dist.images[0].md5 == 'ee4aae1ea378ad7c0299b308c703187a'
    assert dist.images[0].bootstrap == 'docker'
    assert dist.images[0].deffile == 'Singularity'
    assert dist.images[0].schema_version == '1.0'
    assert dist.images[0].build_date == '2017-10-17T19:23:53+00:00'
    assert dist.images[0].build_size == '336MB'
    assert dist.images[0].singularity_version == '2.4-feature-squashbuild-secbuild.g217367c'
    assert dist.images[0].base_image == 'ubuntu:16.04'
    assert dist.images[0].url == 'shub://GodloveD/lolcow@a59d8de3121579fe9c95ab8af0297c2e3aefd827'
