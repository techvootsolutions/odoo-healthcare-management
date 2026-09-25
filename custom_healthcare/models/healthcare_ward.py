# -*- coding: utf-8 -*-
from odoo import fields, models


class HealthcareWard(models.Model):
    _name = 'healthcare.ward'
    _description = 'Ward'
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
    practice_id = fields.Many2one(
        'healthcare.practice',
        required=True,
        index=True,
        check_company=True,
        tracking=True,
    )
    ward_type = fields.Selection(
        [
            ('general', 'General'),
            ('icu', 'ICU'),
            ('isolation', 'Isolation'),
            ('maternity', 'Maternity'),
            ('pediatric', 'Pediatric'),
            ('emergency', 'Emergency'),
            ('day_care', 'Day Care'),
            ('other', 'Other'),
        ],
        default='general',
        required=True,
    )
    floor = fields.Char()
    room_ids = fields.One2many('healthcare.room', 'ward_id', string='Rooms')
    bed_ids = fields.One2many('healthcare.bed', 'ward_id', string='Beds')
    room_count = fields.Integer(compute='_compute_counts')
    bed_count = fields.Integer(compute='_compute_counts')
    available_bed_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for ward in self:
            ward.room_count = len(ward.room_ids)
            ward.bed_count = len(ward.bed_ids)
            ward.available_bed_count = len(ward.bed_ids.filtered(lambda b: b.status == 'available'))

    def action_view_rooms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rooms',
            'res_model': 'healthcare.room',
            'view_mode': 'list,form',
            'domain': [('ward_id', '=', self.id)],
            'context': {'default_ward_id': self.id, 'default_practice_id': self.practice_id.id},
        }

    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Beds',
            'res_model': 'healthcare.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('ward_id', '=', self.id)],
            'context': {'default_ward_id': self.id},
        }
