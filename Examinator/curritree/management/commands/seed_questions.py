from curritree.models import TreeNode
from django.contrib.auth import get_user_model
from quiz.models import Question
from django.db import transaction
from django.core.management.base import BaseCommand

# --- Configuration (Based on your Question model choices) ---
QUESTION_TYPES = ['mcq', 'fill_blank', 'short_answer', 'match', 'true_false']
COUNT_PER_TYPE = 2 # Target 2 questions per type per chapter (Total 10 per chapter)
DIFFICULTY_LEVELS = ['easy', 'medium', 'hard']


class Command(BaseCommand):
    help = "Seed dummy curriculum entries into TreeNode"

    def handle(self, *args, **options):
        # --- User Setup ---
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

        # --- Utility Function for Subject-Specific Text ---

        def generate_subject_specific_text(subject_name, chapter_name, q_type_key, index):
            """Generates unique, context-aware question text."""
            base_text = f"({q_type_key.upper()} {index+1}) For the chapter '{chapter_name}' in {subject_name}: "

            if 'math' in subject_name.lower():
                if 'polynomials' in chapter_name.lower():
                    return base_text + "Determine the number of zeros for the given quadratic equation's graph."
                if 'trigonometry' in chapter_name.lower():
                    return base_text + "Calculate the value of $\\sin^2\\theta + \\cos^2\\theta$."
                # Generic math
                return base_text + "Solve for X in the given linear equation."
            
            elif 'science' in subject_name.lower():
                if 'chemical reactions' in chapter_name.lower():
                    return base_text + "What type of reaction occurs when a single compound breaks down into two or more simpler substances?"
                if 'life processes' in chapter_name.lower():
                    return base_text + "Identify the site of photosynthesis in a plant cell."
                # Generic science
                return base_text + "Define the term 'inertia' and provide an example."
                
            elif 'history' in subject_name.lower():
                if 'french revolution' in chapter_name.lower():
                    return base_text + "Who wrote the pamphlet 'What is the Third Estate?'"
                if 'nationalism in india' in chapter_name.lower():
                    return base_text + "When was the Rowlatt Act passed?"
                # Generic history
                return base_text + "Name the capital of the Roman Empire during its peak."
                
            # Default fallback text
            return base_text + f"General question about the core concepts of {chapter_name}."


        # --- Data Generation Logic ---

        print("--- 1. DELETING all existing questions for clean generation ---")
        Question.objects.all().delete()

        print("\n--- 2. GENERATING Subject-Specific questions (2 of each type per chapter) ---")

        chapter_nodes = TreeNode.objects.filter(node_type='chapter')
        total_chapters = chapter_nodes.count()
        total_questions = 0

        print(f"Found {total_chapters} Chapter nodes. Target: {total_chapters * len(QUESTION_TYPES) * COUNT_PER_TYPE} questions.")

        with transaction.atomic():
            for chapter in chapter_nodes:
                # 1. Retrieve Ancestors (Board and Subject)
                ancestors = chapter.get_ancestors()
                
                board_node = next((n for n in ancestors if n.node_type == 'board'), None)
                subject_node = next((n for n in ancestors if n.node_type == 'subject'), None)

                if not board_node or not subject_node:
                    print(f"Skipping chapter '{chapter.name}': Missing Board or Subject ancestor.")
                    continue

                for q_type_key in QUESTION_TYPES:
                    for i in range(COUNT_PER_TYPE):
                        # Cycle through difficulty levels
                        difficulty_level = DIFFICULTY_LEVELS[i % len(DIFFICULTY_LEVELS)] 
                        
                        # Generate unique, subject-specific text
                        q_text = generate_subject_specific_text(
                            subject_node.name, 
                            chapter.name, 
                            q_type_key, 
                            i
                        )
                        
                        Question.objects.create(
                            question_text=q_text,
                            question_type=q_type_key,
                            difficulty=difficulty_level,
                            marks=2.0 + (i * 0.5),
                            
                            # --- THE EXPLICIT LINKS ---
                            curriculum_board=board_node,
                            curriculum_subject=subject_node,
                            curriculum_chapter=chapter,
                            # -------------------------
                            
                            created_by=admin_user,
                            is_published=True
                        )
                        total_questions += 1

        print("\n--- 3. VERIFICATION AND SUMMARY ---")
        final_count = Question.objects.count()
        print(f"Total Chapter Nodes Processed: {total_chapters}")
        print(f"Total Questions Generated: {final_count}")
        print(f"Questions per Chapter: {final_count / total_chapters if total_chapters else 0:.0f}")

        # Example check
        first_q = Question.objects.first()
        if first_q:
            print(f"\nExample Question Check (QID: {first_q.id}):")
            print(f"  Type: {first_q.question_type}")
            print(f"  Board: {first_q.curriculum_board.name}")
            print(f"  Subject: {first_q.curriculum_subject.name}")
            print(f"  Text: {first_q.question_text}")