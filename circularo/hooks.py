# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "circularo"
app_title = "Circularo Integration"
app_publisher = "Circularo"
app_description = "Example integration of open source DMS to Circularo esigning platform."
app_icon = "octicon octicon-inbox"
app_color = "#4CB6E6"
app_email = "info@circularo.com"
app_version = "1.0.0"

required_apps = ['frappe']

app_include_js = [
    "assets/circularo/js/circularo_utils.js",
    "assets/circularo/js/circularo_doctype_hooks.js"
]