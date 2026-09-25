# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class HealthcareMedicine(models.Model):
    _name = 'healthcare.medicine'
    _description = 'Medicine'
    _order = 'name'

    name = fields.Char(required=True)
    active_ingredient = fields.Char()
    strength = fields.Char()
    form = fields.Selection(
        [
            ('tablet', 'Tablet'),
            ('capsule', 'Capsule'),
            ('syrup', 'Syrup'),
            ('injection', 'Injection'),
            ('inhaler', 'Inhaler'),
            ('cream', 'Cream'),
            ('other', 'Other'),
        ],
        default='tablet',
    )
    allergy_keywords = fields.Char(
        help='Comma-separated keywords matched against patient allergy text.',
    )
    active = fields.Boolean(default=True)


class HealthcarePrescription(models.Model):
    _name = 'healthcare.prescription'
    _description = 'Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc, id desc'

    name = fields.Char(
        string='Prescription Number',
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
    prescribed_by_id = fields.Many2one(
        'res.users',
        string='Prescribed By',
        required=True,
        default=lambda self: self.env.user,
        check_company=True,
    )
    prescription_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        index=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        required=True,
        index=True,
    )
    is_repeat = fields.Boolean(string='Repeat Prescription')
    notes = fields.Text()
    allergy_warning = fields.Text(
        compute='_compute_allergy_warning',
        store=True,
    )
    line_ids = fields.One2many(
        'healthcare.prescription.line',
        'prescription_id',
        string='Medicines',
    )

    @api.depends(
        'patient_id.allergies',
        'line_ids.medicine_id',
        'line_ids.medicine_id.allergy_keywords',
        'line_ids.medicine_id.name',
        'line_ids.medicine_id.active_ingredient',
    )
    def _compute_allergy_warning(self):
        for rx in self:
            allergies = (rx.patient_id.allergies or '').lower()
            warnings = []
            if allergies:
                for line in rx.line_ids:
                    med = line.medicine_id
                    if not med:
                        continue
                    tokens = [med.name or '', med.active_ingredient or '']
                    if med.allergy_keywords:
                        tokens.extend(med.allergy_keywords.split(','))
                    for token in tokens:
                        token = token.strip().lower()
                        if token and token in allergies:
                            warnings.append(
                                f'Possible allergy conflict: {med.name} vs patient allergies.'
                            )
                            break
            rx.allergy_warning = '\n'.join(warnings)

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'healthcare.prescription'
                ) or 'New'
        return super().create(vals_list)

    def action_activate(self):
        for rx in self:
            if rx.allergy_warning:
                raise UserError(
                    'Allergy warning present. Review medications before activating:\n\n'
                    f'{rx.allergy_warning}'
                )
            if not rx.line_ids:
                raise UserError('Add at least one medicine before activating.')
        self.write({'state': 'active'})
        self._sync_patient_medication_summary()

    def action_activate_override(self):
        """Activate even when allergy warning exists (clinician override)."""
        for rx in self:
            if not rx.line_ids:
                raise UserError('Add at least one medicine before activating.')
        self.write({'state': 'active'})
        self._sync_patient_medication_summary()
        for rx in self.filtered('allergy_warning'):
            rx.message_post(body=f'Activated with allergy override.\n{rx.allergy_warning}')

    def action_complete(self):
        self.write({'state': 'completed'})
        self._sync_patient_medication_summary()

    def _sync_patient_medication_summary(self):
        for rx in self:
            patient = rx.patient_id
            active_rx = self.search([
                ('patient_id', '=', patient.id),
                ('state', '=', 'active'),
            ])
            lines = active_rx.mapped('line_ids')
            summary = '; '.join(
                f'{line.medicine_id.name} {line.strength or ""} '
                f'{line.dosage or ""} {line.frequency or ""}'.strip()
                for line in lines
            )
            patient.active_medication_summary = summary or False


class HealthcarePrescriptionLine(models.Model):
    _name = 'healthcare.prescription.line'
    _description = 'Prescription Line'
    _order = 'id'

    prescription_id = fields.Many2one(
        'healthcare.prescription',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='prescription_id.company_id',
        store=True,
        index=True,
    )
    patient_id = fields.Many2one(
        related='prescription_id.patient_id',
        store=True,
        index=True,
    )
    medicine_id = fields.Many2one(
        'healthcare.medicine',
        required=True,
    )
    strength = fields.Char()
    dosage = fields.Char()
    frequency = fields.Char()
    duration = fields.Char()
    instructions = fields.Char()

    @api.onchange('medicine_id')
    def _onchange_medicine_id(self):
        if self.medicine_id and self.medicine_id.strength:
            self.strength = self.medicine_id.strength
