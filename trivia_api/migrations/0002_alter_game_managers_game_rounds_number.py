# Generated by Django 4.1.5 on 2023-02-02 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trivia_api', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='game',
            managers=[
            ],
        ),
        migrations.AddField(
            model_name='game',
            name='rounds_number',
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]