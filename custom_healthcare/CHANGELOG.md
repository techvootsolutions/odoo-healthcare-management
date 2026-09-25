# Changelog

All notable changes to the `custom_healthcare` module are documented here.

## [19.0.3.1.0] - 2026-07-29

- Redesigned Healthcare Dashboards as an OWL client action with KPI cards, highlights, and month charts.
- Replaced basic transient form dashboard navigation with a customer-friendly teal operations board.

## [19.0.3.0.0] - 2026-07-29

- CDS alert model with acknowledge/resolve workflow.
- Daily cron for overdue care activities, care gaps, missed appointments, high-risk and abnormal lab escalations.
- Population health SQL report (pivot/graph/list) with age band and care-gap metrics.
- Demo data seeder wizard (configurable patient volume).
- Dashboard tile for open CDS alerts.

## [19.0.2.0.0] - 2026-07-29

- Lab requests with test lines, abnormal flags, pending GP review, and activity on abnormal complete.
- Medicine catalog and prescriptions with dosage/frequency/duration and active medication sync to patient.
- Allergy keyword warning on prescriptions (block activate + clinician override).
- Allied healthcare sessions (assessment, goals, recommendations, progress, next review).
- Consultation shortcuts: Order Labs / Prescribe; referral shortcut: Allied Session.
- Dashboard KPIs for open labs, abnormal pending, active Rx, allied sessions MTD.
- Demo extended for Maria Santos lab, Rx, and dietician session.

## [19.0.1.0.0] - 2026-07-29

- Initial v1 Healthcare Operations Platform for Odoo 19.
- Practice management with CRM opportunity link for network onboarding.
- Patient registry with clinical context, risk level, and care assignment.
- Appointments, EMR-lite consultations, and referral workflow.
- Care plans with activity lines and mail activity generation on activate.
- Care coordinator menus (caseload, overdue follow-ups, high-risk patients).
- Chronic disease registry with care-gap tracking.
- Ops/clinical KPI dashboard (executive, coordinator, programme tiles).
- Demo data for the Maria Santos end-to-end care journey.
