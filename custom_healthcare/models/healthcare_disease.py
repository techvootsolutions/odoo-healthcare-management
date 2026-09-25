# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareDiseaseType(models.Model):
    _name = 'healthcare.disease.type'
    _description = 'Disease / Programme Type'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ('diabetes', 'Diabetes'),
            ('hypertension', 'Hypertension'),
            ('copd', 'COPD'),
            ('asthma', 'Asthma'),
            ('mental_health', 'Mental Health'),
            ('cancer', 'Cancer'),
            ('hiv', 'HIV'),
            ('other', 'Other'),
        ],
        default='other',
        required=True,
        index=True,
    )
    description = fields.Text()
    registry_ids = fields.One2many(
        'healthcare.disease.registry',
        'disease_id',
        string='Registry Entries',
    )
    patient_count = fields.Integer(compute='_compute_patient_count')

    def _compute_patient_count(self):
        for disease in self:
            disease.patient_count = len(disease.registry_ids)


class HealthcareDiseaseRegistry(models.Model):
    _name = 'healthcare.disease.registry'
    _description = 'Chronic Disease Registry Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_review_date, id'

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
        ondelete='cascade',
    )
    practice_id = fields.Many2one(
        related='patient_id.practice_id',
        store=True,
        index=True,
    )
    disease_id = fields.Many2one(
        'healthcare.disease.type',
        required=True,
        tracking=True,
        index=True,
    )
    enrolment_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    risk_level = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        tracking=True,
        index=True,
    )
    last_review_date = fields.Date()
    next_review_date = fields.Date(index=True)
    compliance_state = fields.Selection(
        [
            ('on_track', 'On Track'),
            ('at_risk', 'At Risk'),
            ('overdue', 'Overdue'),
        ],
        default='on_track',
        tracking=True,
        index=True,
    )
    care_plan_id = fields.Many2one(
        'healthcare.care.plan',
        check_company=True,
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _patient_disease_uniq = models.Constraint(
        'unique(patient_id, disease_id)',
        'Patient is already enrolled in this disease registry.',
    )

    @api.depends('patient_id', 'disease_id')
    def _compute_name(self):
        for rec in self:
            patient = rec.patient_id.name or 'Patient'
            disease = rec.disease_id.name or 'Disease'
            rec.name = f'{patient} — {disease}'

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id and self.patient_id.risk_level:
            self.risk_level = self.patient_id.risk_level
