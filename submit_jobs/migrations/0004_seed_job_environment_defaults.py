from django.db import migrations


# Mirrors the hardcoded values build_job_env_config() used before defaults moved
# to the database, so existing job submissions see no behavior change.
DEFAULT_ROWS = ["local", "gpu", "aws"]


def seed_defaults(apps, schema_editor):
    JobEnvironmentDefault = apps.get_model("submit_jobs", "JobEnvironmentDefault")
    for environment in DEFAULT_ROWS:
        JobEnvironmentDefault.objects.get_or_create(environment=environment)


def remove_defaults(apps, schema_editor):
    JobEnvironmentDefault = apps.get_model("submit_jobs", "JobEnvironmentDefault")
    JobEnvironmentDefault.objects.filter(environment__in=DEFAULT_ROWS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('submit_jobs', '0003_jobenvironmentdefault'),
    ]

    operations = [
        migrations.RunPython(seed_defaults, remove_defaults),
    ]
