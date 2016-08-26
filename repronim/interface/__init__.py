# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""High-level interface definition

"""

__docformat__ = 'restructuredtext'


# the following should be series of import definitions for interface implementations
# that shall be exposed in the Python API and the cmdline interface
# all interfaces should be associated with (at least) one of the groups below
_group_dataset = (
    'Commands for dataset operations',
    [
        # source module, source object[, dest. cmdline name[, dest python name]]
        # src module can be relative, but has to be relative to the main 'repronim' package
        ('repronim.distribution.create', 'Create'),
        ('repronim.distribution.install', 'Install'),
        ('repronim.distribution.publish', 'Publish'),
        ('repronim.distribution.uninstall', 'Uninstall'),
        # N/I ATM
        # ('repronim.distribution.move', 'Move'),
        ('repronim.distribution.update', 'Update'),
        ('repronim.distribution.create_publication_target_sshwebserver',
         'CreatePublicationTargetSSHWebserver',
         'create-publication-target-sshwebserver'),
        ('repronim.distribution.add_sibling', 'AddSibling', 'add-sibling'),
        ('repronim.distribution.modify_subdataset_urls', 'ModifySubdatasetURLs',
         'modify-subdataset-urls'),
        ('repronim.interface.unlock', 'Unlock', 'unlock'),
        ('repronim.interface.save', 'Save', 'save'),
    ])

_group_misc = (
    'Miscellaneous commands',
    [
        ('repronim.interface.test', 'Test'),
        ('repronim.interface.crawl', 'Crawl'),
        ('repronim.interface.crawl_init', 'CrawlInit', 'crawl-init'),
        ('repronim.interface.ls', 'Ls'),
        ('repronim.interface.clean', 'Clean'),
        ('repronim.interface.add_archive_content', 'AddArchiveContent',
         'add-archive-content'),
        ('repronim.interface.download_url', 'DownloadURL', 'download-url'),
        # very optional ones
        ('repronim.distribution.create_test_dataset', 'CreateTestDataset',
         'create-test-dataset'),
    ])
