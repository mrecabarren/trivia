# Generated by Django 4.1.5 on 2023-05-07 02:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trivia_api', '0009_remove_fault_description_fault_fault_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fault',
            name='category',
            field=models.CharField(choices=[('QT', 'QUESTION TIME'), ('AT', 'ANSWER TIME'), ('ET', 'EVALUATION TIME'), ('FT', 'QUALIFICATION TIME'), ('FF', 'FOCUS')], max_length=2),
        ),
        migrations.CreateModel(
            name='ActionError',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.TextField()),
                ('error_message', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errors', to=settings.AUTH_USER_MODEL)),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errors', to='trivia_api.round')),
            ],
        ),
    ]