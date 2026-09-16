from django.db import migrations


# Collapses the seeded local/gpu/aws rows down to a single canonical 'default'
# environment — there's only one rig in play, so gpu/aws never meant anything
# concrete. total_memory is bumped to 30G per the post-incident tuning
# decision; base_directory and everything else carries over unchanged.
def rename_local_to_default(apps, schema_editor):
    JobEnvironmentDefault = apps.get_model("submit_jobs", "JobEnvironmentDefault")
    JobEnvironmentDefault.objects.filter(environment__in=["gpu", "aws"]).delete()
    local = JobEnvironmentDefault.objects.filter(environment="local").first()
    if local is not None:
        local.environment = "default"
        local.total_memory = "30G"
        local.save()
    else:
        JobEnvironmentDefault.objects.get_or_create(
            environment="default", defaults={"total_memory": "30G"}
        )


def restore_local_gpu_aws(apps, schema_editor):
    JobEnvironmentDefault = apps.get_model("submit_jobs", "JobEnvironmentDefault")
    default = JobEnvironmentDefault.objects.filter(environment="default").first()
    if default is not None:
        default.environment = "local"
        default.total_memory = "128G"
        default.save()
    else:
        JobEnvironmentDefault.objects.get_or_create(environment="local")
    JobEnvironmentDefault.objects.get_or_create(environment="gpu")
    JobEnvironmentDefault.objects.get_or_create(environment="aws")


class Migration(migrations.Migration):

    dependencies = [
        ('submit_jobs', '0004_seed_job_environment_defaults'),
    ]

    operations = [
        migrations.RunPython(rename_local_to_default, restore_local_gpu_aws),
    ]
