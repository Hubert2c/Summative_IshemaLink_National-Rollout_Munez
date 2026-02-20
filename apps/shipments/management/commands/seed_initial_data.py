"""
Management command: seed initial Rwandan zones and commodities.

Usage:
    python manage.py seed_initial_data
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.shipments.models import Zone, Commodity


ZONES = [
    ("Kigali Central",   "Kigali",   "50.00", False),
    ("Kigali Nyarugenge","Kigali",   "50.00", False),
    ("Musanze",          "Northern", "45.00", False),
    ("Rubavu",           "Western",  "44.00", False),
    ("Nyamagabe",        "Southern", "42.00", False),
    ("Huye",             "Southern", "43.00", False),
    ("Rwamagana",        "Eastern",  "41.00", False),
    ("Kayonza",          "Eastern",  "41.00", False),
    ("Rusizi",           "Western",  "46.00", True),   # Border with DRC
    ("Bugesera",         "Eastern",  "40.00", False),
    ("Nyanza",           "Southern", "43.00", False),
    ("Gicumbi",          "Northern", "45.00", False),
]

COMMODITIES = [
    ("Potatoes",          "0701.90", True),
    ("Coffee",            "0901.11", True),
    ("Tea",               "0902.10", True),
    ("Maize",             "1005.90", True),
    ("Rice",              "1006.30", True),
    ("Beans",             "0713.31", True),
    ("Bananas",           "0803.90", True),
    ("Avocados",          "0804.40", True),
    ("Steel Pipes",       "7304.11", False),
    ("Electronics",       "8471.30", False),
    ("Clothing / Textiles","6109.10", False),
    ("Construction Materials","6810.11", False),
    ("Beverages",         "2202.10", False),
    ("Pharmaceuticals",   "3004.90", False),
]


class Command(BaseCommand):
    help = "Seed initial Rwandan zones and commodities"

    def handle(self, *args, **options):
        created_zones = 0
        for name, province, rate, is_border in ZONES:
            _, created = Zone.objects.get_or_create(
                name=name,
                defaults={
                    "province":     province,
                    "base_rate_kg": Decimal(rate),
                    "is_border":    is_border,
                },
            )
            if created:
                created_zones += 1

        created_commodities = 0
        for name, hs_code, is_perishable in COMMODITIES:
            _, created = Commodity.objects.get_or_create(
                name=name,
                defaults={"hs_code": hs_code, "is_perishable": is_perishable},
            )
            if created:
                created_commodities += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_zones} zones and {created_commodities} commodities."
        ))
