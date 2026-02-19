"""
IshemaLink Load Test — Locust Script
=====================================
Simulates 2,000 agents uploading manifests simultaneously (Harvest Peak).

Usage:
    locust -f locust_tests/locustfile.py --host=http://localhost:8000 \
           --users=2000 --spawn-rate=100 --run-time=5m --headless

RURA requirement: system must handle 5,000+ concurrent agents.
This test targets 2,000 to validate the baseline before scale-up.
"""

import random
import json
import uuid
from locust import HttpUser, task, between, events
from locust.exception import StopUser

PHONE_PREFIX = ["+25078", "+25079", "+25073", "+25072"]

# Pre-seeded test data (set these to real IDs from your dev DB)
ORIGIN_ZONE_ID = 1
DEST_ZONE_ID   = 2
COMMODITY_ID   = 1


class IshemaLinkAgent(HttpUser):
    """
    Simulates a typical agricultural agent during harvest peak.
    Tasks weighted to reflect real-world usage patterns.
    """
    wait_time = between(0.5, 2.0)   # realistic think-time between actions
    token     = None
    phone     = None

    def on_start(self):
        """Register and log in at the start of each simulated session."""
        self.phone = (
            random.choice(PHONE_PREFIX)
            + str(random.randint(1000000, 9999999))
        )
        self._register()
        self._login()

    def _register(self):
        self.client.post(
            "/api/auth/register/",
            json={
                "phone":     self.phone,
                "full_name": f"Farmer {uuid.uuid4().hex[:6]}",
                "password":  "Harvest@2024",
                "role":      "SENDER",
                "district":  random.choice(["Nyamagabe", "Huye", "Nyanza", "Rwamagana"]),
            },
            name="/api/auth/register/",
        )

    def _login(self):
        resp = self.client.post(
            "/api/auth/login/",
            json={"phone": self.phone, "password": "Harvest@2024"},
            name="/api/auth/login/",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access")
        else:
            raise StopUser()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ── Tasks (weighted) ──────────────────────────────────────────────────────

    @task(5)
    def create_shipment(self):
        """Most common action — farmer creates a new cargo shipment."""
        resp = self.client.post(
            "/api/shipments/create/",
            json={
                "shipment_type": "DOMESTIC",
                "origin_zone":   ORIGIN_ZONE_ID,
                "dest_zone":     DEST_ZONE_ID,
                "commodity":     COMMODITY_ID,
                "weight_kg":     str(random.randint(50, 5000)),
                "declared_value":str(random.randint(10000, 500000)),
                "sync_id":       str(uuid.uuid4()),
                "offline_created": random.random() < 0.15,
            },
            headers=self._headers(),
            name="/api/shipments/create/",
        )
        if resp.status_code == 201:
            self._tracking_code = resp.json().get("tracking_code")

    @task(3)
    def list_shipments(self):
        """Farmer checks status of their shipments."""
        self.client.get(
            "/api/shipments/",
            headers=self._headers(),
            name="/api/shipments/",
        )

    @task(2)
    def get_tariff_estimate(self):
        """Farmer estimates cost before committing."""
        self.client.post(
            "/api/tariff/estimate/",
            json={
                "origin_zone":   ORIGIN_ZONE_ID,
                "commodity":     COMMODITY_ID,
                "shipment_type": "DOMESTIC",
                "weight_kg":     str(random.randint(100, 2000)),
            },
            headers=self._headers(),
            name="/api/tariff/estimate/",
        )

    @task(2)
    def poll_live_tracking(self):
        """Driver or sender polls GPS tracking."""
        code = getattr(self, "_tracking_code", "ISH-XXXXXXXX")
        self.client.get(
            f"/api/tracking/{code}/live/",
            headers=self._headers(),
            name="/api/tracking/[code]/live/",
        )

    @task(1)
    def health_check(self):
        """Simulates monitoring pings — ensures health endpoint is fast."""
        self.client.get("/api/health/deep/", name="/api/health/deep/")


class ControlTowerOperator(HttpUser):
    """
    Simulates admin/control-tower operators (fewer, but heavier queries).
    """
    wait_time = between(2, 5)
    token     = None
    weight    = 1   # 1 admin per ~10 agents

    def on_start(self):
        resp = self.client.post(
            "/api/auth/login/",
            json={"phone": "+250781000002", "password": "Test@1234"},
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access")
        else:
            raise StopUser()

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def dashboard(self):
        self.client.get("/api/admin/dashboard/summary/", headers=self._h(), name="/api/admin/dashboard/")

    @task(2)
    def top_routes(self):
        self.client.get("/api/analytics/routes/top/", headers=self._h(), name="/api/analytics/routes/")

    @task(1)
    def revenue_heatmap(self):
        self.client.get("/api/analytics/revenue/heatmap/", headers=self._h(), name="/api/analytics/revenue/")


# ── Custom events for Locust reporting ────────────────────────────────────────
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== IshemaLink Load Test Complete ===")
    stats = environment.stats.total
    print(f"Total requests:      {stats.num_requests}")
    print(f"Failures:            {stats.num_failures}")
    print(f"Avg response time:   {stats.avg_response_time:.0f}ms")
    print(f"95th percentile:     {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"Requests/sec:        {stats.current_rps:.1f}")
    if stats.num_failures / max(stats.num_requests, 1) > 0.01:
        print("⚠ FAILURE RATE > 1% — RURA compliance threshold exceeded")
    else:
        print("✓ System stable under load")
