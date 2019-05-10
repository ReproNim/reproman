#!/bin/sh
{% block header %}
{% endblock %}

set -eu

jobid={{ jobid }}
metadir={{ shlex_quote(meta_directory) }}
rootdir={{ shlex_quote(root_directory) }}
workdir={{ shlex_quote(working_directory) }}

echo "submitted" >"$metadir/status"
echo "[ReproMan] pre-command..."

{% block pre_command %}
cd "$workdir"
{% endblock %}

echo "running" >"$metadir/status"
echo "[ReproMan] executing command within $PWD..."
{% block command %}
/bin/sh -c {{ shlex_quote(command_str) }} && \
    echo "succeeded" >"$metadir/status" || \
    echo "failed: $?" >"$metadir/status"
{% endblock %}


echo "[ReproMan] post-command..."
{% block post_command %}
{% endblock %}

mkdir -p "$rootdir/completed/"
touch "$rootdir/completed/$jobid"
