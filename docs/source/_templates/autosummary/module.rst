{% if fullname == 'niceman.api' -%}
`{{ name }}`
=={%- for c in name %}={%- endfor %}
.. automodule:: niceman.api

.. currentmodule:: niceman.api

{% for item in members if not item.startswith('_') %}
`{{ item }}`
--{%- for c in item %}-{%- endfor %}

.. autofunction:: {{ item }}
{% endfor %}

{% else -%}
{{ fullname }}
{{ underline }}

.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :show-inheritance:
{% endif %}
