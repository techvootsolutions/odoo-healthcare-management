# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class HealthcareAdmission(models.Model):
    _name = 'healthcare.admission'
    _description = 'Inpatient Admission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'admission_date desc, id desc'

    name = fields.Char(
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
    )
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
    bed_id = fields.Many2one(
        'healthcare.bed',
        string='Bed',
        check_company=True,
        tracking=True,
    )
    ward_id = fields.Many2one(related='bed_id.ward_id', store=True)
    room_id = fields.Many2one(related='bed_id.room_id', store=True)
    admission_type = fields.Selection(
        [
            ('planned', 'Planned'),
            ('emergency', 'Emergency'),
            ('referral', 'Referral'),
            ('day_case', 'Day Case'),
        ],
        default='planned',
        required=True,
    )
    admitting_physician_id = fields.Many2one(
        'res.users',
        string='Admitting Physician',
        check_company=True,
    )
    admission_date = fields.Datetime(required=True, default=fields.Datetime.now, tracking=True)
    expected_discharge_date = fields.Date()
    actual_discharge_date = fields.Datetime(tracking=True)
    admission_reason = fields.Text()
    diagnosis = fields.Text()
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('admitted', 'Admitted'),
            ('discharged', 'Discharged'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )
    discharge_summary = fields.Text()
    discharge_condition = fields.Selection(
        [
            ('recovered', 'Recovered'),
            ('improved', 'Improved'),
            ('referred', 'Referred'),
            ('deceased', 'Deceased'),
            ('against_medical_advice', 'Against Medical Advice'),
            ('other', 'Other'),
        ],
    )
    length_of_stay = fields.Integer(string='Length of Stay (days)', compute='_compute_length_of_stay')
    estimated_charges = fields.Monetary(compute='_compute_estimated_charges', currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    transfer_ids = fields.One2many('healthcare.bed.transfer', 'admission_id', string='Bed Transfers')

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id

    @api.onchange('practice_id')
    def _onchange_practice_id(self):
        if self.bed_id and self.bed_id.practice_id != self.practice_id:
            self.bed_id = False

    @api.depends('admission_date', 'actual_discharge_date', 'state')
    def _compute_length_of_stay(self):
        now = fields.Datetime.now()
        for admission in self:
            if not admission.admission_date:
                admission.length_of_stay = 0
                continue
            end = admission.actual_discharge_date or now
            admission.length_of_stay = max((end - admission.admission_date).days, 0)

    @api.depends('length_of_stay', 'bed_id.daily_rate')
    def _compute_estimated_charges(self):
        for admission in self:
            days = max(admission.length_of_stay, 1) if admission.state in ('admitted', 'discharged') else 0
            admission.estimated_charges = days * (admission.bed_id.daily_rate or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('healthcare.admission') or 'New'
        return super().create(vals_list)

    def action_admit(self):
        for admission in self:
            if not admission.bed_id:
                raise UserError('Assign a bed before admitting the patient.')
            if admission.bed_id.status != 'available':
                raise UserError(
                    f'Bed "{admission.bed_id.display_name}" is not available '
                    f'(current status: {admission.bed_id.status}).'
                )
            admission.bed_id.write({'status': 'occupied'})
            admission.write({'state': 'admitted'})

    def action_discharge(self):
        for admission in self:
            if admission.bed_id:
                admission.bed_id.write({'status': 'cleaning'})
            admission.write({
                'state': 'discharged',
                'actual_discharge_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        for admission in self:
            if admission.bed_id and admission.bed_id.status == 'reserved':
                admission.bed_id.write({'status': 'available'})
            admission.write({'state': 'cancelled'})

    def action_open_transfer_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer Bed',
            'res_model': 'healthcare.bed.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_admission_id': self.id,
                'default_practice_id': self.practice_id.id,
            },
        }


class HealthcareBedTransfer(models.Model):
    _name = 'healthcare.bed.transfer'
    _description = 'Bed Transfer Log'
    _order = 'transfer_date desc, id desc'

    admission_id = fields.Many2one(
        'healthcare.admission',
        required=True,
        index=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(related='admission_id.company_id', store=True, index=True)
    patient_id = fields.Many2one(related='admission_id.patient_id', store=True, index=True)
    from_bed_id = fields.Many2one('healthcare.bed', string='From Bed', check_company=True)
    to_bed_id = fields.Many2one('healthcare.bed', string='To Bed', required=True, check_company=True)
    transfer_date = fields.Datetime(required=True, default=fields.Datetime.now)
    reason = fields.Text()
    transferred_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        check_company=True,
    )
