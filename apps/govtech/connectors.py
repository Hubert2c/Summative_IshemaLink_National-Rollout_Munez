"""
Government API connectors.
RRAConnector  — Electronic Billing Machine (EBM) receipt signing.
RURAConnector — Driver license / vehicle insurance verification.
Both have mock implementations for testing without live government APIs.
"""

import logging
import hashlib
import uuid
import requests
from django.conf import settings

logger = logging.getLogger("ishemalink.govtech")


class RRAConnector:
    """
    Rwanda Revenue Authority — EBM integration.
    Every completed payment must produce a signed digital receipt.
    """

    BASE_URL = settings.RRA_EBM_BASE_URL

    def sign_receipt(self, payment) -> dict:
        """
        POST to EBM API to get a digital signature.
        Returns {"receipt_number": "...", "signature": "..."}
        """
        payload = {
            "transaction_id": str(payment.id),
            "amount":         str(payment.amount),
            "currency":       payment.currency,
            "payer_phone":    payment.payer_phone,
            "timestamp":      payment.created_at.isoformat(),
            "tracking_code":  payment.shipment.tracking_code,
        }
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/ebm/sign/",
                json=payload,
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("EBM signing failed for payment %s: %s", payment.id, exc)
            # Return a locally-computed fallback (for resilience — flag for reconciliation)
            fallback_sig = hashlib.sha256(
                f"{payment.id}{payment.amount}{settings.SECRET_KEY}".encode()
            ).hexdigest()
            return {
                "receipt_number": f"LOCAL-{str(payment.id)[:8].upper()}",
                "signature":      fallback_sig,
                "fallback":       True,
            }


class RURAConnector:
    """
    Rwanda Utilities Regulatory Authority — transport license verification.
    A truck cannot be dispatched unless RURA confirms the license is valid.
    """

    BASE_URL = settings.RURA_API_BASE_URL

    def verify_license(self, license_number: str) -> bool:
        """
        GET /api/verify/{license_number}/ from RURA mock server.
        Returns True if license is valid and insurance is active.
        Blocks dispatch if False.
        """
        try:
            resp = requests.get(
                f"{self.BASE_URL}/api/gov/rura/verify-license/{license_number}/",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                valid = data.get("valid", False) and data.get("insurance_active", False)
                logger.info("RURA check for %s: %s", license_number, valid)
                return valid
            logger.warning("RURA returned %s for license %s", resp.status_code, license_number)
            return False
        except requests.RequestException as exc:
            logger.error("RURA connector error for %s: %s", license_number, exc)
            # Fail-safe: do NOT dispatch if we cannot verify
            return False


class CustomsManifestGenerator:
    """
    Generate EAC-compliant XML customs manifest for international shipments.
    Format follows the East Africa Community Single Customs Territory spec.
    """

    def generate(self, shipment) -> str:
        """Return XML string for the shipment."""
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
</CustomsManifest>"""
        return xml
