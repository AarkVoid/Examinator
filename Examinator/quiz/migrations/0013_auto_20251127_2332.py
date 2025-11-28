# quiz/migrations/0013_populate_uuids.py (or whatever your file is named)
import uuid
from django.db import migrations

def generate_uuids(apps, schema_editor):
    Question = apps.get_model('quiz', 'Question')
    for row in Question.objects.all():
        if row.question_uuid is None: 
            row.question_uuid = uuid.uuid4()
            row.save(update_fields=['question_uuid'])

class Migration(migrations.Migration):
    dependencies = [
        ('quiz', '0011_question_question_uuid'), 
    ]
    operations = [
        migrations.RunPython(generate_uuids, reverse_code=migrations.RunPython.noop),
    ]
