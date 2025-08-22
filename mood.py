
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools import tool


from agno.models.openai import OpenAIChat as OpenAIModel

from openai import OpenAI as OpenAIClient



load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")


POSTURE_MODEL_ID = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")



@tool
def quiz(feel: int, down: int, sleep: int, connected: int, stress: int):
    """
    Receive 1–5 Likert scores and echo them back in a structured way
    so the agent can analyze them.
    """
    return {
        "anxiety": feel,
        "low_mood": down,
        "sleep_quality": sleep,
        "social_support": connected,
        "stress": stress,
    }


@tool
def food(type: str):
    "Give a diet plan based on the type of diet chosen from bulking or cutting."
    return {"type": type}


@tool
def workout(difficulty: str, option: str, time: int, mood: str = None):
    """Give a workout plan based on difficulty, style option, time, and mood."""
    return {
        "difficulty": difficulty, 
        "option": option, 
        "time_minutes": time,
        "mood": mood
    }



well = Agent(
    name="Well-Being Quiz",
    role="Expert in youth mental health and practical self-care",
    model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.1-70b-instant")),
    tools=[quiz],
    instructions=[
        "Always CALL the quiz tool with: feel, down, sleep, connected, stress.",
        "Interpret scales: 1=never/very poor, 3=moderate, 5=very often/very good.",
        "Reason on patterns (e.g., high anxiety+poor sleep; low support+high stress).",
        "Return concise, caring advice with 4–6 concrete steps for the next 7 days.",
        "Flag red-flags gently (e.g., scores ≥4 for down/anxiety/stress) and suggest talking to a trusted adult or a professional if needed.",
        "Keep it ~120–160 words, bullet points, no diagnosis.",
    ],
)

daily = Agent(
    name="Daily task page",
    role="Give daily tasks for the user",
    model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.1-70b-instant")),
    instructions=[
        "Give a task when the user asks for it.",
        "Return a single task that is easy to do and can be done in less than 5 minutes.",
        "Difficulty roughly comparable to 20 push-ups.",
        "Activities must be doable at home.",
        "Vary the types: movement, breathing, stretching, tidying, hydration, sunlight exposure, quick learning.",
        "Keep responses under 15 words and actionable.",
        "Output only the task text.",
    ],
)

diet = Agent(
    name="Diet Planner",
    role="Diet planner",
    model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.1-70b-instant")),
    tools=[food],
    instructions=[
        "You are a personalized AI nutritionist.",
        "The user will specify whether their goal is cutting (fat loss) or bulking (muscle gain).",
        "Generate a 7-day meal plan that matches their goal.",
        "Each day should include: Breakfast, Lunch, Dinner, and 2 Snacks.",
        "Give exact portion sizes (grams, cups, etc.) and macros (protein, carbs, fats, calories).",
        "Ensure variety across the week (not repeating the same meals too much).",
        "Use simple, affordable foods available at most grocery stores.",
        "Highlight key tips (e.g., hydration, meal prep).",
        "If cutting → high protein, moderate carbs, low–moderate fats.",
        "If bulking → high protein, high carbs, moderate fats.",
        "Give the calories in each meal.",
        "Keep plans teen-safe (no extreme cuts, no supplements).",
    ],
)

work = Agent(
    name="Workout Planner",
    role="Expert fitness planner specializing in safe teen workouts",
    model=Groq(id=os.getenv("GROQ_MODEL", "llama-3.1-70b-instant")),
    tools=[workout],
    instructions=[
        "Always CALL the workout tool using: difficulty, option, time, mood (if provided).",
        "Return a ONE-DAY plan with three sections: Warm-up, Main Workout, Cool-down.",
        "Main Workout must list concrete exercises with sets×reps or minutes + rests.",
        "Cover ONLY styles in `option`: cardio, weight lifting, calisthenics, meditation.",
        "Scale intensity by `difficulty` and fit total time ≈ `time` (warm/cool 5–8 min).",
        "Adjust workout based on mood: energized=higher intensity, tired=gentler approach, stressed=calming focus.",
        "Short bullets; no vague items.",
        "Ensure all exercises are safe for teenagers and include proper form cues.",
    ],
)


