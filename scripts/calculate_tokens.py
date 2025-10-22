import json
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
YOUTUBE_CACHE_FILE = DATA_DIR / "youtube_cache.json"
MODEL_CONTEXT_LIMIT = 1048576 # From the documentation for gemini-flash-latest

def estimate_tokens(text):
    """Estimates the number of tokens using the 4 chars/token rule of thumb."""
    return len(text) / 4

def main():
    print("--- Calculating Estimated Token Count for Context Priming ---")
    
    # Load the cached video data
    try:
        with open(YOUTUBE_CACHE_FILE, 'r', encoding='utf-8') as f:
            youtube_cache = json.load(f)
    except FileNotFoundError:
        print(f"Error: Cache file not found at {YOUTUBE_CACHE_FILE}")
        print("Please run the enrich_urls.py script at least once to generate the cache.")
        return

    # Flatten the list of videos from all playlists in the cache
    all_videos = []
    for playlist_id, videos in youtube_cache.items():
        all_videos.extend(videos)

    print(f"Found a total of {len(all_videos)} videos in the cache.")

    # --- Build the giant system prompt string ---
    system_prompt_header = (
        "You are an AI matching engine. The user will provide a Topic. "
        "You must find the best matching video from the following list of available videos. "
        "Respond with ONLY the video's unique ID number.\n\n"
        "AVAILABLE VIDEOS:\n"
    )

    video_entries = []
    for i, video in enumerate(all_videos):
        # Create a compressed representation for each video
        # We truncate the description to save space, as the start is most important
        title = video['title']
        desc = video['description'][:250] # Limit description to first 250 chars
        entry = f"[ID: V{i:04d}] Title: \"{title}\" | Desc: \"{desc}...\""
        video_entries.append(entry)

    # Combine everything into the final prompt text
    full_prompt_text = system_prompt_header + "\n".join(video_entries)
    
    # --- Calculate and report the results ---
    estimated_total_tokens = estimate_tokens(full_prompt_text)

    print(f"\nTotal characters in the prompt: {len(full_prompt_text):,}")
    print(f"Estimated total tokens: {int(estimated_total_tokens):,}")
    print(f"Model context limit: {MODEL_CONTEXT_LIMIT:,}")

    if estimated_total_tokens < MODEL_CONTEXT_LIMIT:
        print("\nSUCCESS: Your dataset will very likely fit into the model's context window!")
    else:
        print("\nWARNING: Your dataset may be too large for the model's context window.")

if __name__ == "__main__":
    main()