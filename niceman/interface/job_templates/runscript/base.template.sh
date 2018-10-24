#!/bin/sh
{% block header %}
{% endblock %}

set -eu

echo "submitted" >"{{ meta_dir }}/status"
echo "[NICEMAN] pre-command..."

{% block pre_command %}
cd "{{ remote_dir }}"
{% endblock %}

echo "running" >"{{ meta_dir }}/status"
echo "[NICEMAN] executing command within $PWD..."
{% block command %}
/bin/sh -c {{ shlex_quote(command_str) }} && \
    echo "completed" >"{{ meta_dir }}/status" || \
    echo "failed: $?" >"{{ meta_dir }}/status"
{% endblock %}


echo "[NICEMAN] post-command..."
{% block post_command %}
{% endblock %}

echo "finished" >"{{ meta_dir }}/status"
