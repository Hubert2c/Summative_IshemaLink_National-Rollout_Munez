# IshemaLink — Assessment Written Reports

---

## Report 1: Integration Report — Solving Domestic vs. International Logic

### The Conflict

When IshemaLink was originally designed with separate Domestic and International modules, they shared no code but duplicated significant logic: both had their own shipment creation flows, tariff engines, and driver assignment pipelines. The core conflict arose from several fundamental differences:

**Schema conflict:** International shipments require `destination_country`, `customs_manifest_xml`, and `ebm_signature` fields that are irrelevant for domestic shipments. A naïve merge would pollute the domestic model with null columns or require a complex inheritance hierarchy.

**Tariff conflict:** Domestic tariffs use a simple zone-based rate (`base_rate_kg × weight`), while international shipments add a 15% cross-border surcharge plus a perishable cold-chain levy for qualifying commodities. The calculation rules are different but overlap significantly.

**Workflow conflict:** Domestic shipments proceed from PAID → ASSIGNED → IN_TRANSIT → DELIVERED. International shipments require an additional AT_BORDER state for customs inspection, plus a customs XML manifest must be generated before the truck can cross.

### The Solution: A Unified Model with Type-Driven Behavior

The solution adopted in IshemaLink v2.0 is a **single `Shipment` model** with a `shipment_type` discriminator field (`DOMESTIC` / `INTERNATIONAL`). This approach follows the principle of "one entity, one table" while handling differences through:

1. **Nullable fields for international extras** (`destination_country`, `customs_manifest_xml`, `ebm_signature`) — these are simply empty for domestic shipments, with a serializer-level validator that enforces their presence for international ones.

2. **`TariffCalculator` using conditional modifiers** — the base calculation is identical; surcharges are applied only when conditions match. This avoids code duplication while keeping the rules transparent and testable.

3. **Status machine** — the shared `Status` enum includes `AT_BORDER` which domestic shipments simply never enter. The `BookingService` skips this state for domestic types, keeping the flow clean.

4. **`CustomsManifestGenerator`** — extracted as its own class in `govtech.connectors`, called only for `INTERNATIONAL` shipments after payment. This clean separation means the domestic flow has zero govtech overhead.

**Key design decision:** Rather than using Django model inheritance (which would create two tables and complex JOIN queries), the single-table approach gives us better query performance at scale and simpler migrations — critical for a 50,000+ shipment database.

---

## Report 2: Scalability Plan — Handling 50,000 Users in 2027

### Current Baseline (February 2026)

IshemaLink currently supports 5,000 concurrent agents during harvest peaks on a single-node Docker stack. The architecture already incorporates several scaling primitives: PgBouncer connection pooling, Redis channel layers for WebSockets, and Celery for async task offloading.

### Phase 1: Vertical Scaling (0–10,000 users, Q1 2026)

The immediate step is to right-size the current server. At 10,000 users we should:
- Scale Gunicorn workers: `--workers = (2 × CPU_cores) + 1`
- Increase Celery worker concurrency from 8 to 16
- Tune PgBouncer: raise `MAX_CLIENT_CONN` to 10,000, `DEFAULT_POOL_SIZE` to 100
- Enable PostgreSQL query caching and add `EXPLAIN ANALYZE` to the top-5 slowest queries (identified via Prometheus latency metrics)

**Cost:** No infrastructure change, just tuning.

### Phase 2: Horizontal Web Scaling (10,000–30,000 users, Q2–Q3 2026)

Deploy a second application node and put both behind a load balancer:
- Use **nginx upstream** with round-robin (already configured in `nginx.conf`)
- Redis acts as the shared state layer — sessions, channel groups, and Celery queue all remain on one Redis node (sufficient for this tier)
- Database remains single-node PostgreSQL; the bottleneck at this scale is connections (solved by PgBouncer) not throughput

**Key optimization:** Add database read replicas and route analytics queries (`GET /api/analytics/*`) to replicas. These queries are heavy (GROUP BY, COUNT, SUM over millions of rows) and should never block the write path.

**Rwanda-specific consideration:** Both nodes should remain in-country at AOS or KtRN. Network latency between Kigali data centers is under 2ms — negligible.

### Phase 3: Database Sharding & Microservices (30,000–50,000 users, 2027)

At 50,000 users the monolith will need structural changes:

1. **Separate the Analytics read model** — run a nightly ETL into a dedicated analytics PostgreSQL instance (or ClickHouse for OLAP). MINICOM queries run against the analytics DB, never the transactional DB.

