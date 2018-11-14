{# Send stdout/stderr to /dev/null because this stdin/stdout is dumped to files
   in .niceman and we don't want to change the content mid-add.  Note that we
   don't bother adding .niceman in a separate step because it may be added if
   the leading path includes a hidden directory.
#}

echo "Using DataLad version $(datalad --version)"  # for debugging
datalad add -m"[NICEMAN] save results for {{ jobid }}" . .niceman >/dev/null 2>&1
