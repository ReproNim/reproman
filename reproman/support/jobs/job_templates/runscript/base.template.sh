#!/bin/sh
{% block header %}
{% endblock %}

set -eu

jobid={{ _jobid }}
subjob=$1
num_subjobs={{ _num_subjobs }}

metadir={{ shlex_quote(_meta_directory) }}
rootdir={{ shlex_quote(root_directory) }}
workdir={{ shlex_quote(working_directory) }}

_reproman_cmd_idx=$(($subjob + 1))
export _reproman_cmd_idx

echo "submitted" >"$metadir/status.$subjob"
echo "[ReproMan] pre-command..."

{% block pre_command %}
cd "$workdir"
{% endblock %}

get_command () {
    perl -n0e \
         '$idx=$ENV{_reproman_cmd_idx}; print "$_" if $. == $idx;' \
         "$metadir/command-array"
}

cmd=$(get_command)
if test -z "$cmd"
then
    echo "[ReproMan] failed getting command at position $_reproman_cmd_idx" >&2
    echo "pre-command failure" >"$metadir/status.$subjob"
    exit 1
fi

echo "running" >"$metadir/status.$subjob"
echo "[ReproMan] executing command $cmd"
echo "[ReproMan] ... within $PWD"
{% block command %}
/bin/sh -c "$cmd" && \
    echo "succeeded" >"$metadir/status.$subjob" || \
    (echo "failed: $?" >"$metadir/status.$subjob";
     mkdir -p "$metadir/failed" && touch "$metadir/failed/$subjob")
{% endblock %}

if test $num_subjobs -eq $_reproman_cmd_idx
then
# Not all jobs should do the cleanup. Ideally none of them should and there
# should be some post-job cleanup triggered through the batch system. But, at
# least for now, below is a brittle solution were the last job waits until it
# sees that all other jobs have exited and then runs the post-command stuff.
nstatus () {
    grep -E '^(succeed|fail)' "$metadir"/status.* | wc -l
}

# Ugly, but this sleep makes it less likely for the post-command tar to fail
# complaining about a log from another run is changing.
sleep 1
while test $(nstatus) -lt $num_subjobs
do
    echo "[ReproMan] Waiting for all jobs to complete before running post-command..."
    sleep 3
done

echo "[ReproMan] post-command..."

{% block post_command %}
{% endblock %}

mkdir -p "$rootdir/completed/"
touch "$rootdir/completed/$jobid"
fi
