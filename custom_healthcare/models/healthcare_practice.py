# -*- coding: utf-8 -*-
from odoo import fields, models


class HealthcarePractice(models.Model):
    _name = 'healthcare.practice'
    _description = 'GP Practice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(copy=False, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Practice Contact',
        required=True,
        ondelete='restrict',
        check_company=True,
    )
    street = fields.Char(related='partner_id.street', readonly=False)
    city = fields.Char(related='partner_id.city', readonly=False)
    state_id = fields.Many2one(related='partner_id.state_id', readonly=False)
    country_id = fields.Many2one(related='partner_id.country_id', readonly=False)
    phone = fields.Char(related='partner_id.phone', readonly=False)
    email = fields.Char(related='partner_id.email', readonly=False)

    gp_owner_id = fields.Many2one(
        'res.users',
        string='GP Owner',
        tracking=True,
        check_company=True,
    )
    nurse_ids = fields.Many2many(
        'res.users',
        'healthcare_practice_nurse_rel',
        'practice_id',
        'user_id',
        string='Nurses',
        check_company=True,
    )
    coordinator_ids = fields.Many2many(
        'res.users',
        'healthcare_practice_coordinator_rel',
        'practice_id',
        'user_id',
        string='Care Coordinators',
        check_company=True,
    )
    doctor_ids = fields.Many2many(
        'res.users',
        'healthcare_practice_doctor_rel',
        'practice_id',
        'user_id',
        string='Doctors',
        check_company=True,
    )

    state = fields.Selection(
        [
            ('prospect', 'Prospect'),
            ('onboarding', 'Onboarding'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
        ],
        string='Status',
        default='prospect',
        tracking=True,
        required=True,
    )
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='CRM Opportunity',
        check_company=True,
    )
    go_live_date = fields.Date()
    programme_participation = fields.Char(string='Programme Participation')
    medical_scheme_notes = fields.Text(string='Medical Scheme Associations')

    patient_ids = fields.One2many('healthcare.patient', 'practice_id', string='Patients')
    patient_count = fields.Integer(compute='_compute_counts')
    appointment_count = fields.Integer(compute='_compute_counts')
    care_plan_count = fields.Integer(compute='_compute_counts')
    referral_count = fields.Integer(compute='_compute_counts')
    consultation_count = fields.Integer(compute='_compute_counts')

    # Inpatient Management
    ward_ids = fields.One2many('healthcare.ward', 'practice_id', string='Wards')
    bed_ids = fields.One2many('healthcare.bed', 'practice_id', string='Beds')
    bed_count = fields.Integer(compute='_compute_bed_counts')
    available_bed_count = fields.Integer(compute='_compute_bed_counts')
    occupied_bed_count = fields.Integer(compute='_compute_bed_counts')

    notes = fields.Html()

    def _compute_counts(self):
        Appointment = self.env['healthcare.appointment']
        CarePlan = self.env['healthcare.care.plan']
        Referral = self.env['healthcare.referral']
        Consultation = self.env['healthcare.consultation']
        for practice in self:
            practice.patient_count = len(practice.patient_ids)
            practice.appointment_count = Appointment.search_count([
                ('practice_id', '=', practice.id),
            ])
            practice.care_plan_count = CarePlan.search_count([
                ('practice_id', '=', practice.id),
            ])
            practice.referral_count = Referral.search_count([
                ('practice_id', '=', practice.id),
            ])
            practice.consultation_count = Consultation.search_count([
                ('practice_id', '=', practice.id),
            ])

    def _compute_bed_counts(self):
        for practice in self:
            beds = practice.bed_ids
            practice.bed_count = len(beds)
            practice.available_bed_count = len(beds.filtered(lambda b: b.status == 'available'))
            practice.occupied_bed_count = len(beds.filtered(lambda b: b.status == 'occupied'))

    def action_view_patients(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Patients',
            'res_model': 'healthcare.patient',
            'view_mode': 'list,form',
            'domain': [('practice_id', '=', self.id)],
            'context': {'default_practice_id': self.id},
        }

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'healthcare.appointment',
            'view_mode': 'list,form',
            'domain': [('practice_id', '=', self.id)],
            'context': {'default_practice_id': self.id},
        }

    def action_view_care_plan(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Care Plans',
            'res_model': 'healthcare.care.plan',
            'view_mode': 'list,form',
            'domain': [('practice_id', '=', self.id)],
            'context': {'default_practice_id': self.id},
        }

    def action_set_active(self):
        self.write({'state': 'active'})
        return True

    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Beds',
            'res_model': 'healthcare.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('practice_id', '=', self.id)],
            'context': {'default_practice_id': self.id},
        }
