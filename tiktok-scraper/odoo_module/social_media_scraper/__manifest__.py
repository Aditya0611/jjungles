# -*- coding: utf-8 -*-
{
    'name': 'Social Media Trend Scraper',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'Manage social media trend scraping and analysis',
    'description': """
Social Media Trend Scraper
==========================
Manage and monitor social media trending topics from TikTok, Instagram, Twitter, and more.

Features:
---------
* Configure scraper frequency for each platform
* View trending topics dashboard
* Filter trends by platform, date, and engagement
* Monitor scraper job history
* Real-time "What's Hot Right Now" widget
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/scheduler_settings_views.xml',
        'views/social_media_trend_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'social_media_scraper/static/src/js/whats_hot_widget.js',
            'social_media_scraper/static/src/xml/whats_hot_widget.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
