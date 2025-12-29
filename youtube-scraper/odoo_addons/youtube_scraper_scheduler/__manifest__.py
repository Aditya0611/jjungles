# -*- coding: utf-8 -*-
{
    'name': "YouTube Scraper Scheduler",
    'summary': """Dynamic scheduling for YouTube Scraper""",
    'description': """
        Allows administrators to configure scraping frequency and triggers
        the YouTube scraper script via an Odoo Cron job.
    """,
    'author': "Antigravity",
    'category': 'Tools',
    'version': '1.0',
    'depends': ['base', 'base_setup'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
}
