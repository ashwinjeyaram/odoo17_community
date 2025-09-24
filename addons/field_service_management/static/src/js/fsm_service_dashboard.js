/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class FSMServiceDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            data: {},
            loading: true,
            error: null
        });

        onWillStart(async () => {
            await this.loadDashboardData();
            this.startAutoRefresh();
        });
    }

    /**
     * Load dashboard data from server
     */
    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;

            console.log("Loading dashboard data...");
            const result = await this.rpc('/fsm/dashboard/data');
            console.log("Dashboard data result:", result);

            if (result && result.success) {
                this.state.data = result.data || {};
                console.log("Dashboard KPI data:", this.state.data);
            } else {
                this.state.error = (result && result.error) || 'Failed to load dashboard data';
                console.error("Dashboard data error:", this.state.error);
            }
        } catch (error) {
            this.state.error = error.message || 'Failed to load dashboard data';
            console.error('Dashboard data loading error:', error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Handle KPI card clicks
     */
    async onKpiCardClick(endpoint) {
        try {
            console.log("Clicking KPI card with endpoint:", endpoint);
            const action = await this.rpc(endpoint);
            console.log("Received action:", action);

            if (action && action.type) {
                // Ensure the action has all required properties
                if (!action.views && action.view_mode) {
                    action.views = action.view_mode.split(',').map(mode => [false, mode.trim()]);
                }

                await this.actionService.doAction(action);
            } else {
                console.error("Invalid action received:", action);
                this.notification.add("Invalid action received from server", {
                    type: "warning",
                });
            }
        } catch (error) {
            console.error("Error in onKpiCardClick:", error);
            this.notification.add("Error opening view: " + error.message, {
                type: "danger",
            });
        }
    }

    /**
     * Refresh dashboard data
     */
    async refreshDashboard() {
        await this.loadDashboardData();
        this.notification.add("Dashboard refreshed successfully", {
            type: "success",
        });
    }

    /**
     * Auto-refresh dashboard every 5 minutes
     */
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 300000); // 5 minutes
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    /**
     * Component lifecycle - cleanup when unmounted
     */
    willUnmount() {
        this.stopAutoRefresh();
    }
}

FSMServiceDashboard.template = "field_service_management.FSMServiceDashboardTemplate";

// Register the dashboard as a client action
console.log("Registering FSM Service Dashboard component");
registry.category("actions").add("fsm_service_dashboard", FSMServiceDashboard);
console.log("FSM Service Dashboard component registered successfully");


/**
 * Utility functions for dashboard
 */
export const FSMDashboardUtils = {
    /**
     * Format numbers for display
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },

    /**
     * Get color class based on value and thresholds
     */
    getStatusColor(value, thresholds = {}) {
        const { danger = 10, warning = 5, success = 0 } = thresholds;

        if (value >= danger) return 'danger';
        if (value >= warning) return 'warning';
        return 'success';
    },

    /**
     * Calculate percentage change
     */
    calculatePercentageChange(current, previous) {
        if (previous === 0) return current > 0 ? 100 : 0;
        return ((current - previous) / previous * 100).toFixed(1);
    }
};