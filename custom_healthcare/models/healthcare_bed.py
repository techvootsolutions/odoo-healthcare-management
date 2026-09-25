# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareBed(models.Model):
    _name = 'healthcare.bed'
    _description = 'Bed'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'ward_id, room_id, name'

    name = fields.Char(string='Bed', required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    room_id = fields.Many2one(
        'healthcare.room',
        required=True,
        index=True,
        check_company=True,
        tracking=True,
    )
    ward_id = fields.Many2one(
        related='room_id.ward_id',
        store=True,
        index=True,
    )
    practice_id = fields.Many2one(
        related='room_id.practice_id',
        store=True,
        index=True,
    )
    bed_type = fields.Selection(
        [
            ('general', 'General'),
            ('icu', 'ICU'),
            ('isolation', 'Isolation'),
            ('pediatric', 'Pediatric'),
            ('maternity', 'Maternity'),
            ('day_care', 'Day Care'),
            ('other', 'Other'),
        ],
        default='general',
        required=True,
    )
    status = fields.Selection(
        [
            ('available', 'Available'),
            ('reserved', 'Reserved'),
            ('occupied', 'Occupied'),
            ('cleaning', 'Cleaning'),
            ('maintenance', 'Maintenance'),
            ('blocked', 'Blocked'),
        ],
        default='available',
        required=True,
        tracking=True,
        index=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    daily_rate = fields.Monetary(
        string='Daily Rate',
        currency_field='currency_id',
        help='Reference rate per day, used for the estimated-charges preview on admissions. '
             'Not linked to invoicing yet.',
    )
    current_admission_id = fields.Many2one(
        'healthcare.admission',
        string='Current Admission',
        compute='_compute_current_admission',
    )
    current_patient_id = fields.Many2one(
        'healthcare.patient',
        string='Current Patient',
        compute='_compute_current_admission',
    )

    @api.depends('room_id.name', 'room_id.ward_id.name', 'name')
    def _compute_display_name(self):
        for bed in self:
            parts = [bed.room_id.ward_id.name, bed.room_id.name, bed.name]
            bed.display_name = ' > '.join(p for p in parts if p)

    def _compute_current_admission(self):
        Admission = self.env['healthcare.admission']
        for bed in self:
            admission = Admission.search([
                ('bed_id', '=', bed.id),
                ('state', '=', 'admitted'),
            ], limit=1)
            bed.current_admission_id = admission
            bed.current_patient_id = admission.patient_id

    def action_mark_available(self):
        self.write({'status': 'available'})

    def action_mark_cleaning(self):
        self.write({'status': 'cleaning'})

    def action_mark_maintenance(self):
        self.write({'status': 'maintenance'})

    def action_block(self):
        self.write({'status': 'blocked'})
