# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcarePatient(models.Model):
    _name = 'healthcare.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True)
    patient_number = fields.Char(
        string='Patient Number',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        ondelete='restrict',
        check_company=True,
    )
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(compute='_compute_age')
    gender = fields.Selection(
        [
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('unknown', 'Unknown'),
        ],
        tracking=True,
    )
    national_id = fields.Char(string='National ID')
    phone = fields.Char()
    email = fields.Char()
    emergency_contact = fields.Char()
    emergency_phone = fields.Char()

    blood_group = fields.Selection(
        [
            ('a+', 'A+'),
            ('a-', 'A-'),
            ('b+', 'B+'),
            ('b-', 'B-'),
            ('ab+', 'AB+'),
            ('ab-', 'AB-'),
            ('o+', 'O+'),
            ('o-', 'O-'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
    )
    allergies = fields.Text()
    family_history = fields.Text()
    smoking_status = fields.Selection(
        [
            ('never', 'Never'),
            ('former', 'Former'),
            ('current', 'Current'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
    )
    alcohol_status = fields.Selection(
        [
            ('none', 'None'),
            ('occasional', 'Occasional'),
            ('regular', 'Regular'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
    )
    vaccination_status = fields.Char()

    medical_scheme = fields.Char(string='Medical Scheme')
    membership_number = fields.Char()
    scheme_plan = fields.Char(string='Plan')
    scheme_validity = fields.Date(string='Scheme Validity')

    practice_id = fields.Many2one(
        'healthcare.practice',
        required=True,
        tracking=True,
        index=True,
        check_company=True,
    )
    primary_gp_id = fields.Many2one(
        'res.users',
        string='Primary GP',
        tracking=True,
        check_company=True,
    )
    care_coordinator_id = fields.Many2one(
        'res.users',
        string='Care Coordinator',
        tracking=True,
        index=True,
        check_company=True,
    )
    risk_level = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='low',
        tracking=True,
        index=True,
    )
    clinical_risk_score = fields.Integer(
        string='Clinical Risk Score',
        default=0,
        tracking=True,
    )
    chronic_disease_ids = fields.Many2many(
        'healthcare.disease.type',
        'healthcare_patient_disease_rel',
        'patient_id',
        'disease_id',
        string='Chronic Conditions',
    )
    consent_notes = fields.Text(string='Consent Notes')

    appointment_ids = fields.One2many('healthcare.appointment', 'patient_id')
    consultation_ids = fields.One2many('healthcare.consultation', 'patient_id')
    care_plan_ids = fields.One2many('healthcare.care.plan', 'patient_id')
    referral_ids = fields.One2many('healthcare.referral', 'patient_id')
    registry_ids = fields.One2many('healthcare.disease.registry', 'patient_id')
    lab_request_ids = fields.One2many('healthcare.lab.request', 'patient_id')
    prescription_ids = fields.One2many('healthcare.prescription', 'patient_id')
    allied_session_ids = fields.One2many('healthcare.allied.session', 'patient_id')

    # Inpatient Management
    admission_ids = fields.One2many('healthcare.admission', 'patient_id', string='Admissions')
    admission_count = fields.Integer(compute='_compute_admission_stats')
    current_admission_id = fields.Many2one('healthcare.admission', compute='_compute_admission_stats')
    is_admitted = fields.Boolean(compute='_compute_admission_stats')

    appointment_count = fields.Integer(compute='_compute_counts')
    consultation_count = fields.Integer(compute='_compute_counts')
    care_plan_count = fields.Integer(compute='_compute_counts')
    referral_count = fields.Integer(compute='_compute_counts')
    lab_request_count = fields.Integer(compute='_compute_counts')
    prescription_count = fields.Integer(compute='_compute_counts')
    allied_session_count = fields.Integer(compute='_compute_counts')
    active_medication_summary = fields.Text(
        string='Current Medications',
        help='Summary of active prescription lines (synced from prescriptions).',
    )
    clinical_alerts = fields.Text(string='Alerts')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for patient in self:
            if patient.date_of_birth:
                born = patient.date_of_birth
                patient.age = (
                    today.year
                    - born.year
                    - ((today.month, today.day) < (born.month, born.day))
                )
            else:
                patient.age = 0

    @api.depends(
        'appointment_ids',
        'consultation_ids',
        'care_plan_ids',
        'referral_ids',
        'lab_request_ids',
        'prescription_ids',
        'allied_session_ids',
    )
    def _compute_counts(self):
        for patient in self:
            patient.appointment_count = len(patient.appointment_ids)
            patient.consultation_count = len(patient.consultation_ids)
            patient.care_plan_count = len(patient.care_plan_ids)
            patient.referral_count = len(patient.referral_ids)
            patient.lab_request_count = len(patient.lab_request_ids)
            patient.prescription_count = len(patient.prescription_ids)
            patient.allied_session_count = len(patient.allied_session_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('patient_number', 'New') == 'New':
                vals['patient_number'] = self.env['ir.sequence'].next_by_code(
                    'healthcare.patient'
                ) or 'New'
        patients = super().create(vals_list)
        patients._ensure_portal_partner()
        return patients

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('name', 'email', 'phone', 'partner_id')):
            self._ensure_portal_partner()
        return res

    def _ensure_portal_partner(self):
        Partner = self.env['res.partner']
        for patient in self:
            if patient.partner_id:
                updates = {}
                if patient.email and patient.partner_id.email != patient.email:
                    updates['email'] = patient.email
                if patient.phone and patient.partner_id.phone != patient.phone:
                    updates['phone'] = patient.phone
                if updates:
                    patient.partner_id.write(updates)
                continue
            partner = Partner.create({
                'name': patient.name,
                'email': patient.email,
                'phone': patient.phone,
                'company_id': patient.company_id.id,
                'type': 'contact',
            })
            patient.partner_id = partner

    def _compute_admission_stats(self):
        for patient in self:
            patient.admission_count = len(patient.admission_ids)
            current = patient.admission_ids.filtered(lambda a: a.state == 'admitted')[:1]
            patient.current_admission_id = current
            patient.is_admitted = bool(current)

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'healthcare.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_consultations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consultations',
            'res_model': 'healthcare.consultation',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_care_plans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Care Plans',
            'res_model': 'healthcare.care.plan',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_lab_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Requests',
            'res_model': 'healthcare.lab.request',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prescriptions',
            'res_model': 'healthcare.prescription',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_allied_sessions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allied Sessions',
            'res_model': 'healthcare.allied.session',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_view_admissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Admissions',
            'res_model': 'healthcare.admission',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }

    def action_admit_patient(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Admit Patient',
            'res_model': 'healthcare.admission',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }
