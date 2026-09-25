# -*- coding: utf-8 -*-
import calendar
import random
from datetime import datetime, timedelta

from odoo import fields, models
from odoo.exceptions import UserError


FIRST_NAMES = [
    'Ava', 'Noah', 'Mia', 'Liam', 'Sofia', 'Ethan', 'Amelia', 'Lucas',
    'Harper', 'Mason', 'Ella', 'Logan', 'Chloe', 'James', 'Grace', 'Benjamin',
    'Olivia', 'Henry', 'Zoe', 'Jack', 'Layla', 'Owen', 'Nora', 'Leo',
]
LAST_NAMES = [
    'Nguyen', 'Patel', 'Silva', 'Johansson', 'Kim', 'Garcia', 'Muller',
    'Rossi', 'Andersen', 'Costa', 'Singh', 'Brown', 'Martinez', 'Wilson',
    'Ali', 'Chen', 'Khan', 'Brooks', 'Dupont', 'Ibrahim',
]

# login, name, healthcare group xmlid suffix (after custom_healthcare.), extra flags
DEMO_USERS = [
    ('ceo_ops', 'Claire Edwards (CEO/Ops)', 'manager'),
    ('clinical_mgr', 'Dr. Marcus Hale (Clinical Manager)', 'manager'),
    ('gp_north', 'Dr. Sarah Chen', 'gp'),
    ('gp_river', 'Dr. David Okonkwo', 'gp'),
    ('gp_oak', 'Dr. Priya Nair', 'gp'),
    ('nurse_amy', 'Amy Brooks (Nurse)', 'user'),
    ('nurse_tom', 'Tom Rivera (Nurse)', 'user'),
    ('receptionist_lia', 'Lia Park (Reception)', 'user'),
    ('receptionist_marc', 'Marc Dubois (Reception)', 'user'),
    ('coord_emma', 'Emma Walsh (Care Coordinator)', 'coordinator'),
    ('coord_raj', 'Raj Mehta (Care Coordinator)', 'coordinator'),
    ('coord_nina', 'Nina Berg (Care Coordinator)', 'coordinator'),
    ('dietician_anita', 'Anita Desai (Dietician)', 'user'),
    ('physio_james', 'James Cole (Physiotherapist)', 'user'),
    ('psych_helen', 'Helen Frost (Psychologist)', 'user'),
    ('lab_tech_kim', 'Kim Lee (Laboratory)', 'user'),
    ('pharmacist_omar', 'Omar Haddad (Pharmacist)', 'user'),
]


