# ruff: noqa
# Copyright 2026 Google LLC

import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
from google.cloud import firestore

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from pathlib import Path
from google import genai
from google.cloud import storage
from google.adk.tools import ToolContext
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

# HARDCODED GCP PROJECT ID, GCS BUCKET NAME, AND MEMORY BANK ID STRINGS
FIRESTORE_PROJECT = "qwiklabs-gcp-02-f445a748878b"
GCS_BUCKET_NAME = "fitness-coach-assets-qwiklabs-gcp-02-f445a748878b"
MEMORY_BANK_ID = "3490227588805165056"
os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ID", MEMORY_BANK_ID)

db = firestore.Client(project=FIRESTORE_PROJECT)


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends the session's events to Memory Bank for cross-session memory generation."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        # Memory service is optional / unavailable in this runtime invocation
        pass
    return None

# Load Agent Engine resource name from deployment_metadata.json if available
agent_engine_resource_name = None
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)
code_executor._project_id = FIRESTORE_PROJECT


async def generate_workout_visual(prompt: str, tool_context: ToolContext) -> str:
    """Generates a motivational workout image or exercise demonstration poster based on a descriptive prompt.

    Args:
        prompt: Description of the workout visual, exercise posture, or motivational image to generate (e.g., 'Motivational poster of a person performing a dumbbell bench press').

    Returns:
        Public HTTPS URL of the uploaded image.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    res = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"])
    )

    part = res.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/jpeg"

    timestamp_str = int(datetime.datetime.now().timestamp())
    filename = f"fitness_visual_{timestamp_str}.jpg"

    # 1. Save artifact for ADK Playground Artifacts panel
    artifact_part = types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=image_bytes)
    )
    await tool_context.save_artifact(filename, artifact_part)

    # 2. Upload image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return public_url


async def generate_workout_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short workout demonstration or exercise form video based on a descriptive prompt using Google's Omni model.

    Args:
        prompt: Description of the workout video or exercise form demonstration to generate (e.g., 'A short video clip showing correct form for a barbell back squat').

    Returns:
        Public HTTPS URL of the uploaded video.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    res = client.models.generate_content(
        model="gemini-omni-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["VIDEO"])
    )

    part = res.candidates[0].content.parts[0]
    video_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "video/mp4"

    timestamp_str = int(datetime.datetime.now().timestamp())
    filename = f"fitness_video_{timestamp_str}.mp4"

    # 1. Save artifact for ADK Playground Artifacts panel
    artifact_part = types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=video_bytes)
    )
    await tool_context.save_artifact(filename, artifact_part)

    # 2. Upload video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return public_url


def search_food_nutrition(query: str) -> str:
    """Searches the Open Food Facts public database for nutritional information (calories, protein, carbs, fat) of foods or supplements.

    Args:
        query: Food item, product name, or ingredient to look up (e.g., 'whey protein', 'banana', 'oatmeal').

    Returns:
        JSON string containing matching products and their nutritional values per 100g.
    """
    # Check optional API key from env var if configured; defaults to public open API endpoint
    api_key = os.getenv("FOOD_FACTS_API_KEY", "")
    encoded_query = urllib.parse.quote(query)
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={encoded_query}&search_simple=1&action=process&json=1&page_size=3"
    
    headers = {"User-Agent": "FitnessCoachAgent/1.0 (GoogleADK; LearningLab)"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            products = data.get("products", [])
            if not products:
                return f"No nutritional data found for food item '{query}'."

            results = []
            for item in products:
                name = item.get("product_name", "Unknown Product")
                brand = item.get("brands", "Generic")
                nutr = item.get("nutriments", {})
                results.append({
                    "product_name": name,
                    "brand": brand,
                    "calories_per_100g": nutr.get("energy-kcal_100g") or nutr.get("energy-kcal") or "N/A",
                    "protein_g_per_100g": nutr.get("proteins_100g") or nutr.get("proteins") or "N/A",
                    "carbs_g_per_100g": nutr.get("carbohydrates_100g") or nutr.get("carbohydrates") or "N/A",
                    "fat_g_per_100g": nutr.get("fat_100g") or nutr.get("fat") or "N/A"
                })
            return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error querying Open Food Facts API: {str(e)}"


def list_exercises(muscle_group: str = "") -> list[dict]:
    """Lists available exercises from the exercise library database, optionally filtered by target muscle group.

    Args:
        muscle_group: Optional target muscle group (e.g., 'Chest', 'Legs', 'Back', 'Core').

    Returns:
        List of exercise dictionaries matching the query.
    """
    collection_ref = db.collection("exercises")
    docs = collection_ref.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if not muscle_group or muscle_group.lower() in data.get("muscle_group", "").lower():
            results.append(data)
    return results


def get_exercise_details(exercise_id: str) -> dict:
    """Gets details and instructions for a specific exercise by ID.

    Args:
        exercise_id: Document ID of the exercise (e.g., 'push-ups', 'barbell-squat').

    Returns:
        Dictionary containing exercise details, or an error message if not found.
    """
    doc_ref = db.collection("exercises").document(exercise_id.lower().strip())
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Exercise '{exercise_id}' not found in database."}


def add_exercise(
    name: str,
    muscle_group: str,
    difficulty: str,
    equipment_needed: str,
    description: str,
    instructions: str = ""
) -> str:
    """Adds a new exercise or updates an existing exercise in the exercise database.

    Args:
        name: Name of the exercise (e.g., 'Overhead Shoulder Press').
        muscle_group: Primary muscle group (e.g., 'Shoulders', 'Chest', 'Legs').
        difficulty: Difficulty level ('Beginner', 'Intermediate', 'Advanced').
        equipment_needed: Required equipment (e.g., 'Dumbbells', 'Barbell', 'Bodyweight').
        description: Short overview of the exercise.
        instructions: Step-by-step performance instructions.

    Returns:
        Success message confirming exercise addition.
    """
    doc_id = name.lower().replace(" ", "-").strip()
    exercise_data = {
        "id": doc_id,
        "name": name,
        "muscle_group": muscle_group,
        "difficulty": difficulty,
        "equipment_needed": equipment_needed,
        "description": description,
        "instructions": instructions
    }
    db.collection("exercises").document(doc_id).set(exercise_data)
    return f"Successfully saved exercise '{name}' to Firestore database (ID: {doc_id})."


def log_workout_session(
    exercise_name: str,
    sets: int,
    reps: int,
    weight_lbs: float = 0.0,
    notes: str = ""
) -> str:
    """Logs a completed workout session to the user's workout log history in Firestore.

    Args:
        exercise_name: Name of the exercise performed (e.g., 'Push-Ups', 'Barbell Back Squat').
        sets: Number of sets completed.
        reps: Repetitions per set.
        weight_lbs: Weight used in pounds (0.0 for bodyweight exercises).
        notes: Optional comments on effort, form, or energy level.

    Returns:
        Confirmation message with logged details.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_entry = {
        "exercise_name": exercise_name,
        "sets": sets,
        "reps": reps,
        "weight_lbs": weight_lbs,
        "notes": notes,
        "timestamp": timestamp,
    }
    _, doc_ref = db.collection("workout_logs").add(log_entry)
    return (
        f"Successfully logged workout: {sets} sets of {reps} reps for '{exercise_name}' "
        f"@ {weight_lbs} lbs (Log ID: {doc_ref.id})."
    )


