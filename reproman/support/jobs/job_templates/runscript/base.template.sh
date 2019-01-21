#!/bin/sh
{% block header %}
{% endblock %}

set -eu

echo "submitted" >"{{ meta_directory }}/status"
echo "[ReproMan] pre-command..."

{% block pre_command %}
cd "{{ working_directory }}"
{% endblock %}

echo "running" >"{{ meta_directory }}/status"
echo "[ReproMan] executing command within $PWD..."
{% block command %}
/bin/sh -c {{ shlex_quote(command_str) }} && \
    echo "succeeded" >"{{ meta_directory }}/status" || \
    echo "failed: $?" >"{{ meta_directory }}/status"
{% endblock %}


echo "[ReproMan] post-command..."
{% block post_command %}
{% endblock %}

mkdir -p "{{ root_directory }}/completed/"
touch "{{ root_directory }}/completed/{{ jobid }}"
