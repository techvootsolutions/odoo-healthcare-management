# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareConsultation(models.Model):
    _name = 'healthcare.consultation'
    _description = 'Clinical Consultation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'consultation_date desc'

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
    practitioner_id = fields.Many2one(
        'res.users',
        string='Practitioner',
        required=True,
        tracking=True,
        check_company=True,
    )
    appointment_id = fields.Many2one(
        'healthcare.appointment',
        check_company=True,
    )
    consultation_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
    )

    chief_complaint = fields.Text()
    history = fields.Html(string='History')
    clinical_examination = fields.Html(string='Clinical Examination')
    vital_bp = fields.Char(string='Blood Pressure')
    vital_hr = fields.Char(string='Heart Rate')
    vital_temp = fields.Char(string='Temperature')
    vital_weight = fields.Float(string='Weight (kg)')
    vital_bmi = fields.Float(string='BMI')
    diagnosis = fields.Text()
    disease_ids = fields.Many2many(
        'healthcare.disease.type',
        'healthcare_consultation_disease_rel',
        'consultation_id',
        'disease_id',
        string='Diagnoses / Conditions',
    )
    treatment = fields.Html()
    medication = fields.Text()
    investigations = fields.Text()
    clinical_notes = fields.Html()
    follow_up_date = fields.Date()
    follow_up_plan = fields.Text()

    referral_ids = fields.One2many('healthcare.referral', 'consultation_id')
    referral_count = fields.Integer(compute='_compute_referral_count')

    @api.depends('patient_id', 'consultation_date')
    def _compute_name(self):
        for rec in self:
            patient = rec.patient_id.name or 'Patient'
            when = fields.Datetime.to_string(rec.consultation_date) if rec.consultation_date else ''
            rec.name = f'Consult — {patient} ({when})'

    @api.depends('referral_ids')
    def _compute_referral_count(self):
        for rec in self:
            rec.referral_count = len(rec.referral_ids)

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id
            if self.patient_id.primary_gp_id:
                self.practitioner_id = self.patient_id.primary_gp_id

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
        for consult in self.filtered('follow_up_date'):
            consult.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=consult.follow_up_date,
                summary=f'Follow-up: {consult.patient_id.name}',
                user_id=(
                    consult.patient_id.care_coordinator_id.id
                    or consult.practitioner_id.id
                ),
            )

    def action_create_referral(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Referral',
            'res_model': 'healthcare.referral',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_practice_id': self.practice_id.id,
                'default_consultation_id': self.id,
                'default_from_practitioner_id': self.practitioner_id.id,
            },
        }

    def action_create_lab_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Lab Request',
            'res_model': 'healthcare.lab.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_practice_id': self.practice_id.id,
                'default_consultation_id': self.id,
                'default_requested_by_id': self.practitioner_id.id,
            },
        }

    def action_create_prescription(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Prescription',
            'res_model': 'healthcare.prescription',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_practice_id': self.practice_id.id,
                'default_consultation_id': self.id,
                'default_prescribed_by_id': self.practitioner_id.id,
            },
        }
