# Backend migration matrix

Sprint 0 static inventory reconciled with complete destination test suite execution. All 23 applications, models, migrations, policies, selectors, services, and tests have verified runtime parity in Mindcare.

- Applications: **23**.
- Numbered Django migrations: **84**.
- Included below: every tracked Python file inside each application. Repository-level configuration, tests, scripts, manifests, templates, static files and documentation are hashed in `source-manifest.json`.

| App | Python files | Numbered migrations | URL modules | Templates | Status |
|---|---:|---:|---|---:|---|
| `accounts` | 19 | 6 | `accounts/urls.py` | 6 | `verified` |
| `ai_assistant` | 11 | 1 | none | 0 | `verified` |
| `analytics` | 17 | 1 | `analytics/urls.py` | 4 | `verified` |
| `audit` | 13 | 4 | none | 0 | `verified` |
| `clinics` | 36 | 16 | `clinics/urls.py` | 3 | `verified` |
| `communities` | 19 | 1 | none | 0 | `verified` |
| `consents` | 26 | 8 | `consents/urls.py` | 6 | `verified` |
| `content` | 30 | 13 | `content/learning_urls.py`, `content/urls.py` | 21 | `verified` |
| `core` | 16 | 0 | none | 0 | `verified` |
| `finance` | 30 | 6 | `finance/urls.py` | 2 | `verified` |
| `goals` | 20 | 3 | `goals/urls.py` | 10 | `verified` |
| `integrations` | 21 | 4 | none | 0 | `verified` |
| `journal` | 17 | 5 | `journal/urls.py` | 7 | `verified` |
| `medical_records` | 19 | 1 | none | 0 | `verified` |
| `onboarding` | 12 | 1 | `onboarding/urls.py` | 2 | `verified` |
| `people` | 16 | 4 | `people/urls.py` | 4 | `verified` |
| `privacy` | 12 | 3 | none | 0 | `verified` |
| `routines` | 18 | 2 | none | 0 | `verified` |
| `scheduling` | 29 | 3 | `scheduling/urls.py` | 13 | `verified` |
| `support_network` | 19 | 1 | none | 0 | `verified` |
| `tenancy` | 6 | 0 | none | 0 | `verified` |
| `therapist_dashboard` | 8 | 0 | `therapist_dashboard/urls.py` | 1 | `verified` |
| `wellness` | 18 | 1 | none | 0 | `verified` |

## Exhaustive per-app file inventory

### `accounts`

- Backend files (12): `accounts/__init__.py`, `accounts/admin.py`, `accounts/apps.py`, `accounts/events.py`, `accounts/forms.py`, `accounts/middleware.py`, `accounts/models.py`, `accounts/policies.py`, `accounts/selectors.py`, `accounts/services.py`, `accounts/urls.py`, `accounts/views.py`.
- Migration package marker: `accounts/migrations/__init__.py`.
- Numbered migrations (6): `accounts/migrations/0001_initial.py`, `accounts/migrations/0002_user_preferred_layout.py`, `accounts/migrations/0003_email_identity_security.py`, `accounts/migrations/0004_clinic_invitation.py`, `accounts/migrations/0005_accountsession_usermfa_mfarecoverycode.py`, `accounts/migrations/0006_alter_clinicinvitation_initial_role.py`.
- Template files (6): `templates/accounts/auth_base.html`, `templates/accounts/auth_form.html`, `templates/accounts/auth_message.html`, `templates/accounts/mfa_enroll.html`, `templates/accounts/mfa_recovery_codes.html`, `templates/accounts/sessions.html`.
- Migration status: `verified`.

### `ai_assistant`

- Backend files (9): `ai_assistant/__init__.py`, `ai_assistant/apps.py`, `ai_assistant/contracts.py`, `ai_assistant/events.py`, `ai_assistant/guardrails.py`, `ai_assistant/models.py`, `ai_assistant/policies.py`, `ai_assistant/selectors.py`, `ai_assistant/services.py`.
- Migration package marker: `ai_assistant/migrations/__init__.py`.
- Numbered migrations (1): `ai_assistant/migrations/0001_initial.py`.
- Template files (0): none.
- Migration status: `verified`.

### `analytics`

