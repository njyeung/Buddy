from importlib import util
import json
import os
import platform
import subprocess
from time import sleep

import psutil
from uprint import uprint, OutGoingDataType
from config import OS_NAME
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv, find_dotenv
import ctypes
from pathlib import Path

from tool_decorator import tool

STORAGE_PATH = Path(__file__).resolve().parent / "storage"
STORAGE_PATH.mkdir(exist_ok=True)

SPOTIFY_JSON = STORAGE_PATH / "spotify.json"

sp = None # Initialized during spotify_launch

dotenv_path = find_dotenv()

if dotenv_path:
    load_dotenv(dotenv_path)
else:
    dotenv_path = ".env"
    open(dotenv_path, "a").close()

def get_spotify_credentials():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    if not client_id:
        client_id = uprint("Enter your Spotify Client ID: ", OutGoingDataType.PROMPT, "SPOTIFY_CLIENT")

    if not client_secret:
        client_secret = uprint("Enter your Spotify Client Secret: ", OutGoingDataType.PROMPT, "SPOTIFY_CLIENT_SECRET")

    return client_id, client_secret

def open_spotify_app():
    try:
        
        if OS_NAME == "Darwin":  # macOS
            subprocess.run(["open", "-a", "Spotify"], check=True)
        elif OS_NAME == "Windows":
            possible_paths = [
                os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Spotify\Spotify.exe"),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    
                    # wake up api using keyboard shotcuts
                    sleep(1)
                    ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0) # Play
                    ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
                    sleep(0.2)
                    ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0) # Then Pause
                    ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0) 

                    return "Spotify launched successfully."
            return "Spotify executable not found. Please ensure it's installed."
        elif OS_NAME == "Linux":
            try:
                subprocess.Popen(["spotify"])
            except FileNotFoundError:
                try:
                    subprocess.Popen(["flatpak", "run", "com.spotify.Client"])
                except FileNotFoundError:
                    return "Spotify not found. Try installing with Snap or Flatpak."
        else:
            return f"Unsupported operating system: {OS_NAME}"

        return "Spotify launched successfully."
    except Exception as e:
        return f"Failed to launch Spotify: {str(e)}"

def spotify_get_playlist_tracks(playlist_id):
    spotify_launch()

    results = sp.playlist_tracks(playlist_id)
    tracks = []

    for item in results["items"]:
        track = item["track"]
        images = track["album"].get("images", [])
        image_url = images[0]["url"] if images else None

        tracks.append({
            "date-added": item["added_at"],
            "name": track["name"],
            "artists": [a["name"] for a in track["artists"]],
            "uri": track["uri"],
            "album-id": track["album"]["id"],
            "album-name": track["album"]["name"],
            "image_url": image_url,
            "explicit": track["explicit"],
            "popularity": track["popularity"]
        })
    
    return tracks

def save_all_playlists_to_json():
    playlists_data = []
    
    for playlist in spotify_get_playlists():
        tracks = spotify_get_playlist_tracks(playlist["id"])
        print(playlist)
        playlists_data.append({
            "name": playlist["name"],
            "description": playlist["description"],
            "tracks": tracks
        })

    with open(SPOTIFY_JSON, "w", encoding="utf-8") as f:
        json.dump(playlists_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(playlists_data)} playlists to {SPOTIFY_JSON}")

# Tool Definitions

# Returns None if successful, otherwise returns message to be forwarded.
@tool("Launches the Spotify desktop app. Must be installed the machine.")
def spotify_launch():
    global sp
    
    client_id, client_secret = get_spotify_credentials()

    if client_id == None or client_secret == None:
        return "client_id or client_secret missing from .env file. A window has opened up in the frontend prompting the user for their credentials."

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="user-modify-playback-state playlist-modify-public playlist-modify-private user-library-read user-read-playback-state"
    ))

    # Is spotify running?
    spotify_running = any("spotify" in p.name().lower() for p in psutil.process_iter())
    if not spotify_running:
        open_spotify_app()
    
    return None

@tool("Returns the list of tracks in a given album uri")
def spotify_get_album_tracks(uri: str):
    if (result := spotify_launch()): return result

    try:
        album_id = uri.split(":")[-1]
        songs = sp.album_tracks(album_id)
        tracks = []

        for item in songs.get("items", []):
            tracks.append({
                "name": item["name"],
                "track_number": item["track_number"],
                "duration_ms": item["duration_ms"],
                "explicit": item["explicit"],
                "uri": item["uri"],
                "artists": [a["name"] for a in item["artists"]]
            })

        return tracks

    except spotipy.SpotifyException as e:
        return f"Failed to get album tracks: {str(e)}"

@tool("Returns the user's Spotify playlists.")
def spotify_get_playlists(limit:int=10):
    if (result := spotify_launch()): return result

    playlists = sp.current_user_playlists(limit=limit)["items"]
    return [
        {"name": pl["name"], "id": pl["id"], "description": pl["description"], "uri": pl["uri"]}
        for pl in playlists
    ]

@tool("Toggles Spotify playback: pauses if playing, plays if paused (launches spotify automatically if it isn't already open)")
def spotify_toggle_play_pause():
    if (result := spotify_launch()): return result

    playback = sp.current_playback()

    if not playback or playback.get("item") is None:
        return "Nothing is currently playing."

    item = playback["item"]
    song_name = item["name"]
    artists = ", ".join(artist["name"] for artist in item["artists"])

    if not playback or not playback.get("is_playing"):
        sp.start_playback()
        return f"Now playing: {song_name} by {artists}"
    else:
        sp.pause_playback()
        return f"Paused: {song_name} by {artists}"

