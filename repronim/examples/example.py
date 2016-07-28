"""
    Example script to read a provenance file and then create the environment on the localhost.
    The provenance files in the repronim/examples directory are used for this test.
"""

from repronim import ProvenanceParser
from repronim import Orchestrator
from repronim import Provisioner

# provenance = ProvenanceParser('pipype_output.trig', format='trig')
provenance = ProvenanceParser.factory('reprozip_output.yml', format='reprozip')
orchestrator = Orchestrator.factory('localhost')
provisioner = Provisioner.factory()

# Add NeuroDebian repository to Ubuntu server.
distribution = provenance.get_distribution()
print '\nAdding the NeuroDebian repository to the server for %s %s ...' % (distribution['OS'], distribution['version'])
provisioner.add_command('apt_repository', dict(repo='deb http://neuro.debian.net/debian data main contrib non-free'))
if distribution['version'] == '12.04':
    provisioner.add_command('apt_repository', dict(repo='deb http://neuro.debian.net/debian precise main contrib non-free'))
else:
    provisioner.add_command('apt_repository', dict(repo='deb http://neuro.debian.net/debian trusty main contrib non-free'))
provisioner.add_command('apt_key', dict(keyserver='hkp://pgp.mit.edu:80', id='0xA5D32F012649A5A9'))
provisioner.add_command('apt', dict(update_cache='yes'))

# Add packages to task list.
print '\nFound the following PACKAGES:\n'
for package in provenance.get_packages():
	print '%s=%s' % package
	provisioner.add_command('apt', dict(name='%s=%s' % package))

provisioner.run(orchestrator.get_target_host())
