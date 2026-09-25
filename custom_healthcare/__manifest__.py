# -*- coding: utf-8 -*-
{   'application': True,
    'assets': {   'web.assets_backend': [   'custom_healthcare/static/src/dashboard/healthcare_chart.js',
                                            'custom_healthcare/static/src/dashboard/healthcare_dashboard.js',
                                            'custom_healthcare/static/src/dashboard/healthcare_dashboard.xml',
                                            'custom_healthcare/static/src/dashboard/healthcare_dashboard.scss'],
                  'web.assets_web_dark': [   'custom_healthcare/static/src/dashboard/healthcare_dashboard.dark.scss']},
    'author': 'Techvoot',
    'auto_install': False,
    'category': 'Healthcare',
    'data': [   'security/healthcare_groups.xml',
                'security/ir.model.access.csv',
                'security/healthcare_security.xml',
                'security/healthcare_inpatient_security.xml',
                'security/healthcare_portal_security.xml',
                'data/ir_sequence_data.xml',
                'data/healthcare_disease_data.xml',
                'data/healthcare_clinical_data.xml',
                'data/ir_cron_data.xml',
                'views/healthcare_practice_views.xml',
                'views/healthcare_patient_views.xml',
                'views/healthcare_appointment_views.xml',
                'views/healthcare_consultation_views.xml',
                'views/healthcare_care_plan_views.xml',
                'views/healthcare_referral_views.xml',
                'views/healthcare_disease_views.xml',
                'views/healthcare_lab_views.xml',
                'views/healthcare_medication_views.xml',
                'views/healthcare_allied_views.xml',
                'views/healthcare_alert_views.xml',
                'views/healthcare_dashboard_views.xml',
                'views/crm_lead_views.xml',
                'views/healthcare_ward_views.xml',
                'views/healthcare_room_views.xml',
                'views/healthcare_bed_views.xml',
                'views/healthcare_admission_views.xml',
                'views/healthcare_portal_templates.xml',
                'views/website_snippets_patient_register.xml',
                'wizard/healthcare_demo_seeder_views.xml',
                'wizard/healthcare_bed_transfer_wizard_views.xml',
                'report/healthcare_admission_report.xml',
                'views/healthcare_menus.xml'],
    'demo': [   'demo/healthcare_demo.xml',
                'demo/healthcare_inpatient_demo.xml',
                'demo/healthcare_portal_demo.xml'],
    'depends': ['mail', 'crm', 'calendar', 'portal', 'website'],
    'description': '\n'
                   'Healthcare Operations Platform (v4 - Consolidated)\n'
                   '==================================================\n'
                   'Complete healthcare ERP layer for GP networks and primary-care groups:\n'
                   '\n'
                   '* Practice management and CRM-linked onboarding\n'
                   '* Patient registry, appointments, consultations, referrals\n'
                   '* Care plans, coordinator cockpit, chronic disease registry\n'
                   '* Lab requests/results, prescriptions, allied sessions\n'
                   '* CDS alerts + scheduled reminder/escalation automation\n'
                   '* Population health analytics (SQL report)\n'
                   '* Inpatient / bed / ward / admission management with bed transfers\n'
                   '* Patient, GP, and care coordinator portals\n'
                   '* Public patient self-registration\n'
                   '* Demo data seeder wizard\n'
                   '* Ops / clinical KPI dashboards\n'
                   '    ',
    'external_dependencies': {},
    'images': ['static/description/banner.gif'],
    'installable': True,
    'license': 'LGPL-3',
    'name': 'Healthcare Operations Platform',
    'post_init_hook': 'post_init_hook',
    'post_load': 'post_load',
    'summary': 'GP network / VBHC care coordination platform with inpatient management and portals',
    'version': '19.0.1.0.0',
    'website': 'https://www.techvoot.com'}
