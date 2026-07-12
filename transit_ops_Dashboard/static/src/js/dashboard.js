/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TransitDashboard extends Component {
    static template = "transit_ops.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.vehicleChartRef = useRef("vehicleStatusChart");
        this.tripsChartRef = useRef("tripsChart");
        this.fuelChartRef = useRef("fuelChart");
        this.expenseChartRef = useRef("expenseChart");

        this.charts = {};

        this.state = useState({
            loading: true,
            kpis: {
                total_vehicles: 0,
                available_vehicles: 0,
                total_drivers: 0,
                trips_today: 0,
                fuel_cost_month: 0,
                maintenance_due: 0,
                monthly_expense: 0,
                currency_symbol: "",
                currency_position: "before",
            },
            charts: {
                vehicle_status: { labels: [], data: [] },
                trips: { labels: [], data: [] },
                fuel_usage: { labels: [], data: [] },
                expenses: { labels: [], data: [] },
            },
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            Object.values(this.charts).forEach((chart) => chart && chart.destroy());
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        const data = await this.orm.call("transit.dashboard", "get_dashboard_data", []);
        this.state.kpis = data.kpis;
        this.state.charts = data.charts;
        this.state.loading = false;
    }

    formatCurrency(value) {
        const symbol = this.state.kpis.currency_symbol || "";
        const position = this.state.kpis.currency_position || "before";
        const formatted = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return position === "after" ? `${formatted}\u00A0${symbol}` : `${symbol}\u00A0${formatted}`;
    }

    async onRefresh() {
        await this.loadDashboardData();
        this.renderCharts();
    }

    renderCharts() {
        if (typeof Chart === "undefined") {
            return;
        }
        const ORANGE = "#FF7A00";
        const ORANGE_LIGHT = "#FFB067";
        const GREY = "#8A8F98";
        const GRID_COLOR = "rgba(255,255,255,0.06)";
        const TEXT_COLOR = "#C9CDD3";

        Chart.defaults.color = TEXT_COLOR;
        Chart.defaults.font.family = "Inter, 'Segoe UI', Roboto, Arial, sans-serif";

        // ---- Vehicle Status Doughnut ----
        this._destroyChart("vehicleStatus");
        if (this.vehicleChartRef.el) {
            this.charts.vehicleStatus = new Chart(this.vehicleChartRef.el, {
                type: "doughnut",
                data: {
                    labels: this.state.charts.vehicle_status.labels,
                    datasets: [{
                        data: this.state.charts.vehicle_status.data,
                        backgroundColor: ["#FF7A00", "#3DA5F5", "#FFC069", "#5A5F6B"],
                        borderColor: "#1E2128",
                        borderWidth: 3,
                        hoverOffset: 6,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",
                    plugins: {
                        legend: { position: "bottom", labels: { boxWidth: 10, padding: 14 } },
                    },
                },
            });
        }

        // ---- Trips Last 7 Days Line ----
        this._destroyChart("trips");
        if (this.tripsChartRef.el) {
            this.charts.trips = new Chart(this.tripsChartRef.el, {
                type: "line",
                data: {
                    labels: this.state.charts.trips.labels,
                    datasets: [{
                        label: "Trips",
                        data: this.state.charts.trips.data,
                        borderColor: ORANGE,
                        backgroundColor: "rgba(255,122,0,0.15)",
                        tension: 0.35,
                        fill: true,
                        pointBackgroundColor: ORANGE,
                        pointRadius: 4,
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
                        y: { beginAtZero: true, grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR, precision: 0 } },
                    },
                },
            });
        }

        // ---- Fuel Usage Bar ----
        this._destroyChart("fuel");
        if (this.fuelChartRef.el) {
            this.charts.fuel = new Chart(this.fuelChartRef.el, {
                type: "bar",
                data: {
                    labels: this.state.charts.fuel_usage.labels,
                    datasets: [{
                        label: "Fuel Cost",
                        data: this.state.charts.fuel_usage.data,
                        backgroundColor: ORANGE_LIGHT,
                        borderRadius: 6,
                        maxBarThickness: 28,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: TEXT_COLOR } },
                        y: { beginAtZero: true, grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
                    },
                },
            });
        }

        // ---- Expenses by Category Polar/Bar ----
        this._destroyChart("expense");
        if (this.expenseChartRef.el) {
            this.charts.expense = new Chart(this.expenseChartRef.el, {
                type: "bar",
                data: {
                    labels: this.state.charts.expenses.labels,
                    datasets: [{
                        label: "Expenses",
                        data: this.state.charts.expenses.data,
                        backgroundColor: ["#FF7A00", "#FFC069", "#3DA5F5", "#5CD6C0", "#C9CDD3", "#5A5F6B"],
                        borderRadius: 6,
                        maxBarThickness: 28,
                    }],
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { beginAtZero: true, grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
                        y: { grid: { display: false }, ticks: { color: TEXT_COLOR } },
                    },
                },
            });
        }
    }

    _destroyChart(key) {
        if (this.charts[key]) {
            this.charts[key].destroy();
            delete this.charts[key];
        }
    }
}

registry.category("actions").add("transit_ops.dashboard", TransitDashboard);
