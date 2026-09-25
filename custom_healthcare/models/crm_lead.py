# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    healthcare_practice_id = fields.Many2one(
        'healthcare.practice',
        string='Healthcare Practice',
        check_company=True,
        help='Link this opportunity to a GP practice onboarding record.',
    )

    def action_create_healthcare_practice(self):
        self.ensure_one()
        if self.healthcare_practice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'healthcare.practice',
                'res_id': self.healthcare_practice_id.id,
                'view_mode': 'form',
            }
        partner = self.partner_id or self.env['res.partner'].create({
            'name': self.partner_name or self.name,
            'email': self.email_from,
            'phone': self.phone,
            'is_company': True,
            'company_id': self.company_id.id,
        })
        if not self.partner_id:
            self.partner_id = partner
        practice = self.env['healthcare.practice'].create({
            'name': partner.name,
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'state': 'onboarding',
            'opportunity_id': self.id,
        })
        self.healthcare_practice_id = practice
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'healthcare.practice',
            'res_id': practice.id,
            'view_mode': 'form',
        }
