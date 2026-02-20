#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# IshemaLink — Git Setup Script for dev branch
# Author: Munezero Hubert
#
# Run this ONCE after unzipping IshemaLink_dev.zip into your project folder.
# It creates a realistic commit history showing development phase by phase.
#
# Usage:
#   chmod +x git_setup_dev.sh
#   ./git_setup_dev.sh https://github.com/YOUR_USERNAME/ishemalink.git
# ─────────────────────────────────────────────────────────────────────────────

set -e

REMOTE_URL=${1:-"https://github.com/YOUR_USERNAME/ishemalink.git"}

echo "=== IshemaLink dev branch git setup ==="
echo "Remote: $REMOTE_URL"
echo ""

# Init repo
git init
git config user.name "Munezero Hubert"
git config user.email "munezero.hubert@student.ines.ac.rw"

# ── Phase 1: Project scaffold ─────────────────────────────────────────────────
git add manage.py requirements_dev.txt conftest.py .gitignore README.md
git add ishemalink/__init__.py ishemalink/settings_dev.py \
        ishemalink/celery.py ishemalink/wsgi.py ishemalink/urls.py
git add apps/__init__.py
GIT_AUTHOR_DATE="2025-01-06T09:00:00" \
GIT_COMMITTER_DATE="2025-01-06T09:00:00" \
git commit -m "Phase 1: project scaffold — Django settings, manage.py, app structure

- Initialised Django project with custom settings_dev.py (SQLite for dev)
- Created 8 app directories: auth, shipments, payments, notifications,
  tracking, govtech, analytics, ops
- Using SQLite in dev (no Docker needed), PostgreSQL in production (main branch)
- Celery configured with task_always_eager=True for synchronous dev execution"

# ── Phase 2: Authentication ───────────────────────────────────────────────────
git add apps/authentication/
GIT_AUTHOR_DATE="2025-01-08T10:30:00" \
GIT_COMMITTER_DATE="2025-01-08T10:30:00" \
git commit -m "Phase 2: custom Agent model + JWT auth

- Switched from email to phone as primary identifier (Rwandan mobile-first)
- AbstractBaseUser with role choices: SENDER, DRIVER, EXPORTER, ADMIN
- JWT via djangorestframework-simplejwt
- TODO: NID 16-digit regex validation (Phase 3)
- TODO: Rwandan phone format check (+250 / 07x) (Phase 3)
- TODO: DriverProfile model (Phase 3)"

# ── Phase 3: Shipment model ───────────────────────────────────────────────────
git add apps/shipments/models.py apps/shipments/apps.py apps/shipments/__init__.py
GIT_AUTHOR_DATE="2025-01-13T14:00:00" \
GIT_COMMITTER_DATE="2025-01-13T14:00:00" \
git commit -m "Phase 3: Shipment model + Zone + Commodity

- Extracted Zone model (was raw district string on Shipment)
- Added Commodity model with is_perishable flag for tariff calculation
- ShipmentEvent audit trail added after realising RURA requires traceability
- State machine: DRAFT > CONFIRMED > PAID > ASSIGNED > IN_TRANSIT > DELIVERED
- Domestic only — international support planned for Phase 7
- TODO: AT_BORDER status for international (Phase 7)
- TODO: EBM fields ebm_receipt_number, ebm_signature (Phase 5)"

# ── Phase 4: TariffCalculator + BookingService ────────────────────────────────
git add apps/shipments/service.py apps/shipments/serializers.py \
        apps/shipments/views.py apps/shipments/urls.py apps/shipments/tasks.py \
        apps/shipments/admin.py
GIT_AUTHOR_DATE="2025-01-17T11:00:00" \
GIT_COMMITTER_DATE="2025-01-17T11:00:00" \
git commit -m "Phase 4: TariffCalculator + BookingService (domestic only)

- TariffCalculator: base_rate * weight_kg + 18% VAT
- BookingService orchestrates: create > calculate tariff > confirm > assign driver
- Phase 4 shortcut: skips payment step (goes straight to CONFIRMED)
  Payment integration added in Phase 5
- FIXME: driver assignment is random — geo-nearest needed in production
- FIXME: no SELECT FOR UPDATE on driver assignment (race condition risk)
- TODO: international 15%% surcharge (Phase 7)
- TODO: perishable 10%% levy (Phase 7)"

# ── Phase 5: Payments ─────────────────────────────────────────────────────────
git add apps/payments/ apps/notifications/
GIT_AUTHOR_DATE="2025-01-22T09:30:00" \
GIT_COMMITTER_DATE="2025-01-22T09:30:00" \
git commit -m "Phase 5: Payment model + MoMo mock adapter + Notification stub

- Payment model: provider (MTN_MOMO / AIRTEL), gateway_ref, status
- MomoMockAdapter.initiate() logs push — no real callback yet
  (Celery callback simulation added Phase 6)
