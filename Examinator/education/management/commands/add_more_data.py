from django.core.management.base import BaseCommand
from accounts.models import User, Profile
from education.models import Board, StudentClass, Subject, Chapter
from institute.models import Institution, InstitutionGroup
from datetime import date

class Command(BaseCommand):
    help = 'Add more dummy data entries'

    def handle(self, *args, **options):
        self.stdout.write('Adding more dummy data...')
        
        # Get existing objects
        cbse_board = Board.objects.get(name='CBSE')
        state_board = Board.objects.get(name='State Board')
        
        # Create more classes
        classes_data = [
            ('Class 12', cbse_board),
            ('Class 11', cbse_board), 
            ('Class 7', state_board),
            ('Class 6', state_board),
        ]
        
        for class_name, board in classes_data:
            StudentClass.objects.get_or_create(name=class_name, board=board)
        
        # Create more subjects
        class_12 = StudentClass.objects.get(name='Class 12', board=cbse_board)
        class_11 = StudentClass.objects.get(name='Class 11', board=cbse_board)
        
        subjects_data = [
            ('Physics', class_12),
            ('Chemistry', class_12),
            ('Biology', class_12),
            ('Computer Science', class_11),
            ('Economics', class_11),
            ('Political Science', class_11),
        ]
        
        for subject_name, student_class in subjects_data:
            Subject.objects.get_or_create(name=subject_name, student_class=student_class)
        
        # Create more users
        users_data = [
            ('teacher2@school.com', 'teacher', 'Math Teacher', 'Smith'),
            ('teacher3@school.com', 'teacher', 'Science Teacher', 'Johnson'),
            ('student2@school.com', 'student', 'Bob', 'Wilson'),
            ('student3@school.com', 'student', 'Carol', 'Brown'),
        ]
        
        school1 = Institution.objects.get(name='Delhi Public School')
        
        for email, role, first_name, last_name in users_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'role': role,
                    'is_active': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'Name': first_name,
                        'Surname': last_name,
                        'Contact': 9876543200 + user.id,
                        'BirthDate': date(1990, 1, 1),
                        'address': f'{user.id} Sample Street',
                        'board': cbse_board,
                        'institute': school1
                    }
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully added more dummy data!')
        )