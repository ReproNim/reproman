Package for creating reproducible workflow environments.

To install package:

1) Make sure you are installing on an Ubuntu 14.04 system.
2) cd into the repronim directory.
3) Source the setup.sh file. (i.e. "source setup.sh")
4) Add this line to your .bashrc:
	export PYTHONPATH="${PYTHONPATH}:/path/to/repronim"


For docker baseed environments, make sure the user who is running
the script is in the "docker" group. See: /etc/group


See repronim/examples for example scripts on spinning up environments.
