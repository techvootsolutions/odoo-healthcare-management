/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, onWillUpdateProps, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * Read a CSS custom property from the dashboard root so charts follow the
 * light / dark tokens defined in SCSS instead of hard-coded hex values.
 */
export function cssVar(el, name, fallback = "") {
    const root = el?.closest(".hc-dash") || document.body;
    return getComputedStyle(root).getPropertyValue(name).trim() || fallback;
}

/**
 * Thin OWL wrapper around Chart.js (bundled with Odoo as web.chartjs_lib).
 * `config` is a function receiving a token getter and returning a Chart.js config,
 * so colors resolve against the live theme at render time.
 */
export class HealthcareChart extends Component {
    static template = "custom_healthcare.HealthcareChart";
    static props = {
        config: Function,
        height: { type: Number, optional: true },
        ariaLabel: { type: String, optional: true },
    };
    static defaultProps = { height: 260 };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        onWillStart(() => loadBundle("web.chartjs_lib"));
        onMounted(() => this.renderChart(this.props));
        onWillUpdateProps((nextProps) => {
            if (nextProps.config !== this.props.config) {
                this.renderChart(nextProps);
            }
        });
        onWillUnmount(() => this.chart?.destroy());
    }

    renderChart(props) {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }
        const token = (name, fallback) => cssVar(canvas, name, fallback);
        const config = props.config(token);
        const Chart = window.Chart;
        Chart.defaults.font.family = token("--hc-font", "system-ui, sans-serif");
        Chart.defaults.font.size = 12;
        Chart.defaults.color = token("--hc-muted", "#898781");
        this.chart?.destroy();
        this.chart = new Chart(canvas, config);
    }
}
