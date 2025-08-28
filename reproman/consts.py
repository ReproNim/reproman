# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""reproman constants"""

# whenever to come - to be defined here

# Define a RepDigest for the testing SSH Docker container for use across
# all testing modules. Using a tag name does not guarantee the same image will
# be used over time.
TEST_SSH_DOCKER_DIGEST = (
    "rastasheep/ubuntu-sshd@sha256:918aae46c217701b5516776e0ccc9ebb93abce5ebf3efa4bfd75a842cffc4e04"
)
