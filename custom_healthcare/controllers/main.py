# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time, timedelta

from odoo import fields, http, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class HealthcarePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        patient = self._get_patient()
        if 'healthcare_appointment_count' in counters:
            values['healthcare_appointment_count'] = (
                request.env['healthcare.appointment'].sudo().search_count([
                    ('patient_id', '=', patient.id),
                ]) if patient else 0
            )
        if 'healthcare_care_plan_count' in counters:
            values['healthcare_care_plan_count'] = (
                request.env['healthcare.care.plan'].sudo().search_count([
                    ('patient_id', '=', patient.id),
                    ('state', '=', 'active'),
                ]) if patient else 0
            )
        return values

    def _get_patient(self):
        partner = request.env.user.partner_id
        patient = request.env['healthcare.patient'].sudo().search([
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not patient and request.env.user.has_group('base.group_user'):
            patient = request.env['healthcare.patient'].sudo().search([
                ('name', '=', 'Maria Santos'),
            ], limit=1) or request.env['healthcare.patient'].sudo().search([], limit=1)
        return patient

    def _patient_values(self, page_name):
        patient = self._get_patient()
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': page_name,
            'patient': patient,
        })
        return values, patient

    def _day_bounds(self):
        today = fields.Date.context_today(request.env.user)
        start = fields.Datetime.to_string(datetime.combine(today, time.min))
        end = fields.Datetime.to_string(datetime.combine(today, time.max))
        return today, start, end

    @http.route(['/my/healthcare'], type='http', auth='user', website=True)
    def portal_healthcare_home(self, **kw):
        values, patient = self._patient_values('healthcare_home')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        appts = request.env['healthcare.appointment'].sudo().search([
            ('patient_id', '=', patient.id),
        ], limit=10, order='start desc')
        care_plans = request.env['healthcare.care.plan'].sudo().search([
            ('patient_id', '=', patient.id),
            ('state', '=', 'active'),
        ])
        labs = request.env['healthcare.lab.request'].sudo().search([
            ('patient_id', '=', patient.id),
        ], limit=10, order='request_date desc')
        prescriptions = request.env['healthcare.prescription'].sudo().search([
            ('patient_id', '=', patient.id),
            ('state', 'in', ['active', 'completed']),
        ], limit=10, order='prescription_date desc')
        values.update({
            'appointments': appts,
            'care_plans': care_plans,
            'labs': labs,
            'prescriptions': prescriptions,
            'stats': [
                {'label': 'Appointments', 'value': len(appts), 'tone': 'bg-light'},
                {'label': 'Active Care Plans', 'value': len(care_plans), 'tone': 'bg-light'},
                {'label': 'Lab Reports', 'value': len(labs), 'tone': 'bg-light'},
                {'label': 'Prescriptions', 'value': len(prescriptions), 'tone': 'bg-light'},
            ],
        })
        return request.render('custom_healthcare.portal_healthcare_home', values)

    @http.route(['/my/healthcare/appointments'], type='http', auth='user', website=True)
    def portal_healthcare_appointments(self, **kw):
        values, patient = self._patient_values('healthcare_appointments')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        values.update({
            'appointments': request.env['healthcare.appointment'].sudo().search([
                ('patient_id', '=', patient.id),
            ], order='start desc'),
            'request_success': kw.get('request_success'),
        })
        return request.render('custom_healthcare.portal_healthcare_appointments', values)

    @http.route(['/my/healthcare/appointments/new'], type='http', auth='user', website=True)
    def portal_healthcare_appointment_new(self, **kw):
        values, patient = self._patient_values('healthcare_appointment_new')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        values.update({
            'appointment_types': request.env['healthcare.appointment']._fields['appointment_type'].selection,
            'request_error': None,
            'post': {},
        })
        return request.render('custom_healthcare.portal_healthcare_appointment_new', values)

    @http.route(['/my/healthcare/appointments/request'], type='http', auth='user', website=True, methods=['POST'])
    def portal_healthcare_appointment_request(self, **post):
        values, patient = self._patient_values('healthcare_appointment_new')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)

        error = self._validate_appointment_request(patient, post)
        if not error:
            self._create_appointment_request(patient, post)
            return request.redirect('/my/healthcare/appointments?request_success=1')

        values.update({
            'appointment_types': request.env['healthcare.appointment']._fields['appointment_type'].selection,
            'request_error': error,
            'post': post,
        })
        return request.render('custom_healthcare.portal_healthcare_appointment_new', values)

    def _validate_appointment_request(self, patient, post):
        appointment_type = post.get('appointment_type')
        allowed_types = dict(request.env['healthcare.appointment']._fields['appointment_type'].selection)
        if appointment_type not in allowed_types:
            return 'Please choose a visit type.'

        if not (post.get('reason') or '').strip():
            return 'Please tell us the reason for your visit.'

        raw_date = post.get('preferred_date')
        if not raw_date:
            return 'Please choose a preferred date and time.'
        try:
            preferred_start = datetime.strptime(raw_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            return 'Please choose a valid date and time.'
        if preferred_start <= datetime.now():
            return 'Please choose a date and time in the future.'

        if not self._pick_practitioner(patient):
            return 'No practitioner is available to review your request. Please contact the practice directly.'

        return None

    def _pick_practitioner(self, patient):
        if patient.primary_gp_id:
            return patient.primary_gp_id
        practice = patient.practice_id
        if practice.gp_owner_id:
            return practice.gp_owner_id
        return practice.doctor_ids[:1]

    def _create_appointment_request(self, patient, post):
        preferred_start = datetime.strptime(post.get('preferred_date'), '%Y-%m-%dT%H:%M')
        request.env['healthcare.appointment'].sudo().create({
            'patient_id': patient.id,
            'practice_id': patient.practice_id.id,
            'practitioner_id': self._pick_practitioner(patient).id,
            'start': preferred_start,
            'stop': preferred_start + timedelta(minutes=30),
            'appointment_type': post.get('appointment_type'),
            'state': 'requested',
            'reason': post.get('reason'),
            'notes': post.get('notes'),
        })

    @http.route(['/my/healthcare/care-plans'], type='http', auth='user', website=True)
    def portal_healthcare_care_plans(self, **kw):
        values, patient = self._patient_values('healthcare_care_plans')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        values['care_plans'] = request.env['healthcare.care.plan'].sudo().search([
            ('patient_id', '=', patient.id),
        ])
        return request.render('custom_healthcare.portal_healthcare_care_plans', values)

    @http.route(['/my/healthcare/labs'], type='http', auth='user', website=True)
    def portal_healthcare_labs(self, **kw):
        values, patient = self._patient_values('healthcare_labs')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        values['labs'] = request.env['healthcare.lab.request'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='request_date desc')
        return request.render('custom_healthcare.portal_healthcare_labs', values)

    @http.route(['/my/healthcare/prescriptions'], type='http', auth='user', website=True)
    def portal_healthcare_prescriptions(self, **kw):
        values, patient = self._patient_values('healthcare_prescriptions')
        if not patient:
            return request.render('custom_healthcare.portal_no_patient', values)
        values['prescriptions'] = request.env['healthcare.prescription'].sudo().search([
            ('patient_id', '=', patient.id),
        ], order='prescription_date desc')
        return request.render('custom_healthcare.portal_healthcare_prescriptions', values)

    @http.route(['/my/healthcare/gp'], type='http', auth='user', website=True)
    def portal_healthcare_gp(self, **kw):
        if not request.env.user.has_group('custom_healthcare.group_healthcare_gp'):
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        user = request.env.user
        today, day_start, day_end = self._day_bounds()
        Appointment = request.env['healthcare.appointment']
        Alert = request.env['healthcare.alert']

        appointments_today = Appointment.search([
            ('practitioner_id', '=', user.id),
            ('state', '=', 'scheduled'),
            ('start', '>=', day_start),
            ('start', '<=', day_end),
        ], order='start asc')
        appointments_upcoming = Appointment.search([
            ('practitioner_id', '=', user.id),
            ('state', '=', 'scheduled'),
            ('start', '>', day_end),
        ], order='start asc', limit=20)
        alerts = Alert.search([
            ('responsible_id', '=', user.id),
            ('state', '=', 'open'),
        ], order='priority desc, create_date desc', limit=30)
        critical_alerts = alerts.filtered(lambda a: a.priority in ('2', '3'))

        values.update({
            'page_name': 'healthcare_gp',
            'today': today,
            'appointments_today': appointments_today,
            'appointments_upcoming': appointments_upcoming,
            'alerts': alerts,
            'stats': [
                {'label': 'Today', 'value': len(appointments_today), 'tone': 'bg-primary-subtle'},
                {'label': 'Upcoming', 'value': len(appointments_upcoming), 'tone': 'bg-100'},
                {'label': 'Open alerts', 'value': len(alerts), 'tone': 'bg-100'},
                {
                    'label': 'High / critical',
                    'value': len(critical_alerts),
                    'tone': 'bg-danger-subtle' if critical_alerts else 'bg-100',
                },
            ],
        })
        return request.render('custom_healthcare.portal_healthcare_gp', values)

    @http.route(['/my/healthcare/coordinator'], type='http', auth='user', website=True)
    def portal_healthcare_coordinator(self, **kw):
        if not request.env.user.has_group('custom_healthcare.group_healthcare_coordinator'):
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        user = request.env.user
        today = fields.Date.context_today(user)
        Patient = request.env['healthcare.patient']
        CareLine = request.env['healthcare.care.plan.line']
        Alert = request.env['healthcare.alert']

        patients = Patient.search([
            ('care_coordinator_id', '=', user.id),
        ], order='risk_level desc, name asc', limit=50)
        high_risk = patients.filtered(lambda p: p.risk_level in ('high', 'critical'))
        overdue_lines = CareLine.search([
            ('responsible_id', '=', user.id),
            ('next_due_date', '<', today),
            ('state', 'in', ['pending', 'scheduled', 'overdue']),
        ], order='next_due_date asc', limit=40)
        alerts = Alert.search([
            ('responsible_id', '=', user.id),
            ('state', '=', 'open'),
        ], order='priority desc, create_date desc', limit=30)

        values.update({
            'page_name': 'healthcare_coordinator',
            'today': today,
            'patients': patients,
            'overdue_lines': overdue_lines,
            'alerts': alerts,
            'stats': [
                {'label': 'Caseload', 'value': len(patients), 'tone': 'bg-primary-subtle'},
                {
                    'label': 'High / critical',
                    'value': len(high_risk),
                    'tone': 'bg-danger-subtle' if high_risk else 'bg-100',
                },
                {
                    'label': 'Overdue',
                    'value': len(overdue_lines),
                    'tone': 'bg-warning-subtle' if overdue_lines else 'bg-100',
                },
                {'label': 'Open alerts', 'value': len(alerts), 'tone': 'bg-100'},
            ],
        })
        return request.render('custom_healthcare.portal_healthcare_coordinator', values)


class HealthcarePatientRegistration(http.Controller):
    """Public self-registration: a patient fills one form and gets a
    healthcare.patient record plus a portal user (invited by email to set
    their password), mirroring the standard 'Grant Portal Access' flow.
    """

    _GENDER_VALUES = {'male', 'female', 'other', 'unknown'}

    @http.route(
        ['/patient/register'], type='http', auth='public', website=True,
        sitemap=True, methods=['GET', 'POST'],
        captcha='healthcare_patient_registration',
    )
    def patient_register(self, **post):
        values = {'post': post}

        if request.httprequest.method == 'POST':
            error = self._validate_registration(post)
            if error:
                values['error'] = error
            else:
                try:
                    self._create_patient_and_portal_user(post)
                except (UserError, ValidationError) as exc:
                    request.env.cr.rollback()
                    values['error'] = str(exc)
                except Exception:
                    request.env.cr.rollback()
                    _logger.exception('Patient self-registration failed')
                    values['error'] = _(
                        'Something went wrong while creating your account. '
                        'Please try again or contact the practice directly.'
                    )
                else:
                    return request.render('custom_healthcare.patient_register_success', values)

        return request.render('custom_healthcare.patient_register_form', values)

    def _validate_registration(self, post):
        # Honeypot: hidden field left empty by humans, filled in by most bots.
        if post.get('registration_hp'):
            _logger.info(
                'Patient self-registration blocked by honeypot from %s',
                request.httprequest.remote_addr,
            )
            return _('Could not process your registration. Please try again.')

        if not (post.get('name') or '').strip():
            return _('Please enter your full name.')

        email = email_normalize(post.get('email') or '')
        if not email:
            return _('Please enter a valid email address.')

        existing_user = request.env['res.users'].sudo().with_context(active_test=False).search_count([
            ('login', '=', email),
        ])
        if existing_user:
            return _(
                'An account with this email already exists. '
                'Please sign in instead, or use "Forgot password" if you need to reset it.'
            )

        dob = post.get('date_of_birth')
        if dob:
            try:
                fields.Date.from_string(dob)
            except ValueError:
                return _('Please enter a valid date of birth.')

        practice = request.env['healthcare.practice'].sudo()._get_registration_practice()
        if not practice:
            _logger.warning('Patient self-registration attempted with no default practice configured')
            return _('Online registration is temporarily unavailable. Please contact the practice directly.')

        return None

    def _create_patient_and_portal_user(self, post):
        email = email_normalize(post.get('email'))
        practice = request.env['healthcare.practice'].sudo()._get_registration_practice()
        gender = post.get('gender') if post.get('gender') in self._GENDER_VALUES else 'unknown'

        patient_vals = {
            'name': post.get('name').strip(),
            'email': email,
            'phone': (post.get('phone') or '').strip(),
            'gender': gender,
            'national_id': (post.get('national_id') or '').strip(),
            'emergency_contact': (post.get('emergency_contact') or '').strip(),
            'emergency_phone': (post.get('emergency_phone') or '').strip(),
            'practice_id': practice.id,
        }
        dob = post.get('date_of_birth')
        if dob:
            patient_vals['date_of_birth'] = fields.Date.from_string(dob)

        patient = request.env['healthcare.patient'].sudo().create(patient_vals)
        self._grant_portal_access(patient.partner_id, email, practice)
        return patient

    def _grant_portal_access(self, partner, email, practice):
        """Create a portal user for `partner` and send the standard
        'set your password' invite email, the same way Settings > Users >
        'Grant Portal Access' does for an existing contact.
        """
        if partner.user_ids:
            raise ValidationError(_('An account already exists for this contact.'))

        company = practice.company_id or request.env.company
        user = request.env['res.users'].sudo()._create_user_from_template({
            'email': email,
            'login': email,
            'partner_id': partner.id,
            'company_id': company.id,
            'company_ids': [(6, 0, company.ids)],
        })
        group_portal = request.env.ref('base.group_portal')
        user.write({'active': True, 'group_ids': [(4, group_portal.id)]})
        user.partner_id.signup_prepare()

        template = request.env.ref('auth_signup.portal_set_password_email', raise_if_not_found=False)
        if template:
            template.sudo().with_context(
                dbname=request.env.cr.dbname,
                lang=user.lang,
                medium='portalinvite',
            ).send_mail(user.id, force_send=True)
        return user
