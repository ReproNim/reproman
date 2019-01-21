{% extends "datalad-local-run.template.sh" %}

{% block post_command %}
{{ super() }}

{% include "includes/datalad-add.template.sh" %}

{% include "includes/create-ref.template.sh" %}

{% endblock %}
