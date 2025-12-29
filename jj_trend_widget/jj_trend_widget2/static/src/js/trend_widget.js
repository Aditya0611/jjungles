/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml } from "@odoo/owl";

class TrendAdminView extends Component {
    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            loading: true,
            trends: [],
            platform: "",
            hashtag: "",
            minEngagement: "",
            dateFrom: "",
            dateTo: "",
        });
        this.loadTrends();
    }

    async loadTrends() {
        this.state.loading = true;
        const params = {
            platform: this.state.platform || null,
            hashtag: this.state.hashtag || null,
            date_from: this.state.dateFrom || null,
            date_to: this.state.dateTo || null,
            min_engagement: this.state.minEngagement || null,
        };
        try {
            const result = await this.rpc("/jj_trend/fetch", params);
            this.state.trends = result.trends;
        } catch (e) {
            console.error("Error loading trends:", e);
            this.state.trends = [];
        }
        this.state.loading = false;
    }

    onFilterChange(ev) {
        const { name, value } = ev.target;
        this.state[name] = value;
    }

    onApplyFilters() {
        this.loadTrends();
    }
}
TrendAdminView.template = xml`
    <div class="o_jj_scroll_container">
        <div class="o_jj_trend_admin_view p-3">
            <div class="o_filters d-flex mb-3 gap-2">
                <select class="form-select" t-att-name="'platform'" t-on-change="onFilterChange">
                    <option value="">All Platforms</option>
                    <option value="facebook">Facebook</option>
                    <option value="instagram">Instagram</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="tiktok">TikTok</option>
                    <option value="twitter">Twitter/X</option>
                    <option value="youtube">YouTube</option>
                </select>
                <input type="text" class="form-control" t-att-name="'hashtag'"
                       placeholder="Hashtag/Topic"
                       t-on-change="onFilterChange"/>
                <input type="date" class="form-control" t-att-name="'dateFrom'" t-on-change="onFilterChange"/>
                <input type="date" class="form-control" t-att-name="'dateTo'" t-on-change="onFilterChange"/>
                <input type="number" class="form-control" t-att-name="'minEngagement'"
                       placeholder="Min Engagement"
                       t-on-change="onFilterChange"/>
                <button class="btn btn-primary" t-on-click="onApplyFilters">Apply</button>
            </div>

            <t t-if="state.loading">
                <p>Loading…</p>
            </t>
            <t t-else="">
                <t t-if="state.trends.length === 0">
                    <div class="alert alert-info">
                        <p>No trends found. Try adjusting your filters or ensure data exists in Supabase.</p>
                    </div>
                </t>
                <t t-else="">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Platform</th>
                                <th>Title</th>
                                <th>Engagement Score</th>
                                <th>Timestamp</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-foreach="state.trends" t-as="trend" t-key="trend.id + '_' + trend_index">
                                <tr>
                                    <td><t t-esc="trend.platform"/></td>
                                    <td><t t-esc="trend.title"/></td>
                                    <td><t t-esc="trend.engagement_score"/></td>
                                    <td><t t-esc="trend.timestamp"/></td>
                                    <td>
                                        <a t-att-href="trend.url" target="_blank" class="btn btn-sm btn-link">View</a>
                                    </td>
                                </tr>
                            </t>
                        </tbody>
                    </table>
                </t>
            </t>
        </div>
    </div>
`;

registry.category("actions").add("jj_trend_admin_view", TrendAdminView);

class TrendHotNow extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            loading: true,
            trends: [],
            platform: "",
            hashtag: "",
            minEngagement: "",
            dateFrom: "",
            dateTo: "",
        });
        this.loadTrends();
    }

    async loadTrends() {
        this.state.loading = true;
        const params = {
            top_n: 3,
            platform: this.state.platform || null,
            hashtag: this.state.hashtag || null,
            date_from: this.state.dateFrom || null,
            date_to: this.state.dateTo || null,
            min_engagement: this.state.minEngagement || null,
        };
        try {
            const result = await this.rpc("/jj_trend/fetch_top_per_platform", params);
            this.state.trends = result.trends;
        } catch (e) {
            console.error("Error loading trends:", e);
            this.state.trends = [];
        }
        this.state.loading = false;
    }

    onFilterChange(ev) {
        const { name, value } = ev.target;
        this.state[name] = value;
    }

    onApplyFilters() {
        this.loadTrends();
    }
}
TrendHotNow.template = xml`
    <div class="o_jj_scroll_container">
        <div class="o_jj_trend_hot_now p-3">
            <h2>What's Hot Right Now</h2>
            <p class="text-muted">Top 3 trending hashtags from each platform (TikTok, LinkedIn, Twitter, Facebook, YouTube, Instagram)</p>

            <div class="o_filters d-flex mb-3 gap-2">
                <select class="form-select" t-att-name="'platform'" t-on-change="onFilterChange">
                    <option value="">All Platforms</option>
                    <option value="facebook">Facebook</option>
                    <option value="instagram">Instagram</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="tiktok">TikTok</option>
                    <option value="twitter">Twitter/X</option>
                    <option value="youtube">YouTube</option>
                </select>
                <input type="text" class="form-control" t-att-name="'hashtag'"
                       placeholder="Hashtag/Topic"
                       t-on-change="onFilterChange"/>
                <input type="date" class="form-control" t-att-name="'dateFrom'" t-on-change="onFilterChange"/>
                <input type="date" class="form-control" t-att-name="'dateTo'" t-on-change="onFilterChange"/>
                <input type="number" class="form-control" t-att-name="'minEngagement'"
                       placeholder="Min Engagement"
                       t-on-change="onFilterChange"/>
                <button class="btn btn-primary" t-on-click="onApplyFilters">Apply</button>
            </div>

            <t t-if="state.loading">
                <p>Loading trends…</p>
            </t>
            <t t-else="">
                <t t-if="state.trends.length === 0">
                    <div class="alert alert-info">
                        <p>No trends found. Ensure data exists in Supabase.</p>
                    </div>
                </t>
                <t t-else="">
                    <div class="o_trend_cards d-flex flex-wrap gap-3 justify-content-center">
                        <t t-foreach="state.trends" t-as="trend" t-key="trend.id + '_' + trend_index">
                            <div class="o_trend_card p-4 border rounded shadow-sm" style="width: 350px;">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <span class="badge bg-info"><t t-esc="trend.platform"/></span>
                                    <span class="badge bg-success">🔥 Trending</span>
                                </div>
                                <div class="o_trend_title fw-bold mb-3" style="font-size: 1.2rem;">
                                    <t t-esc="trend.title"/>
                                </div>
                                <div class="o_trend_meta small text-muted mb-3">
                                    <strong>Engagement Score:</strong> <t t-esc="trend.engagement_score"/>
                                    <br/>
                                    <strong>Date:</strong> <t t-esc="trend.timestamp"/>
                                </div>
                                <a t-att-href="trend.url" target="_blank" class="btn btn-primary w-100">View Post</a>
                            </div>
                        </t>
                    </div>
                </t>
            </t>
        </div>
    </div>
`;
registry.category("actions").add("jj_trend_hot_now", TrendHotNow);
