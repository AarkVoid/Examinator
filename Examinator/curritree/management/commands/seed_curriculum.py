from django.core.management.base import BaseCommand
from curritree.models import TreeNode
from django.contrib.auth import get_user_model
from django.db import IntegrityError 

class Command(BaseCommand):
    help = "Seed dummy curriculum entries into TreeNode"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding dummy curriculum..."))

        # Clear old data if needed
        User = get_user_model()
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.create_user(email='test@example.com', username='testuser', password='password123', role='admin')
        except Exception as e:
            print(f"Error getting/creating admin user: {e}. Please ensure a user exists.")
            admin_user = None

        if not admin_user:
            print("FATAL: Cannot proceed without an admin user.")
            exit()

        print("--- 1. Creating EXPANDED Curriculum Hierarchy (TreeNodes) ---")

        # --- LEVEL 0: Boards (Roots) ---
        board_cbse, _ = TreeNode.objects.get_or_create(name="CBSE", node_type="board", parent=None, defaults={'order': 0})
        board_icse, _ = TreeNode.objects.get_or_create(name="ICSE", node_type="board", parent=None, defaults={'order': 1})

        # --- LEVEL 1: Classes ---

        # CBSE Classes
        classes_cbse = {}
        for i, name in enumerate(["Class 9", "Class 10", "Class 11", "Class 12"]):
            classes_cbse[name], _ = TreeNode.objects.get_or_create(
                name=name, node_type="class", parent=board_cbse, defaults={'order': i}
            )
        class_10_cbse = classes_cbse["Class 10"]
        class_12_cbse = classes_cbse["Class 12"]

        # ICSE Classes
        classes_icse = {}
        for i, name in enumerate(["Class 8", "Class 9", "Class 10"]):
            classes_icse[name], _ = TreeNode.objects.get_or_create(
                name=name, node_type="class", parent=board_icse, defaults={'order': i}
            )
        class_9_icse = classes_icse["Class 9"]

        # --- LEVEL 2: Subjects ---

        # Subjects for CBSE Class 10
        sub_math_cbse, _ = TreeNode.objects.get_or_create(name="Mathematics", node_type="subject", parent=class_10_cbse, defaults={'order': 0})
        sub_sci_cbse, _ = TreeNode.objects.get_or_create(name="Science", node_type="subject", parent=class_10_cbse, defaults={'order': 1})
        sub_soc_cbse, _ = TreeNode.objects.get_or_create(name="Social Studies", node_type="subject", parent=class_10_cbse, defaults={'order': 2})

        # Subjects for CBSE Class 12 (Science Stream)
        sub_phy_cbse_12, _ = TreeNode.objects.get_or_create(name="Physics", node_type="subject", parent=class_12_cbse, defaults={'order': 0})
        sub_chem_cbse_12, _ = TreeNode.objects.get_or_create(name="Chemistry", node_type="subject", parent=class_12_cbse, defaults={'order': 1})

        # Subjects for ICSE Class 9
        sub_hist_icse, _ = TreeNode.objects.get_or_create(name="History", node_type="subject", parent=class_9_icse, defaults={'order': 0})
        sub_geo_icse, _ = TreeNode.objects.get_or_create(name="Geography", node_type="subject", parent=class_9_icse, defaults={'order': 1})

        # --- LEVEL 3: Chapters ---

        chapters_created = []

        # Chapters for CBSE Class 10 Mathematics
        for i, name in enumerate(["Polynomials", "Trigonometry", "Quadratic Equations", "Statistics"]):
            chap, _ = TreeNode.objects.get_or_create(
                name=name, node_type="chapter", parent=sub_math_cbse, defaults={'order': i}
            )
            chapters_created.append(chap)
        chap_poly = chapters_created[0] # Keep a reference to one chapter for question creation

        # Chapters for CBSE Class 10 Science
        for i, name in enumerate(["Chemical Reactions", "Carbon Compounds", "Life Processes", "Light Reflection"]):
            chap, _ = TreeNode.objects.get_or_create(
                name=name, node_type="chapter", parent=sub_sci_cbse, defaults={'order': i}
            )
            chapters_created.append(chap)
        chap_chem_eq = chapters_created[4] # Keep a reference to one chapter

        # Chapters for CBSE Class 10 Social Studies
        for i, name in enumerate(["Nationalism in India", "Water Resources", "Power Sharing"]):
            chap, _ = TreeNode.objects.get_or_create(
                name=name, node_type="chapter", parent=sub_soc_cbse, defaults={'order': i}
            )
            chapters_created.append(chap)

        # Chapters for CBSE Class 12 Physics
        for i, name in enumerate(["Electrostatics", "Current Electricity", "Magnetism"]):
            chap, _ = TreeNode.objects.get_or_create(
                name=name, node_type="chapter", parent=sub_phy_cbse_12, defaults={'order': i}
            )
            chapters_created.append(chap)

        # Chapters for ICSE Class 9 History
        for i, name in enumerate(["French Revolution", "The World Wars", "Rise of Dictatorship"]):
            chap, _ = TreeNode.objects.get_or_create(
                name=name, node_type="chapter", parent=sub_hist_icse, defaults={'order': i}
            )
            chapters_created.append(chap)
        chap_french = chapters_created[14] # Keep a reference to one chapter

        print("\n--- Summary of Expanded Curriculum ---")
        print(f"Total Boards: {TreeNode.objects.filter(node_type='board').count()}")
        print(f"Total Classes: {TreeNode.objects.filter(node_type='class').count()}")
        print(f"Total Subjects: {TreeNode.objects.filter(node_type='subject').count()}")
        print(f"Total Chapters: {TreeNode.objects.filter(node_type='chapter').count()}")
        print(f"Math Chapter Node ID: {chap_poly.id}")

        # --- 2. Creating Dummy Questions (Linked to new structure) ---
        # Assuming your Question model is in quiz/models.py
        try:
            from quiz.models import Question
            
            # Simple Question Types/Difficulties assumed for demonstration
            QUESTION_TYPE_MCQ = "MCQ" 
            DIFFICULTY_EASY = "EASY"
            DIFFICULTY_MEDIUM = "MEDIUM"

            # Clean up old questions and create new ones
            Question.objects.all().delete()
            print("\nExisting questions deleted. Creating new dummy questions...")

            q_data = [
                # CBSE 10 Math (Polynomials)
                ("What is the degree of the polynomial $x^5 - 4x^2 + 7$?", QUESTION_TYPE_MCQ, DIFFICULTY_EASY, chap_poly),
                ("Find the zeros of the quadratic polynomial $x^2 - 3x - 4$.", QUESTION_TYPE_MCQ, DIFFICULTY_MEDIUM, chap_poly),
                
                # CBSE 10 Science (Chemical Reactions)
                ("Which type of reaction is the decomposition of silver chloride?", QUESTION_TYPE_MCQ, DIFFICULTY_MEDIUM, chap_chem_eq),
                ("Balance the equation: $\\text{Fe} + \\text{H}_2\\text{O} \\rightarrow \\text{Fe}_3\\text{O}_4 + \\text{H}_2$", QUESTION_TYPE_MCQ, DIFFICULTY_HARD, chap_chem_eq),
                
                # CBSE 12 Physics (Electrostatics)
                ("State Coulomb's Law.", "SJT", DIFFICULTY_EASY, sub_phy_cbse_12), # Linked to Subject level
                
                # ICSE 9 History (French Revolution)
                ("Briefly describe the significance of the Storming of the Bastille.", "SJT", DIFFICULTY_MEDIUM, chap_french),
            ]

            for text, q_type, difficulty, node in q_data:
                Question.objects.get_or_create(
                    question_text=text,
                    question_type=q_type,
                    difficulty=difficulty,
                    marks=1.0,
                    curriculum_node=node,
                    created_by=admin_user,
                    defaults={'is_published': True}
                )
            
            print(f"Created {len(q_data)} new dummy questions.")
            
        except ImportError:
            print("\nSkipping question creation: 'quiz.models.Question' not found or imported incorrectly.")
        except Exception as e:
            print(f"\nError creating questions: {e}")
