# Copyright 2026 Google LLC
# Seed Firestore with initial exercise catalog for Fitness Coach AI

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-f445a748878b"
COLLECTION_NAME = "exercises"

SEED_EXERCISES = [
    {
        "id": "push-ups",
        "name": "Push-Ups",
        "muscle_group": "Chest",
        "difficulty": "Beginner",
        "equipment_needed": "Bodyweight",
        "description": "A classic compound exercise targeting chest, shoulders, and triceps.",
        "instructions": "Maintain a rigid plank position, lower chest to near floor, push back up explosive."
    },
    {
        "id": "barbell-squat",
        "name": "Barbell Back Squat",
        "muscle_group": "Legs",
        "difficulty": "Intermediate",
        "equipment_needed": "Barbell",
        "description": "Primary lower-body strength builder targeting quadriceps, glutes, and hamstrings.",
        "instructions": "Position bar across upper back, squat down until thighs parallel to floor, drive through heels."
    },
    {
        "id": "pull-ups",
        "name": "Pull-Ups",
        "muscle_group": "Back",
        "difficulty": "Intermediate",
        "equipment_needed": "Pull-up bar",
        "description": "Upper-body pulling exercise targeting latissimus dorsi and biceps.",
        "instructions": "Overhand grip, pull chin over bar with elbows driving down, lower with control."
    },
    {
        "id": "dumbbell-bench-press",
        "name": "Dumbbell Bench Press",
        "muscle_group": "Chest",
        "difficulty": "Intermediate",
        "equipment_needed": "Dumbbells",
        "description": "Chest press variation allowing greater range of motion and stabilizer recruitment.",
        "instructions": "Lie flat on bench, press dumbbells upward above chest, lower until chest stretch."
    },
    {
        "id": "plank",
        "name": "Forearm Plank",
        "muscle_group": "Core",
        "difficulty": "Beginner",
        "equipment_needed": "Bodyweight",
        "description": "Isometric core exercise strengthening abdominal wall, obliques, and lower back.",
        "instructions": "Hold straight body line supported on forearms and toes, squeeze glutes and core."
    },
    {
        "id": "romanian-deadlift",
        "name": "Romanian Deadlift",
        "muscle_group": "Legs",
        "difficulty": "Intermediate",
        "equipment_needed": "Barbell",
        "description": "Posterior chain movement focusing on hamstrings and glute strength.",
        "instructions": "Hinge at hips with soft knee bend, lower barbell along shins, contract glutes to return."
    }
]

def seed():
    db = firestore.Client(project=PROJECT_ID)
    print(f"Seeding '{COLLECTION_NAME}' collection in Firestore project: {PROJECT_ID}...")
    
    collection_ref = db.collection(COLLECTION_NAME)
    for exercise in SEED_EXERCISES:
        doc_id = exercise["id"]
        collection_ref.document(doc_id).set(exercise)
        print(f"  ✓ Added exercise: {exercise['name']} ({doc_id})")
        
    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed()