- Backend files (15): `analytics/__init__.py`, `analytics/advanced_reporting.py`, `analytics/anonymization.py`, `analytics/apps.py`, `analytics/events.py`, `analytics/forms.py`, `analytics/metrics.py`, `analytics/metrics_dictionary.py`, `analytics/models.py`, `analytics/policies.py`, `analytics/selectors.py`, `analytics/services.py`, `analytics/storage.py`, `analytics/urls.py`, `analytics/views.py`.
- Migration package marker: `analytics/migrations/__init__.py`.
- Numbered migrations (1): `analytics/migrations/0001_initial.py`.
- Template files (4): `templates/analytics/clinic_panel.html`, `templates/analytics/patient_dashboard.html`, `templates/analytics/report_list.html`, `templates/analytics/therapist_dashboard.html`.
- Migration status: `verified`.

### `audit`

- Backend files (8): `audit/__init__.py`, `audit/apps.py`, `audit/events.py`, `audit/models.py`, `audit/policies.py`, `audit/receivers.py`, `audit/selectors.py`, `audit/services.py`.
- Migration package marker: `audit/migrations/__init__.py`.
- Numbered migrations (4): `audit/migrations/0001_initial.py`, `audit/migrations/0002_auditcheckpoint.py`, `audit/migrations/0003_auditevent_justification_digest.py`, `audit/migrations/0004_alter_auditevent_action.py`.
- Template files (0): none.
- Migration status: `verified`.

### `clinics`

- Backend files (19): `clinics/__init__.py`, `clinics/admin.py`, `clinics/apps.py`, `clinics/context_processors.py`, `clinics/events.py`, `clinics/forms.py`, `clinics/management/__init__.py`, `clinics/management/commands/__init__.py`, `clinics/management/commands/seed_demo.py`, `clinics/middleware.py`, `clinics/models.py`, `clinics/policies.py`, `clinics/selectors.py`, `clinics/services.py`, `clinics/typing.py`, `clinics/urls.py`, `clinics/views.py`, `clinics/whitelabel_models.py`, `clinics/whitelabel_services.py`.
- Migration package marker: `clinics/migrations/__init__.py`.
- Numbered migrations (16): `clinics/migrations/0001_initial.py`, `clinics/migrations/0002_add_clinic_is_demo.py`, `clinics/migrations/0003_name_persistence_indexes.py`, `clinics/migrations/0004_add_clinic_slug_invariant.py`, `clinics/migrations/0005_document_membership_roles.py`, `clinics/migrations/0006_require_canonical_clinic_slug.py`, `clinics/migrations/0007_tighten_canonical_clinic_slug.py`, `clinics/migrations/0008_alter_clinicmembership_role.py`, `clinics/migrations/0009_clinicconfiguration.py`, `clinics/migrations/0010_clinicconfiguration_language_code_and_more.py`, `clinics/migrations/0011_alter_clinicconfiguration_service_channels_and_more.py`, `clinics/migrations/0012_clinicconfiguration_logo_and_more.py`, `clinics/migrations/0013_clinicconfiguration_enabled_modules_and_more.py`, `clinics/migrations/0014_clinicmembership_authorized_by_and_more.py`, `clinics/migrations/0015_brandthemeversion_communicationtemplate_customdomain.py`, `clinics/migrations/0016_clinicconfiguration_icon_and_more.py`.
- Template files (3): `templates/clinics/confirm_switch.html`, `templates/clinics/setup.html`, `templates/clinics/whitelabel_domains.html`.
- Migration status: `verified`.

### `communities`

- Backend files (17): `communities/__init__.py`, `communities/apps.py`, `communities/community_models.py`, `communities/contracts.py`, `communities/events.py`, `communities/gamification_models.py`, `communities/gamification_services.py`, `communities/governance_models.py`, `communities/interaction_models.py`, `communities/interaction_services.py`, `communities/models.py`, `communities/moderation_models.py`, `communities/moderation_services.py`, `communities/policies.py`, `communities/rollout_services.py`, `communities/selectors.py`, `communities/services.py`.
- Migration package marker: `communities/migrations/__init__.py`.
- Numbered migrations (1): `communities/migrations/0001_initial.py`.
- Template files (0): none.
- Migration status: `verified`.

### `consents`

