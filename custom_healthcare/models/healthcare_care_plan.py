# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HealthcareCarePlan(models.Model):
    _name = 'healthcare.care.plan'
    _description = 'Care Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

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
        tracking=True,
        index=True,
        check_company=True,
        ondelete='restrict',
    )
    practice_id = fields.Many2one(
        'healthcare.practice',
        required=True,
        index=True,
        check_company=True,
    )
    disease_id = fields.Many2one(
        'healthcare.disease.type',
        string='Primary Condition',
        tracking=True,
    )
    coordinator_id = fields.Many2one(
        'res.users',
        string='Care Coordinator',
        tracking=True,
        index=True,
        check_company=True,
    )
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
        index=True,
    )
    goal = fields.Text()
    compliance_rate = fields.Float(
        string='Compliance %',
        compute='_compute_compliance_rate',
        store=True,
    )
    line_ids = fields.One2many(
        'healthcare.care.plan.line',
        'care_plan_id',
        string='Care Activities',
    )
    overdue_line_count = fields.Integer(compute='_compute_overdue_line_count')

    @api.depends('line_ids.state')
    def _compute_compliance_rate(self):
        for plan in self:
            lines = plan.line_ids
            if not lines:
                plan.compliance_rate = 0.0
                continue
            done = len(lines.filtered(lambda l: l.state == 'done'))
            plan.compliance_rate = (done / len(lines)) * 100.0

    def _compute_overdue_line_count(self):
        today = fields.Date.context_today(self)
        for plan in self:
            plan.overdue_line_count = len(plan.line_ids.filtered(
                lambda l: l.state in ('pending', 'scheduled')
                and l.next_due_date
                and l.next_due_date < today
            ))

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id
            self.coordinator_id = self.patient_id.care_coordinator_id

    def action_activate(self):
        for plan in self:
            plan.state = 'active'
            plan._generate_activities()
        return True

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_view_overdue_lines(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Overdue Activities',
            'res_model': 'healthcare.care.plan.line',
            'view_mode': 'list,form',
            'domain': [
                ('care_plan_id', '=', self.id),
                ('state', 'in', ['pending', 'scheduled']),
                ('next_due_date', '<', today),
            ],
            'context': {'default_care_plan_id': self.id},
        }

    def _generate_activities(self):
        """Create mail activities for pending care-plan lines."""
        for plan in self:
            for line in plan.line_ids.filtered(lambda l: l.state == 'pending'):
                user = line.responsible_id or plan.coordinator_id or self.env.user
                deadline = line.next_due_date or fields.Date.context_today(self)
                line.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=deadline,
                    summary=line.name,
                    user_id=user.id,
                )
                line.state = 'scheduled'


class HealthcareCarePlanLine(models.Model):
    _name = 'healthcare.care.plan.line'
    _description = 'Care Plan Activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_due_date, id'

    care_plan_id = fields.Many2one(
        'healthcare.care.plan',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='care_plan_id.company_id',
        store=True,
        index=True,
    )
    name = fields.Char(required=True)
    activity_type = fields.Selection(
        [
            ('gp_review', 'GP Review'),
            ('dietician', 'Dietician'),
            ('physio', 'Physiotherapy'),
            ('lab', 'Lab Test'),
            ('medication_review', 'Medication Review'),
            ('monitoring', 'Monitoring'),
            ('coordinator_call', 'Coordinator Call'),
            ('other', 'Other'),
        ],
        default='other',
        required=True,
    )
    frequency = fields.Selection(
        [
            ('once', 'Once'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('biannual', 'Every 6 Months'),
            ('annual', 'Annual'),
        ],
        default='monthly',
        required=True,
    )
    responsible_id = fields.Many2one('res.users', string='Responsible')
    next_due_date = fields.Date(index=True)
    last_done_date = fields.Date()
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('scheduled', 'Scheduled'),
            ('done', 'Done'),
            ('skipped', 'Skipped'),
            ('overdue', 'Overdue'),
        ],
        default='pending',
        required=True,
        index=True,
    )
    notes = fields.Text()

    def action_mark_done(self):
        today = fields.Date.context_today(self)
        for line in self:
            line.last_done_date = today
            line.state = 'done'
            line.next_due_date = line._next_date_from_frequency(today)
            if line.frequency != 'once' and line.next_due_date:
                line.state = 'pending'
                line.care_plan_id._generate_activities()

    def _next_date_from_frequency(self, from_date):
        self.ensure_one()
        mapping = {
            'once': None,
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'biannual': relativedelta(months=6),
            'annual': relativedelta(years=1),
        }
        delta = mapping.get(self.frequency)
        return (from_date + delta) if delta else False