posture_agent = Agent(
    name="Posture & Form Coach",
    role="Expert strength coach that analyzes workout photos and gives precise, safe corrections.",
    model=OpenAIModel(id=POSTURE_MODEL_ID),
    instructions=[
        "You are an expert fitness coach analyzing workout form from photos.",
        "You will receive workout photos and analyze the form being demonstrated.",
        "Provide feedback in VALID JSON format ONLY.",
        "",
        "Structure your analysis like this:",
        "1) IDENTIFY the exercise being performed",
        "2) MAJOR ISSUES FIRST (sorted by severity: high, medium, low)",
        "3) RISKS if form continues unchanged",
        "4) SPECIFIC CORRECTIONS with actionable cues and drills",
        "",
        "Return ONLY valid JSON (no markdown, no extra text) in this EXACT schema:",
        "{",
        '  "exercise": "name of exercise identified",',
        '  "overall": "one-sentence summary of form quality",',
        '  "confidence": 0.8,',
        '  "major_issues": [',
        "    {",
        '      "body_part": "specific body part",',
        '      "problem": "what is wrong",',
        '      "severity": "high|medium|low",',
        '      "evidence": "what in the image shows this issue"',
        "    }",
        "  ],",
        '  "risks_if_unchanged": [',
        '    "specific injury risk 1",',
        '    "specific injury risk 2"',
        "  ],",
        '  "corrections": [',
        "    {",
        '      "issue_ref": "body_part/problem reference",',
        '      "fix": "specific instruction to correct",',
        '      "cues": ["coaching cue 1", "coaching cue 2"],',
        '      "drills": ["corrective drill 1", "corrective drill 2"]',
        "    }",
        "  ],",
        '  "needs": ["if confidence < 0.7, what better angle/lighting is needed"]',
        "}",
        "",
        "Guidelines:",
        "- Set confidence < 0.7 if lighting/angle is poor and populate 'needs' array",
        "- Focus on major safety issues first, then performance improvements",
        "- Give specific, actionable corrections with coaching cues",
        "- Be encouraging but safety-focused",
        "- If no clear issues, still provide optimization tips",
    ],
)



def generate_correct_form_image(exercise_name, corrections_data):
    """
    Generate an image showing the correct form for the exercise based on analysis.
    Uses OpenAI's Images API (DALL·E).
    """
    try:
        client = OpenAIClient()
        exercise = corrections_data.get("exercise", exercise_name or "exercise")
        corrections = corrections_data.get("corrections", [])

        prompt_parts = [
            f"A professional fitness demonstration photo showing perfect form for {exercise}.",
            "The person should be in a modern, well-lit gym environment.",
            "Focus on anatomically correct positioning with ideal posture and alignment.",
            "The posture and form should be perfect and not the user's photo.",
            "The person should be demonstrating the exercise with proper technique.",
        ]

        if corrections:
            prompt_parts.append("Key form points to emphasize:")
            for correction in corrections[:3]:
                fix = correction.get("fix", "")
                if fix:
                    prompt_parts.append(f"- {fix}")

        form_guidance = {
            "squat": "straight back, knees tracking over toes, chest up, weight distributed evenly",
            "deadlift": "straight spine, shoulders back, bar close to body, engaged core",
            "push-up": "straight plank position, elbows at ~45 degrees, controlled movement",
            "plank": "straight line from head to heels, engaged core, neutral neck",
            "lunge": "upright torso, front knee over ankle, back leg straight",
        }
        for key, guidance in form_guidance.items():
            if key.lower() in exercise.lower():
                prompt_parts.append(f"Ensure {guidance}.")
                break

        prompt_parts.extend(
            [
                "Professional lighting, clear view of body positioning.",
                "Athletic wear, confident posture, demonstration quality photo.",
                "Side or three-quarter view angle for best form visibility.",
            ]
        )

        full_prompt = " ".join(prompt_parts)

        result = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        return result.data[0].url

    except Exception as e:
        print(f"Error generating image: {e}")
        return None



CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def create_spotify_client():
    """Create and test Spotify client connection"""
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Missing Spotify credentials (.env CLIENT_ID / CLIENT_SECRET)")
        return None
    try:
        mgr = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        sp = spotipy.Spotify(client_credentials_manager=mgr, requests_timeout=10, retries=3)

        _ = sp.categories(limit=1)
        print("✅ Spotify client ready")
        return sp
    except spotipy.exceptions.SpotifyException as e:
        print(f"❌ Spotify API Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating Spotify client: {e}")
        return None