class HealthcareDemoSeeder(models.TransientModel):
    _name = 'healthcare.demo.seeder'
    _description = 'Healthcare Demo Data Seeder'

    patient_count = fields.Integer(default=80, required=True)
    appointment_per_patient = fields.Integer(default=2, required=True)
    create_care_plans = fields.Boolean(default=True)
    create_registry = fields.Boolean(default=True)
    create_users = fields.Boolean(
        string='Create Role Users (password: admin)',
        default=True,
    )
    seed_current_month = fields.Boolean(
        string='Seed Current-Month Scenarios',
        default=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    def action_seed(self):
        self.ensure_one()
        users = self._ensure_demo_users() if self.create_users else {}
        created = self._seed_patients_volume(users)
        month_stats = {}
        if self.seed_current_month:
            month_stats = self._seed_current_month_scenarios(users)
        self.env['healthcare.automation']._cron_care_reminders_and_escalations()
        msg = (
            f'Users: {len(users)}; patients added: {created}; '
            f"month appts: {month_stats.get('appointments', 0)}; "
            f"consults: {month_stats.get('consultations', 0)}; "
            f"labs: {month_stats.get('labs', 0)}; "
            f"rx: {month_stats.get('prescriptions', 0)}; "
            f"referrals: {month_stats.get('referrals', 0)}; "
            f"allied: {month_stats.get('allied', 0)}."
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Demo seeding complete',
                'message': msg,
                'type': 'success',
                'sticky': True,
            },
        }

    def action_seed_full_demo(self):
        """One-click full demo: users + volume + current month scenarios."""
        self.ensure_one()
        self.write({
            'create_users': True,
            'seed_current_month': True,
            'create_care_plans': True,
            'create_registry': True,
            'patient_count': max(self.patient_count, 80),
            'appointment_per_patient': max(self.appointment_per_patient, 2),
        })
        return self.action_seed()

    def _group(self, suffix):
        return self.env.ref(f'custom_healthcare.group_healthcare_{suffix}')

    def _ensure_demo_users(self):
        """Create/update demo users for each role. Password always 'admin'."""
        Users = self.env['res.users'].with_context(no_reset_password=True)
        base_user = self.env.ref('base.group_user')
        admin = self.env.ref('base.user_admin')
        admin.password = 'admin'
        users = {'admin': admin}
        for login, name, suffix in DEMO_USERS:
            group = self._group(suffix)
            user = Users.search([('login', '=', login)], limit=1)
            group_ids = [base_user.id, group.id]
            # managers also need implied groups already via privilege chain
            vals = {
                'name': name,
                'login': login,
                'password': 'admin',
                'company_id': self.company_id.id,
                'company_ids': [(4, self.company_id.id)],
                'group_ids': [(6, 0, group_ids)],
            }
            if user:
                user.write(vals)
            else:
                user = Users.create(vals)
            users[login] = user

        # Assign staff onto practices
        practices = self.env['healthcare.practice'].search([
            ('company_id', '=', self.company_id.id),
        ])
        gps = [users['gp_north'], users['gp_river'], users['gp_oak']]
        coords = [users['coord_emma'], users['coord_raj'], users['coord_nina']]
        nurses = [users['nurse_amy'], users['nurse_tom']]
        for idx, practice in enumerate(practices):
            gp = gps[idx % len(gps)]
            practice.write({
                'gp_owner_id': gp.id,
                'doctor_ids': [(6, 0, [gp.id, gps[(idx + 1) % len(gps)].id])],
                'coordinator_ids': [(6, 0, [coords[idx % len(coords)].id, coords[(idx + 1) % len(coords)].id])],
                'nurse_ids': [(6, 0, [n.id for n in nurses])],
                'state': 'active' if practice.state != 'onboarding' else practice.state,
            })
            if practice.state == 'onboarding':
                practice.state = 'active'
        return users

    def _seed_patients_volume(self, users):
        if self.patient_count < 1 or self.patient_count > 2000:
            raise UserError('Patient count must be between 1 and 2000.')
        practices = self.env['healthcare.practice'].search([
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'active'),
        ])
        if not practices:
            raise UserError('Create at least one active practice before seeding.')
        diseases = self.env['healthcare.disease.type'].search([])
        if not diseases:
            raise UserError('Disease types are missing.')
        gps = practices.mapped('doctor_ids') or self.env['res.users']
        coords = practices.mapped('coordinator_ids') or self.env['res.users']
        admin = users.get('admin') or self.env.ref('base.user_admin')
        Patient = self.env['healthcare.patient']
        Appointment = self.env['healthcare.appointment']
        CarePlan = self.env['healthcare.care.plan']
        Registry = self.env['healthcare.disease.registry']
        today = fields.Date.context_today(self)
        created = 0
        for _i in range(self.patient_count):
            practice = random.choice(practices)
            gender = random.choice(['male', 'female', 'other'])
            risk = random.choices(
                ['low', 'medium', 'high', 'critical'],
                weights=[45, 30, 18, 7],
            )[0]
            dob = today - timedelta(days=random.randint(18 * 365, 80 * 365))
            name = f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}'
            disease = random.choice(diseases)
            gp = random.choice(list(practice.doctor_ids)) if practice.doctor_ids else (gps[:1] or admin)
            coord = random.choice(list(practice.coordinator_ids)) if practice.coordinator_ids else (coords[:1] or admin)
            patient = Patient.create({
                'name': name,
                'gender': gender,
                'date_of_birth': dob,
                'practice_id': practice.id,
                'company_id': self.company_id.id,
                'primary_gp_id': gp.id,
                'care_coordinator_id': coord.id,
                'risk_level': risk,
                'clinical_risk_score': {
                    'low': random.randint(5, 25),
                    'medium': random.randint(26, 50),
                    'high': random.randint(51, 75),
                    'critical': random.randint(76, 95),
                }[risk],
                'chronic_disease_ids': [(4, disease.id)],
                'blood_group': random.choice(['a+', 'b+', 'o+', 'ab+', 'unknown']),
                'smoking_status': random.choice(['never', 'former', 'current', 'unknown']),
                'email': f"{name.lower().replace(' ', '.')}@demo.healthcare.local",
                'phone': f'+1 555 {random.randint(1000, 9999)}',
            })
            created += 1
            for j in range(self.appointment_per_patient):
                start = fields.Datetime.now() - timedelta(
                    days=random.randint(1, 60),
                    hours=random.randint(0, 8),
                )
                Appointment.create({
                    'patient_id': patient.id,
                    'practice_id': practice.id,
                    'company_id': self.company_id.id,
                    'practitioner_id': patient.primary_gp_id.id,
                    'start': start,
                    'stop': start + timedelta(minutes=30),
                    'appointment_type': random.choice([
                        'consultation', 'follow_up', 'teleconsultation', 'walk_in', 'urgent',
                    ]),
                    'state': random.choice([
                        'completed', 'completed', 'scheduled', 'no_show', 'cancelled',
                    ]),
                    'reason': f'Seeded visit {j + 1}',
                })
            if self.create_care_plans and risk in ('medium', 'high', 'critical'):
                plan = CarePlan.create({
                    'name': f'{patient.name} — {disease.name} Care Plan',
                    'patient_id': patient.id,
                    'practice_id': practice.id,
                    'company_id': self.company_id.id,
                    'disease_id': disease.id,
                    'coordinator_id': patient.care_coordinator_id.id,
                    'state': 'active',
                    'goal': 'Seeded care plan for demo volume.',
                    'line_ids': [(0, 0, {
                        'name': 'Coordinator Follow-up',
                        'activity_type': 'coordinator_call',
                        'frequency': 'monthly',
                        'responsible_id': patient.care_coordinator_id.id,
                        'next_due_date': today - timedelta(days=random.randint(0, 20)),
                        'state': random.choice(['scheduled', 'overdue', 'pending']),
                    })],
                })
                if self.create_registry:
                    existing = Registry.search([
                        ('patient_id', '=', patient.id),
                        ('disease_id', '=', disease.id),
                    ], limit=1)
                    if not existing:
                        Registry.create({
                            'patient_id': patient.id,
                            'disease_id': disease.id,
                            'company_id': self.company_id.id,
                            'risk_level': risk,
                            'care_plan_id': plan.id,
                            'next_review_date': today + timedelta(days=random.randint(-15, 90)),
                            'compliance_state': random.choice([
                                'on_track', 'at_risk', 'overdue',
                            ]),
                        })
        return created

    def _month_bounds(self):
        today = fields.Date.context_today(self)
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
        return today, start, end

    def _dt_on(self, day, hour=9, minute=0):
        return datetime(day.year, day.month, day.day, hour, minute, 0)

    def _seed_current_month_scenarios(self, users):
        """Dense current-month data covering clinical + coordination scenarios."""
        today, month_start, month_end = self._month_bounds()
        company = self.company_id
        patients = self.env['healthcare.patient'].search([
            ('company_id', '=', company.id),
        ])
        if not patients:
            raise UserError('No patients available to seed current-month scenarios.')
        practices = self.env['healthcare.practice'].search([
            ('company_id', '=', company.id),
            ('state', '=', 'active'),
        ])
        diseases = self.env['healthcare.disease.type'].search([])
        lab_types = self.env['healthcare.lab.test.type'].search([])
        medicines = self.env['healthcare.medicine'].search([])
        gp_users = [
            users.get('gp_north'), users.get('gp_river'), users.get('gp_oak'),
        ]
        gp_users = [u for u in gp_users if u]
        coords = [
            users.get('coord_emma'), users.get('coord_raj'), users.get('coord_nina'),
        ]
        coords = [u for u in coords if u]
        allied_map = {
            'dietician': users.get('dietician_anita'),
            'physiotherapist': users.get('physio_james'),
            'psychologist': users.get('psych_helen'),
        }
        admin = users.get('admin') or self.env.ref('base.user_admin')

        Appointment = self.env['healthcare.appointment']
        Consultation = self.env['healthcare.consultation']
        LabRequest = self.env['healthcare.lab.request']
        Prescription = self.env['healthcare.prescription']
        Referral = self.env['healthcare.referral']
        Allied = self.env['healthcare.allied.session']
        CarePlan = self.env['healthcare.care.plan']

        stats = {
            'appointments': 0,
            'consultations': 0,
            'labs': 0,
            'prescriptions': 0,
            'referrals': 0,
            'allied': 0,
        }

        # Walk every day of current month up to today (+ a few future scheduled)
        day = month_start
        day_index = 0
        while day <= month_end:
            is_future = day > today
            # 4-8 appointments per day
            daily_count = random.randint(4, 8)
            for slot in range(daily_count):
                patient = random.choice(patients)
                practice = patient.practice_id or random.choice(practices)
                gp = patient.primary_gp_id or random.choice(gp_users or [admin])
                hour = 8 + (slot % 8)
                start = self._dt_on(day, hour, random.choice([0, 15, 30, 45]))
                if is_future:
                    state = 'scheduled'
                    appt_type = random.choice(['consultation', 'follow_up', 'teleconsultation'])
                else:
                    state = random.choices(
                        ['completed', 'completed', 'completed', 'no_show', 'cancelled', 'scheduled'],
                        weights=[50, 20, 10, 8, 7, 5],
                    )[0]
                    appt_type = random.choice([
                        'consultation', 'follow_up', 'urgent', 'walk_in', 'teleconsultation', 'allied',
                    ])
                appt = Appointment.create({
                    'patient_id': patient.id,
                    'practice_id': practice.id,
                    'company_id': company.id,
                    'practitioner_id': gp.id,
                    'start': start,
                    'stop': start + timedelta(minutes=30),
                    'appointment_type': appt_type,
                    'state': state,
                    'reason': f'{day.isoformat()} clinic visit',
                })
                stats['appointments'] += 1

                if state == 'completed' and not is_future:
                    consult = Consultation.create({
                        'patient_id': patient.id,
                        'practice_id': practice.id,
                        'company_id': company.id,
                        'practitioner_id': gp.id,
                        'appointment_id': appt.id,
                        'consultation_date': start + timedelta(minutes=5),
                        'state': 'done',
                        'chief_complaint': random.choice([
                            'Follow-up for chronic condition',
                            'Fatigue and polyuria',
                            'Blood pressure review',
                            'Medication review',
                            'Respiratory symptoms',
                        ]),
                        'vital_bp': f'{random.randint(110, 160)}/{random.randint(70, 100)}',
                        'vital_hr': str(random.randint(60, 100)),
                        'vital_weight': round(random.uniform(55, 110), 1),
                        'diagnosis': random.choice([
                            'Stable chronic disease',
                            'Suboptimal glycaemic control',
                            'Hypertension not at target',
                            'Acute exacerbation — improving',
                        ]),
                        'medication': patient.active_medication_summary or 'Continue current therapy',
                        'follow_up_date': day + timedelta(days=random.randint(7, 28)),
                    })
                    appt.consultation_id = consult.id
                    stats['consultations'] += 1

                    # Every ~3rd completed visit: lab + prescription
                    if day_index % 3 == slot % 3 and lab_types:
                        lab = LabRequest.create({
                            'patient_id': patient.id,
                            'practice_id': practice.id,
                            'company_id': company.id,
                            'consultation_id': consult.id,
                            'requested_by_id': gp.id,
                            'request_date': start + timedelta(minutes=20),
                            'priority': random.choice(['routine', 'urgent']),
                            'state': 'completed',
                            'clinical_notes': 'Current-month monitoring panel',
                            'line_ids': [
                                (0, 0, {
                                    'test_type_id': lt.id,
                                    'result_value': str(round(random.uniform(4.5, 9.5), 1)),
                                    'result_unit': lt.default_unit or '',
                                    'reference_range': lt.reference_range or '',
                                    'is_abnormal': random.random() < 0.35,
                                    'result_date': start + timedelta(days=1, hours=2),
                                    'review_state': random.choice(['pending', 'reviewed', 'pending']),
                                })
                                for lt in random.sample(list(lab_types), k=min(3, len(lab_types)))
                            ],
                        })
                        stats['labs'] += 1

                    if day_index % 4 == 0 and medicines:
                        meds = random.sample(list(medicines), k=min(2, len(medicines)))
                        # Avoid penicillin conflict for demo patients with penicillin allergy text
                        meds = [m for m in meds if 'penicillin' not in (m.allergy_keywords or '').lower()]
                        if meds:
                            Prescription.create({
                                'patient_id': patient.id,
                                'practice_id': practice.id,
                                'company_id': company.id,
                                'consultation_id': consult.id,
                                'prescribed_by_id': gp.id,
                                'prescription_date': start + timedelta(minutes=25),
                                'state': 'active',
                                'is_repeat': True,
                                'line_ids': [
                                    (0, 0, {
                                        'medicine_id': m.id,
                                        'strength': m.strength or '',
                                        'dosage': '1',
                                        'frequency': random.choice(['OD', 'BD', 'TDS']),
                                        'duration': '30 days',
                                    }) for m in meds
                                ],
                            })
                            stats['prescriptions'] += 1

                    # Referral + allied every ~5th consult
                    if day_index % 5 == 0:
                        specialty = random.choice(list(allied_map.keys()))
                        referral = Referral.create({
                            'patient_id': patient.id,
                            'practice_id': practice.id,
                            'company_id': company.id,
                            'consultation_id': consult.id,
                            'from_practitioner_id': gp.id,
                            'specialty': specialty,
                            'receiving_specialist': (allied_map[specialty] or admin).name,
                            'reason': f'Referred for {specialty} support this month.',
                            'priority': random.choice(['normal', 'high']),
                            'state': random.choice(['sent', 'accepted', 'appointment', 'feedback']),
                            'appointment_date': start + timedelta(days=random.randint(2, 10)),
                        })
                        stats['referrals'] += 1
                        allied_user = allied_map.get(specialty) or admin
                        Allied.create({
                            'patient_id': patient.id,
                            'practice_id': practice.id,
                            'company_id': company.id,
                            'referral_id': referral.id,
                            'specialty': specialty,
                            'practitioner_id': allied_user.id,
                            'session_date': start + timedelta(days=random.randint(1, 7), hours=1),
                            'state': 'completed' if day < today else 'in_progress',
                            'assessment': '<p>Current-month allied assessment completed.</p>',
                            'goals': 'Improve adherence and functional outcomes.',
                            'recommendations': '<p>Continue programme; review next month.</p>',
                            'progress_notes': '<p>Patient engaged.</p>',
                            'next_review_date': day + timedelta(days=28),
                            'outcome': random.choice(['improved', 'stable', 'unknown']),
                        })
                        stats['allied'] += 1

            # Care plan activity due dates across the month
            if day_index % 2 == 0 and coords:
                sample_patients = random.sample(list(patients), k=min(5, len(patients)))
                for patient in sample_patients:
                    plan = CarePlan.search([
                        ('patient_id', '=', patient.id),
                        ('state', '=', 'active'),
                    ], limit=1)
                    if not plan and diseases:
                        disease = patient.chronic_disease_ids[:1] or diseases[:1]
                        plan = CarePlan.create({
                            'name': f'{patient.name} — Monthly Care Plan',
                            'patient_id': patient.id,
                            'practice_id': patient.practice_id.id,
                            'company_id': company.id,
                            'disease_id': disease.id,
                            'coordinator_id': (patient.care_coordinator_id or random.choice(coords)).id,
                            'state': 'active',
                            'start_date': month_start,
                            'goal': 'Current-month care coordination.',
                        })
                    if plan:
                        due_state = 'overdue' if day < today else 'scheduled'
                        self.env['healthcare.care.plan.line'].create({
                            'care_plan_id': plan.id,
                            'name': f'{day.strftime("%d %b")} coordinator call',
                            'activity_type': 'coordinator_call',
                            'frequency': 'weekly',
                            'responsible_id': (patient.care_coordinator_id or random.choice(coords)).id,
                            'next_due_date': day,
                            'state': due_state if day != today else 'scheduled',
                        })

            day += timedelta(days=1)
            day_index += 1

        # Link portal partners for a few named patients
        self._ensure_patient_portal_users(users)
        return stats

    def _ensure_patient_portal_users(self, users):
        """Create portal users for key demo patients (password admin)."""
        PortalUsers = self.env['res.users'].with_context(no_reset_password=True)
        portal_group = self.env.ref('base.group_portal')
        targets = [
            ('patient_maria', 'Maria Santos'),
            ('patient_james', 'James Okeke'),
            ('patient_aisha', 'Aisha Khan'),
            ('patient_robert', 'Robert Lee'),
        ]
        for login, pname in targets:
            patient = self.env['healthcare.patient'].search([('name', '=', pname)], limit=1)
            if not patient:
                continue
            if hasattr(patient, '_ensure_portal_partner'):
                patient._ensure_portal_partner()
            elif not patient.partner_id:
                partner = self.env['res.partner'].create({
                    'name': patient.name,
                    'email': patient.email or f'{login}@demo.healthcare.local',
                    'phone': patient.phone,
                    'company_id': patient.company_id.id,
                })
                patient.partner_id = partner
            partner = patient.partner_id
            user = PortalUsers.search([('login', '=', login)], limit=1)
            vals = {
                'name': patient.name,
                'login': login,
                'password': 'admin',
                'partner_id': partner.id,
                'company_id': self.company_id.id,
                'company_ids': [(4, self.company_id.id)],
                'group_ids': [(6, 0, [portal_group.id])],
            }
            if user:
                user.write(vals)
            else:
                PortalUsers.create(vals)

        # Ensure complete demo portal records for Maria Santos
        maria = self.env['healthcare.patient'].search([('name', '=', 'Maria Santos')], limit=1)
        if maria:
            self._ensure_maria_portal_demo_data(maria, users)

    def _ensure_maria_portal_demo_data(self, maria, users):
        practice = maria.practice_id or self.env['healthcare.practice'].search([('state', '=', 'active')], limit=1)
        gp = maria.primary_gp_id or users.get('gp_north') or self.env.ref('base.user_admin')
        coord = maria.care_coordinator_id or users.get('coord_emma') or self.env.ref('base.user_admin')
        disease_dm = self.env['healthcare.disease.type'].search([('code', '=', 'DM2')], limit=1) or self.env['healthcare.disease.type'].search([], limit=1)

        # 1. Care plan
        if not self.env['healthcare.care.plan'].search([('patient_id', '=', maria.id), ('state', '=', 'active')], limit=1):
            self.env['healthcare.care.plan'].create({
                'name': 'Maria Santos — Type 2 Diabetes & Hypertension Care Plan',
                'patient_id': maria.id,
                'practice_id': practice.id,
                'company_id': self.company_id.id,
                'disease_id': disease_dm.id if disease_dm else False,
                'coordinator_id': coord.id,
                'start_date': fields.Date.today() - timedelta(days=30),
                'state': 'active',
                'goal': 'Target HbA1c < 7.0%, BP < 130/80 mmHg, weight reduction 5% in 6 months.',
                'line_ids': [
                    (0, 0, {
                        'name': 'Quarterly GP Review',
                        'activity_type': 'gp_review',
                        'frequency': 'quarterly',
                        'responsible_id': gp.id,
                        'next_due_date': fields.Date.today() + timedelta(days=14),
                        'state': 'scheduled',
                    }),
                    (0, 0, {
                        'name': 'Care Coordinator Monthly Check-in',
                        'activity_type': 'coordinator_call',
                        'frequency': 'monthly',
                        'responsible_id': coord.id,
                        'next_due_date': fields.Date.today() + timedelta(days=7),
                        'state': 'scheduled',
                    }),
                    (0, 0, {
                        'name': 'Quarterly HbA1c & Fasting Lipids Lab',
                        'activity_type': 'lab',
                        'frequency': 'quarterly',
                        'responsible_id': gp.id,
                        'next_due_date': fields.Date.today() + timedelta(days=21),
                        'state': 'scheduled',
                    }),
                ],
            })

        # 2. Lab request & results
        if not self.env['healthcare.lab.request'].search([('patient_id', '=', maria.id)], limit=1):
            test_types = self.env['healthcare.lab.test.type'].search([])
            if test_types:
                hba1c_type = test_types.filtered(lambda t: 'hba1c' in (t.code or t.name).lower())[:1] or test_types[:1]
                glucose_type = test_types.filtered(lambda t: 'glucose' in (t.code or t.name).lower())[:1] or (test_types[1:2] or test_types[:1])
                chol_type = test_types.filtered(lambda t: 'cholesterol' in (t.code or t.name).lower() or 'lipid' in (t.code or t.name).lower())[:1] or (test_types[2:3] or test_types[:1])
                self.env['healthcare.lab.request'].create({
                    'patient_id': maria.id,
                    'practice_id': practice.id,
                    'company_id': self.company_id.id,
                    'requested_by_id': gp.id,
                    'request_date': fields.Datetime.now() - timedelta(days=4),
                    'priority': 'routine',
                    'state': 'completed',
                    'clinical_notes': 'Routine 3-month diabetes & metabolic evaluation.',
                    'line_ids': [
                        (0, 0, {
                            'test_type_id': hba1c_type.id,
                            'result_value': '8.2',
                            'result_unit': '%',
                            'reference_range': '4.0 - 5.6 %',
                            'is_abnormal': True,
                            'review_state': 'reviewed',
                            'result_date': fields.Datetime.now() - timedelta(days=3),
                        }),
                        (0, 0, {
                            'test_type_id': glucose_type.id,
                            'result_value': '142',
                            'result_unit': 'mg/dL',
                            'reference_range': '70 - 99 mg/dL',
                            'is_abnormal': True,
                            'review_state': 'reviewed',
                            'result_date': fields.Datetime.now() - timedelta(days=3),
                        }),
                        (0, 0, {
                            'test_type_id': chol_type.id,
                            'result_value': '185',
                            'result_unit': 'mg/dL',
                            'reference_range': '< 200 mg/dL',
                            'is_abnormal': False,
                            'review_state': 'reviewed',
                            'result_date': fields.Datetime.now() - timedelta(days=3),
                        }),
                    ],
                })

        # 3. Prescriptions
        if not self.env['healthcare.prescription'].search([('patient_id', '=', maria.id), ('state', 'in', ['active', 'completed'])], limit=1):
            medicines = self.env['healthcare.medicine'].search([])
            if medicines:
                metformin = medicines.filtered(lambda m: 'metformin' in m.name.lower())[:1] or medicines[:1]
                amlodipine = medicines.filtered(lambda m: 'amlodipine' in m.name.lower())[:1] or (medicines[1:2] or medicines[:1])
                atorvastatin = medicines.filtered(lambda m: 'atorvastatin' in m.name.lower())[:1] or (medicines[2:3] or medicines[:1])
                self.env['healthcare.prescription'].create({
                    'patient_id': maria.id,
                    'practice_id': practice.id,
                    'company_id': self.company_id.id,
                    'prescribed_by_id': gp.id,
                    'prescription_date': fields.Datetime.now() - timedelta(days=10),
                    'state': 'active',
                    'notes': 'Take medications with meals.',
                    'line_ids': [
                        (0, 0, {
                            'medicine_id': metformin.id,
                            'strength': metformin.strength or '500mg',
                            'dosage': '1 tablet',
                            'frequency': 'Twice daily with meals',
                            'duration': '90 days',
                        }),
                        (0, 0, {
                            'medicine_id': amlodipine.id,
                            'strength': amlodipine.strength or '5mg',
                            'dosage': '1 tablet',
                            'frequency': 'Once daily in morning',
                            'duration': '90 days',
                        }),
                        (0, 0, {
                            'medicine_id': atorvastatin.id,
                            'strength': atorvastatin.strength or '20mg',
                            'dosage': '1 tablet',
                            'frequency': 'Once daily at bedtime',
                            'duration': '90 days',
                        }),
                    ],
                })

        # 4. Scheduled and pending appointments
        maria_appts = self.env['healthcare.appointment'].search([('patient_id', '=', maria.id)])
        if not maria_appts.filtered(lambda a: a.state == 'scheduled'):
            start_time = fields.Datetime.now() + timedelta(days=3, hours=2)
            self.env['healthcare.appointment'].create({
                'patient_id': maria.id,
                'practice_id': practice.id,
                'company_id': self.company_id.id,
                'practitioner_id': gp.id,
                'start': start_time,
                'stop': start_time + timedelta(minutes=30),
                'appointment_type': 'follow_up',
                'state': 'scheduled',
                'reason': 'Care plan follow-up & BP check',
            })
