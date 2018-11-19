#!/bin/sh
{% block header %}
{% endblock %}

set -eu

echo "submitted" >"{{ meta_directory }}/status"
echo "[NICEMAN] pre-command..."

{% block pre_command %}
cd "{{ working_directory }}"
{% endblock %}

echo "running" >"{{ meta_directory }}/status"
echo "[NICEMAN] executing command within $PWD..."
{% block command %}
/bin/sh -c {{ shlex_quote(command_str) }} && \
    echo "completed" >"{{ meta_directory }}/status" || \
    echo "failed: $?" >"{{ meta_directory }}/status"
{% endblock %}


echo "[NICEMAN] post-command..."
{% block post_command %}
{% endblock %}

echo "finished" >"{{ meta_directory }}/status"