def get_recommendations_via_api(sp, mood="happy", limit=8):
    """Get music recommendations using Spotify's recommendation API"""
    if not sp:
        return []

    mood_genres = {
        "motivational": ["rock", "pop", "hip-hop"],
        "focus": ["classical", "ambient", "electronic"],
        "peaceful": ["acoustic", "chill", "folk"],
        "happy": ["pop", "dance", "indie"],
    }

    mood_attributes = {
        "motivational": {"energy": 0.8, "valence": 0.7, "danceability": 0.6},
        "focus": {"energy": 0.3, "valence": 0.5, "instrumentalness": 0.7},
        "peaceful": {"energy": 0.2, "valence": 0.6, "acousticness": 0.8},
        "happy": {"energy": 0.7, "valence": 0.8, "danceability": 0.7},
    }

    seed_genres = mood_genres.get(mood, ["pop"])
    attributes = mood_attributes.get(mood, {})

    try:
        print(f"🎵 Trying recommendations API with genres: {seed_genres}")
        rec = sp.recommendations(
            seed_genres=seed_genres[:5],
            limit=limit,
            market="US",
            **attributes,
        )
        tracks = rec.get("tracks", [])
        return [
            {
                "name": t.get("name", "Unknown"),
                "artist": t["artists"][0]["name"] if t.get("artists") else "Unknown",
                "url": t.get("external_urls", {}).get("spotify", "#"),
            }
            for t in tracks
        ]
    except Exception as e:
        print(f"❌ Recommendations API failed: {e}")
        return []


MOOD_TO_SEARCH_QUERIES = {
    "motivational": ["workout music", "pump up songs", "motivational hits", "gym music", "energetic rock"],
    "focus": ["focus music", "concentration music", "study music", "ambient focus", "lo-fi beats"],
    "peaceful": ["relaxing music", "calm music", "peaceful songs", "meditation music", "acoustic chill"],
    "happy": ["happy songs", "feel good music", "upbeat music", "pop hits", "dance music"],
}


def get_recommendations_via_search(sp, mood="happy", limit=8):
    """Get music recommendations using Spotify search as fallback"""
    if not sp:
        return []

    queries = MOOD_TO_SEARCH_QUERIES.get(mood, MOOD_TO_SEARCH_QUERIES["happy"])
    results = []

    try:
        for q in queries:
            if len(results) >= limit:
                break
            print(f"🔍 Searching: {q}")
            r = sp.search(q=q, type="track", limit=max(2, limit // len(queries) + 2), market="US")
            for tr in r.get("tracks", {}).get("items", []):
                song = {
                    "name": tr.get("name", "Unknown"),
                    "artist": tr["artists"][0]["name"] if tr.get("artists") else "Unknown",
                    "url": tr.get("external_urls", {}).get("spotify", "#"),
                }

                if not any(s["name"] == song["name"] and s["artist"] == song["artist"] for s in results):
                    results.append(song)
                if len(results) >= limit:
                    break
        print(f"✅ Search returned {len(results)} songs for mood={mood}")
        return results[:limit]
    except Exception as e:
        print(f"❌ Search method failed: {e}")
        return []


def get_recommendations(sp, mood="happy", limit=8):
    """Main entry point for getting music recommendations"""
    print(f"\n🎧 Getting songs for mood: {mood}")

    songs = get_recommendations_via_api(sp, mood, limit)

    if not songs:
        print("🔄 Falling back to search method...")
        songs = get_recommendations_via_search(sp, mood, limit)

    print(f"➡️ Final result: {len(songs)} songs")
    return songs


def debug_spotify_setup():
    """Debug function to test Spotify integration"""
    print("\n" + "=" * 50)
    print("🔧 SPOTIFY DEBUG")
    print("=" * 50)
    print(f"CLIENT_ID set: {bool(CLIENT_ID)}")
    print(f"CLIENT_SECRET set: {bool(CLIENT_SECRET)}")

    sp = create_spotify_client()
    if not sp:
        print("❌ Failed to create client")
        return

    try:
        cats = sp.categories(limit=3)
        print(f"✅ Categories OK: {len(cats['categories']['items'])} found")
    except Exception as e:
        print(f"❌ Categories failed: {e}")

    try:
        rec = sp.recommendations(seed_genres=["pop"], limit=2)
        print(f"✅ Recommendations OK: {len(rec.get('tracks', []))} tracks")
    except Exception as e:
        print(f"❌ Recommendations failed: {e}")

    try:
        sr = sp.search(q="happy", type="track", limit=2)
        print(f"✅ Search OK: {len(sr.get('tracks', {}).get('items', []))} results")
    except Exception as e:
        print(f"❌ Search failed: {e}")

    print("=" * 50)


__all__ = [
    "create_spotify_client",
    "get_recommendations",
    "debug_spotify_setup",
    "work",
    "well",
    "daily",
    "posture_agent",
    "generate_correct_form_image",
    "diet",
]


if __name__ == "__main__":
    debug_spotify_setup()
