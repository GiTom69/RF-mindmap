import os
import csv
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.discovery import build
import google.generativeai as genai # <-- IMPORT GEMINI
from tqdm import tqdm

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TOPICS_FILE = DATA_DIR / "topics.csv"
URLS_FILE = DATA_DIR / "urls.csv"
PLAYLISTS_FILE = BASE_DIR / "yt-playlists.url"
YOUTUBE_CACHE_FILE = BASE_DIR / "youtube_cache.json"

# --- MAIN SCRIPT LOGIC ---

def load_api_keys():
    """Loads API keys from a .env file into environment variables."""
    load_dotenv()
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") # <-- CHANGED
    
    if not youtube_key or not gemini_key: # <-- CHANGED
        print("Error: API keys not found.")
        print("Please create a .env file with YOUTUBE_API_KEY and GEMINI_API_KEY.") # <-- CHANGED
        exit(1)
        
    return youtube_key, gemini_key # <-- CHANGED

def load_topics(filepath):
    """Loads all topics from the topics.csv file."""
    print(f"Loading topics from {filepath}...")
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_existing_urls(filepath):
    """Loads existing Identifier-URL pairs to prevent duplicates."""
    print(f"Loading existing URLs from {filepath} to prevent duplicates...")
    if not filepath.exists():
        return set()
    
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {(row['Identifier'], row['URL']) for row in reader}

def load_playlists(filepath):
    """Loads the list of YouTube playlist URLs from the specified file."""
    print(f"Loading playlists from {filepath}...")
    with open(filepath, mode='r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_playlist_videos(playlist_url, youtube_api, cache):
    """
    Fetches all video details from a YouTube playlist URL using the API.
    Uses a cache to avoid re-fetching data for the same playlist.
    """
    playlist_id_match = re.search(r'list=([^&]+)', playlist_url)
    if not playlist_id_match:
        print(f"Warning: Could not extract Playlist ID from {playlist_url}. Skipping.")
        return []
    playlist_id = playlist_id_match.group(1)

    if playlist_id in cache:
        print(f"Found playlist {playlist_id} in cache. Using cached data.")
        return cache[playlist_id]

    print(f"Fetching videos from playlist: {playlist_id}...")
    videos = []
    next_page_token = None
    try:
        while True:
            request = youtube_api.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response['items']:
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                videos.append({
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        cache[playlist_id] = videos
        return videos
    except Exception as e:
        print(f"An error occurred fetching playlist {playlist_id}: {e}")
        return []

def is_good_match(topic, video, ai_model):
    """
    Uses the Gemini API to determine if a video is a good match for a topic.
    Returns True for a good match, False otherwise.
    """
    # Gemini uses a simpler, combined prompt structure.
    prompt = (
        "You are an expert AI assistant specializing in technical and scientific topics. "
        "Your task is to determine if a YouTube video is a relevant and high-quality explanation for a given topic. "
        "Base your decision on the titles and descriptions provided. "
        "Respond with ONLY the word 'YES' or 'NO'.\n\n"
        "--- START OF DATA ---\n"
        f"Topic Title: \"{topic['Topic']}\"\n"
        f"Topic Description: \"{topic['Description / Key Concepts']}\"\n\n"
        f"Video Title: \"{video['title']}\"\n"
        f"Video Description: \"{video['description'][:500]}...\"\n" # Truncate long descriptions
        "--- END OF DATA ---\n\n"
        "Based on the information above, does this video provide a good explanation for the given topic? "
        "Consider if the video seems educational and directly related. "
        "Answer with ONLY 'YES' or 'NO'."
    )
    
    try:
        # Generate the content
        response = ai_model.generate_content(prompt)
        answer = response.text.strip().upper()
        return answer == "YES"
    except Exception as e:
        # Gemini can raise errors for safety reasons or other API issues
        print(f"\nAn error occurred with the Gemini API: {e}")
        return False

def append_to_urls_csv(filepath, new_urls):
    """Appends new Identifier-URL pairs to the urls.csv file."""
    print(f"\nAppending {len(new_urls)} new URLs to {filepath}...")
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(['Identifier', 'URL'])
        
        for identifier, url in new_urls:
            writer.writerow([identifier, url])
    print("Done.")

def main():
    """Main function to orchestrate the entire process."""
    print("--- Starting URL Enrichment Script (using Gemini) ---")
    youtube_api_key, gemini_api_key = load_api_keys()

    # --- INITIALIZE API CLIENTS (UPDATED FOR GEMINI) ---
    youtube_api = build('youtube', 'v3', developerKey=youtube_api_key)
    
    # Configure the Gemini client
    genai.configure(api_key=gemini_api_key)
    ai_model = genai.GenerativeModel(
        'gemini-pro',
        # Set safety settings to be less restrictive if needed,
        # though default is usually fine for this task.
        safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE'}
    )
    
    # --- The rest of the script is the same ---
    topics = load_topics(TOPICS_FILE)
    existing_urls = load_existing_urls(URLS_FILE)
    playlist_urls = load_playlists(PLAYLISTS_FILE)
    
    try:
        with open(YOUTUBE_CACHE_FILE, 'r') as f:
            youtube_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        youtube_cache = {}

    all_videos = []
    for url in playlist_urls:
        all_videos.extend(get_playlist_videos(url, youtube_api, youtube_cache))

    with open(YOUTUBE_CACHE_FILE, 'w') as f:
        json.dump(youtube_cache, f, indent=4)
    
    print(f"\nFound a total of {len(all_videos)} videos across {len(playlist_urls)} playlists.")
    print("Now matching videos to topics using Gemini. This may take a while...")

    new_urls_to_add = []
    
    with tqdm(total=len(topics) * len(all_videos), desc="Matching Progress") as pbar:
        for topic in topics:
            for video in all_videos:
                pbar.update(1)
                
                if video['title'].lower() in ['private video', 'deleted video']:
                    continue

                if (topic['Index'], video['url']) in existing_urls:
                    continue
                
                if is_good_match(topic, video, ai_model):
                    print(f"\nMatch found! Topic: '{topic['Topic']}' -> Video: '{video['title']}'")
                    new_url_pair = (topic['Index'], video['url'])
                    new_urls_to_add.append(new_url_pair)
                    existing_urls.add(new_url_pair)

    if new_urls_to_add:
        append_to_urls_csv(URLS_FILE, new_urls_to_add)
    else:
        print("\nNo new URLs to add.")
        
    print("--- Script Finished ---")

if __name__ == "__main__":
    main()