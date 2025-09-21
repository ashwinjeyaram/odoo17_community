/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class FSMInventoryDashboard extends Component {
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

            console.log("Loading inventory dashboard data...");
            const result = await this.rpc('/fsm/inventory/dashboard/data');
            console.log("Inventory dashboard data result:", result);

            if (result && result.success) {
                this.state.data = result.data || {};
                console.log("Inventory dashboard KPI data:", this.state.data);
            } else {
                this.state.error = (result && result.error) || 'Failed to load inventory dashboard data';
                console.error("Inventory dashboard data error:", this.state.error);
            }
        } catch (error) {
            this.state.error = error.message || 'Failed to load inventory dashboard data';
            console.error('Inventory dashboard data loading error:', error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Handle KPI card clicks
     */
    async onKpiCardClick(endpoint) {
        try {
            console.log("Clicking inventory KPI card with endpoint:", endpoint);
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
            console.error("Error in inventory onKpiCardClick:", error);
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
        this.notification.add("Inventory dashboard refreshed successfully", {
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

FSMInventoryDashboard.template = "field_service_management.FSMInventoryDashboardTemplate";

// Register the dashboard as a client action
console.log("Registering FSM Inventory Dashboard component");
registry.category("actions").add("fsm_inventory_dashboard", FSMInventoryDashboard);
console.log("FSM Inventory Dashboard component registered successfully");

/**
 * Utility functions for inventory dashboard
 */
export const FSMInventoryDashboardUtils = {
    /**
     * Format currency values
     */
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    },

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
     * Get stock status color based on levels
     */
    getStockStatusColor(available, min_stock, reorder_qty) {
        if (available <= 0) return 'danger';
        if (available < min_stock) return 'warning';
        if (available > (reorder_qty * 2)) return 'info';
        return 'success';
    },

    /**
     * Calculate stock turnover ratio color
     */
    getTurnoverColor(ratio) {
        if (ratio >= 2) return 'success';
        if (ratio >= 1) return 'warning';
        return 'danger';
    }
};