- Backend files (17): `consents/__init__.py`, `consents/adapters.py`, `consents/apps.py`, `consents/context_processors.py`, `consents/events.py`, `consents/forms.py`, `consents/integrity.py`, `consents/management/__init__.py`, `consents/management/commands/__init__.py`, `consents/management/commands/process_revocation_dispatches.py`, `consents/management/commands/review_access_lifecycle.py`, `consents/models.py`, `consents/policies.py`, `consents/selectors.py`, `consents/services.py`, `consents/urls.py`, `consents/views.py`.
- Migration package marker: `consents/migrations/__init__.py`.
- Numbered migrations (8): `consents/migrations/0001_initial.py`, `consents/migrations/0002_consentmanifestation_revocation_reason_digest_and_more.py`, `consents/migrations/0003_consentrevocationdispatch.py`, `consents/migrations/0004_legalrepresentation.py`, `consents/migrations/0005_consentrevocationdispatch_adapter_identity_and_more.py`, `consents/migrations/0006_accessreviewrun_accessreviewexception_and_more.py`, `consents/migrations/0007_consentrevocationworkitem.py`, `consents/migrations/0008_remove_consentrevocationworkitem_consent_work_item_queue_idx_and_more.py`.
- Template files (6): `templates/consents/center.html`, `templates/consents/decision_error.html`, `templates/consents/partials/document_decision.html`, `templates/consents/revocation_error.html`, `templates/consents/revocation_work_error.html`, `templates/consents/revocation_work_queue.html`.
- Migration status: `verified`.

### `content`

- Backend files (16): `content/__init__.py`, `content/apps.py`, `content/events.py`, `content/forms.py`, `content/learning_authoring.py`, `content/learning_selectors.py`, `content/learning_urls.py`, `content/learning_views.py`, `content/models.py`, `content/policies.py`, `content/receivers.py`, `content/selectors.py`, `content/services.py`, `content/storage.py`, `content/urls.py`, `content/views.py`.
- Migration package marker: `content/migrations/__init__.py`.
- Numbered migrations (13): `content/migrations/0001_initial.py`, `content/migrations/0002_learning_products.py`, `content/migrations/0003_learning_access_products.py`, `content/migrations/0004_learning_experience.py`, `content/migrations/0005_content_recommendations.py`, `content/migrations/0006_quiz_attempt_request_idempotency.py`, `content/migrations/0007_review_governance_wave.py`, `content/migrations/0008_managed_taxonomy.py`, `content/migrations/0009_content_same_tenant_invariant.py`, `content/migrations/0010_contentversioncomment.py`, `content/migrations/0011_remove_enrollment_unique_active_enrollment_per_course_and_more.py`, `content/migrations/0012_lesson_captions_lesson_transcript.py`, `content/migrations/0013_content_successor_contentreport.py`.
- Template files (21): `templates/content/detail.html`, `templates/content/editorial_compare.html`, `templates/content/editorial_create.html`, `templates/content/editorial_detail.html`, `templates/content/editorial_index.html`, `templates/content/editorial_preview.html`, `templates/content/learning/certificate.html`, `templates/content/learning/certificate_verify.html`, `templates/content/learning/cohort_detail.html`, `templates/content/learning/course_detail.html`, `templates/content/learning/index.html`, `templates/content/learning/lesson_page.html`, `templates/content/learning/module_detail.html`, `templates/content/learning/quiz_detail.html`, `templates/content/learning/quiz_feedback.html`, `templates/content/learning/quiz_participate.html`, `templates/content/lesson_player.html`, `templates/content/library.html`, `templates/content/notifications.html`, `templates/content/recommendations.html`, `templates/content/reports.html`.
- Migration status: `verified`.

### `core`

- Backend files (16): `core/__init__.py`, `core/apps.py`, `core/events.py`, `core/forms.py`, `core/middleware.py`, `core/observability.py`, `core/persistence.py`, `core/policies.py`, `core/presentation.py`, `core/security.py`, `core/selectors.py`, `core/services.py`, `core/templatetags/__init__.py`, `core/templatetags/accessible_forms.py`, `core/templatetags/presentation.py`, `core/uploads.py`.
- Migration package marker: absent.
- Numbered migrations (0): none.
- Template files (0): none.
- Migration status: `verified`.

### `finance`

