# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class HealthcareBedTransferWizard(models.TransientModel):
    _name = 'healthcare.bed.transfer.wizard'
    _description = 'Transfer Patient to a New Bed'

    admission_id = fields.Many2one('healthcare.admission', required=True)
    practice_id = fields.Many2one(related='admission_id.practice_id')
    current_bed_id = fields.Many2one(related='admission_id.bed_id', string='Current Bed')
    new_bed_id = fields.Many2one(
        'healthcare.bed',
        string='New Bed',
        required=True,
        domain="[('practice_id', '=', practice_id), ('status', '=', 'available')]",
    )
    reason = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        admission = self.admission_id
        old_bed = admission.bed_id

        if self.new_bed_id == old_bed:
            raise UserError('Choose a different bed to transfer to.')
        if self.new_bed_id.status != 'available':
            raise UserError(f'Bed "{self.new_bed_id.display_name}" is not available.')
        if admission.state != 'admitted':
            raise UserError('Only an admitted patient can be transferred between beds.')

        if old_bed:
            old_bed.write({'status': 'cleaning'})
        self.new_bed_id.write({'status': 'occupied'})
        admission.write({'bed_id': self.new_bed_id.id})

        self.env['healthcare.bed.transfer'].create({
            'admission_id': admission.id,
            'from_bed_id': old_bed.id if old_bed else False,
            'to_bed_id': self.new_bed_id.id,
            'reason': self.reason,
        })
        admission.message_post(
            body=f'Patient transferred from '
                 f'{old_bed.display_name if old_bed else "no bed"} to {self.new_bed_id.display_name}.'
        )
        return {'type': 'ir.actions.act_window_close'}
