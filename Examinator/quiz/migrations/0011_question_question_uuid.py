# quiz/migrations/0011_question_question_uuid.py

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0010_remove_questionuploadlog_upload_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_uuid',
            # --- CHANGES MADE BELOW ---
            field=models.UUIDField(
                blank=True, 
                db_index=True, 
                editable=False, 
                null=True # <--- Keep this!
                # default=uuid.uuid4 REMOVED 
                # unique=True REMOVED
            ),
        ),
    ]
