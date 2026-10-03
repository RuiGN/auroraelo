# Clinic authorization matrix

Technical action identifiers remain in en-US. User-facing labels remain in pt-BR.
All decisions are evaluated on the backend and default to denial.

| Action | Clinic admin | Therapist | Administrative staff | Patient | Additional conditions |
|---|---:|---:|---:|---:|---|
| `clinic.read` | Yes | Yes | Yes | No | Active user, clinic and membership |
| `clinic.manage` | Yes | No | No | No | Active user, clinic and membership |
| `professionals.manage` | Yes | No | No | No | Active user, clinic and membership |
| `patients.create` | Yes | No | Yes | No | Active user, clinic and membership |
| `patient.demographics.read` | Yes | Yes | Yes | No | Patient must have a current patient membership in the same clinic; resource must be active |
| `patient.clinical.read` | No | Yes | No | No | Patient must have a current patient membership and an active, dated therapist-patient relationship in the same clinic; resource must be active |
| `audit.read` | Yes | No | No | No | Active user, clinic and membership; audit-specific policy still applies |
| `invitation.issue` | Yes | No | No | No | Active user, clinic and membership |
| `invitation.revoke` | Yes | No | No | No | Active user, clinic and membership |
| `membership.enumerate` | Yes | No | No | No | Active user, clinic and membership |
| `membership.update` | Yes | No | No | No | Target membership must belong to the active clinic |
| `aftercare.read` | Yes | No | Yes | No | Concierge e acompanhamento pós-alta; sem conteúdo clínico. Active user, clinic and membership |
| `aftercare.manage` | Yes | No | Yes | No | Registrar alta, contatos, família e pedidos. A família só é contatada com consentimento do paciente registrado |
| `aftercare.rules.manage` | Yes | No | No | No | Régua de comunicação da clínica; cada alteração cria nova versão |
| `mfa.reset` | Yes | No | No | No | Target must belong to the active clinic; reset is audited and revokes sessions |

## Enforcement rules

1. The authenticated identity has no global business role. Roles are dated `ClinicMembership` records.
2. An inactive identity, clinic, membership or resource grants no access.
3. Unknown action identifiers are denied.
4. A patient identifier is resolved through a tenant-scoped membership before the user record is returned.
5. Clinical access requires an active `CareRelationship`; demographic access does not imply clinical access.
6. Altering a URL or UUID cannot move authorization to another tenant or bypass the relationship requirement.
7. Interface visibility is not an authorization control. Services, selectors and policies enforce the same decision on the server.

## Patient app (token) access

The post-discharge patient app does not use the matrix above: it holds no clinic role other
than `patient`, and every route acts on the patient's own data only.

- A token session is issued only to an identity with an active `patient` membership and a
  linked patient profile. The server fixes the clinic and the profile at login; the client
  cannot name either (`X-Clinic-ID`, query and body identifiers are ignored or absent, and
  `tests/test_mobile_api_contract.py` fails any route that accepts them).
- Membership, role, clinic, user status and credential changes are re-checked on every
  request; any loss ends the session.
- Domain services that authorize only by clinic are never called with a client-supplied id
  directly: each route first resolves the object through a selector restricted to the
  patient profile, and answers `404` for anyone else's id.
- What the patient writes (recovery goal, relapse prevention plan, urgent support plan with
  its trusted contacts, low-energy actions) is private to the patient: no staff role reads
  or changes it through this API, the goal is always created private, and the audit trail
  records who and when but never the text or a third party's phone number. Saving the
  urgent plan notifies and contacts nobody.
- Details, endpoints and error codes: `docs/mobile-patient-api.md`.

