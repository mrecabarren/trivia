# Generated by Django 4.1.5 on 2023-04-28 21:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trivia_api', '0008_rename_sent_qualification_qualified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fault',
            name='description',
        ),
        migrations.AddField(
            model_name='fault',
            name='fault_value',
            field=models.IntegerField(default=1),
        ),
    ]