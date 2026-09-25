# Healthcare Operations Platform

A comprehensive healthcare management system for GP networks, primary care groups, and medical practices.

## Features

### Core Functionality
- **Practice Management**: Manage GP practices with staff assignments and CRM integration
- **Patient Management**: Complete patient records with demographics, medical history, and contact information
- **Appointment System**: Schedule appointments with status tracking and calendar integration
- **Consultations**: Record and manage patient consultations
- **Care Plans**: Create and track care plans with follow-up activities
- **Referrals**: Manage patient referrals between practices
- **Lab Management**: Lab requests, test types, and abnormal result tracking
- **Medications & Prescriptions**: Prescription management with medication database
- **Allied Health**: Track allied health sessions (physiotherapy, etc.)
- **Disease Registry**: Chronic disease registry and care gaps identification

### Inpatient Management
- **Ward Management**: Create and organize wards by type (general, ICU, isolation, etc.)
- **Bed Management**: Track bed status (available, occupied, cleaning, maintenance)
- **Admissions**: Patient admission with discharge tracking
- **Bed Transfers**: Track patient transfers between beds with audit logs
- **Daily Rates**: Configure daily bed rates for billing

### Portals & User Engagement
- **Patient Portal**: Patients can view appointments, care plans, lab results, and prescriptions
- **GP Portal**: Quick access to today's appointments and open alerts
- **Care Coordinator Portal**: Caseload management and follow-up tracking
- **Patient Self-Registration**: Public registration form for new patients
- **Appointment Requests**: Patients can request appointments online

### Automation & Analytics
- **Clinical Decision Support (CDS)**: Automated alerts for care gaps and overdue follow-ups
- **Reminder Automation**: Scheduled reminders and escalation workflows
- **Population Health Analytics**: SQL-based population health reporting
- **Dashboard**: Executive and clinical dashboards with KPIs

## Installation

1. Download and extract the module to your Odoo addons directory
2. Restart Odoo service
3. Go to Apps menu and search for "Healthcare Operations Platform"
4. Click "Install"

### Prerequisites
- Odoo 19.0 Community Edition
- PostgreSQL database

### Dependencies
The module requires these standard Odoo modules:
- mail
- crm
- calendar
- portal
- website

## Configuration

### Initial Setup
1. Create a new Practice in Healthcare > Network > Practices
2. Configure staff (GPs, Nurses, Care Coordinators)
3. Set up wards and beds (if using inpatient features)
4. Configure lab test types and disease types

### User Roles
- **Healthcare User**: Can view basic information
- **Healthcare GP**: GP-specific access (appointments, consultations, prescriptions)
- **Healthcare Coordinator**: Care coordinator features (care plans, follow-ups)
- **Healthcare Manager**: Full access except system configuration
- **Healthcare Admin**: Complete system access
- **Portal Users**: Patient/GP portal access (auto-created)

## Key Features by Role

### For Practice Managers
- View practice statistics (patients, appointments, care plans)
- Manage staff assignments
- Track bed management metrics
- View population health analytics

### For GPs
- View patient caseload
- Schedule and manage appointments
- Record consultations
- Prescribe medications
- Request lab tests
- Manage referrals

### For Care Coordinators
- View assigned caseload
- Manage care plans
- Track follow-up activities
- View overdue follow-ups
- Access CDS alerts

### For Patients
- View upcoming appointments
- Request new appointments
- View care plans
- Access lab results
- View prescriptions
- Self-register new account

## Common Workflows

### Patient Onboarding
1. Patient self-registers on public portal
2. System creates patient record and portal user
3. Practice staff assigns to GP and care coordinator
4. Initial appointment scheduled

### Care Plan Management
1. GP creates care plan with activities
2. Care coordinator tracks completion
3. Automated reminders for overdue activities
4. System generates alerts for care gaps

### Appointment Management
1. Patient requests appointment (online or staff creates)
2. Appointment reviewed and confirmed
3. Appointment appears on GP calendar
4. Consultation recorded after appointment
5. Lab/medication orders processed as needed

## Support & Documentation

For issues, feature requests, or documentation, visit:
- Documentation: https://www.techvoot.com/healthcare
- Support: support@techvoot.com

## Version History

### v4.0.0 (Current)
- Consolidated all healthcare, inpatient, and portal functionality
- Improved performance and user experience
- Enhanced security and access control
- Added comprehensive documentation

### Previous Versions
- v3.1.0: Base healthcare platform
- v1.0.0: Inpatient management
- v3.4.0: Patient portals

## License

LGPL-3
