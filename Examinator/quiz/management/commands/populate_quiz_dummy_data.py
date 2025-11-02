from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from quiz.models import *
from education.models import Subject, Chapter
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate quiz database with comprehensive dummy data'

    def handle(self, *args, **options):
        # Get or create a teacher user
        teacher, created = User.objects.get_or_create(
            username='teacher1',
            defaults={
                'email': 'teacher@example.com',
                'first_name': 'John',
                'last_name': 'Teacher',
                'role': 'teacher'
            }
        )
        if created:
            teacher.set_password('password123')
            teacher.save()

        # Get subjects
        subjects = list(Subject.objects.all())
        if not subjects:
            self.stdout.write('No subjects found. Please run education dummy data first.')
            return

        # Create MCQ Questions
        mcq_questions = [
            {'text': 'What is the capital of France?', 'options': [('Paris', True), ('London', False), ('Berlin', False), ('Madrid', False)]},
            {'text': 'Which planet is known as the Red Planet?', 'options': [('Venus', False), ('Mars', True), ('Jupiter', False), ('Saturn', False)]},
            {'text': 'What is 2 + 2?', 'options': [('3', False), ('4', True), ('5', False), ('6', False)]},
            {'text': 'Who wrote Romeo and Juliet?', 'options': [('Charles Dickens', False), ('William Shakespeare', True), ('Jane Austen', False), ('Mark Twain', False)]},
            {'text': 'What is the largest ocean on Earth?', 'options': [('Atlantic Ocean', False), ('Indian Ocean', False), ('Pacific Ocean', True), ('Arctic Ocean', False)]},
            {'text': 'What is the chemical symbol for gold?', 'options': [('Go', False), ('Gd', False), ('Au', True), ('Ag', False)]},
            {'text': 'How many continents are there?', 'options': [('5', False), ('6', False), ('7', True), ('8', False)]},
            {'text': 'What is the smallest prime number?', 'options': [('0', False), ('1', False), ('2', True), ('3', False)]},
            {'text': 'Which gas makes up most of Earth\'s atmosphere?', 'options': [('Oxygen', False), ('Carbon Dioxide', False), ('Nitrogen', True), ('Hydrogen', False)]},
            {'text': 'What year did World War II end?', 'options': [('1944', False), ('1945', True), ('1946', False), ('1947', False)]},
            {'text': 'What is the largest mammal?', 'options': [('Elephant', False), ('Blue Whale', True), ('Giraffe', False), ('Hippopotamus', False)]},
            {'text': 'Which programming language is known for AI?', 'options': [('Java', False), ('C++', False), ('Python', True), ('JavaScript', False)]},
            {'text': 'What is the speed of light?', 'options': [('300,000 km/s', True), ('150,000 km/s', False), ('450,000 km/s', False), ('600,000 km/s', False)]},
            {'text': 'Who painted the Mona Lisa?', 'options': [('Van Gogh', False), ('Picasso', False), ('Leonardo da Vinci', True), ('Michelangelo', False)]},
            {'text': 'What is the hardest natural substance?', 'options': [('Gold', False), ('Iron', False), ('Diamond', True), ('Platinum', False)]},
            {'text': 'Which organ produces insulin?', 'options': [('Liver', False), ('Kidney', False), ('Pancreas', True), ('Heart', False)]},
            {'text': 'What is the capital of Australia?', 'options': [('Sydney', False), ('Melbourne', False), ('Canberra', True), ('Perth', False)]},
            {'text': 'How many sides does a hexagon have?', 'options': [('5', False), ('6', True), ('7', False), ('8', False)]},
            {'text': 'What is the currency of Japan?', 'options': [('Yuan', False), ('Won', False), ('Yen', True), ('Rupee', False)]},
            {'text': 'Which element has the symbol O?', 'options': [('Gold', False), ('Oxygen', True), ('Silver', False), ('Iron', False)]}
        ]

        for i, mcq_data in enumerate(mcq_questions):
            question = Question.objects.create(
                question_type='mcq',
                subject=random.choice(subjects),
                question_text=mcq_data['text'],
                difficulty=random.choice(['easy', 'medium', 'hard']),
                marks=random.randint(1, 5),
                created_by=teacher
            )
            
            for j, (option_text, is_correct) in enumerate(mcq_data['options']):
                MCQOption.objects.create(
                    question=question,
                    option_text=option_text,
                    is_correct=is_correct,
                    order=j + 1
                )

        # Create Fill in the Blank Questions
        fill_blank_questions = [
            {'text': 'The capital of India is ______.', 'answers': ['New Delhi', 'Delhi']},
            {'text': 'Water boils at ______ degrees Celsius.', 'answers': ['100', '100°C']},
            {'text': 'The largest mammal in the world is the ______.', 'answers': ['Blue Whale', 'blue whale']},
            {'text': 'HTML stands for HyperText ______ Language.', 'answers': ['Markup', 'markup']},
            {'text': 'The process by which plants make food is called ______.', 'answers': ['photosynthesis', 'Photosynthesis']},
            {'text': 'The smallest unit of matter is an ______.', 'answers': ['atom', 'Atom']},
            {'text': 'The study of earthquakes is called ______.', 'answers': ['seismology', 'Seismology']},
            {'text': 'The longest river in the world is the ______.', 'answers': ['Nile', 'Nile River']},
            {'text': 'The formula for water is ______.', 'answers': ['H2O', 'h2o']},
            {'text': 'The first man on the moon was ______.', 'answers': ['Neil Armstrong', 'armstrong']},
            {'text': 'The largest planet in our solar system is ______.', 'answers': ['Jupiter', 'jupiter']},
            {'text': 'The currency of the United States is the ______.', 'answers': ['Dollar', 'dollar']},
            {'text': 'The human body has ______ bones.', 'answers': ['206', '206 bones']},
            {'text': 'The Great Wall of China was built in ______.', 'answers': ['China', 'china']},
            {'text': 'The inventor of the telephone was ______.', 'answers': ['Alexander Graham Bell', 'Bell']}
        ]

        for fb_data in fill_blank_questions:
            question = Question.objects.create(
                question_type='fill_blank',
                subject=random.choice(subjects),
                question_text=fb_data['text'],
                difficulty=random.choice(['easy', 'medium', 'hard']),
                marks=random.randint(1, 3),
                created_by=teacher
            )
            
            for answer in fb_data['answers']:
                FillBlankAnswer.objects.create(
                    question=question,
                    correct_answer=answer,
                    is_case_sensitive=random.choice([True, False])
                )

        # Create True/False Questions
        tf_questions = [
            {'text': 'The Earth is flat.', 'answer': False, 'explanation': 'The Earth is spherical in shape.'},
            {'text': 'Python is a programming language.', 'answer': True, 'explanation': 'Python is indeed a popular programming language.'},
            {'text': 'There are 24 hours in a day.', 'answer': True, 'explanation': 'A day consists of 24 hours.'},
            {'text': 'The sun revolves around the Earth.', 'answer': False, 'explanation': 'The Earth revolves around the sun.'},
            {'text': 'Water freezes at 0 degrees Celsius.', 'answer': True, 'explanation': 'Water freezes at 0°C under normal atmospheric pressure.'},
            {'text': 'All birds can fly.', 'answer': False, 'explanation': 'Some birds like penguins and ostriches cannot fly.'},
            {'text': 'The human heart has four chambers.', 'answer': True, 'explanation': 'The heart has two atria and two ventricles.'},
            {'text': 'Lightning never strikes the same place twice.', 'answer': False, 'explanation': 'Lightning can and often does strike the same place multiple times.'},
            {'text': 'Sharks are mammals.', 'answer': False, 'explanation': 'Sharks are fish, not mammals.'},
            {'text': 'The Great Wall of China is visible from space.', 'answer': False, 'explanation': 'This is a common myth; it\'s not visible from space with the naked eye.'},
            {'text': 'Honey never spoils.', 'answer': True, 'explanation': 'Honey has natural preservative properties and can last indefinitely.'},
            {'text': 'Humans use only 10% of their brain.', 'answer': False, 'explanation': 'This is a myth; humans use virtually all of their brain.'},
            {'text': 'The Amazon rainforest produces 20% of the world\'s oxygen.', 'answer': True, 'explanation': 'The Amazon is often called the "lungs of the Earth".'},
            {'text': 'Goldfish have a 3-second memory.', 'answer': False, 'explanation': 'Goldfish can remember things for months, not seconds.'},
            {'text': 'Mount Everest is the tallest mountain on Earth.', 'answer': True, 'explanation': 'Mount Everest stands at 29,029 feet above sea level.'}
        ]

        for tf_data in tf_questions:
            question = Question.objects.create(
                question_type='true_false',
                subject=random.choice(subjects),
                question_text=tf_data['text'],
                difficulty=random.choice(['easy', 'medium', 'hard']),
                marks=random.randint(1, 2),
                created_by=teacher
            )
            
            TrueFalseAnswer.objects.create(
                question=question,
                correct_answer=tf_data['answer'],
                explanation=tf_data['explanation']
            )

        # Create Short Answer Questions
        short_answer_questions = [
            {'text': 'Explain the process of photosynthesis.', 'sample': 'Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen.', 'max_words': 100},
            {'text': 'What are the benefits of exercise?', 'sample': 'Exercise improves cardiovascular health, strengthens muscles, boosts mental health, and helps maintain a healthy weight.', 'max_words': 75},
            {'text': 'Describe the water cycle.', 'sample': 'The water cycle involves evaporation, condensation, precipitation, and collection of water in a continuous process.', 'max_words': 80},
            {'text': 'What is climate change and its causes?', 'sample': 'Climate change refers to long-term shifts in global temperatures and weather patterns, primarily caused by human activities like burning fossil fuels.', 'max_words': 120},
            {'text': 'Explain the importance of biodiversity.', 'sample': 'Biodiversity ensures ecosystem stability, provides resources for medicine and food, and maintains ecological balance.', 'max_words': 90},
            {'text': 'What is artificial intelligence?', 'sample': 'AI is the simulation of human intelligence in machines that are programmed to think and learn like humans.', 'max_words': 85},
            {'text': 'Describe the structure of an atom.', 'sample': 'An atom consists of a nucleus containing protons and neutrons, surrounded by electrons in orbital shells.', 'max_words': 70},
            {'text': 'What is democracy and its principles?', 'sample': 'Democracy is a system of government where power is held by the people through elected representatives, based on equality and freedom.', 'max_words': 95},
            {'text': 'Explain renewable energy sources.', 'sample': 'Renewable energy comes from natural sources like solar, wind, hydro, and geothermal that replenish themselves naturally.', 'max_words': 80},
            {'text': 'What is the greenhouse effect?', 'sample': 'The greenhouse effect is the warming of Earth due to certain gases in the atmosphere trapping heat from the sun.', 'max_words': 75}
        ]

        for sa_data in short_answer_questions:
            question = Question.objects.create(
                question_type='short_answer',
                subject=random.choice(subjects),
                question_text=sa_data['text'],
                difficulty=random.choice(['medium', 'hard']),
                marks=random.randint(3, 10),
                created_by=teacher
            )
            
            ShortAnswer.objects.create(
                question=question,
                sample_answer=sa_data['sample'],
                max_words=sa_data['max_words']
            )

        # Create Match the Following Questions
        match_questions = [
            {'text': 'Match the countries with their capitals:', 'pairs': [('France', 'Paris'), ('Germany', 'Berlin'), ('Italy', 'Rome'), ('Spain', 'Madrid')]},
            {'text': 'Match the animals with their habitats:', 'pairs': [('Fish', 'Water'), ('Bird', 'Sky'), ('Lion', 'Jungle'), ('Penguin', 'Antarctica')]},
            {'text': 'Match the scientists with their discoveries:', 'pairs': [('Newton', 'Gravity'), ('Einstein', 'Relativity'), ('Darwin', 'Evolution'), ('Curie', 'Radioactivity')]},
            {'text': 'Match the planets with their characteristics:', 'pairs': [('Mars', 'Red Planet'), ('Saturn', 'Rings'), ('Venus', 'Hottest'), ('Jupiter', 'Largest')]},
            {'text': 'Match the programming languages with their uses:', 'pairs': [('Python', 'AI/ML'), ('JavaScript', 'Web Development'), ('C++', 'System Programming'), ('SQL', 'Database')]},
            {'text': 'Match the organs with their functions:', 'pairs': [('Heart', 'Pumps Blood'), ('Lungs', 'Gas Exchange'), ('Liver', 'Detoxification'), ('Brain', 'Control Center')]},
            {'text': 'Match the chemical elements with their symbols:', 'pairs': [('Hydrogen', 'H'), ('Carbon', 'C'), ('Oxygen', 'O'), ('Nitrogen', 'N')]},
            {'text': 'Match the literary works with their authors:', 'pairs': [('1984', 'George Orwell'), ('Pride and Prejudice', 'Jane Austen'), ('Hamlet', 'Shakespeare'), ('The Great Gatsby', 'F. Scott Fitzgerald')]}
        ]

        for match_data in match_questions:
            question = Question.objects.create(
                question_type='match',
                subject=random.choice(subjects),
                question_text=match_data['text'],
                difficulty=random.choice(['medium', 'hard']),
                marks=random.randint(4, 8),
                created_by=teacher
            )
            
            for i, (left, right) in enumerate(match_data['pairs']):
                MatchPair.objects.create(
                    question=question,
                    left_item=left,
                    right_item=right,
                    order=i + 1
                )

        # Only create questions, no papers
        self.stdout.write('Skipping question paper creation - only adding questions as requested.')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {Question.objects.count()} questions with complete answers and options'
            )
        )