# S07 shared foundation review

Reviewed the supplied source-to-Mindcare diff and current workspace/authentication shell, controller, integration CSS, shared branding, and changed tests. Scope is the shared foundation increment, not completion of the entire DURALUX PRD. No tests were rerun by this reviewer and no backend or source-project files were edited.

## Verdict

**Bounded review approved after correction of the minimenu accessibility finding; final test completion remains owned by the integration run.** No actionable backend authorization, CSRF, MFA, route, or data-policy regression was found in this bounded diff. Removing `_component_examples()` from the workspace retains the staff-only reference inventory and avoids presenting synthetic metrics as operational data. Workspace shortcuts use existing active-clinic policy context rather than introducing a new authorization layer.

## Resolved finding

The initial P2 finding was that minimenu hid `.nxl-mtext` with `display:none`, removing accessible names from native accordion buttons and direct links. The current `static/duralux/css/product-integration.css:999-1008` instead clips text visually while preserving it in the accessibility tree. `static/duralux/js/product-shell.js:110-120` centralizes expanded/hidden state and collapses groups when entering minimenu; initialization at line 170 honors the saved mini state. The current browser harness at `scripts/verify-duralux-shell.cjs:69-70` resolves the administration button by its accessible name and checks its collapsed ARIA state. Static review confirms the correction. No unresolved actionable finding remains in this bounded review.

## Validation and test quality

The supplied `docs/migration/evidence/visual-foundation/results.json` records 12 passed scenarios with no collected errors: eight workspace layout/viewport/theme combinations and four login-validation combinations. This is existing evidence, not a fresh reviewer execution; the owner is rerunning after CSS changes and owns focused/full-suite results.

The new database tests meaningfully cover three membership roles across both layouts and a clinic switch that changes available workspace actions. Their positive/negative role link checks and absence of synthetic context validate user behavior. Existing script-string assertions remain structural checks rather than proof of browser behavior; the browser harness materially improves coverage.

Nonblocking coverage improvements:

- The revised browser harness at `scripts/verify-duralux-shell.cjs:51-56` now asserts the exact backward and forward wrap targets, resolving the initial weak containment-only assertion.
- Min menu persistence across a desktop reload and role-specific direct-link accessible names are useful additional coverage; saved preference handling and shared clipping are correct by inspection. These are not current defects.
- `tests/test_workspace_foundation.py:16-26` starts collecting links at the shortcuts section and never stops at its closing tag. This does not invalidate current tests because shortcuts are the final content, but should be scoped with balanced element depth if additional footer/content links are introduced.

Shared brand rendering retains tenant logo URL and tenant display name as alternative text and uses Mindcare fallback identity. Authentication templates retain native POST forms, CSRF tokens, accessible field rendering, and existing form behavior scripts. Completion of other domain templates, production deployment, and full application accessibility certification are outside this review.
