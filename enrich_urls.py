import os
import csv
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.discovery import build
import google.generativeai as genai
from tqdm import tqdm

# --- CONFIGURATION & UNCHANGED FUNCTIONS ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TOPICS_FILE = DATA_DIR / "topics.csv"
URLS_FILE = DATA_DIR / "urls.csv"
PLAYLISTS_FILE = DATA_DIR / "yt-playlists.url"
YOUTUBE_CACHE_FILE = DATA_DIR / "youtube_cache.json"

def load_api_keys():
    load_dotenv()
    youtube_key, gemini_key = os.getenv("YOUTUBE_API_KEY"), os.getenv("GEMINI_API_KEY")
    if not youtube_key or not gemini_key: exit("Error: API keys not found in .env file.")
    return youtube_key, gemini_key

def load_topics(filepath):
    print(f"Loading topics from {filepath}...");
    with open(filepath, mode='r', encoding='utf-8') as f: return list(csv.DictReader(f))

def load_existing_urls(filepath):
    print(f"Loading existing URLs from {filepath} to prevent duplicates...");
    if not filepath.exists(): return set()
    with open(filepath, mode='r', encoding='utf-8') as f: return {(row['Identifier'], row['URL']) for row in csv.DictReader(f)}

def load_playlists(filepath):
    print(f"Loading playlists from {filepath}...");
    with open(filepath, mode='r', encoding='utf-8') as f: return [line.strip() for line in f if line.strip()]

def get_playlist_videos(playlist_url, youtube_api, cache):
    # This function is unchanged
    playlist_id_match = re.search(r'list=([^&]+)', playlist_url)
    if not playlist_id_match: print(f"Warning: Could not extract Playlist ID from {playlist_url}. Skipping."); return []
    playlist_id = playlist_id_match.group(1)
    if playlist_id in cache: print(f"Found playlist {playlist_id} in cache. Using cached data."); return cache[playlist_id]
    print(f"Fetching videos from playlist: {playlist_id}..."); videos = []; next_page_token = None
    try:
        while True:
            request = youtube_api.playlistItems().list(part="snippet", playlistId=playlist_id, maxResults=50, pageToken=next_page_token)
            response = request.execute()
            for item in response['items']:
                snippet = item['snippet']; video_id = snippet['resourceId']['videoId']
                videos.append({'title': snippet['title'], 'description': snippet['description'], 'url': f"https://www.youtube.com/watch?v={video_id}"})
            next_page_token = response.get('nextPageToken')
            if not next_page_token: break
        cache[playlist_id] = videos; return videos
    except Exception as e: print(f"An error occurred fetching playlist {playlist_id}: {e}"); return []

def append_url_to_csv(filepath, identifier, url):
    is_new_file = not filepath.exists() or os.path.getsize(filepath) == 0
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if is_new_file: writer.writerow(['Identifier', 'URL'])
        writer.writerow([identifier, url])

def main():
    print("--- Starting Final Optimized URL Enrichment Script ---")
    youtube_api_key, gemini_api_key = load_api_keys()

    # --- Step 1: Load all data into memory ---
    topics = load_topics(TOPICS_FILE)
    existing_urls = load_existing_urls(URLS_FILE)
    playlist_urls = load_playlists(PLAYLISTS_FILE)
    
    try:
        with open(YOUTUBE_CACHE_FILE, 'r') as f: youtube_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error: Cache file not found at {YOUTUBE_CACHE_FILE}. Please run once to generate.")
        return

    all_videos = []
    for playlist_id, videos in youtube_cache.items():
        all_videos.extend(videos)
    print(f"\nLoaded {len(all_videos)} total videos from cache.")

    # --- Step 2: Prepare video context and lookup map ---
    video_map = {}
    video_entries_for_prompt = []
    for i, video in enumerate(all_videos):
        video_id = f"V{i:04d}"
        video_map[video_id] = video
        title = video['title']
        desc = video['description'][:250].replace("\n", " ")
        video_entries_for_prompt.append(f"[{video_id}] Title: \"{title}\" | Desc: \"{desc}...\"")
    
    video_context_block = "\n".join(video_entries_for_prompt)

    # --- Step 3: Initialize the AI model ---
    genai.configure(api_key=gemini_api_key)
    ai_model = genai.GenerativeModel('models/gemini-flash-latest')
    
    print("AI model initialized. Starting topic matching...")
    print("NOTE: A ~16 second delay between topics is required to stay within the free tier token limit.")

    # --- Step 4: Loop through topics and get matches via ONE-SHOT requests ---
    with tqdm(total=len(topics), desc="Matching Topics") as pbar:
        for topic in topics:
            pbar.update(1)

            if any(topic['Index'] == identifier for identifier, url in existing_urls):
                continue
            
            # --- CONSTRUCT THE FULL, SELF-CONTAINED PROMPT FOR EACH REQUEST ---
            full_prompt = (
                "You are an AI matching engine. Your task is to find the single best video from the provided list that explains the given topic. "
                "Respond with ONLY the video's unique ID (e.g., '[Vxxxx]') and nothing else. "
                "If no video is a good match, respond with ONLY the word 'NONE'.\n\n"
                "--- AVAILABLE VIDEOS ---\n"
                f"{video_context_block}\n"
                "--- END OF VIDEO LIST ---\n\n"
                f"Topic Title: \"{topic['Topic']}\"\n"
                f"Topic Description: \"{topic['Description / Key Concepts']}\"\n\n"
                "Based on the topic above, which is the best video from the list? Respond with ONLY its ID."
            )
            
            try:
                response = ai_model.generate_content(full_prompt)
                match = re.search(r'\[(V\d{4})\]', response.text)
                
                if match:
                    matched_video_id = match.group(1)
                    matched_video = video_map.get(matched_video_id)
                    
                    if matched_video:
                        print(f"\nMatch found! Topic: '{topic['Topic']}' -> Video: '{matched_video['title']}'")
                        append_url_to_csv(URLS_FILE, topic['Index'], matched_video['url'])
                        existing_urls.add((topic['Index'], matched_video['url']))
                
            except Exception as e:
                print(f"\nAn error occurred processing topic '{topic['Topic']}': {e}")
            
            # --- FINAL, CORRECT DELAY ---
            # Respects the 250k token/minute limit (4 requests/minute).
            time.sleep(16)
        
    print("\n--- Script Finished ---")


if __name__ == "__main__":
    main()