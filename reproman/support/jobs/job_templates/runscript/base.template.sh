#!/bin/sh
{% block header %}
{% endblock %}

set -eu

jobid={{ jobid }}
subjob=$1
num_subjobs={{ num_subjobs }}

metadir={{ shlex_quote(meta_directory) }}
rootdir={{ shlex_quote(root_directory) }}
workdir={{ shlex_quote(working_directory) }}

echo "submitted" >"$metadir/status.$subjob"
echo "[ReproMan] pre-command..."

{% block pre_command %}
cd "$workdir"
{% endblock %}

echo "running" >"$metadir/status.$subjob"
echo "[ReproMan] executing command within $PWD..."
{% block command %}
/bin/sh -c {{ shlex_quote(command_str) }} && \
    echo "succeeded" >"$metadir/status.$subjob" || \
    (echo "failed: $?" >"$metadir/status.$subjob";
     mkdir -p "$metadir/failed" && touch "$metadir/failed/$subjob")
{% endblock %}


echo "[ReproMan] post-command..."
{% block post_command %}
{% endblock %}

mkdir -p "$rootdir/completed/"
touch "$rootdir/completed/$jobid"
