# Generated by Django 5.1.6 on 2025-04-22 01:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stream_handler", "0012_alter_streamsubscription_provide_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="sns_topic_arn",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
