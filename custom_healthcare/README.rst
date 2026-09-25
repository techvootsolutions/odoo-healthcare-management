===============================
Healthcare Operations Platform
===============================

.. image:: https://img.shields.io/static/v1.svg?label=license&message=LGPL%20v3&color=blue
   :target: https://www.gnu.org/licenses/lgpl-3.0
   :alt: License: LGPL v3

.. image:: https://img.shields.io/static/v1.svg?label=maturity&message=Beta&color=yellow
   :alt: Maturity: Beta

Odoo 19 application for GP networks and primary-care groups operating a
value-based / care-coordination model. Provides practice network management,
patient registry, appointments, EMR-lite consultations, care plans with
task generation, referrals, chronic disease registry, ops/clinical KPI
dashboards, lab requests/results, prescriptions with allergy warnings, and
allied professional session workflows. Links CRM opportunities to practice
onboarding.

What this module does NOT do
============================

* Does not replace a full hospital HIS/EMR (wards, theatre, billing engines)
* Does not include deep medical-scheme claims adjudication
* Does not include lab instrument interfaces or pharmacy dispensing robots
* Does not ship patient/GP/scheme portals in v2
* Does not provide full clinical decision-support rule engines

Configuration
=============

To configure this module, you need to:

#. Install **Healthcare Operations Platform** (`custom_healthcare`).
#. Assign users to Healthcare groups (User, Care Coordinator, GP / Clinician,
   Ops / Clinical Manager, Administrator).
#. Review **Healthcare > Configuration > Disease Types**.
#. Create practices under **Healthcare > Network > Practices**.

Usage
=====

To use this module, you need to:

#. Open **Healthcare > Dashboards** for ops/clinical KPI tiles.
#. Register patients and assign practice, GP, and care coordinator.
#. Schedule appointments and start consultations from the appointment form.
#. Activate care plans to generate follow-up activities.
#. Enrol patients in the chronic disease registry and track care gaps.
#. From CRM opportunities, use **Practice** to create/link onboarding records.

Known Issues / Roadmap
======================

* Demo dataset is story-sized; heavy seeding (500+ patients) is a follow-up.
* Portals and CDS automation planned for later phases.
* Graph/pivot analytics rely on native Odoo views; Spreadsheet dashboards optional.
* Allergy checks are keyword-based (not a full drug-interaction database).
* Install `custom_healthcare_portal` for Patient/GP/Coordinator portal pages.

Credits
=======

Contributors
------------

* Techvoot

Maintainer
----------

This repository is maintained by Techvoot.