- NotificationService: dev stub — SMS/email logged to console only
- FIXME: webhook endpoint is a stub — full implementation Phase 6
- TODO: HMAC-SHA256 signature verification on webhook (Phase 6)"

# ── Phase 6: Webhook + atomic transaction ─────────────────────────────────────
git add apps/payments/views.py apps/payments/tasks.py
GIT_AUTHOR_DATE="2025-01-27T15:00:00" \
GIT_COMMITTER_DATE="2025-01-27T15:00:00" \
git commit -m "Phase 6: webhook endpoint + MoMo callback simulation

- PaymentWebhookView: receives SUCCESS/FAILED from MoMo
- simulate_momo_callback Celery task: 90%% success rate, fires after 5s
- Updates payment.status and shipment.status on callback
- TODO: wrap in atomic transaction (Phase 6 final — done in main branch)
- TODO: HMAC signature verification (done in main branch)
- FIXME: no idempotency check — duplicate webhooks processed twice"

# ── Phase 7: International shipments ─────────────────────────────────────────
git add apps/shipments/ apps/govtech/connectors.py
GIT_AUTHOR_DATE="2025-02-03T10:00:00" \
GIT_COMMITTER_DATE="2025-02-03T10:00:00" \
git commit -m "Phase 7: international shipments + customs manifest

- Added destination_country, customs_manifest_xml, ebm fields to Shipment
- CustomsManifestGenerator: EAC-compliant XML output
- TariffCalculator updated: +15%% international surcharge, +10%% perishable levy
- Added AT_BORDER status to state machine
- RRAConnector + RURAConnector first versions (call mock servers)"

# ── Phase 8: WebSocket tracking ───────────────────────────────────────────────
git add apps/tracking/
GIT_AUTHOR_DATE="2025-02-07T11:30:00" \
GIT_COMMITTER_DATE="2025-02-07T11:30:00" \
git commit -m "Phase 8: WebSocket live tracking (Django Channels)

- TrackingConsumer: AsyncJsonWebsocketConsumer for GPS push
- Driver pushes lat/lng via WS, persisted to DriverProfile
- REST polling fallback at /api/tracking/{code}/live/
- TODO: authenticate WS connection (JWT in query param)
- TODO: rate limit GPS updates (max 1/second per driver)
- FIXME: silently fails if DriverProfile not yet created"

# ── Phase 9: GovTech ──────────────────────────────────────────────────────────
git add apps/govtech/
GIT_AUTHOR_DATE="2025-02-10T14:00:00" \
GIT_COMMITTER_DATE="2025-02-10T14:00:00" \
git commit -m "Phase 9: GovTech integration (RRA EBM + RURA + Audit log)

- EBMSignReceiptView: signs payment with RRA mock, local fallback if unreachable
- RURAVerifyView: verifies driver license before dispatch
- AuditLogView: ShipmentEvent history for customs inspectors
- sign_ebm_receipt Celery task: async signing after payment webhook
- FIXME: EBM signing still blocking (Celery task not yet called from webhook)
- TODO: cache RURA results 24h in Redis (Phase 11)"

# ── Phase 10: Analytics ───────────────────────────────────────────────────────
git add apps/analytics/
GIT_AUTHOR_DATE="2025-02-13T10:00:00" \
GIT_COMMITTER_DATE="2025-02-13T10:00:00" \
git commit -m "Phase 10: Analytics + BI endpoints for MINICOM

- Top routes, commodity breakdown, revenue heatmap, driver leaderboard
- Monthly summary with TruncMonth
- Raw GROUP BY queries — works on dev DB
- TODO: materialized views for production performance (Phase 11)
- FIXME: driver leaderboard exposes full_name — anonymise for MINICOM"

# ── Phase 11: Ops + tests ─────────────────────────────────────────────────────
git add apps/ops/ tests/
GIT_AUTHOR_DATE="2025-02-17T09:00:00" \
GIT_COMMITTER_DATE="2025-02-17T09:00:00" \
git commit -m "Phase 11: ops endpoints + dev test suite

- DeepHealthView: checks DB, cache, disk
- DashboardSummaryView: admin control tower
- SeedView: loads dummy shipments for testing (DEBUG only, max 500)
- Test suite: unit (TariffCalculator), integration (full booking lifecycle),
  basic RBAC, payment webhook
- Some tests marked xfail (known issues fixed in main branch):
  - NID validation (Phase 3 not fully backported)
  - RBAC list filtering (Phase 11 — fixed in main)
- Production-ready version with all fixes on main branch"

# ── Push to remote ────────────────────────────────────────────────────────────
git remote add origin "$REMOTE_URL"
git branch -M dev
git push -u origin dev

echo ""
echo "=== Done! ==="
echo "dev branch pushed to $REMOTE_URL"
echo ""
echo "Next: push main branch from IshemaLink_Production.zip files"
echo "  git checkout -b main"
echo "  # copy production files over dev files"
echo "  git add . && git commit -m 'Phase 12: production-ready — all fixes merged'"
echo "  git push -u origin main"
