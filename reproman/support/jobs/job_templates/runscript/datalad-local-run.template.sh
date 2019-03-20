{% extends "base.template.sh" %}

{% block pre_command %}
{{ super() }}
{% include "includes/pre-run.template.sh" %}
{% endblock %}

{% block post_command %}
{{ super() }}
{% include "includes/post-run.template.sh" %}
{% endblock %}
