# Generated by Django 5.1.6 on 2025-03-22 21:47

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(unique=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='StreamSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('provide_notification', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('frame_fetch_frequency', models.IntegerField()),
                ('stream', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='stream_handler.stream')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to='stream_handler.user')),
            ],
        ),
        migrations.CreateModel(
            name='RecognitionEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('earth_timestamp', models.DateTimeField(auto_now_add=True)),
                ('stream_timestamp', models.DateTimeField(auto_now_add=True)),
                ('recognized_specie_name', models.CharField(max_length=255)),
                ('recognized_specie_img_url', models.URLField()),
                ('stream_subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recognition_history', to='stream_handler.streamsubscription')),
            ],
        ),
    ]
