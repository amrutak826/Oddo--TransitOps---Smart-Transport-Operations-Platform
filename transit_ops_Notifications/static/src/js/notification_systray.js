/** @odoo-module **/

import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const POLL_INTERVAL_MS = 30000;

export class TransitNotificationMenu extends Component {
    static template = "transit_ops.NotificationMenu";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.busService = useService("bus_service");
        this.notificationService = useService("notification");

        this.state = useState({
            notifications: [],
            unreadCount: 0,
        });

        onWillStart(async () => {
            await this.fetchNotifications();
        });

        // Real-time push: the server sends on the user's own partner channel,
        // which the bus service already listens to once `mail` is installed.
        this.busService.subscribe("transit_ops_notification", (payload) => {
            this.onNewNotification(payload);
        });
        this.busService.start();

        // Polling fallback guarantees the unread count stays correct even if
        // a push is missed (e.g. websocket reconnect window).
        this.pollingTimer = setInterval(() => this.fetchNotifications(), POLL_INTERVAL_MS);
        onWillDestroy(() => clearInterval(this.pollingTimer));
    }

    async fetchNotifications() {
        const data = await this.orm.call("transit.notification", "get_systray_notifications", [10]);
        this.state.notifications = data.notifications;
        this.state.unreadCount = data.unread_count;
    }

    onNewNotification(payload) {
        const alreadyKnown = this.state.notifications.some((n) => n.id === payload.id);
        if (!alreadyKnown) {
            this.state.notifications.unshift(payload);
            if (this.state.notifications.length > 10) {
                this.state.notifications.pop();
            }
            if (!payload.is_read) {
                this.state.unreadCount += 1;
            }
            this.notificationService.add(payload.name, {
                type: payload.severity === "danger" ? "danger" : "warning",
                title: "TransitOps Alert",
            });
        }
    }

    async onClickNotification(notif) {
        if (!notif.is_read) {
            await this.orm.call("transit.notification", "action_mark_read", [[notif.id]]);
            notif.is_read = true;
            this.state.unreadCount = Math.max(0, this.state.unreadCount - 1);
        }
        if (notif.res_model && notif.res_id) {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: notif.res_model,
                res_id: notif.res_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    async onMarkAllRead(ev) {
        ev.stopPropagation();
        await this.orm.call("transit.notification", "action_mark_all_read", []);
        await this.fetchNotifications();
    }

    async onViewAll() {
        await this.actionService.doAction("transit_ops.action_transit_notification");
    }
}

registry.category("systray").add(
    "transit_ops.NotificationMenu",
    { Component: TransitNotificationMenu },
    { sequence: 5 }
);