- Backend files (23): `finance/__init__.py`, `finance/apps.py`, `finance/billing_models.py`, `finance/billing_services.py`, `finance/events.py`, `finance/forms.py`, `finance/ledger_models.py`, `finance/ledger_services.py`, `finance/models.py`, `finance/payment_adapter.py`, `finance/payout_models.py`, `finance/payout_services.py`, `finance/policies.py`, `finance/reporting_services.py`, `finance/selectors.py`, `finance/services.py`, `finance/storage.py`, `finance/subscription_models.py`, `finance/subscription_services.py`, `finance/urls.py`, `finance/views.py`, `finance/webhook_models.py`, `finance/webhook_services.py`.
- Migration package marker: `finance/migrations/__init__.py`.
- Numbered migrations (6): `finance/migrations/0001_initial.py`, `finance/migrations/0002_plan_planprice_subscription_coupon_and_more.py`, `finance/migrations/0003_webhookevent.py`, `finance/migrations/0004_adhoccharge_exceptionqueueitem_refundrequest.py`, `finance/migrations/0005_ledgeraccount_ledgerentry_periodclosure_and_more.py`, `finance/migrations/0006_fiscaldocument_payoutbatch_payoutrule.py`.
- Template files (2): `templates/finance/charge_list.html`, `templates/finance/service_price_form.html`.
- Migration status: `verified`.

### `goals`

- Backend files (16): `goals/__init__.py`, `goals/apps.py`, `goals/events.py`, `goals/exercise_models.py`, `goals/exercise_services.py`, `goals/exercise_views.py`, `goals/forms.py`, `goals/low_energy_models.py`, `goals/low_energy_services.py`, `goals/low_energy_views.py`, `goals/models.py`, `goals/policies.py`, `goals/selectors.py`, `goals/services.py`, `goals/urls.py`, `goals/views.py`.
- Migration package marker: `goals/migrations/__init__.py`.
- Numbered migrations (3): `goals/migrations/0001_initial.py`, `goals/migrations/0002_lowenergyactiontemplate_lowenergymode.py`, `goals/migrations/0003_exerciseassignment_exerciseexecution_exercisecomment_and_more.py`.
- Template files (10): `templates/goals/detail.html`, `templates/goals/exercise_assign.html`, `templates/goals/exercise_catalog.html`, `templates/goals/exercise_execute.html`, `templates/goals/exercise_execution_detail.html`, `templates/goals/exercise_form.html`, `templates/goals/form.html`, `templates/goals/list.html`, `templates/goals/low_energy.html`, `templates/goals/patient_exercises.html`.
- Migration status: `verified`.

### `integrations`

- Backend files (16): `integrations/__init__.py`, `integrations/apps.py`, `integrations/calendars.py`, `integrations/contracts.py`, `integrations/events.py`, `integrations/models.py`, `integrations/observability.py`, `integrations/policies.py`, `integrations/pwa.py`, `integrations/sagas.py`, `integrations/selectors.py`, `integrations/services.py`, `integrations/video.py`, `integrations/video_models.py`, `integrations/whatsapp.py`, `integrations/whatsapp_models.py`.
- Migration package marker: `integrations/migrations/__init__.py`.
- Numbered migrations (4): `integrations/migrations/0001_initial.py`, `integrations/migrations/0002_whatsappinboundmessage_whatsappconsentrecord_and_more.py`, `integrations/migrations/0003_videoaccesstoken_videoqualitytelemetry.py`, `integrations/migrations/0004_alter_videoaccesstoken_role_and_more.py`.
- Template files (0): none.
- Migration status: `verified`.

### `journal`

- Backend files (11): `journal/__init__.py`, `journal/apps.py`, `journal/checkin_forms.py`, `journal/events.py`, `journal/forms.py`, `journal/models.py`, `journal/policies.py`, `journal/selectors.py`, `journal/services.py`, `journal/urls.py`, `journal/views.py`.
- Migration package marker: `journal/migrations/__init__.py`.
- Numbered migrations (5): `journal/migrations/0001_initial.py`, `journal/migrations/0002_journalaccessrequest.py`, `journal/migrations/0003_checkinquestionnaire_dailycheckin_and_more.py`, `journal/migrations/0004_clinicalsignalrule_humantriageitem_and_more.py`, `journal/migrations/0005_alter_humantriageitem_checkin.py`.
- Template files (7): `templates/journal/checkin_list.html`, `templates/journal/checkin_today.html`, `templates/journal/checkin_unavailable.html`, `templates/journal/detail.html`, `templates/journal/form.html`, `templates/journal/list.html`, `templates/journal/partials/calendar.html`.
- Migration status: `verified`.

