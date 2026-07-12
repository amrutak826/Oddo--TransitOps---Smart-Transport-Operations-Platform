/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

export class TransitDashboard extends Component {
    static template = "transit_ops.TransitDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            vehicle: {
                total: 0,
                active: 0,
                on_trip: 0,
                maintenance: 0,
                inactive: 0,
                doc_alert: 0,
            },
            vehicleByType: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const [
                totalCount,
                activeCount,
                onTripCount,
                maintenanceCount,
                inactiveCount,
                docAlertCount,
                typeGroups,
            ] = await Promise.all([
                this.orm.searchCount("transit.vehicle", [], { context: { active_test: false } }),
                this.orm.searchCount("transit.vehicle", [["state", "=", "active"]]),
                this.orm.searchCount("transit.vehicle", [["state", "=", "on_trip"]]),
                this.orm.searchCount("transit.vehicle", [["state", "=", "maintenance"]]),
                this.orm.searchCount("transit.vehicle", [["state", "=", "inactive"]]),
                this.orm.searchCount("transit.vehicle", [["document_alert_state", "!=", "ok"]]),
                this.orm.readGroup("transit.vehicle", [], ["vehicle_type"], ["vehicle_type"]),
            ]);

            this.state.vehicle = {
                total: totalCount,
                active: activeCount,
                on_trip: onTripCount,
                maintenance: maintenanceCount,
                inactive: inactiveCount,
                doc_alert: docAlertCount,
            };
            this.state.vehicleByType = typeGroups.map((g) => ({
                label: g.vehicle_type,
                count: g.vehicle_type_count,
            }));
        } finally {
            this.state.loading = false;
        }
    }

    async openVehicles(domain = []) {
        await this.action.doAction({
            name: "Vehicles",
            type: "ir.actions.act_window",
            res_model: "transit.vehicle",
            view_mode: "list,form,kanban",
            views: [
                [false, "list"],
                [false, "form"],
                [false, "kanban"],
            ],
            domain,
            target: "current",
        });
    }

    onClickTotalVehicles() {
        this.openVehicles([]);
    }

    onClickActiveVehicles() {
        this.openVehicles([["state", "=", "active"]]);
    }

    onClickOnTripVehicles() {
        this.openVehicles([["state", "=", "on_trip"]]);
    }

    onClickMaintenanceVehicles() {
        this.openVehicles([["state", "=", "maintenance"]]);
    }

    onClickDocAlertVehicles() {
        this.openVehicles([["document_alert_state", "!=", "ok"]]);
    }
}

registry.category("actions").add("transit_dashboard", TransitDashboard);
