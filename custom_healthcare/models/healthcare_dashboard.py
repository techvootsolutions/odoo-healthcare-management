# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HealthcareDashboard(models.TransientModel):
    _name = 'healthcare.dashboard'
    _description = 'Healthcare KPI Dashboard'
    _rec_name = 'name'

    name = fields.Char(
        default='Healthcare Dashboards',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    # Executive / Ops KPIs
    patient_count = fields.Integer(compute='_compute_kpis')
    active_practice_count = fields.Integer(compute='_compute_kpis')
    active_care_plan_count = fields.Integer(compute='_compute_kpis')
    high_risk_patient_count = fields.Integer(compute='_compute_kpis')
    open_referral_count = fields.Integer(compute='_compute_kpis')
    consultation_month_count = fields.Integer(compute='_compute_kpis')
    # Coordinator KPIs
    today_followup_count = fields.Integer(compute='_compute_kpis')
    overdue_followup_count = fields.Integer(compute='_compute_kpis')
    assigned_caseload_count = fields.Integer(compute='_compute_kpis')
    escalation_count = fields.Integer(compute='_compute_kpis')
    # Disease KPIs
    registry_count = fields.Integer(compute='_compute_kpis')
    overdue_review_count = fields.Integer(compute='_compute_kpis')
    care_gap_count = fields.Integer(compute='_compute_kpis')
    # Clinical v2 KPIs
    open_lab_count = fields.Integer(compute='_compute_kpis')
    abnormal_lab_count = fields.Integer(compute='_compute_kpis')
    active_prescription_count = fields.Integer(compute='_compute_kpis')
    allied_session_month_count = fields.Integer(compute='_compute_kpis')
    open_alert_count = fields.Integer(compute='_compute_kpis')

    @api.depends('company_id')
    def _compute_kpis(self):
        Patient = self.env['healthcare.patient']
        Practice = self.env['healthcare.practice']
        CarePlan = self.env['healthcare.care.plan']
        Referral = self.env['healthcare.referral']
        Consultation = self.env['healthcare.consultation']
        CareLine = self.env['healthcare.care.plan.line']
        Registry = self.env['healthcare.disease.registry']
        LabRequest = self.env['healthcare.lab.request']
        LabLine = self.env['healthcare.lab.request.line']
        Prescription = self.env['healthcare.prescription']
        Allied = self.env['healthcare.allied.session']
        Alert = self.env['healthcare.alert']
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        for dash in self:
            company = dash.company_id
            domain_company = [('company_id', '=', company.id)]
            dash.patient_count = Patient.search_count(domain_company)
            dash.active_practice_count = Practice.search_count(
                domain_company + [('state', '=', 'active')]
            )
            dash.active_care_plan_count = CarePlan.search_count(
                domain_company + [('state', '=', 'active')]
            )
            dash.high_risk_patient_count = Patient.search_count(
                domain_company + [('risk_level', 'in', ['high', 'critical'])]
            )
            dash.open_referral_count = Referral.search_count(
                domain_company + [('state', 'not in', ['closed', 'cancelled'])]
            )
            dash.consultation_month_count = Consultation.search_count(
                domain_company + [
                    ('consultation_date', '>=', fields.Datetime.to_datetime(month_start)),
                ]
            )
            dash.today_followup_count = CareLine.search_count([
                ('company_id', '=', company.id),
                ('next_due_date', '=', today),
                ('state', 'in', ['pending', 'scheduled', 'overdue']),
            ])
            dash.overdue_followup_count = CareLine.search_count([
                ('company_id', '=', company.id),
                ('next_due_date', '<', today),
                ('state', 'in', ['pending', 'scheduled', 'overdue']),
            ])
            dash.assigned_caseload_count = Patient.search_count([
                ('company_id', '=', company.id),
                ('care_coordinator_id', '=', self.env.user.id),
            ])
            dash.escalation_count = Patient.search_count(
                domain_company + [('risk_level', '=', 'critical')]
            )
            dash.registry_count = Registry.search_count(domain_company)
            dash.overdue_review_count = Registry.search_count(
                domain_company + [
                    ('next_review_date', '<', today),
                    ('compliance_state', '!=', 'on_track'),
                ]
            )
            dash.care_gap_count = Registry.search_count(
                domain_company + [('compliance_state', 'in', ['at_risk', 'overdue'])]
            )
            dash.open_lab_count = LabRequest.search_count(
                domain_company + [('state', 'in', ['requested', 'in_progress'])]
            )
            dash.abnormal_lab_count = LabLine.search_count(
                domain_company + [
                    ('is_abnormal', '=', True),
                    ('review_state', '=', 'pending'),
                ]
            )
            dash.active_prescription_count = Prescription.search_count(
                domain_company + [('state', '=', 'active')]
            )
            dash.allied_session_month_count = Allied.search_count(
                domain_company + [
                    ('session_date', '>=', fields.Datetime.to_datetime(month_start)),
                ]
            )
            dash.open_alert_count = Alert.search_count(
                domain_company + [('state', '=', 'open')]
            )

    @api.model
    def get_dashboard_data(self, period_days=30, practice_id=False):
        """JSON payload for the OWL healthcare dashboard client action.

        :param period_days: analysis window ending today (30 / 90 / 365)
        :param practice_id: restrict every figure to one practice (False = network)
        """
        company = self.env.company
        period_days = int(period_days or 30) if int(period_days or 30) in (30, 90, 365) else 30
        practice = self.env['healthcare.practice'].browse(int(practice_id)).exists() if practice_id else False
        # Aggregates run as sudo: every domain below is pinned to the current company (the only
        # record rule on these models), and only counts leave the server. Drill-down actions are
        # offered solely for models the user can read.

        today = fields.Date.context_today(self)
        period_start = today - timedelta(days=period_days - 1)
        prev_start = period_start - timedelta(days=period_days)
        start_dt = fields.Datetime.to_datetime(period_start)
        prev_dt = fields.Datetime.to_datetime(prev_start)
        end_dt = fields.Datetime.to_datetime(today + timedelta(days=1))

        base = [('company_id', '=', company.id)]
        scope = base + ([('practice_id', '=', practice.id)] if practice else [])
        line_scope = base + ([('care_plan_id.practice_id', '=', practice.id)] if practice else [])
        lab_line_scope = base + ([('request_id.practice_id', '=', practice.id)] if practice else [])

        Patient = self.env['healthcare.patient'].sudo()
        Practice = self.env['healthcare.practice'].sudo()
        Appointment = self.env['healthcare.appointment'].sudo()
        Consultation = self.env['healthcare.consultation'].sudo()
        CarePlan = self.env['healthcare.care.plan'].sudo()
        CareLine = self.env['healthcare.care.plan.line'].sudo()
        Registry = self.env['healthcare.disease.registry'].sudo()
        LabRequest = self.env['healthcare.lab.request'].sudo()
        LabLine = self.env['healthcare.lab.request.line'].sudo()
        Prescription = self.env['healthcare.prescription'].sudo()
        Referral = self.env['healthcare.referral'].sudo()
        Allied = self.env['healthcare.allied.session'].sudo()
        Alert = self.env['healthcare.alert'].sudo()
        Bed = self.env['healthcare.bed'].sudo()
        Admission = self.env['healthcare.admission'].sudo()

        def act(res_model, name, domain, views=('list', 'form')):
            if not self.env[res_model].has_access('read'):
                return False
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'res_model': res_model,
                'views': [[False, v] for v in views],
                'domain': domain,
            }

        def pct(part, whole):
            return round(100.0 * part / whole, 1) if whole else 0.0

        def delta(cur, prev):
            if not prev:
                return None
            return round(100.0 * (cur - prev) / prev, 1)

        def count_by(model, domain, field):
            return {
                (key.id if hasattr(key, 'id') else key): count
                for key, count in model._read_group(domain, [field], ['__count'])
            }

        # ------------------------------------------------------------ appointments
        in_period = [('start', '>=', start_dt), ('start', '<', end_dt)]
        in_prev = [('start', '>=', prev_dt), ('start', '<', start_dt)]
        appt_states = count_by(Appointment, scope + in_period, 'state')
        prev_states = count_by(Appointment, scope + in_prev, 'state')
        appts = sum(appt_states.values())
        prev_appts = sum(prev_states.values())

        def attendance(states):
            done, missed = states.get('completed', 0), states.get('no_show', 0)
            return pct(done, done + missed)

        def no_show(states):
            return pct(states.get('no_show', 0), sum(states.values()))

        attendance_rate = attendance(appt_states)
        no_show_rate = no_show(appt_states)
        upcoming = Appointment.search_count(scope + [
            ('start', '>=', end_dt),
            ('start', '<', fields.Datetime.to_datetime(today + timedelta(days=15))),
            ('state', 'in', ['requested', 'scheduled']),
        ])
        pending_requests = Appointment.search_count(scope + [('state', '=', 'requested')])

        # Trend buckets: daily for 30d, weekly for 90d, monthly for 12m
        if period_days == 30:
            buckets = [period_start + timedelta(days=i) for i in range(period_days)]
            bucket_of = lambda d: d  # noqa: E731
            bucket_label = lambda d: d.strftime('%d %b')  # noqa: E731
        elif period_days == 90:
            first = period_start - timedelta(days=period_start.weekday())
            buckets = []
            while first <= today:
                buckets.append(first)
                first += timedelta(days=7)
            bucket_of = lambda d: d - timedelta(days=d.weekday())  # noqa: E731
            bucket_label = lambda d: 'Wk ' + d.strftime('%d %b')  # noqa: E731
        else:
            first = period_start.replace(day=1)
            buckets = []
            while first <= today:
                buckets.append(first)
                first = (first + relativedelta(months=1)).replace(day=1)
            bucket_of = lambda d: d.replace(day=1)  # noqa: E731
            bucket_label = lambda d: d.strftime('%b %Y')  # noqa: E731

        outcome_keys = [
            ('completed', 'Completed', ['completed']),
            ('booked', 'Booked / Requested', ['scheduled', 'requested', 'rescheduled']),
            ('no_show', 'No-show', ['no_show']),
            ('cancelled', 'Cancelled', ['cancelled']),
        ]
        state_to_outcome = {s: key for key, _l, states in outcome_keys for s in states}
        trend = {b: dict.fromkeys([k for k, _l, _s in outcome_keys], 0) for b in buckets}
        for rec in Appointment.search_read(scope + in_period, ['start', 'state']):
            local_day = fields.Datetime.context_timestamp(self, rec['start']).date()
            bucket = bucket_of(local_day)
            if bucket in trend:
                trend[bucket][state_to_outcome.get(rec['state'], 'booked')] += 1

        type_labels = dict(Appointment._fields['appointment_type'].selection)
        type_counts = count_by(Appointment, scope + in_period, 'appointment_type')
        visit_mix = sorted(
            [{'label': type_labels.get(k, k or 'Other'), 'value': v} for k, v in type_counts.items()],
            key=lambda r: r['value'], reverse=True,
        )

        consults = Consultation.search_count(scope + [
            ('consultation_date', '>=', start_dt), ('consultation_date', '<', end_dt),
        ])
        prev_consults = Consultation.search_count(scope + [
            ('consultation_date', '>=', prev_dt), ('consultation_date', '<', start_dt),
        ])

        # ------------------------------------------------------------ population
        patient_count = Patient.search_count(scope)
        new_patients = Patient.search_count(scope + [('create_date', '>=', start_dt)])
        risk_counts = count_by(Patient, scope, 'risk_level')
        risk_rows = [
            {'key': k, 'label': label, 'value': risk_counts.get(k, 0)}
            for k, label in [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
        ]
        high_risk = risk_counts.get('high', 0) + risk_counts.get('critical', 0)

        # Registry compliance per disease (stacked)
        compliance = {}
        for disease, state, count in Registry._read_group(
            scope, ['disease_id', 'compliance_state'], ['__count'],
        ):
            row = compliance.setdefault(disease.id, {
                'label': disease.name or 'Unspecified', 'on_track': 0, 'at_risk': 0, 'overdue': 0,
            })
            row[state or 'on_track'] = row.get(state or 'on_track', 0) + count
        disease_rows = sorted(
            compliance.values(),
            key=lambda r: r['on_track'] + r['at_risk'] + r['overdue'], reverse=True,
        )
        registry_total = sum(r['on_track'] + r['at_risk'] + r['overdue'] for r in disease_rows)
        care_gaps = sum(r['at_risk'] + r['overdue'] for r in disease_rows)

        # Age band x gender
        bands = [(0, 17, '0-17'), (18, 34, '18-34'), (35, 49, '35-49'),
                 (50, 64, '50-64'), (65, 79, '65-79'), (80, 200, '80+')]
        demo = {label: {'male': 0, 'female': 0, 'other': 0} for _a, _b, label in bands}
        for rec in Patient.search_read(scope, ['date_of_birth', 'gender']):
            dob = rec['date_of_birth']
            if not dob:
                continue
            age = relativedelta(today, dob).years
            label = next(lbl for lo, hi, lbl in bands if lo <= age <= hi)
            demo[label][rec['gender'] if rec['gender'] in ('male', 'female') else 'other'] += 1

        # ------------------------------------------------------------ clinical quality
        lab_lines_period = lab_line_scope + [
            ('request_id.request_date', '>=', start_dt), ('request_id.request_date', '<', end_dt),
        ]
        lab_by_type = {}
        for test, abnormal, count in LabLine._read_group(
            lab_line_scope, ['test_type_id', 'is_abnormal'], ['__count'],
        ):
            row = lab_by_type.setdefault(test.id, {'label': test.name, 'normal': 0, 'abnormal': 0})
            row['abnormal' if abnormal else 'normal'] += count
        lab_rows = sorted(lab_by_type.values(), key=lambda r: r['normal'] + r['abnormal'], reverse=True)
        lab_total = sum(r['normal'] + r['abnormal'] for r in lab_rows)
        lab_abnormal = sum(r['abnormal'] for r in lab_rows)
        abnormal_pending = LabLine.search_count(
            lab_line_scope + [('is_abnormal', '=', True), ('review_state', '=', 'pending')]
        )
        tests_period = LabLine.search_count(lab_lines_period)
        open_labs = LabRequest.search_count(scope + [('state', 'in', ['requested', 'in_progress'])])

        ref_labels = dict(Referral._fields['state'].selection)
        ref_counts = count_by(Referral, scope, 'state')
        funnel_order = ['sent', 'accepted', 'appointment', 'feedback', 'closed']
        # Cumulative funnel: a referral at "feedback" has also passed sent/accepted/appointment
        referral_funnel = []
        for idx, key in enumerate(funnel_order):
            reached = sum(ref_counts.get(k, 0) for k in funnel_order[idx:])
            referral_funnel.append({'label': ref_labels.get(key, key), 'value': reached})
        open_referrals = sum(v for k, v in ref_counts.items() if k not in ('closed', 'cancelled'))
        spec_labels = dict(Referral._fields['specialty'].selection)
        referral_specialty = sorted(
            [{'label': spec_labels.get(k, k), 'value': v}
             for k, v in count_by(Referral, scope, 'specialty').items()],
            key=lambda r: r['value'], reverse=True,
        )
        active_rx = Prescription.search_count(scope + [('state', '=', 'active')])
        allied_period = Allied.search_count(scope + [
            ('session_date', '>=', start_dt), ('session_date', '<', end_dt),
        ])

        # ------------------------------------------------------------ inpatient
        bed_scope = base + ([('practice_id', '=', practice.id)] if practice else [])
        bed_counts = count_by(Bed, bed_scope, 'status')
        bed_total = sum(bed_counts.values())
        bed_occupied = bed_counts.get('occupied', 0)
        occupancy = pct(bed_occupied, bed_total)
        bed_status = [
            {'key': k, 'label': label, 'value': bed_counts.get(k, 0)}
            for k, label in [
                ('occupied', 'Occupied'), ('available', 'Available'), ('reserved', 'Reserved'),
                ('cleaning', 'Cleaning'), ('maintenance', 'Maintenance'), ('blocked', 'Blocked'),
            ]
        ]
        ward_rows = []
        for ward, status, count in Bed._read_group(bed_scope, ['ward_id', 'status'], ['__count']):
            row = next((r for r in ward_rows if r['id'] == ward.id), None)
            if not row:
                label = ward.name if practice else f'{ward.name} · {ward.practice_id.code or ward.practice_id.name}'
                row = {'id': ward.id, 'label': label, 'total': 0, 'occupied': 0}
                ward_rows.append(row)
            row['total'] += count
            if status == 'occupied':
                row['occupied'] += count
        for row in ward_rows:
            row['rate'] = pct(row['occupied'], row['total'])
        ward_rows.sort(key=lambda r: r['rate'], reverse=True)

        current_admissions = Admission.search(scope + [('state', '=', 'admitted')])
        discharged = Admission.search(scope + [
            ('state', '=', 'discharged'),
            ('actual_discharge_date', '>=', start_dt), ('actual_discharge_date', '<', end_dt),
        ])
        alos = round(sum(discharged.mapped('length_of_stay')) / len(discharged), 1) if discharged else 0
        inpatient_charges = sum(current_admissions.mapped('estimated_charges'))
        adm_trend = {b: {'admitted': 0, 'discharged': 0} for b in buckets}
        for rec in Admission.search_read(scope + [
            ('admission_date', '>=', start_dt), ('admission_date', '<', end_dt),
            ('state', 'in', ['admitted', 'discharged']),
        ], ['admission_date']):
            b = bucket_of(fields.Datetime.context_timestamp(self, rec['admission_date']).date())
            if b in adm_trend:
                adm_trend[b]['admitted'] += 1
        for rec in discharged.read(['actual_discharge_date']):
            b = bucket_of(fields.Datetime.context_timestamp(self, rec['actual_discharge_date']).date())
            if b in adm_trend:
                adm_trend[b]['discharged'] += 1

        # ------------------------------------------------------------ coordination
        open_line_states = ['pending', 'scheduled', 'overdue']
        overdue_domain = line_scope + [('next_due_date', '<', today), ('state', 'in', open_line_states)]
        today_domain = line_scope + [('next_due_date', '=', today), ('state', 'in', open_line_states)]
        overdue_followups = CareLine.search_count(overdue_domain)
        today_followups = CareLine.search_count(today_domain)
        done_period = CareLine.search_count(line_scope + [
            ('last_done_date', '>=', period_start), ('last_done_date', '<=', today),
        ])
        coord_rows = {}
        for user, count in CareLine._read_group(
            line_scope + [('state', 'in', open_line_states)], ['responsible_id'], ['__count'],
        ):
            coord_rows[user.id] = {'id': user.id, 'label': user.name or 'Unassigned', 'open': count,
                                   'overdue': 0, 'caseload': 0, 'high_risk': 0}
        for user, count in CareLine._read_group(overdue_domain, ['responsible_id'], ['__count']):
            if user.id in coord_rows:
                coord_rows[user.id]['overdue'] = count
        for user, risk, count in Patient._read_group(
            scope + [('care_coordinator_id', '!=', False)], ['care_coordinator_id', 'risk_level'], ['__count'],
        ):
            row = coord_rows.setdefault(user.id, {'id': user.id, 'label': user.name, 'open': 0,
                                                  'overdue': 0, 'caseload': 0, 'high_risk': 0})
            row['caseload'] += count
            if risk in ('high', 'critical'):
                row['high_risk'] += count
        coordinators = sorted(coord_rows.values(), key=lambda r: (r['overdue'], r['open']), reverse=True)[:8]
        for row in coordinators:
            row['overdue_rate'] = pct(row['overdue'], row['open'])

        alert_labels = dict(Alert._fields['alert_type'].selection)
        open_alert_domain = scope + [('state', '=', 'open')]
        alert_counts = count_by(Alert, open_alert_domain, 'alert_type')
        open_alerts = sum(alert_counts.values())
        critical_alerts = Alert.search_count(open_alert_domain + [('priority', 'in', ['2', '3'])])
        alert_rows = sorted(
            [{'key': k, 'label': alert_labels.get(k, k), 'value': v} for k, v in alert_counts.items()],
            key=lambda r: r['value'], reverse=True,
        )

        # ------------------------------------------------------------ practice benchmark
        practices = Practice.search(base + [('state', '=', 'active')] + ([('id', '=', practice.id)] if practice else []))
        practice_rows = []
        for pr in practices:
            p_dom = base + [('practice_id', '=', pr.id)]
            st = count_by(Appointment, p_dom + in_period, 'state')
            p_patients = Patient.search_count(p_dom)
            p_high = Patient.search_count(p_dom + [('risk_level', 'in', ['high', 'critical'])])
            p_beds = Bed.search_count(base + [('practice_id', '=', pr.id)])
            p_occ = Bed.search_count(base + [('practice_id', '=', pr.id), ('status', '=', 'occupied')])
            practice_rows.append({
                'id': pr.id,
                'label': pr.name,
                'code': pr.code or '',
                'patients': p_patients,
                'appointments': sum(st.values()),
                'attendance': attendance(st),
                'no_show': no_show(st),
                'high_risk': pct(p_high, p_patients),
                'overdue': CareLine.search_count(base + [
                    ('care_plan_id.practice_id', '=', pr.id),
                    ('next_due_date', '<', today), ('state', 'in', open_line_states),
                ]),
                'occupancy': pct(p_occ, p_beds) if p_beds else None,
            })
        practice_rows.sort(key=lambda r: r['patients'], reverse=True)

        # ------------------------------------------------------------ insights
        insights = []
        appt_delta = delta(appts, prev_appts)
        if appt_delta is not None:
            insights.append({
                'tone': 'good' if appt_delta >= 0 else 'warning',
                'icon': 'fa-line-chart',
                'text': f'Appointment volume is {"up" if appt_delta >= 0 else "down"} '
                        f'{abs(appt_delta):g}% versus the previous {period_days} days ({appts} vs {prev_appts}).',
            })
        if no_show_rate >= 8:
            insights.append({
                'tone': 'serious', 'icon': 'fa-user-times',
                'text': f'No-show rate is {no_show_rate:g}% - consider reminder outreach for high-risk patients.',
            })
        if disease_rows:
            worst = max(disease_rows, key=lambda r: pct(r['at_risk'] + r['overdue'],
                                                       r['on_track'] + r['at_risk'] + r['overdue']))
            worst_total = worst['on_track'] + worst['at_risk'] + worst['overdue']
            insights.append({
                'tone': 'warning', 'icon': 'fa-heartbeat',
                'text': f'{worst["label"]} has the largest care-gap share: '
                        f'{pct(worst["at_risk"] + worst["overdue"], worst_total):g}% of enrolled patients are at risk or overdue.',
            })
        if coordinators and coordinators[0]['overdue']:
            top = coordinators[0]
            insights.append({
                'tone': 'critical' if top['overdue_rate'] > 50 else 'warning', 'icon': 'fa-user-md',
                'text': f'{top["label"]} carries the most overdue follow-ups ({top["overdue"]} of {top["open"]} open).',
            })
        if bed_total:
            insights.append({
                'tone': 'critical' if occupancy >= 85 else 'good', 'icon': 'fa-bed',
                'text': f'Bed occupancy is {occupancy:g}% ({bed_occupied}/{bed_total}); '
                        f'average length of stay {alos:g} days.',
            })
        if lab_total:
            insights.append({
                'tone': 'serious' if abnormal_pending else 'good', 'icon': 'fa-flask',
                'text': f'{pct(lab_abnormal, lab_total):g}% of lab results are abnormal; '
                        f'{abnormal_pending} still await GP review.',
            })

        # ------------------------------------------------------------ assemble
        appt_domain = scope + in_period
        return {
            'title': 'Healthcare Analytics',
            'subtitle': (
                f'{practice.name if practice else company.name} · '
                f'{period_start.strftime("%d %b")} – {today.strftime("%d %b %Y")}'
            ),
            'filters': {
                'period_days': period_days,
                'practice_id': practice.id if practice else False,
                'practices': [{'id': p.id, 'name': p.name} for p in Practice.search(base + [('state', '=', 'active')])],
            },
            'kpis': [
                {
                    'key': 'patients', 'label': 'Registered patients', 'value': patient_count,
                    'format': 'int', 'icon': 'fa-users',
                    'sub': f'+{new_patients} new this period',
                    'action': act('healthcare.patient', 'Patients', scope),
                },
                {
                    'key': 'appointments', 'label': 'Appointments', 'value': appts, 'format': 'int',
                    'icon': 'fa-calendar-check-o', 'delta': appt_delta, 'good_when': 'up',
                    'sub': f'{upcoming} booked for next 14 days',
                    'action': act('healthcare.appointment', 'Appointments', appt_domain,
                                  ('list', 'calendar', 'form')),
                },
                {
                    'key': 'attendance', 'label': 'Attendance rate', 'value': attendance_rate,
                    'format': 'pct', 'icon': 'fa-check-circle',
                    'delta': round(attendance_rate - attendance(prev_states), 1) if prev_appts else None,
                    'delta_unit': 'pts', 'good_when': 'up',
                    'sub': f'No-show {no_show_rate:g}%',
                    'action': act('healthcare.appointment', 'Missed Appointments',
                                  appt_domain + [('state', '=', 'no_show')]),
                },
                {
                    'key': 'consults', 'label': 'Consultations', 'value': consults, 'format': 'int',
                    'icon': 'fa-stethoscope', 'delta': delta(consults, prev_consults), 'good_when': 'up',
                    'sub': f'{allied_period} allied sessions',
                    'action': act('healthcare.consultation', 'Consultations', scope + [
                        ('consultation_date', '>=', start_dt), ('consultation_date', '<', end_dt)]),
                },
                {
                    'key': 'occupancy', 'label': 'Bed occupancy', 'value': occupancy, 'format': 'pct',
                    'icon': 'fa-bed', 'sub': f'{bed_occupied} of {bed_total} beds · ALOS {alos:g}d',
                    'action': act('healthcare.bed', 'Bed Board', bed_scope, ('kanban', 'list', 'form')),
                },
                {
                    'key': 'alerts', 'label': 'Open CDS alerts', 'value': open_alerts, 'format': 'int',
                    'icon': 'fa-bell', 'sub': f'{critical_alerts} high / critical priority',
                    'tone': 'critical' if critical_alerts else '',
                    'action': act('healthcare.alert', 'Open CDS Alerts', open_alert_domain),
                },
            ],
            'insights': insights[:5],
            'queues': [
                {'label': "Today's follow-ups", 'value': today_followups, 'icon': 'fa-phone', 'tone': 'info',
                 'action': act('healthcare.care.plan.line', "Today's Follow-ups", today_domain)},
                {'label': 'Overdue follow-ups', 'value': overdue_followups, 'icon': 'fa-clock-o',
                 'tone': 'critical' if overdue_followups else 'good',
                 'action': act('healthcare.care.plan.line', 'Overdue Follow-ups', overdue_domain)},
                {'label': 'Appointment requests', 'value': pending_requests, 'icon': 'fa-inbox',
                 'tone': 'warning' if pending_requests else 'good',
                 'action': act('healthcare.appointment', 'Appointment Requests',
                               scope + [('state', '=', 'requested')])},
                {'label': 'Abnormal labs to review', 'value': abnormal_pending, 'icon': 'fa-flask',
                 'tone': 'serious' if abnormal_pending else 'good',
                 'action': act('healthcare.lab.request.line', 'Abnormal Labs Pending Review',
                               lab_line_scope + [('is_abnormal', '=', True), ('review_state', '=', 'pending')])},
                {'label': 'Open lab requests', 'value': open_labs, 'icon': 'fa-hourglass-half', 'tone': 'info',
                 'action': act('healthcare.lab.request', 'Open Lab Requests',
                               scope + [('state', 'in', ['requested', 'in_progress'])])},
                {'label': 'Open referrals', 'value': open_referrals, 'icon': 'fa-share-alt', 'tone': 'info',
                 'action': act('healthcare.referral', 'Open Referrals',
                               scope + [('state', 'not in', ['closed', 'cancelled'])])},
                {'label': 'Care gaps', 'value': care_gaps, 'icon': 'fa-exclamation-triangle',
                 'tone': 'warning' if care_gaps else 'good',
                 'action': act('healthcare.disease.registry', 'Care Gaps',
                               scope + [('compliance_state', 'in', ['at_risk', 'overdue'])])},
                {'label': 'Current inpatients', 'value': len(current_admissions), 'icon': 'fa-hospital-o',
                 'tone': 'info',
                 'action': act('healthcare.admission', 'Current Inpatients',
                               scope + [('state', '=', 'admitted')])},
            ],
            'activity': {
                'labels': [bucket_label(b) for b in buckets],
                'series': [
                    {'key': key, 'label': label, 'data': [trend[b][key] for b in buckets]}
                    for key, label, _s in outcome_keys
                ],
                'granularity': {30: 'day', 90: 'week', 365: 'month'}[period_days],
                'visit_mix': visit_mix,
            },
            'population': {
                'risk': risk_rows,
                'high_risk': high_risk,
                'high_risk_pct': pct(high_risk, patient_count),
                'diseases': disease_rows,
                'registry_total': registry_total,
                'care_gap_pct': pct(care_gaps, registry_total),
                'demographics': {
                    'labels': list(demo.keys()),
                    'female': [v['female'] for v in demo.values()],
                    'male': [v['male'] for v in demo.values()],
                    'other': [v['other'] for v in demo.values()],
                },
                'active_care_plans': CarePlan.search_count(scope + [('state', '=', 'active')]),
            },
            'clinical': {
                'labs': lab_rows,
                'lab_total': lab_total,
                'abnormal_pct': pct(lab_abnormal, lab_total),
                'tests_period': tests_period,
                'referral_funnel': referral_funnel,
                'referral_specialty': referral_specialty,
                'active_rx': active_rx,
            },
            'inpatient': {
                'bed_status': bed_status,
                'bed_total': bed_total,
                'occupancy': occupancy,
                'wards': ward_rows,
                'current': len(current_admissions),
                'discharged': len(discharged),
                'alos': alos,
                'charges': inpatient_charges,
                'currency': company.currency_id.symbol or '',
                'trend': {
                    'labels': [bucket_label(b) for b in buckets],
                    'admitted': [adm_trend[b]['admitted'] for b in buckets],
                    'discharged': [adm_trend[b]['discharged'] for b in buckets],
                },
            },
            'coordination': {
                'coordinators': coordinators,
                'alerts': alert_rows,
                'done_period': done_period,
                'overdue': overdue_followups,
            },
            'practices': practice_rows,
        }

    @api.model
    def action_open_dashboard(self):
        """Legacy form fallback; menu uses OWL client action."""
        return {
            'type': 'ir.actions.client',
            'tag': 'healthcare_dashboard',
            'name': 'Healthcare Dashboards',
            'target': 'current',
        }

    def action_open_patients(self):
        return self._action_open('healthcare.patient', 'Patients')

    def action_open_high_risk(self):
        return self._action_open(
            'healthcare.patient',
            'High Risk Patients',
            domain=[('risk_level', 'in', ['high', 'critical'])],
        )

    def action_open_care_plans(self):
        return self._action_open(
            'healthcare.care.plan',
            'Active Care Plans',
            domain=[('state', '=', 'active')],
        )

    def action_open_active_practices(self):
        return self._action_open(
            'healthcare.practice',
            'Active Practices',
            domain=[('state', '=', 'active')],
        )

    def action_open_consultations_month(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        return self._action_open(
            'healthcare.consultation',
            'Consultations This Month',
            domain=[('consultation_date', '>=', fields.Datetime.to_datetime(month_start))],
        )

    def action_open_today_followups(self):
        today = fields.Date.context_today(self)
        return self._action_open(
            'healthcare.care.plan.line',
            "Today's Follow-ups",
            domain=[
                ('next_due_date', '=', today),
                ('state', 'in', ['pending', 'scheduled', 'overdue']),
            ],
        )

    def action_open_caseload(self):
        return self._action_open(
            'healthcare.patient',
            'My Caseload',
            domain=[('care_coordinator_id', '=', self.env.user.id)],
        )

    def action_open_registry(self):
        return self._action_open(
            'healthcare.disease.registry',
            'Registry Entries',
        )

    def action_open_overdue_reviews(self):
        today = fields.Date.context_today(self)
        return self._action_open(
            'healthcare.disease.registry',
            'Overdue Reviews',
            domain=[
                ('next_review_date', '<', today),
                ('compliance_state', '!=', 'on_track'),
            ],
        )

    def action_open_referrals(self):
        return self._action_open(
            'healthcare.referral',
            'Open Referrals',
            domain=[('state', 'not in', ['closed', 'cancelled'])],
        )

    def action_open_overdue_followups(self):
        today = fields.Date.context_today(self)
        return self._action_open(
            'healthcare.care.plan.line',
            'Overdue Follow-ups',
            domain=[
                ('next_due_date', '<', today),
                ('state', 'in', ['pending', 'scheduled', 'overdue']),
            ],
        )

    def action_open_registry_gaps(self):
        return self._action_open(
            'healthcare.disease.registry',
            'Care Gaps',
            domain=[('compliance_state', 'in', ['at_risk', 'overdue'])],
        )

    def action_open_labs(self):
        return self._action_open(
            'healthcare.lab.request',
            'Open Lab Requests',
            domain=[('state', 'in', ['requested', 'in_progress'])],
        )

    def action_open_abnormal_labs(self):
        return self._action_open(
            'healthcare.lab.request.line',
            'Abnormal Labs Pending Review',
            domain=[('is_abnormal', '=', True), ('review_state', '=', 'pending')],
        )

    def action_open_prescriptions(self):
        return self._action_open(
            'healthcare.prescription',
            'Active Prescriptions',
            domain=[('state', '=', 'active')],
        )

    def action_open_allied_month(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        return self._action_open(
            'healthcare.allied.session',
            'Allied Sessions This Month',
            domain=[('session_date', '>=', fields.Datetime.to_datetime(month_start))],
        )

    def action_open_alerts(self):
        return self._action_open(
            'healthcare.alert',
            'Open CDS Alerts',
            domain=[('state', '=', 'open')],
        )

    def _action_open(self, model, name, domain=None):
        self.ensure_one()
        domain = list(domain or [])
        domain = [('company_id', '=', self.company_id.id)] + domain
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': domain,
        }