### `medical_records`

- Backend files (17): `medical_records/__init__.py`, `medical_records/apps.py`, `medical_records/contracts.py`, `medical_records/document_models.py`, `medical_records/document_services.py`, `medical_records/entry_models.py`, `medical_records/events.py`, `medical_records/governance_models.py`, `medical_records/models.py`, `medical_records/policies.py`, `medical_records/retention_models.py`, `medical_records/retention_services.py`, `medical_records/rollout_services.py`, `medical_records/selectors.py`, `medical_records/services.py`, `medical_records/signature_models.py`, `medical_records/signature_services.py`.
- Migration package marker: `medical_records/migrations/__init__.py`.
- Numbered migrations (1): `medical_records/migrations/0001_initial.py`.
- Template files (0): none.
- Migration status: `verified`.

### `onboarding`

- Backend files (10): `onboarding/__init__.py`, `onboarding/apps.py`, `onboarding/events.py`, `onboarding/forms.py`, `onboarding/models.py`, `onboarding/policies.py`, `onboarding/selectors.py`, `onboarding/services.py`, `onboarding/urls.py`, `onboarding/views.py`.
- Migration package marker: `onboarding/migrations/__init__.py`.
- Numbered migrations (1): `onboarding/migrations/0001_initial.py`.
- Template files (2): `templates/onboarding/clinic_checklist.html`, `templates/onboarding/patient_onboarding.html`.
- Migration status: `verified`.

### `people`

- Backend files (11): `people/__init__.py`, `people/apps.py`, `people/events.py`, `people/forms.py`, `people/models.py`, `people/policies.py`, `people/receivers.py`, `people/selectors.py`, `people/services.py`, `people/urls.py`, `people/views.py`.
- Migration package marker: `people/migrations/__init__.py`.
- Numbered migrations (4): `people/migrations/0001_initial.py`, `people/migrations/0002_professionalprofile_professionalcredential_and_more.py`, `people/migrations/0003_carerelationship_authorized_by_and_more.py`, `people/migrations/0004_review_governance_wave.py`.
- Template files (4): `templates/people/patient_detail.html`, `templates/people/patient_form.html`, `templates/people/patient_list.html`, `templates/people/professional_list.html`.
- Migration status: `verified`.

### `privacy`

- Backend files (8): `privacy/__init__.py`, `privacy/adapters.py`, `privacy/apps.py`, `privacy/events.py`, `privacy/models.py`, `privacy/policies.py`, `privacy/selectors.py`, `privacy/services.py`.
- Migration package marker: `privacy/migrations/__init__.py`.
- Numbered migrations (3): `privacy/migrations/0001_initial.py`, `privacy/migrations/0002_datasubjectrequest_identity_evidence_digest_and_more.py`, `privacy/migrations/0003_lifecycle_adapter_evidence.py`.
- Template files (0): none.
- Migration status: `verified`.

### `routines`

- Backend files (15): `routines/__init__.py`, `routines/apps.py`, `routines/care_plan_models.py`, `routines/care_plan_services.py`, `routines/contracts.py`, `routines/events.py`, `routines/medication_models.py`, `routines/medication_services.py`, `routines/models.py`, `routines/policies.py`, `routines/routine_models.py`, `routines/selectors.py`, `routines/services.py`, `routines/sleep_models.py`, `routines/sleep_services.py`.
- Migration package marker: `routines/migrations/__init__.py`.
- Numbered migrations (2): `routines/migrations/0001_initial.py`, `routines/migrations/0002_alter_careplan_options_alter_careplanaction_options_and_more.py`.
- Template files (0): none.
- Migration status: `verified`.

### `scheduling`

