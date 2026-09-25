/** @odoo-module **/

import { Component, onWillStart, toRaw, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { HealthcareChart } from "./healthcare_chart";

const PERIODS = [
    { value: 30, label: "30 days" },
    { value: 90, label: "90 days" },
    { value: 365, label: "12 months" },
];

// Categorical slots in validated stacking order (CVD-safe adjacent pairs, light + dark).
const OUTCOME_TOKENS = {
    completed: "--hc-series-1",
    booked: "--hc-series-3",
    no_show: "--hc-series-2",
    cancelled: "--hc-series-4",
};
// Status tokens; every status color ships with a text label (axis, legend or table).
const RISK_TOKENS = {
    low: "--hc-good",
    medium: "--hc-warning",
    high: "--hc-serious",
    critical: "--hc-critical",
};
const BED_TOKENS = {
    occupied: "--hc-series-1",
    available: "--hc-good",
    reserved: "--hc-series-4",
    cleaning: "--hc-warning",
    maintenance: "--hc-serious",
    blocked: "--hc-neutral",
};

/** Shared Chart.js scaffolding: recessive hairline grid, tooltips, thin rounded bars. */
function baseOptions(token, { horizontal = false, stacked = false, legend = false, percent = false } = {}) {
    const grid = { color: token("--hc-grid"), drawTicks: false };
    const valueAxis = {
        stacked,
        beginAtZero: true,
        grid,
        border: { display: false },
        ticks: {
            padding: 8,
            precision: 0,
            callback: percent ? (v) => `${v}%` : undefined,
        },
        max: percent ? 100 : undefined,
    };
    const categoryAxis = {
        stacked,
        grid: { display: false },
        border: { color: token("--hc-axis") },
        ticks: { padding: 6, autoSkip: true, maxRotation: 0, color: token("--hc-ink-2") },
    };
    return {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: horizontal ? "y" : "x",
        animation: { duration: 350 },
        interaction: { mode: horizontal ? "nearest" : "index", intersect: false, axis: horizontal ? "y" : "x" },
        scales: horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis },
        plugins: {
            legend: {
                display: legend,
                position: "top",
                align: "start",
                labels: {
                    usePointStyle: true,
                    pointStyle: "rectRounded",
                    boxWidth: 10,
                    boxHeight: 10,
                    padding: 14,
                    color: token("--hc-ink-2"),
                },
            },
            tooltip: {
                backgroundColor: token("--hc-tooltip-bg"),
                titleColor: token("--hc-tooltip-ink"),
                bodyColor: token("--hc-tooltip-ink"),
                borderColor: token("--hc-border"),
                borderWidth: 1,
                padding: 10,
                cornerRadius: 8,
                boxPadding: 4,
                usePointStyle: true,
                callbacks: percent ? { label: (ctx) => ` ${ctx.dataset.label || ctx.label}: ${ctx.formattedValue}%` } : {},
            },
        },
    };
}

function barDataset(token, label, data, colorToken, { stacked = false, last = true } = {}) {
    const color = Array.isArray(colorToken) ? colorToken.map((t) => token(t)) : token(colorToken);
    return {
        label,
        data,
        backgroundColor: color,
        hoverBackgroundColor: color,
        borderColor: token("--hc-surface"),
        // 1px surface border on each touching segment = 2px gap; rounded data-end only on the outer segment.
        borderWidth: stacked ? 1 : 0,
        borderRadius: !stacked || last ? 4 : 0,
        borderSkipped: "start",
        maxBarThickness: 24,
        categoryPercentage: 0.72,
        barPercentage: 0.9,
    };
}

