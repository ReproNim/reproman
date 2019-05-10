{# Inspired by and modified from dataladh-htcondor. #}

prep_stamp="$metadir/pre-finished"


{#
  Hmm, hard to use placeholders because those are absolute paths, but we want
  the archive to be relative to this working directory.
#}
find ./.reproman \( -type f -o -type l \) | \
    grep $jobid  >"$metadir/togethome"

if [ -f "$prep_stamp" ]; then
  find . \
     \( -type f -o -type l \) \
    -newer "$prep_stamp" \
    -not -wholename "./.reproman/*" \
    >>"$metadir/togethome"
fi

mkdir -p "$rootdir/outputs"

tar \
  --files-from "$metadir/togethome" \
  -cz \
  -C "$workdir" \
  -f "$rootdir/outputs/$jobid.tar.gz"
