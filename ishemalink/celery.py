"""
Celery — dev branch.
Redis not required in dev; tasks run synchronously via CELERY_TASK_ALWAYS_EAGER.
TODO Phase 11: remove ALWAYS_EAGER and wire real Redis broker.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ishemalink.settings_dev")

app = Celery("ishemalink")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Dev convenience: run tasks synchronously without a broker
# TODO Phase 11: remove this line when Redis is wired up
app.conf.task_always_eager = True

app.autodiscover_tasks()
