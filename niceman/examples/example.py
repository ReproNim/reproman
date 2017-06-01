"""
    Example script to read a provenance file and then create the environment on the localhost.
    The provenance files in the niceman/examples directory are used for this example.
"""

# # Add current NeuroDebian and archived NeuroDebian repos.
# print '\nAdding the NeuroDebian repository to the server for %s %s ...' % (distribution['OS'], distribution['version'])
# # orchestrator.add_task('apt_repository', dict(repo='deb http://snapshot.debian.org/archive/debian/%s/ data main contrib non-free' % (create_date,)))
# orchestrator.add_task('apt_repository', dict(repo='deb http://neuro.debian.net/debian data main contrib non-free'))

# if distribution['version'] == '12.04':
#     # orchestrator.add_task('apt_repository', dict(repo='deb http://snapshot.debian.org/archive/debian/%s/ precise main' % (create_date,)))
#     orchestrator.add_task('apt_repository', dict(repo='deb http://neuro.debian.net/debian precise main contrib non-free'))
# else:
#     # orchestrator.add_task('apt_repository', dict(repo='deb http://snapshot.debian.org/archive/debian/%s/ trusty main' % (create_date,)))
#     orchestrator.add_task('apt_repository', dict(repo='deb http://neuro.debian.net/debian trusty main contrib non-free'))

# orchestrator.add_task('apt_key', dict(keyserver='hkp://pgp.mit.edu:80', id='0xA5D32F012649A5A9'))
# orchestrator.add_task('apt', dict(update_cache='yes'))

import logging
lgr = logging.getLogger('niceman.examples')


# Add packages to task list.
def get_url_for_packages(provenance):
    """Return url for every package (versioned) as specified in provenance

    It traverses passes provenance ...

    Examples
    --------

    >>> get_url_for_packages({'cmtk' : '3.2.2-1.4build1'})
    {'cmtk': 'http://example.com/cmtk_3.2.2-1.4build1.deb'}

    Parameters
    ----------
    provenance : TODO
      Provenance read from somewhere

    Returns
    -------
    dict
      package: url   for every package found in provenance

    """
    lgr.debug('Finding versioned urls for following provenance info: %s',
              str(provenance))
    return {
        package:  'http://example.com/%s_%s.deb' % (package, version)  # dpm.get_ubuntu_binary_pkg_url(package[0], package[1])
        for package, version in provenance.items()  # get_packages()
    }
    # orchestrator.add_task('apt', dict(name='%s=%s' % package))

# Run the orchestrator against the target host.
# orchestrator.run()
