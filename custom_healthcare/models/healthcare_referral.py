# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareReferral(models.Model):
    _name = 'healthcare.referral'
    _description = 'Referral'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

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
    consultation_id = fields.Many2one(
        'healthcare.consultation',
        check_company=True,
    )
    from_practitioner_id = fields.Many2one(
        'res.users',
        string='Referring Practitioner',
        required=True,
        check_company=True,
    )
    specialty = fields.Selection(
        [
            ('dietician', 'Dietician'),
            ('physiotherapist', 'Physiotherapist'),
            ('psychologist', 'Psychologist'),
            ('occupational', 'Occupational Therapist'),
            ('speech', 'Speech Therapist'),
            ('specialist', 'Medical Specialist'),
            ('lab', 'Laboratory'),
            ('other', 'Other'),
        ],
        required=True,
        tracking=True,
    )
    receiving_specialist = fields.Char(string='Receiving Specialist')
    reason = fields.Text(required=True)
    priority = fields.Selection(
        [
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='normal',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('accepted', 'Accepted'),
            ('appointment', 'Appointment Booked'),
            ('feedback', 'Feedback Received'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
        index=True,
    )
    appointment_date = fields.Datetime()
    clinical_feedback = fields.Html()
    closure_date = fields.Date()

    @api.depends('patient_id', 'specialty')
    def _compute_name(self):
        for rec in self:
            patient = rec.patient_id.name or 'Patient'
            specialty = dict(rec._fields['specialty'].selection).get(rec.specialty, '')
            rec.name = f'Referral — {patient} → {specialty}'

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id
            if self.patient_id.primary_gp_id:
                self.from_practitioner_id = self.patient_id.primary_gp_id

    def action_send(self):
        self.write({'state': 'sent'})

    def action_accept(self):
        self.write({'state': 'accepted'})

    def action_close(self):
        self.write({
            'state': 'closed',
            'closure_date': fields.Date.context_today(self),
        })

    def action_create_allied_session(self):
        self.ensure_one()
        specialty = self.specialty if self.specialty in (
            'dietician', 'physiotherapist', 'psychologist',
            'occupational', 'speech', 'other',
        ) else 'other'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allied Session',
            'res_model': 'healthcare.allied.session',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_practice_id': self.practice_id.id,
                'default_referral_id': self.id,
                'default_specialty': specialty,
            },
        }
