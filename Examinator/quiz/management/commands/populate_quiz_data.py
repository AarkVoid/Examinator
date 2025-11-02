from django.core.management.base import BaseCommand
from accounts.models import User
from education.models import Subject, Chapter
from quiz.models import Question, MCQOption, FillBlankAnswer, ShortAnswer, MatchPair, TrueFalseAnswer, QuestionPaper, PaperQuestion

class Command(BaseCommand):
    help = 'Populate quiz app with dummy questions and papers'

    def handle(self, *args, **options):
        self.stdout.write('Creating quiz dummy data...')
        
        # Get existing data
        try:
            teacher = User.objects.filter(role='teacher').first()
            if not teacher:
                teacher = User.objects.create_user(
                    email='quiz_teacher@school.com',
                    username='quiz_teacher@school.com',
                    password='teacher123',
                    role='teacher'
                )
            
            math_subject = Subject.objects.filter(name='Mathematics').first()
            science_subject = Subject.objects.filter(name='Science').first()
            
            if not math_subject or not science_subject:
                self.stdout.write('Please run populate_dummy_data first to create subjects')
                return
            
            # Create MCQ Questions
            mcq1 = Question.objects.create(
                question_type='mcq',
                subject=math_subject,
                question_text='What is 2 + 2?',
                difficulty='easy',
                marks=1,
                created_by=teacher
            )
            MCQOption.objects.create(question=mcq1, option_text='3', is_correct=False, order=1)
            MCQOption.objects.create(question=mcq1, option_text='4', is_correct=True, order=2)
            MCQOption.objects.create(question=mcq1, option_text='5', is_correct=False, order=3)
            MCQOption.objects.create(question=mcq1, option_text='6', is_correct=False, order=4)
            
            mcq2 = Question.objects.create(
                question_type='mcq',
                subject=science_subject,
                question_text='What is the chemical symbol for water?',
                difficulty='easy',
                marks=1,
                created_by=teacher
            )
            MCQOption.objects.create(question=mcq2, option_text='H2O', is_correct=True, order=1)
            MCQOption.objects.create(question=mcq2, option_text='CO2', is_correct=False, order=2)
            MCQOption.objects.create(question=mcq2, option_text='NaCl', is_correct=False, order=3)
            MCQOption.objects.create(question=mcq2, option_text='O2', is_correct=False, order=4)
            
            # Create Fill in the Blank Questions
            fill1 = Question.objects.create(
                question_type='fill_blank',
                subject=math_subject,
                question_text='The square root of 16 is ____.',
                difficulty='easy',
                marks=1,
                created_by=teacher
            )
            FillBlankAnswer.objects.create(question=fill1, correct_answer='4', is_case_sensitive=False)
            
            # Create True/False Questions
            tf1 = Question.objects.create(
                question_type='true_false',
                subject=science_subject,
                question_text='The Earth is flat.',
                difficulty='easy',
                marks=1,
                created_by=teacher
            )
            TrueFalseAnswer.objects.create(
                question=tf1, 
                correct_answer=False, 
                explanation='The Earth is spherical, not flat.'
            )
            
            # Create Short Answer Questions
            short1 = Question.objects.create(
                question_type='short_answer',
                subject=math_subject,
                question_text='Explain the Pythagorean theorem.',
                difficulty='medium',
                marks=3,
                created_by=teacher
            )
            ShortAnswer.objects.create(
                question=short1,
                sample_answer='The Pythagorean theorem states that in a right triangle, the square of the hypotenuse equals the sum of squares of the other two sides: a² + b² = c²',
                max_words=50
            )
            
            # Create Match Questions
            match1 = Question.objects.create(
                question_type='match',
                subject=science_subject,
                question_text='Match the elements with their symbols:',
                difficulty='medium',
                marks=2,
                created_by=teacher
            )
            MatchPair.objects.create(question=match1, left_item='Hydrogen', right_item='H', order=1)
            MatchPair.objects.create(question=match1, left_item='Oxygen', right_item='O', order=2)
            MatchPair.objects.create(question=match1, left_item='Carbon', right_item='C', order=3)
            
            # Create Question Papers
            math_paper = QuestionPaper.objects.create(
                title='Mathematics Basic Test',
                subject=math_subject,
                pattern='standard',
                duration_minutes=60,
                instructions='Answer all questions. Show your work.',
                created_by=teacher,
                is_published=True
            )
            
            # Add questions to paper
            PaperQuestion.objects.create(paper=math_paper, question=mcq1, order=1, marks=1, section='Section A')
            PaperQuestion.objects.create(paper=math_paper, question=fill1, order=2, marks=1, section='Section A')
            PaperQuestion.objects.create(paper=math_paper, question=short1, order=3, marks=3, section='Section B')
            
            math_paper.total_marks = math_paper.calculate_total_marks()
            math_paper.save()
            
            science_paper = QuestionPaper.objects.create(
                title='Science Fundamentals Quiz',
                subject=science_subject,
                pattern='section_wise',
                duration_minutes=45,
                instructions='Read each question carefully before answering.',
                created_by=teacher,
                is_published=True
            )
            
            PaperQuestion.objects.create(paper=science_paper, question=mcq2, order=1, marks=1, section='MCQ')
            PaperQuestion.objects.create(paper=science_paper, question=tf1, order=2, marks=1, section='True/False')
            PaperQuestion.objects.create(paper=science_paper, question=match1, order=3, marks=2, section='Matching')
            
            science_paper.total_marks = science_paper.calculate_total_marks()
            science_paper.save()
            
            self.stdout.write(
                self.style.SUCCESS('Successfully created quiz dummy data!')
            )
            self.stdout.write(f'Created {Question.objects.count()} questions')
            self.stdout.write(f'Created {QuestionPaper.objects.count()} question papers')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating quiz data: {e}')
            )