{
    'name': 'Instagram Scraper Manager',
    'version': '1.0',
    'category': 'Social Media',
    'summary': 'Manage Instagram Scraper and View Trends',
    'description': """
        Integrate Python Instagram Scraper with Odoo.
        - Configure Scraper Frequency
        - View Trending Hashtags
        - Schedule Jobs via Cron
    """,
    'author': 'Antigravity',
    'website': 'https://github.com/your-org/instagram-scraper',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/scraper_config_view.xml',
        'views/dashboard_view.xml',
        'views/jjungles_dashboard_inherit.xml',
    ],
    'installable': True,
    'application': True,
}