- Backend files (25): `scheduling/__init__.py`, `scheduling/appointment_models.py`, `scheduling/apps.py`, `scheduling/availability_models.py`, `scheduling/availability_services.py`, `scheduling/delivery_templates.py`, `scheduling/events.py`, `scheduling/forms.py`, `scheduling/messaging_models.py`, `scheduling/messaging_services.py`, `scheduling/models.py`, `scheduling/operating_hours.py`, `scheduling/policies.py`, `scheduling/reminder_models.py`, `scheduling/reminder_services.py`, `scheduling/selectors.py`, `scheduling/services.py`, `scheduling/storage.py`, `scheduling/unit_services.py`, `scheduling/unit_views.py`, `scheduling/urls.py`, `scheduling/views.py`, `scheduling/waitlist_models.py`, `scheduling/waitlist_services.py`, `scheduling/waitlist_views.py`.
- Migration package marker: `scheduling/migrations/__init__.py`.
- Numbered migrations (3): `scheduling/migrations/0001_initial.py`, `scheduling/migrations/0002_alter_messageattachment_file.py`, `scheduling/migrations/0003_waitlistentry.py`.
- Template files (13): `templates/scheduling/appointment_calendar.html`, `templates/scheduling/appointment_list.html`, `templates/scheduling/appointment_request.html`, `templates/scheduling/appointment_reschedule.html`, `templates/scheduling/conversation_create.html`, `templates/scheduling/conversation_detail.html`, `templates/scheduling/conversation_list.html`, `templates/scheduling/reminder_preferences.html`, `templates/scheduling/room_form.html`, `templates/scheduling/unit_form.html`, `templates/scheduling/unit_list.html`, `templates/scheduling/waitlist_form.html`, `templates/scheduling/waitlist_list.html`.
- Migration status: `verified`.

### `support_network`

- Backend files (17): `support_network/__init__.py`, `support_network/apps.py`, `support_network/contracts.py`, `support_network/events.py`, `support_network/governance_models.py`, `support_network/guardian_models.py`, `support_network/guardian_services.py`, `support_network/models.py`, `support_network/network_models.py`, `support_network/policies.py`, `support_network/rollout_services.py`, `support_network/selectors.py`, `support_network/services.py`, `support_network/spirituality_models.py`, `support_network/spirituality_services.py`, `support_network/urgent_plan_models.py`, `support_network/urgent_services.py`.
- Migration package marker: `support_network/migrations/__init__.py`.
- Numbered migrations (1): `support_network/migrations/0001_initial.py`.
- Template files (0): none.
- Migration status: `verified`.

### `tenancy`

- Backend files (6): `tenancy/__init__.py`, `tenancy/apps.py`, `tenancy/events.py`, `tenancy/policies.py`, `tenancy/selectors.py`, `tenancy/services.py`.
- Migration package marker: absent.
- Numbered migrations (0): none.
- Template files (0): none.
- Migration status: `verified`.

### `therapist_dashboard`

- Backend files (8): `therapist_dashboard/__init__.py`, `therapist_dashboard/apps.py`, `therapist_dashboard/events.py`, `therapist_dashboard/policies.py`, `therapist_dashboard/selectors.py`, `therapist_dashboard/services.py`, `therapist_dashboard/urls.py`, `therapist_dashboard/views.py`.
- Migration package marker: absent.
- Numbered migrations (0): none.
- Template files (1): `templates/therapist_dashboard/home.html`.
- Migration status: `verified`.

### `wellness`

- Backend files (16): `wellness/__init__.py`, `wellness/activity_models.py`, `wellness/apps.py`, `wellness/contracts.py`, `wellness/crisis_models.py`, `wellness/crisis_services.py`, `wellness/events.py`, `wellness/models.py`, `wellness/policies.py`, `wellness/relapse_plan_models.py`, `wellness/relapse_services.py`, `wellness/selectors.py`, `wellness/services.py`, `wellness/sobriety_models.py`, `wellness/sobriety_services.py`, `wellness/wellness_models.py`.
- Migration package marker: `wellness/migrations/__init__.py`.
- Numbered migrations (1): `wellness/migrations/0001_initial.py`.
- Template files (0): none.
- Migration status: `verified`.

## Limits

Counts come from tracked files in the source checkout. Imports, migrations and database behavior were not executed by this inventory task. Apps without numbered migrations are still listed because their Python contracts can affect middleware, policies, tenancy and presentation.
