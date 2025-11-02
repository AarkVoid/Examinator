from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from accounts.models import User, Profile
from education.models import Board, StudentClass, Subject, Chapter, Division, Lesson
from institute.models import Institution, InstitutionGroup, InstitutionPasskey
from home.models import Comment, ContactMessage
from datetime import date, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populate database with dummy data'

    def handle(self, *args, **options):
        self.stdout.write('Creating dummy data...')
        
        # Create Groups
        student_group, _ = Group.objects.get_or_create(name='Students')
        teacher_group, _ = Group.objects.get_or_create(name='Teachers')
        admin_group, _ = Group.objects.get_or_create(name='Admins')
        
        # Create Institution Groups
        cbse_group, _ = InstitutionGroup.objects.get_or_create(
            name='CBSE Schools',
            defaults={'description': 'Central Board of Secondary Education affiliated schools'}
        )
        state_group, _ = InstitutionGroup.objects.get_or_create(
            name='State Board Schools',
            defaults={'description': 'State board affiliated schools'}
        )
        
        # Create Boards
        cbse_board, _ = Board.objects.get_or_create(name='CBSE')
        state_board, _ = Board.objects.get_or_create(name='State Board')
        icse_board, _ = Board.objects.get_or_create(name='ICSE')
        
        # Create Institutions
        school1, _ = Institution.objects.get_or_create(
            name='Delhi Public School',
            defaults={
                'code': 'DPS001',
                'address': '123 Education Street, Delhi',
                'board': cbse_board,
                'group': cbse_group
            }
        )
        school2, _ = Institution.objects.get_or_create(
            name='Modern High School',
            defaults={
                'code': 'MHS002',
                'address': '456 Learning Avenue, Mumbai',
                'board': state_board,
                'group': state_group
            }
        )
        
        # Create Classes
        class_10, _ = StudentClass.objects.get_or_create(name='Class 10', board=cbse_board)
        class_9, _ = StudentClass.objects.get_or_create(name='Class 9', board=cbse_board)
        class_8, _ = StudentClass.objects.get_or_create(name='Class 8', board=state_board)
        
        # Create Divisions
        div_a, _ = Division.objects.get_or_create(name='A', student_class=class_10)
        div_b, _ = Division.objects.get_or_create(name='B', student_class=class_10)
        div_a9, _ = Division.objects.get_or_create(name='A', student_class=class_9)
        
        # Create Subjects
        math, _ = Subject.objects.get_or_create(name='Mathematics', student_class=class_10)
        science, _ = Subject.objects.get_or_create(name='Science', student_class=class_10)
        english, _ = Subject.objects.get_or_create(name='English', student_class=class_9)
        history, _ = Subject.objects.get_or_create(name='History', student_class=class_8)
        
        # Create Chapters
        algebra, _ = Chapter.objects.get_or_create(name='Algebra', subject=math)
        geometry, _ = Chapter.objects.get_or_create(name='Geometry', subject=math)
        physics, _ = Chapter.objects.get_or_create(name='Physics', subject=science)
        chemistry, _ = Chapter.objects.get_or_create(name='Chemistry', subject=science)
        
        # Create Users
        admin_user, created = User.objects.get_or_create(
            email='admin@school.com',
            defaults={
                'username': 'admin@school.com',
                'role': 'admin',
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            
        teacher_user, created = User.objects.get_or_create(
            email='teacher@school.com',
            defaults={
                'username': 'teacher@school.com',
                'role': 'teacher',
                'is_active': True
            }
        )
        if created:
            teacher_user.set_password('teacher123')
            teacher_user.save()
            
        student_user, created = User.objects.get_or_create(
            email='student@school.com',
            defaults={
                'username': 'student@school.com',
                'role': 'student',
                'is_active': True
            }
        )
        if created:
            student_user.set_password('student123')
            student_user.save()
        
        # Create Profiles
        admin_profile, _ = Profile.objects.get_or_create(
            user=admin_user,
            defaults={
                'Name': 'John',
                'Surname': 'Admin',
                'Contact': 9876543210,
                'BirthDate': date(1980, 5, 15),
                'address': '123 Admin Street',
                'board': cbse_board,
                'class_field': class_10,
                'division': div_a,
                'institute': school1
            }
        )
        
        teacher_profile, _ = Profile.objects.get_or_create(
            user=teacher_user,
            defaults={
                'Name': 'Jane',
                'Surname': 'Teacher',
                'Contact': 9876543211,
                'BirthDate': date(1985, 8, 20),
                'address': '456 Teacher Lane',
                'board': cbse_board,
                'class_field': class_10,
                'institute': school1
            }
        )
        
        student_profile, _ = Profile.objects.get_or_create(
            user=student_user,
            defaults={
                'Name': 'Alice',
                'Surname': 'Student',
                'Contact': 9876543212,
                'BirthDate': date(2005, 12, 10),
                'address': '789 Student Road',
                'board': cbse_board,
                'class_field': class_10,
                'division': div_a,
                'institute': school1
            }
        )
        
        # Create Passkeys
        passkey1, _ = InstitutionPasskey.objects.get_or_create(
            institution=school1,
            defaults={
                'passkey': 'DPS2024',
                'valid_until': date.today() + timedelta(days=365)
            }
        )
        
        # Create Lessons
        lesson1, _ = Lesson.objects.get_or_create(
            title='Introduction to Algebra',
            defaults={
                'chapter': algebra,
                'content': 'Basic concepts of algebra including variables and expressions.',
                'notes': 'Remember to practice solving equations daily.',
                'created_by': teacher_user,
                'is_published': True
            }
        )
        
        lesson2, _ = Lesson.objects.get_or_create(
            title='Basic Geometry',
            defaults={
                'chapter': geometry,
                'content': 'Understanding shapes, angles, and geometric properties.',
                'notes': 'Use visual aids to understand geometric concepts better.',
                'created_by': teacher_user,
                'is_published': True
            }
        )
        
        # Create Comments
        comment1, _ = Comment.objects.get_or_create(
            user=student_user,
            defaults={
                'subject': 'Great Learning Platform',
                'message': 'This platform is really helpful for my studies!',
                'is_public': True
            }
        )
        
        # Create Contact Messages
        contact1, _ = ContactMessage.objects.get_or_create(
            email='parent@example.com',
            defaults={
                'name': 'Parent Name',
                'subject': 'Inquiry about admission',
                'message': 'I would like to know more about the admission process.',
                'has_been_read': False
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created dummy data for all models!')
        )