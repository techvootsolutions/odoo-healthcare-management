# -*- coding: utf-8 -*-
from odoo import fields, models


class HealthcareRoom(models.Model):
    _name = 'healthcare.room'
    _description = 'Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Room Number', required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    ward_id = fields.Many2one(
        'healthcare.ward',
        required=True,
        index=True,
        check_company=True,
        tracking=True,
    )
    practice_id = fields.Many2one(
        related='ward_id.practice_id',
        store=True,
        index=True,
    )
    room_type = fields.Selection(
        [
            ('general', 'General'),
            ('private', 'Private'),
            ('semi_private', 'Semi-Private'),
            ('icu', 'ICU'),
            ('isolation', 'Isolation'),
            ('procedure', 'Procedure'),
            ('day_care', 'Day Care'),
            ('other', 'Other'),
        ],
        default='general',
        required=True,
    )
    bed_ids = fields.One2many('healthcare.bed', 'room_id', string='Beds')
    bed_count = fields.Integer(compute='_compute_counts')
    available_bed_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for room in self:
            room.bed_count = len(room.bed_ids)
            room.available_bed_count = len(room.bed_ids.filtered(lambda b: b.status == 'available'))

    def action_view_beds(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Beds',
            'res_model': 'healthcare.bed',
            'view_mode': 'kanban,list,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }
