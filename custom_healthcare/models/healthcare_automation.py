# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HealthcareAlert(models.Model):
    _name = 'healthcare.alert'
    _description = 'Clinical Decision Support Alert'
    _inherit = ['mail.thread']
    _order = 'priority desc, create_date desc'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    patient_id = fields.Many2one(
        'healthcare.patient',
        required=True,
        index=True,
        check_company=True,
        ondelete='cascade',
    )
    practice_id = fields.Many2one(
        related='patient_id.practice_id',
        store=True,
        index=True,
    )
    alert_type = fields.Selection(
        [
            ('overdue_followup', 'Overdue Follow-up'),
            ('missed_appointment', 'Missed Appointment'),
            ('care_gap', 'Care Gap'),
            ('abnormal_lab', 'Abnormal Lab'),
            ('high_risk', 'High Risk Escalation'),
            ('preventive', 'Preventive Care'),
            ('other', 'Other'),
        ],
        required=True,
        index=True,
        default='other',
    )
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Normal'),
            ('2', 'High'),
            ('3', 'Critical'),
        ],
        default='1',
        required=True,
        index=True,
    )
    state = fields.Selection(
        [
            ('open', 'Open'),
            ('acknowledged', 'Acknowledged'),
            ('resolved', 'Resolved'),
            ('cancelled', 'Cancelled'),
        ],
        default='open',
        tracking=True,
        required=True,
        index=True,
    )
    responsible_id = fields.Many2one('res.users', index=True)
    source_model = fields.Char()
    source_res_id = fields.Integer()
    notes = fields.Text()

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})

    def action_resolve(self):
        self.write({'state': 'resolved'})


class HealthcareAutomation(models.AbstractModel):
    _name = 'healthcare.automation'
    _description = 'Healthcare CDS Automation'

    @api.model
    def _cron_care_reminders_and_escalations(self):
        """Generate alerts/activities for overdue care, gaps, no-shows, high risk."""
        today = fields.Date.context_today(self)
        now = fields.Datetime.now()
        since = fields.Datetime.to_string(now - relativedelta(days=30))
        Alert = self.env['healthcare.alert']
        CareLine = self.env['healthcare.care.plan.line']
        Registry = self.env['healthcare.disease.registry']
        Appointment = self.env['healthcare.appointment']
        Patient = self.env['healthcare.patient']

        overdue_lines = CareLine.search([
            ('next_due_date', '<', today),
            ('state', 'in', ['pending', 'scheduled', 'overdue']),
        ])
        overdue_lines.write({'state': 'overdue'})
        for line in overdue_lines:
            patient = line.care_plan_id.patient_id
            user = (
                line.responsible_id
                or line.care_plan_id.coordinator_id
                or patient.care_coordinator_id
            )
            self._ensure_alert(
                Alert,
                patient=patient,
                alert_type='overdue_followup',
                name=f'Overdue care activity: {line.name}',
                priority='2',
                responsible=user,
                source=line,
                notes=f'Due date was {line.next_due_date}.',
            )
            if user:
                plan = line.care_plan_id
                summary = f'Overdue: {line.name}'
                existing = self.env['mail.activity'].search_count([
                    ('res_model', '=', plan._name),
                    ('res_id', '=', plan.id),
                    ('user_id', '=', user.id),
                    ('summary', '=', summary),
                ])
                if not existing:
                    plan.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=today,
                        summary=summary,
                        user_id=user.id,
                    )

        gap_regs = Registry.search([
            '|',
            ('next_review_date', '<', today),
            ('compliance_state', 'in', ['at_risk', 'overdue']),
        ])
        for reg in gap_regs:
            if reg.next_review_date and reg.next_review_date < today:
                reg.compliance_state = 'overdue'
            patient = reg.patient_id
            user = patient.care_coordinator_id or patient.primary_gp_id
            self._ensure_alert(
                Alert,
                patient=patient,
                alert_type='care_gap',
                name=f'Care gap: {reg.disease_id.name}',
                priority='2' if reg.risk_level in ('high', 'critical') else '1',
                responsible=user,
                source=reg,
            )

        no_shows = Appointment.search([
            ('state', '=', 'no_show'),
            ('start', '>=', since),
        ])
        for appt in no_shows:
            user = appt.patient_id.care_coordinator_id or appt.practitioner_id
            self._ensure_alert(
                Alert,
                patient=appt.patient_id,
                alert_type='missed_appointment',
                name=f'Missed appointment: {appt.appointment_type}',
                priority='2',
                responsible=user,
                source=appt,
            )

        high_risk = Patient.search([('risk_level', 'in', ['high', 'critical'])])
        for patient in high_risk:
            user = patient.care_coordinator_id or patient.primary_gp_id
            self._ensure_alert(
                Alert,
                patient=patient,
                alert_type='high_risk',
                name=f'High-risk patient monitoring: {patient.name}',
                priority='3' if patient.risk_level == 'critical' else '2',
                responsible=user,
                source=patient,
                notes=f'Clinical risk score: {patient.clinical_risk_score}',
            )

        abnormal_labs = self.env['healthcare.lab.request.line'].search([
            ('is_abnormal', '=', True),
            ('review_state', '=', 'pending'),
        ])
        for line in abnormal_labs:
            patient = line.patient_id
            user = line.request_id.requested_by_id or patient.primary_gp_id
            self._ensure_alert(
                Alert,
                patient=patient,
                alert_type='abnormal_lab',
                name=f'Abnormal lab pending review: {line.test_type_id.name}',
                priority='2',
                responsible=user,
                source=line,
                notes=f'Result: {line.result_value} {line.result_unit or ""}',
            )
        return True

    @api.model
    def _ensure_alert(self, Alert, patient, alert_type, name, priority, responsible, source, notes=False):
        domain = [
            ('patient_id', '=', patient.id),
            ('alert_type', '=', alert_type),
            ('state', '=', 'open'),
            ('source_model', '=', source._name),
            ('source_res_id', '=', source.id),
        ]
        if Alert.search_count(domain):
            return Alert.browse()
        return Alert.create({
            'name': name,
            'patient_id': patient.id,
            'company_id': patient.company_id.id,
            'alert_type': alert_type,
            'priority': priority,
            'responsible_id': responsible.id if responsible else False,
            'source_model': source._name,
            'source_res_id': source.id,
            'notes': notes,
        })
