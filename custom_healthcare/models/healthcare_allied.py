# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareAlliedSession(models.Model):
    _name = 'healthcare.allied.session'
    _description = 'Allied Healthcare Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'session_date desc, id desc'

    name = fields.Char(compute='_compute_name', store=True)
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
    referral_id = fields.Many2one(
        'healthcare.referral',
        check_company=True,
    )
    care_plan_id = fields.Many2one(
        'healthcare.care.plan',
        check_company=True,
    )
    specialty = fields.Selection(
        [
            ('dietician', 'Dietician'),
            ('physiotherapist', 'Physiotherapist'),
            ('psychologist', 'Psychologist'),
            ('occupational', 'Occupational Therapist'),
            ('speech', 'Speech Therapist'),
            ('other', 'Other'),
        ],
        required=True,
        tracking=True,
        index=True,
    )
    practitioner_id = fields.Many2one(
        'res.users',
        string='Allied Professional',
        required=True,
        default=lambda self: self.env.user,
        check_company=True,
    )
    session_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
        index=True,
    )
    assessment = fields.Html()
    recommendations = fields.Html()
    goals = fields.Text()
    progress_notes = fields.Html()
    next_review_date = fields.Date(tracking=True)
    outcome = fields.Selection(
        [
            ('improved', 'Improved'),
            ('stable', 'Stable'),
            ('worsened', 'Worsened'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
    )

    @api.depends('patient_id', 'specialty', 'session_date')
    def _compute_name(self):
        for rec in self:
            patient = rec.patient_id.name or 'Patient'
            specialty = dict(rec._fields['specialty'].selection).get(rec.specialty, '')
            when = fields.Datetime.to_string(rec.session_date) if rec.session_date else ''
            rec.name = f'{specialty} — {patient} ({when})'

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id

    @api.onchange('referral_id')
    def _onchange_referral_id(self):
        if self.referral_id:
            self.patient_id = self.referral_id.patient_id
            self.practice_id = self.referral_id.practice_id
            if self.referral_id.specialty in dict(self._fields['specialty'].selection):
                self.specialty = self.referral_id.specialty

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})
        for session in self:
            if session.referral_id and session.referral_id.state not in ('closed', 'cancelled'):
                session.referral_id.write({
                    'state': 'feedback',
                    'clinical_feedback': session.progress_notes or session.recommendations,
                })
            if session.next_review_date:
                session.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=session.next_review_date,
                    summary=f'Allied follow-up: {session.patient_id.name}',
                    user_id=session.practitioner_id.id,
                )
