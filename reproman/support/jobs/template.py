# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Render for orchestrator templates."""

import os.path as op
import logging

# jinja2 is imported at the point of use for faster startup

from shlex import quote as shlex_quote

lgr = logging.getLogger("reproman.support.jobs.template")


class Template(object):
    """Job templates.

    Parameters
    ----------
    **kwds
        Passed as keywords when rendering templates.
    """

    def __init__(self, **kwds):
        self.kwds = kwds

    def _render(self, template_name, subdir):
        import jinja2

        lgr.debug("Using template %s", template_name)
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader([op.join(op.dirname(__file__), "job_templates", subdir)]),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True,
        )
        env.globals["shlex_quote"] = shlex_quote
        return env.get_template(template_name).render(**self.kwds)

    def render_runscript(self, template_name):
        """Generate the run script from `template_name`.

        A run script is a wrapper around the original command and may do
        additional pre- and post-processing.

        Parameters
        ----------
        template_name : str
            Name of template to use instead of the default one for this class.

        Returns
        -------
        Rendered run script (str).
        """
        return self._render(template_name, "runscript")

    def render_submission(self, template_name):
        """Generate the submission file from `template_name`.

        A submission file is the file the will be passed to `submitter.submit`.
        It should result in the execution of the run script.

        Parameters
        ----------
        template_name : str
            Name of template to use instead of the default one for this class.

        Returns
        -------
        Rendered submission file (str).
        """
        return self._render(template_name, "submission")

    def render_cluster(self, template_name):
        """Generate the cluster file from `template_name`.

        Parameters
        ----------
        template_name : str
            Name of template to use instead of the default one for this class.

        Returns
        -------
        Rendered submission file (str).
        """
        return self._render(template_name, "cluster")
