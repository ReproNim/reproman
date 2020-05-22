#!/bin/bash
{% block header %}
{% endblock %}

set -eu

export PS4='> $(date +%T.%N) [$$] '
set -x

jobid={{ _jobid }}
subjob=$1
num_subjobs={{ _num_subjobs }}

metadir={{ shlex_quote(_meta_directory) }}
rootdir={{ shlex_quote(root_directory) }}
workdir={{ shlex_quote(working_directory) }}

_reproman_cmd_idx=$(($subjob + 1))
export _reproman_cmd_idx

printf_nobuff () {
    stdbuf -o0 printf "$@"
}

printf_nobuff "submitted\n" >"$metadir/status.$subjob"
printf_nobuff "[ReproMan] pre-command...\n"

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
    printf_nobuff "[ReproMan] failed getting command at position $_reproman_cmd_idx\n" >&2
    printf_nobuff "pre-command failure\n" >"$metadir/status.$subjob"
    exit 1
fi

printf_nobuff "running\n" >"$metadir/status.$subjob"
printf_nobuff "[ReproMan] executing command %s" "$cmd"
printf_nobuff "[ReproMan] ... within %s" "$PWD"
{% block command %}
/bin/sh -c "$cmd" && \
    printf_nobuff "succeeded\n" >"$metadir/status.$subjob" || \
    (printf_nobuff "failed: $?\n" >"$metadir/status.$subjob";
     mkdir -p "$metadir/failed" && touch "$metadir/failed/$subjob")
{% endblock %}

if test $num_subjobs -eq $_reproman_cmd_idx
then
# Not all jobs should do the cleanup. Ideally none of them should and there
# should be some post-job cleanup triggered through the batch system. But, at
# least for now, below is a brittle solution were the last job waits until it
# sees that all other jobs have exited and then runs the post-command stuff.
nstatus () {
    find "$metadir" -regex '.*/status\.[0-9][0-9]*' | wc -l
}

# Ugly, but this sleep makes it less likely for the post-command tar to fail
# complaining about a log from another run is changing.
sleep 1
while test $(nstatus) -lt $num_subjobs
do
    printf_nobuff "[ReproMan] Waiting for all jobs to complete before running post-command...\n"
    sleep 3
done

printf_nobuff "[ReproMan] post-command...\n"

# PS4 goes to stderr which we might be saving in the post_command, so we must stop
set +x

{% block post_command %}
{% endblock %}

mkdir -p "$rootdir/completed/"
touch "$rootdir/completed/$jobid"
fi
