# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HealthcareAppointment(models.Model):
    _name = 'healthcare.appointment'
    _description = 'Healthcare Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start desc'

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
        ondelete='restrict',
    )
    practice_id = fields.Many2one(
        'healthcare.practice',
        required=True,
        tracking=True,
        index=True,
        check_company=True,
    )
    practitioner_id = fields.Many2one(
        'res.users',
        string='Practitioner',
        required=True,
        tracking=True,
        check_company=True,
    )
    start = fields.Datetime(required=True, tracking=True, index=True)
    stop = fields.Datetime(required=True)
    appointment_type = fields.Selection(
        [
            ('consultation', 'Consultation'),
            ('follow_up', 'Follow-up'),
            ('urgent', 'Urgent'),
            ('walk_in', 'Walk-in'),
            ('teleconsultation', 'Teleconsultation'),
            ('allied', 'Allied Health'),
        ],
        default='consultation',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('requested', 'Requested Online'),
            ('scheduled', 'Scheduled'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('rescheduled', 'Rescheduled'),
            ('no_show', 'No Show'),
        ],
        default='scheduled',
        tracking=True,
        required=True,
        index=True,
    )
    reason = fields.Char()
    notes = fields.Text()
    calendar_event_id = fields.Many2one('calendar.event', copy=False)
    consultation_id = fields.Many2one(
        'healthcare.consultation',
        copy=False,
        check_company=True,
    )

    @api.depends('patient_id', 'start', 'appointment_type')
    def _compute_name(self):
        for rec in self:
            patient = rec.patient_id.name or 'Patient'
            appt_type = dict(rec._fields['appointment_type'].selection).get(
                rec.appointment_type, ''
            )
            when = fields.Datetime.to_string(rec.start) if rec.start else ''
            rec.name = f'{patient} — {appt_type} ({when})'

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        if self.patient_id:
            self.practice_id = self.patient_id.practice_id
            if self.patient_id.primary_gp_id:
                self.practitioner_id = self.patient_id.primary_gp_id

    def action_mark_completed(self):
        self.write({'state': 'completed'})

    def action_mark_no_show(self):
        self.write({'state': 'no_show'})

    def action_create_consultation(self):
        self.ensure_one()
        consultation = self.env['healthcare.consultation'].create({
            'patient_id': self.patient_id.id,
            'practice_id': self.practice_id.id,
            'practitioner_id': self.practitioner_id.id,
            'appointment_id': self.id,
            'consultation_date': self.start or fields.Datetime.now(),
        })
        self.consultation_id = consultation
        self.state = 'completed'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'healthcare.consultation',
            'res_id': consultation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm_request(self):
        self.write({'state': 'scheduled'})

    def action_reject_request(self):
        self.write({'state': 'cancelled'})