export class HealthcareDashboardAction extends Component {
    static template = "custom_healthcare.Dashboard";
    static components = { Layout, HealthcareChart };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.periods = PERIODS;
        this.state = useState({
            loading: true,
            periodDays: 30,
            practiceId: false,
            tableView: {},
            data: null,
        });
        onWillStart(() => this.loadDashboard());
    }

    get display() {
        return { controlPanel: {} };
    }

    async loadDashboard() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("healthcare.dashboard", "get_dashboard_data", [], {
                period_days: this.state.periodDays,
                practice_id: this.state.practiceId,
            });
        } catch (error) {
            this.notification.add("Unable to load healthcare analytics.", { type: "danger" });
            throw error;
        } finally {
            this.state.loading = false;
        }
    }

    async setPeriod(days) {
        if (this.state.periodDays !== days) {
            this.state.periodDays = days;
            await this.loadDashboard();
        }
    }

    async onPracticeChange(ev) {
        this.state.practiceId = ev.target.value ? parseInt(ev.target.value) : false;
        await this.loadDashboard();
    }

    async onRefresh() {
        await this.loadDashboard();
        this.notification.add("Analytics refreshed.", { type: "success" });
    }

    openAction(action) {
        if (action) {
            this.action.doAction(action);
        }
    }

    toggleTable(key) {
        this.state.tableView[key] = !this.state.tableView[key];
    }

    // ------------------------------------------------------------------ formatting

    fmt(value, format) {
        if (value === null || value === undefined) {
            return "–";
        }
        if (format === "pct") {
            return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
        }
        return Number(value).toLocaleString();
    }

    deltaInfo(kpi) {
        if (kpi.delta === null || kpi.delta === undefined) {
            return null;
        }
        const up = kpi.delta >= 0;
        const good = kpi.good_when === "down" ? !up : up;
        const unit = kpi.delta_unit === "pts" ? " pts" : "%";
        return {
            text: `${up ? "+" : "−"}${Math.abs(kpi.delta).toLocaleString(undefined, { maximumFractionDigits: 1 })}${unit}`,
            icon: up ? "fa-arrow-up" : "fa-arrow-down",
            cls: good ? "is-good" : "is-bad",
        };
    }

    pct(part, whole) {
        return whole ? Math.round((100 * part) / whole) : 0;
    }

    round(value) {
        return Math.round(value || 0);
    }

    sum(values) {
        return values.reduce((a, b) => a + b, 0);
    }

    get periodLabel() {
        return PERIODS.find((p) => p.value === this.state.periodDays)?.label || "";
    }

    get bedSegments() {
        const inp = this.state.data.inpatient;
        return inp.bed_status
            .filter((s) => s.value)
            .map((s) => ({ ...s, token: BED_TOKENS[s.key], width: (100 * s.value) / (inp.bed_total || 1) }));
    }

    get alertMax() {
        return Math.max(1, ...this.state.data.coordination.alerts.map((a) => a.value));
    }

    bedColor(key) {
        return `var(${BED_TOKENS[key]})`;
    }

    riskColor(key) {
        return `var(${RISK_TOKENS[key]})`;
    }

    // ------------------------------------------------------------------ chart configs

    /**
     * Chart.js instruments the arrays it receives; handing it OWL reactive proxies makes
     * every internal write re-trigger a render (infinite layout loop). Always feed raw data.
     */
    get rawData() {
        return toRaw(this.state.data);
    }

    get activityChart() {
        const activity = this.rawData.activity;
        const series = activity.series;
        return (token) => ({
            type: "bar",
            data: {
                labels: activity.labels,
                datasets: series.map((s, i) =>
                    barDataset(token, s.label, s.data, OUTCOME_TOKENS[s.key], {
                        stacked: true,
                        last: i === series.length - 1,
                    })
                ),
            },
            options: baseOptions(token, { stacked: true, legend: true }),
        });
    }

    get visitMixChart() {
        const rows = this.rawData.activity.visit_mix;
        return (token) => ({
            type: "bar",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [barDataset(token, "Appointments", rows.map((r) => r.value), "--hc-series-1")],
            },
            options: baseOptions(token, { horizontal: true }),
        });
    }

    get riskChart() {
        const rows = this.rawData.population.risk;
        return (token) => ({
            type: "bar",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [
                    barDataset(token, "Patients", rows.map((r) => r.value), rows.map((r) => RISK_TOKENS[r.key])),
                ],
            },
            options: baseOptions(token),
        });
    }

    get diseaseChart() {
        const rows = this.rawData.population.diseases;
        const parts = [
            ["on_track", "On track", "--hc-good"],
            ["at_risk", "At risk", "--hc-warning"],
            ["overdue", "Overdue", "--hc-critical"],
        ];
        return (token) => ({
            type: "bar",
            data: {
                labels: rows.map((r) => r.label),
                datasets: parts.map(([key, label, t], i) =>
                    barDataset(token, label, rows.map((r) => r[key]), t, { stacked: true, last: i === parts.length - 1 })
                ),
            },
            options: baseOptions(token, { horizontal: true, stacked: true, legend: true }),
        });
    }

    get demographicsChart() {
        const demo = this.rawData.population.demographics;
        const parts = [
            ["female", "Female", "--hc-series-1"],
            ["male", "Male", "--hc-series-2"],
            ["other", "Other / undisclosed", "--hc-series-3"],
        ];
        return (token) => ({
            type: "bar",
            data: {
                labels: demo.labels,
                datasets: parts.map(([key, label, t]) => barDataset(token, label, demo[key], t)),
            },
            options: baseOptions(token, { legend: true }),
        });
    }

    get labChart() {
        const rows = this.rawData.clinical.labs;
        return (token) => ({
            type: "bar",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [
                    barDataset(token, "Normal", rows.map((r) => r.normal), "--hc-series-1", { stacked: true, last: false }),
                    barDataset(token, "Abnormal", rows.map((r) => r.abnormal), "--hc-series-2", { stacked: true }),
                ],
            },
            options: baseOptions(token, { horizontal: true, stacked: true, legend: true }),
        });
    }

    get funnelChart() {
        const rows = this.rawData.clinical.referral_funnel;
        return (token) => ({
            type: "bar",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [barDataset(token, "Referrals reaching stage", rows.map((r) => r.value), "--hc-series-1")],
            },
            options: baseOptions(token, { horizontal: true }),
        });
    }

    get admissionChart() {
        const trend = this.rawData.inpatient.trend;
        return (token) => ({
            type: "bar",
            data: {
                labels: trend.labels,
                datasets: [
                    barDataset(token, "Admissions", trend.admitted, "--hc-series-1"),
                    barDataset(token, "Discharges", trend.discharged, "--hc-series-2"),
                ],
            },
            options: baseOptions(token, { legend: true }),
        });
    }

    /** Chart configs are rebuilt only when a new payload arrives, so UI toggles don't redraw charts. */
    get charts() {
        if (this._chartsFor !== this.rawData) {
            this._chartsFor = this.rawData;
            this._charts = {
                activity: this.activityChart,
                visitMix: this.visitMixChart,
                risk: this.riskChart,
                disease: this.diseaseChart,
                demographics: this.demographicsChart,
                labs: this.labChart,
                funnel: this.funnelChart,
                admissions: this.admissionChart,
            };
        }
        return this._charts;
    }
}

registry.category("actions").add("healthcare_dashboard", HealthcareDashboardAction);
