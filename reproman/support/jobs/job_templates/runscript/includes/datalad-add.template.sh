{# Send stdout/stderr to /dev/null because this stdin/stdout is dumped to files
   in .reproman and we don't want to change the content mid-add.  Note that we
   don't bother adding .reproman in a separate step because it may be added if
   the leading path includes a hidden directory.
#}

echo "Using DataLad version $(datalad --version)"  # for debugging
{% if message is defined %}
msg={{ shlex_quote(message) }}
{% else %}
msg="[ReproMan] save results for {{ jobid }}"
{% endif %}
# Track these small files directly in git.
git add "{{ meta_directory }}/status" "{{ meta_directory }}/idmap"
datalad add -m"$msg" . .reproman >/dev/null 2>&1