def get_weather(query: str) -> str:
    """Simulates getting weather information."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting current time."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="You are Fitness Coach AI, a knowledgeable and encouraging fitness assistant.",
    workflow_description="Analyze the user request, call tools as needed, and return structured A2UI when appropriate to present workouts, exercises, nutrition facts, calculations, and visuals.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

instruction = (
    a2ui_instruction + "\n\n"
    "Additional guidelines:\n"
    "1. Pay special attention to and remember all user allergies (e.g. peanuts, dairy, gluten, shellfish, penicillin), "
    "dietary restrictions, and health/fitness preferences across sessions. Always cross-check and enforce these "
    "allergies before recommending foods, meals, or supplement plans.\n"
    "2. Use your exercise library tools (list_exercises, get_exercise_details, add_exercise) "
    "to help users find exercises and expand their routine database, use log_workout_session "
    "to log completed workout sets and track history, use search_food_nutrition to look up "
    "nutritional facts and macros for foods and supplements, use generate_workout_visual "
    "to generate workout motivation cards and posture demonstration posters, use generate_workout_video "
    "to generate exercise demonstration video clips, and use your "
    "Python code execution sandbox to perform complex fitness calculations or data analysis. "
    "To run Python code in the sandbox, output the code inside a ```python markdown block."
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_exercises,
        get_exercise_details,
        add_exercise,
        log_workout_session,
        search_food_nutrition,
        generate_workout_visual,
        generate_workout_video,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

from google.adk.memory import VertexAiMemoryBankService


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


app = App(
    root_agent=root_agent,
    name="app",
)
