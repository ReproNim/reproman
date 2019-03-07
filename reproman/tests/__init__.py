# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
import tempfile
from logging import getLogger

lgr = getLogger("reproman.tests")

# We will delay generation of some test files/directories until they are
# actually used but then would remove them here
_TEMP_PATHS_GENERATED = []

# Give a custom template so we could hunt them down easily
tempfile.template = os.path.join(tempfile.gettempdir(),
                                 'tmp-page2annex')

