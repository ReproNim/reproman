{% extends "datalad-local-run.template.sh" %}

{% block post_command %}
{{ super() }}

prev_commit=$(git rev-parse HEAD)

{% include "includes/datalad-save.template.sh" %}

{% include "includes/create-ref.template.sh" %}

if test -z "$(git status --untracked-files=normal --ignore-submodules=none --porcelain)"
then
    git reset --hard $prev_commit
else
    printf_nobuff "[ReproMan] Remote repository is unexpectedly dirty\n" >&2
    git status
fi


{% endblock %}
