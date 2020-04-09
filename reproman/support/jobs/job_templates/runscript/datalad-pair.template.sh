{% extends "base.template.sh" %}

{% block post_command %}

{% include "includes/datalad-save.template.sh" %}

{% include "includes/create-ref.template.sh" %}

{% endblock %}
