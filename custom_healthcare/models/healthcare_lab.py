# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareLabTestType(models.Model):
    _name = 'healthcare.lab.test.type'
    _description = 'Lab Test Type'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    category = fields.Selection(
        [
            ('blood', 'Blood'),
            ('urine', 'Urine'),
            ('imaging', 'Imaging'),
            ('other', 'Other'),
        ],
        default='blood',
        required=True,
    )
    default_unit = fields.Char()
    reference_range = fields.Char()
    active = fields.Boolean(default=True)


class HealthcareLabRequest(models.Model):
    _name = 'healthcare.lab.request'
    _description = 'Lab Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(
        string='Request Number',
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
    consultation_id = fields.Many2one(
        'healthcare.consultation',
        check_company=True,
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        check_company=True,
    )
    request_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    priority = fields.Selection(
        [
            ('routine', 'Routine'),
            ('urgent', 'Urgent'),
        ],
        default='routine',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('requested', 'Requested'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
        index=True,
    )
    clinical_notes = fields.Text()
    line_ids = fields.One2many(
        'healthcare.lab.request.line',
        'request_id',
        string='Tests',
    )
    abnormal_count = fields.Integer(compute='_compute_result_stats')
    pending_review_count = fields.Integer(compute='_compute_result_stats')

    @api.depends('line_ids.is_abnormal', 'line_ids.review_state')
    def _compute_result_stats(self):
        for request in self:
            lines = request.line_ids
            request.abnormal_count = len(lines.filtered('is_abnormal'))
            request.pending_review_count = len(lines.filtered(
                lambda l: l.result_value and l.review_state == 'pending'
            ))

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'healthcare.lab.request'
                ) or 'New'
        return super().create(vals_list)

    def action_request(self):
        self.write({'state': 'requested'})

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})
        for request in self:
            abnormal = request.line_ids.filtered('is_abnormal')
            if abnormal and request.requested_by_id:
                request.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f'Abnormal lab results: {request.name}',
                    user_id=request.requested_by_id.id,
                    note='One or more lab results are flagged abnormal and need review.',
                )

    def action_view_abnormal_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Abnormal Results',
            'res_model': 'healthcare.lab.request.line',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id), ('is_abnormal', '=', True)],
            'context': {'default_request_id': self.id},
        }

    def action_view_pending_review_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Review',
            'res_model': 'healthcare.lab.request.line',
            'view_mode': 'list,form',
            'domain': [
                ('request_id', '=', self.id),
                ('review_state', '=', 'pending'),
                ('result_value', '!=', False),
            ],
            'context': {'default_request_id': self.id},
        }


class HealthcareLabRequestLine(models.Model):
    _name = 'healthcare.lab.request.line'
    _description = 'Lab Request Line'
    _order = 'id'

    request_id = fields.Many2one(
        'healthcare.lab.request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='request_id.company_id',
        store=True,
        index=True,
    )
    patient_id = fields.Many2one(
        related='request_id.patient_id',
        store=True,
        index=True,
    )
    test_type_id = fields.Many2one(
        'healthcare.lab.test.type',
        required=True,
    )
    result_value = fields.Char()
    result_unit = fields.Char()
    reference_range = fields.Char()
    is_abnormal = fields.Boolean(string='Abnormal', index=True)
    result_date = fields.Datetime()
    review_state = fields.Selection(
        [
            ('pending', 'Pending Review'),
            ('reviewed', 'Reviewed'),
            ('na', 'N/A'),
        ],
        default='na',
        required=True,
        index=True,
    )
    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By')
    reviewed_date = fields.Datetime()
    review_notes = fields.Text()

    @api.onchange('test_type_id')
    def _onchange_test_type_id(self):
        if self.test_type_id:
            self.result_unit = self.test_type_id.default_unit
            self.reference_range = self.test_type_id.reference_range

    @api.onchange('result_value')
    def _onchange_result_value(self):
        for line in self:
            if line.result_value and line.review_state == 'na':
                line.review_state = 'pending'
                if not line.result_date:
                    line.result_date = fields.Datetime.now()

    def action_mark_reviewed(self):
        self.write({
            'review_state': 'reviewed',
            'reviewed_by_id': self.env.user.id,
            'reviewed_date': fields.Datetime.now(),
        })