@tool("Returns the user's currently playing Spotify song (launches spotify automatically if it isn't already open)")
def spotify_get_current_song():
    if (result := spotify_launch()): return result

    playback = sp.current_playback()
    if not playback or playback.get("item") is None:
        return "Nothing is currently playing."

    item = playback["item"]
    name = item["name"]
    artists = ", ".join(artist["name"] for artist in item["artists"])
    album = item["album"]["name"]
    image_url = item["album"]["images"][0]["url"] if item["album"]["images"] else None
    uri = item["uri"]

    return {
        "name": name,
        "artists": artists,
        "album": album,
        "image_url": image_url,
        "uri": uri,
        "explicit": item.get("explicit", False),
        "popularity": item.get("popularity", 0),
        "is_playing": playback.get("is_playing", False),
        "progress_ms": playback.get("progress_ms", 0),
        "duration_ms": item.get("duration_ms", 0)
    }

@tool("Adds one or more Spotify track URIs to a playlist (launches Spotify automatically if it isn't already open).")
def spotify_add_to_playlist(playlist_id: str, track_uri: str):
    if (result := spotify_launch()): return result

    if not track_uri:
        return "No track URIs provided."

    try:
        result = sp.playlist_add_items(playlist_id, [track_uri])
        return {
            "status": "success",
            "snapshot_id": result.get("snapshot_id"),
            "message": f"Added {track_uri} to playlist {playlist_id}."
        }
    except spotipy.SpotifyException as e:
        return {
            "status": "error",
            "message": f"Failed to add tracks to playlist: {str(e)}"
        }

@tool("Plays a spotify song, album, or playlist by its uri (launches spotify automatically if it isn't already open)")
def spotify_play_uri(uri: str):
    if (result := spotify_launch()): return result

    try:
        if uri.startswith("spotify:track:") or uri.startswith("spotify:episode:"):
            sp.start_playback(uris=[uri])
        elif uri.startswith("spotify:album:") or uri.startswith("spotify:playlist:"):
            sp.start_playback(context_uri=uri)
        else:
            return f"Unsupported URI type: {uri}"

        return f"Now playing: {uri}"

    except spotipy.SpotifyException as e:
        return f"Failed to play content: {str(e)}"

def spotify_get_new_releases():
    sp.search()

@tool("Gets user's library of favorite albums (launches spotify automatically if it isn't already open)")
def spotify_get_user_saved_albums(limit:int=10):
    if (result := spotify_launch()): return result

    try:
        results = sp.current_user_saved_albums(limit=limit)
        albums = []

        for item in results.get("items", []):
            album = item["album"]
            albums.append({
                "name": album["name"],
                "artists": [artist["name"] for artist in album["artists"]],
                "release_date": album["release_date"],
                "total_tracks": album["total_tracks"],
                "uri": album["uri"],
                "image_url": album["images"][0]["url"] if album["images"] else None
            })

        return albums

    except spotipy.SpotifyException as e:
        return f"Failed to fetch saved albums: {str(e)}"

@tool("Search on spotify, returns top results from tracks and albums (launches spotify automatically if it isn't already open)")
def spotify_search(query:str, limit:int=5):
    if (result := spotify_launch()): return result

    try:
        results = sp.search(q=query, type="track,album", limit=limit)
        
        def extract_image(images):
            return images[0]["url"] if images else None

        tracks = [
            {
                "type": "track",
                "name": item["name"],
                "artists": [a["name"] for a in item["artists"]],
                "album": item["album"]["name"],
                "uri": item["uri"],
                "image_url": extract_image(item["album"]["images"]),
                "popularity": item["popularity"]
            }
            for item in results.get("tracks", {}).get("items", [])
        ]

        albums = [
            {
                "type": "album",
                "name": item["name"],
                "artists": [a["name"] for a in item["artists"]],
                "release_date": item["release_date"],
                "uri": item["uri"],
                "image_url": extract_image(item["images"]),
                "total_tracks": item["total_tracks"]
            }
            for item in results.get("albums", {}).get("items", [])
        ]

        return {
            "tracks": tracks,
            "albums": albums,
        }
    
    except spotipy.SpotifyException as e:
        return f"Search failed: {str(e)}"


@tool("Queues a spotify song, album, or playlist by its uri (launches spotify automatically if it isn't already open)")
def spotify_add_queue(uri):
    if (result := spotify_launch()): return result

    try:
        if uri.startswith("spotify:track") or uri.startswith("spotify:episode:"):
            sp.add_to_queue(uri)
            return f"Queued 1 item: {uri}"
        elif uri.startswith("spotify:album:"):
            album_id = uri.split(":")[-1]
            album = sp.album(album_id)
            tracks = album["tracks"]["items"]
        elif uri.startswith("spotify:playlist:"):
            playlist_id = uri.split(":")[-1]
            playlist = sp.playlist_tracks(playlist_id)
            tracks = [item["track"] for item in playlist["items"] if item["track"]]
        else:
            return f"Unsupported context type for queueing: {uri}"

        queued = 0
        for track in tracks:
            try:
                sp.add_to_queue(track["uri"])
                queued += 1
            except spotipy.SpotifyException:
                pass

        return f"Queued {queued} tracks from {uri}"
    except spotipy.SpotifyException as e:
        return f"Failed to queue context: {str(e)}"
