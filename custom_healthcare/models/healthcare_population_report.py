# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists


class HealthcarePopulationReport(models.Model):
    _name = 'healthcare.population.report'
    _description = 'Population Health Report'
    _auto = False
    _order = 'patient_id'

    patient_id = fields.Many2one('healthcare.patient', readonly=True)
    practice_id = fields.Many2one('healthcare.practice', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    care_coordinator_id = fields.Many2one('res.users', readonly=True)
    primary_gp_id = fields.Many2one('res.users', string='Primary GP', readonly=True)
    risk_level = fields.Selection(
        [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        readonly=True,
    )
    gender = fields.Selection(
        [
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('unknown', 'Unknown'),
        ],
        readonly=True,
    )
    age_band = fields.Selection(
        [
            ('0_17', '0-17'),
            ('18_39', '18-39'),
            ('40_59', '40-59'),
            ('60_plus', '60+'),
            ('unknown', 'Unknown'),
        ],
        readonly=True,
        string='Age Band',
    )
    active_care_plan_count = fields.Integer(readonly=True)
    open_referral_count = fields.Integer(readonly=True)
    registry_count = fields.Integer(readonly=True)
    open_alert_count = fields.Integer(readonly=True)
    care_gap_count = fields.Integer(readonly=True)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    p.id AS id,
                    p.id AS patient_id,
                    p.practice_id AS practice_id,
                    p.company_id AS company_id,
                    p.care_coordinator_id AS care_coordinator_id,
                    p.primary_gp_id AS primary_gp_id,
                    p.risk_level AS risk_level,
                    p.gender AS gender,
                    CASE
                        WHEN p.date_of_birth IS NULL THEN 'unknown'
                        WHEN date_part('year', age(p.date_of_birth)) < 18 THEN '0_17'
                        WHEN date_part('year', age(p.date_of_birth)) < 40 THEN '18_39'
                        WHEN date_part('year', age(p.date_of_birth)) < 60 THEN '40_59'
                        ELSE '60_plus'
                    END AS age_band,
                    (
                        SELECT COUNT(*) FROM healthcare_care_plan cp
                        WHERE cp.patient_id = p.id AND cp.state = 'active'
                    ) AS active_care_plan_count,
                    (
                        SELECT COUNT(*) FROM healthcare_referral r
                        WHERE r.patient_id = p.id
                          AND r.state NOT IN ('closed', 'cancelled')
                    ) AS open_referral_count,
                    (
                        SELECT COUNT(*) FROM healthcare_disease_registry dr
                        WHERE dr.patient_id = p.id AND dr.active = TRUE
                    ) AS registry_count,
                    (
                        SELECT COUNT(*) FROM healthcare_alert a
                        WHERE a.patient_id = p.id AND a.state = 'open'
                    ) AS open_alert_count,
                    (
                        SELECT COUNT(*) FROM healthcare_disease_registry dr2
                        WHERE dr2.patient_id = p.id
                          AND dr2.compliance_state IN ('at_risk', 'overdue')
                    ) AS care_gap_count
                FROM healthcare_patient p
                WHERE p.active = TRUE
            )
        """)
