import django.db.models.deletion
from django.db import migrations, models

def set_question_class(apps, schema_editor):
    """
    Infers the curriculum_class for existing Question objects.
    Assumes that the curriculum_subject's parent is the correct Class/Grade node.
    """
    # Get the historical versions of the models
    Question = apps.get_model('quiz', 'Question')
    
    questions_to_update = []
    
    # Iterate over all existing questions
    # Note: select_related is used here for query efficiency
    for question in Question.objects.all().select_related('curriculum_subject'):
        subject = question.curriculum_subject
        
        # Check if the subject exists and has a parent (the class node)
        if subject and subject.parent:
            # Assign the subject's parent (the Class/Grade node) as the new curriculum_class
            question.curriculum_class = subject.parent
            questions_to_update.append(question)
            
    # Perform a bulk update to save database time
    if questions_to_update:
        # We only update the new 'curriculum_class' field
        Question.objects.bulk_update(questions_to_update, ['curriculum_class'])


class Migration(migrations.Migration):

    dependencies = [
        ('curritree', '0002_alter_treenode_node_type'),
        ('quiz', '0006_question_organization'),
    ]

    operations = [
        # 1. SCHEMA CHANGE: Add the new column to the database
        migrations.AddField(
            model_name='question',
            name='curriculum_class',
            field=models.ForeignKey(
                blank=True, default=None, limit_choices_to={'node_type': 'class'}, 
                null=True, on_delete=django.db.models.deletion.CASCADE, 
                related_name='class_questions', to='curritree.treenode'
            ),
        ),
        
        # 2. DATA CHANGE: Run the Python function to populate the new column
        migrations.RunPython(set_question_class, migrations.RunPython.noop),
    ]