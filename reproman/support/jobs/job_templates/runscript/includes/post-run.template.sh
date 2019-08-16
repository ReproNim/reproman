{# Inspired by and modified from dataladh-htcondor. #}

oldest_stamp () {
    find "$metadir" \
         -regex '.*/pre-finished\.[0-9]+' -printf '@%T@\n' | \
        sort | head -n1
}

prep_stamp=$(oldest_stamp)

{#
  Hmm, hard to use placeholders because those are absolute paths, but we want
  the archive to be relative to this working directory.
#}
find ./.reproman \( -type f -o -type l \) | \
    grep $jobid  >"$metadir/togethome"

if test -n "$prep_stamp"
then
  find . \
     \( -type f -o -type l \) \
    -newermt "$prep_stamp" \
    -not -wholename "./.reproman/*" \
    >>"$metadir/togethome"
fi

mkdir -p "$rootdir/outputs"

tar \
  -C "$workdir" \
  --files-from "$metadir/togethome" \
  --ignore-failed-read \
  -cz \
  -f "$rootdir/outputs/$jobid.tar.gz"
