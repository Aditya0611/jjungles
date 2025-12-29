{
    'name': 'LinkedIn Hashtag Scraper Scheduler',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Schedule and manage LinkedIn hashtag scraping runs',
    'description': """
        This module integrates the LinkedIn Hashtag Scraper with Odoo.
        It allows admins to configure scrape frequency and monitor runs
        directly from the Odoo interface.
    """,
    'author': 'Your Name',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/linkedin_scraper_views.xml',
    ],
    'installable': True,
    'application': True,
}
