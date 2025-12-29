/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class WhatsHotWidget extends Component {
    setup() {
        super.setup();
        this.state = {
            filters: {
                platform: '',
                days: '1',
                min_score: '6.0'
            },
            loading: false
        };
        this.loadHotTrends();
    }

    async loadHotTrends() {
        this.state.loading = true;
        try {
            const trends = await this.env.services.orm.call(
                'social.media.trend',
                'get_whats_hot',
                [],
                {
                    limit: 10,
                    platform: this.state.filters.platform || false,
                    days: parseInt(this.state.filters.days) || 1,
                    min_score: parseFloat(this.state.filters.min_score) || 6.0
                }
            );
            this.trends = trends;
        } finally {
            this.state.loading = false;
            this.render();
        }
    }

    onFilterChange(ev) {
        const { name, value } = ev.target;
        this.state.filters[name] = value;
        this.loadHotTrends();
    }

    formatNumber(num) {
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(1) + 'B';
        }
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num;
    }

    getPlatformIcon(platform) {
        const icons = {
            'tiktok': '🎵',
            'instagram': '📷',
            'twitter': '🐦',
            'linkedin': '💼',
            'facebook': '👥'
        };
        return icons[platform] || '📱';
    }

    getSentimentColor(sentiment) {
        const colors = {
            'positive': 'success',
            'neutral': 'warning',
            'negative': 'danger'
        };
        return colors[sentiment] || 'secondary';
    }
}

WhatsHotWidget.template = "social_media_scraper.WhatsHotWidget";

registry.category("actions").add("whats_hot_widget", WhatsHotWidget);

export default WhatsHotWidget;
