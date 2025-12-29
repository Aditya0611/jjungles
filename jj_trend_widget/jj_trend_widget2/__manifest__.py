{
    "name": "JJ Trend Engine – Odoo Widget",
    "version": "16.0.1.0.0",
    "author": "Agency OS",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/trend_admin_views.xml",
        "views/trend_widget_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "jj_trend_widget2/static/src/css/trend_widget.css",
            "jj_trend_widget2/static/src/js/trend_widget.js",
        ],
    },
    "external_dependencies": {
        "python": ["requests"],
    },
    "application": False,
    "license": "LGPL-3",
}
