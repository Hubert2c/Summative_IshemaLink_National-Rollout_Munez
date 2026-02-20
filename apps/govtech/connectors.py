"""
Government API connectors — Phase 9 (early).

DEVELOPMENT NOTES:
- Phase 9 (this file): first integration attempt. RRA and RURA connectors
  call mock servers. Fallback logic for EBM is basic (no flagging yet).
- Phase 9 final (main): added local fallback signature, reconciliation flag,
  fail-safe for RURA (return False if server unreachable).

TODO: flag fallback EBM receipts in a reconciliation table (Phase 10)
TODO: add circuit breaker for RURA connector — if 3 consecutive failures,
      mark connector as unavailable and alert admin (Phase 11)
FIXME: EBM fallback does not notify admin when used
FIXME: RURA timeout is 5s — too long under load (reduce to 2s in Phase 11)
"""

import hashlib
import uuid
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class RRAConnector:
    """
    Rwanda Revenue Authority — EBM receipt signing.
    Phase 9: calls mock server. Falls back to local hash if unreachable.
    """

    BASE_URL = settings.RRA_EBM_BASE_URL

    def sign_receipt(self, payment) -> dict:
        payload = {
            "transaction_id": str(payment.id),
            "amount":         str(payment.amount),
            "currency":       payment.currency,
            "payer_phone":    payment.payer_phone,
            "tracking_code":  payment.shipment.tracking_code,
        }
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/ebm/sign/",
                json=payload,
                timeout=5,  # TODO Phase 11: reduce to 2s
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("EBM signing failed: %s", exc)
            # FIXME: fallback not flagged to admin yet
            fallback_sig = hashlib.sha256(
                f"{payment.id}{payment.amount}{settings.SECRET_KEY}".encode()
            ).hexdigest()
            return {
                "receipt_number": f"LOCAL-{str(payment.id)[:8].upper()}",
                "signature":      fallback_sig,
                "fallback":       True,
                # TODO Phase 10: log to ReconciliationRecord model
            }


class RURAConnector:
    """
    RURA license verification.
    Phase 9: returns False if server unreachable (fail-safe — don't dispatch).
    """

    BASE_URL = settings.RURA_API_BASE_URL

    def verify_license(self, license_number: str) -> bool:
        try:
            resp = requests.get(
                f"{self.BASE_URL}/api/gov/rura/verify-license/{license_number}/",
                timeout=5,  # FIXME: too long — reduce to 2s in Phase 11
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("valid", False) and data.get("insurance_active", False)
            return False
        except requests.RequestException as exc:
            logger.error("RURA connector error for %s: %s", license_number, exc)
            # Fail-safe: do NOT dispatch if RURA is unreachable
            return False


class CustomsManifestGenerator:
    """
    EAC-compliant XML manifest — Phase 9.
    TODO: validate XML against official EAC XSD schema (Phase 10)
    TODO: add digital signature from RRA to manifest (Phase 10)
    """

    def generate(self, shipment) -> str:
        manifest_id = str(uuid.uuid4())[:8].upper()
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<CustomsManifest xmlns="urn:eac:customs:manifest:v1" id="{manifest_id}">
  <Header>
    <ManifestNumber>RW-ISH-{shipment.tracking_code}</ManifestNumber>
    <IssueDate>{shipment.created_at.date().isoformat()}</IssueDate>
    <ExportingCountry>RW</ExportingCountry>
    <DestinationCountry>{shipment.destination_country}</DestinationCountry>
  </Header>
  <Consignment>
    <TrackingCode>{shipment.tracking_code}</TrackingCode>
    <Commodity>
      <Description>{shipment.commodity.name}</Description>
      <HSCode>{shipment.commodity.hs_code or "0000.00"}</HSCode>
      <WeightKG>{shipment.weight_kg}</WeightKG>
      <DeclaredValue currency="RWF">{shipment.declared_value}</DeclaredValue>
    </Commodity>
    <Exporter>
      <NationalID>{shipment.sender.national_id or "UNKNOWN"}</NationalID>
      <Phone>{shipment.sender.phone}</Phone>
    </Exporter>
  </Consignment>
  <EBMReceipt>
    <ReceiptNumber>{shipment.ebm_receipt_number}</ReceiptNumber>
    <Signature>{shipment.ebm_signature}</Signature>
  </EBMReceipt>
  <!-- TODO Phase 10: add digital signature block -->
</CustomsManifest>"""
        return xml
