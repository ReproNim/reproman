"""
    Example script to read a provenance file and then create the environment on the localhost.
    The provenance files in the repronim/examples directory are used for this example.
"""

from repronim import ProvenanceParser
from debian_package_manager import DebianPackageManager
# from repronim import Orchestrator

# provenance = ProvenanceParser.factory('pipype_output.trig', format='trig')
provenance = ProvenanceParser.factory('reprozip_output.yml', format='reprozip')
# orchestrator = Orchestrator.factory('localhost', provenance)
# orchestrator = Orchestrator.factory('docker', provenance)
dpm = DebianPackageManager()


# Add NeuroDebian repository to Ubuntu server.
distribution = provenance.get_distribution()
create_date = provenance.get_create_date()
print('create_date = {}'.format(create_date))

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


# Add packages to task list.
print('\nFound the following PACKAGES:\n')
for package in provenance.get_packages():
	print '%s=%s' % package
	url = dpm.get_ubuntu_binary_pkg_url(package[0], package[1])
	print url
	# orchestrator.add_task('apt', dict(name='%s=%s' % package))

# Run the orchestrator against the target host.
# orchestrator.run()
