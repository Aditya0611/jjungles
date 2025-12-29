{
    'name': 'Twitter Integrator',
    'version': '1.1',
    'category': 'Social Media',
    'summary': 'Integrates Twitter Scraper with Odoo Scheduler',
    'description': """
        This module provides a dedicated Scheduled Action to run the external Twitter Scraper.
        Configuration:
        - Go to Settings > System Parameters
        - Set 'twitter.scraper_path' to the directory containing main.py
    """,
    'author': 'Antigravity',
    'depends': ['base', 'base_setup'],
    'data': [
        'views/res_config_settings_views.xml',
        'data/scheduler_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