2. **Shard shipments by region** — Rwanda has five provinces. Shard the `Shipment` table by province prefix in `tracking_code` (e.g., `KGL-*`, `NST-*`). This reduces write contention during regional harvest peaks.

3. **Extract the Payment service** — payments are the highest-criticality component. Running the payment webhook processor as a separate service (with its own DB connection pool) ensures a MoMo callback storm doesn't degrade shipment creation.

4. **CDN for static assets** — offload all static files to a Rwanda CDN (RwandaOnline or comparable) to reduce server load.

**Target:** 50,000 users @ 200ms p95 response time with 99.9% uptime.

---

## Report 3: Local Context Essay — Why Generic Logistics Software Fails in Rwanda, and How IshemaLink Succeeds

### The Generic Failure Mode

Global logistics platforms like Shopify Shipping, ShipBob, or even Africa-focused tools like Sendy were built around assumptions that simply do not hold in Rwanda's agricultural export corridor:

**Assumption 1: Reliable, always-on internet.** Generic platforms require constant connectivity — they have no concept of offline-first workflows. A farmer in Nyamagabe or Musanze, at 2,000m elevation during a coffee harvest, may face 4–8 hour connectivity gaps. If the app cannot create a shipment offline and sync when a signal returns, it is useless.

**Assumption 2: Card-based payments.** Stripe, PayPal, and similar gateways assume a banked population. Rwanda's financial inclusion rate through mobile money (MTN MoMo and Airtel Money) exceeds 80%, while credit card penetration is under 5%. A platform without push-to-pay integration is simply unusable.

**Assumption 3: Fixed addresses and ZIP codes.** Rwanda's addressing system is district/sector/cell based, not street-address based. Generic mapping systems fail to route correctly in rural Rwanda because Google Maps often lacks the granularity of Rwanda's road network.

**Assumption 4: No government integration.** RRA's EBM (Electronic Billing Machine) requirement means every commercial transaction must generate a digitally-signed receipt. A platform that ignores this exposes users to tax compliance risk — a serious deterrent for formal export businesses.

**Assumption 5: English-only interfaces.** While Rwanda's educated professional class uses English, many farmers and small transporters are more comfortable in Kinyarwanda. An English-only interface reduces adoption in the highest-volume agricultural zones.

### How IshemaLink Succeeds

**Offline-first with `sync_id`:** Every shipment creation carries a client-generated idempotency key. The mobile app stores the payload locally and retries on reconnect. The server is idempotent — duplicate syncs are detected by `sync_id` and return the existing shipment without creating duplicates. This solves the Nyamagabe outage scenario completely.

**MTN + Airtel integration at the core:** Payment is not an afterthought. The entire booking flow is gated on Mobile Money confirmation. The `MomoMockAdapter` — designed to be swapped with the production MTN MoMo API SDK — implements the real push-to-pay flow: initiate → asynchronous callback → confirmation. This mirrors how Rwandans actually pay for services.

**Zone-based routing, not address-based:** IshemaLink models Rwanda's geography as `Zone` objects tied to provinces and districts. Tariffs are calculated based on zone-to-zone rates agreed with MINICOM, not on distance estimates. This reflects how Rwandan transporters actually price their services.

**EBM compliance built-in:** The `RRAConnector` calls the EBM API for every successful payment. If the government server is unreachable, a locally-computed fallback signature is stored and flagged for reconciliation. The system never blocks a payment confirmation waiting for a government API — it handles failure gracefully and queues reconciliation asynchronously.

**RURA gate:** No truck moves in IshemaLink without a valid RURA transport authorization check. This is not optional — the `assign_driver` method in `BookingService` verifies the license via the RURA API and refuses to dispatch if the check fails. This aligns with how RURA actually enforces transport regulations.

**Built for Rwanda's harvest peaks:** The architecture is explicitly designed for 500% traffic spikes during coffee, tea, and potato harvests. Rate limiting in Nginx protects against accidental overload while PgBouncer's 5,000-connection ceiling ensures database stability at the highest concurrency levels Rwanda's agricultural calendar demands.

### Conclusion

IshemaLink succeeds where generic platforms fail because it was designed from the ground up for Rwanda's specific realities: rural connectivity gaps, mobile money as the primary payment rail, district-based logistics pricing, EBM tax compliance, and RURA transport regulation. It treats these not as edge cases to be bolted on after launch, but as first-class architectural requirements. The result is a platform that is not just technically functional, but operationally trusted by the farmers, drivers, exporters, and regulators who use it every day.
