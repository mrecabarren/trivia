# Generated by Django 4.1.5 on 2023-04-18 18:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trivia_api', '0007_move_auto_evaluation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='qualification',
            old_name='sent',
            new_name='qualified',
        ),
    ]
