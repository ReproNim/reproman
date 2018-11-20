{% extends "datalad-local-run.template.sh" %}

{% block post_command %}
{{ super() }}

{% include "includes/datalad-add.template.sh" %}

git update-ref refs/niceman/{{ jobid }} HEAD
{% endblock %}
