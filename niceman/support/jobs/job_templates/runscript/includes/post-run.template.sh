{# Inspired by and modified from dataladh-htcondor. #}

prep_stamp="{{ meta_directory }}/pre-finished"


{#
  Hmm, hard to use placeholders because those are absolute paths, but we want
  the archive to be relative to this working directory.
#}
find ./.niceman \( -type f -o -type l \) | \
    grep {{ jobid }}  >"{{ meta_directory }}/togethome"

if [ -f "$prep_stamp" ]; then
  find . \
     \( -type f -o -type l \) \
    -newer "$prep_stamp" \
    -not -wholename "./.niceman/*" \
    >>"{{ meta_directory }}/togethome"
fi

mkdir -p "{{ root_directory }}/outputs"

tar \
  --files-from "{{ meta_directory }}/togethome" \
  -cz \
  -C "{{ remote_directory }}" \
  -f "{{ root_directory }}/outputs/{{ jobid }}.tar.gz"

prev_commit=$(git rev-parse HEAD)

{% include "includes/datalad-add.template.sh" %}

git update-ref refs/niceman/{{ jobid }} HEAD
