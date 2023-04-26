import os
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
from colorama import Fore, Back, Style
from rich import pretty, print
from math import floor

pretty.install()

with open(".secrets/SPOTIPY_CLIENT_ID") as f:
    os.environ["SPOTIPY_CLIENT_ID"] = f.read().strip()

with open(".secrets/SPOTIPY_CLIENT_SECRET") as f:
    os.environ["SPOTIPY_CLIENT_SECRET"] = f.read().strip()

with open(".secrets/SPOTIPY_REDIRECT_URI") as f:
    os.environ["SPOTIPY_REDIRECT_URI"] = f.read().strip()

with open(".secrets/OPENAI_API_KEY") as f:
    openai.api_key = f.read().strip()

scope = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private playlist-read-collaborative"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


specialization = input("What should the DJ specialize in? ")
system_message = f"""
You are a DJ who {'specializes in ' + specialization if specialization else ''}outputs a list of songs based on a given input, in bullet point format, and sticks to strictly real song names, trying to avoid repeat songs. 
You will NEVER explain your selections, comment on them, or chat with the user.  
All songs will be in the format: - \"song name\" by \"artist name\"
"""

DEFAULT_PLAYLIST_NAME = f"DJ Playlist {str(random.randint(0, 99999))}"
playlist_name = input("What should the playlist name be? ")
if not playlist_name: playlist_name = DEFAULT_PLAYLIST_NAME

DEFAULT_PLAYLIST_DESCRIPTION = "A playlist generated by a DJ AI."
playlist_description = input("What should the playlist description be? ")
if not playlist_description: playlist_description = DEFAULT_PLAYLIST_DESCRIPTION

playlist = sp.user_playlist_create(sp.me()["id"], playlist_name, public=False, collaborative=False, description=playlist_description)

autofill = input("Autofill playlist? (y/N): ")
autofill = True if autofill in ["y", "Y", "yes", "Yes", "YES"] else False

context = []
tokens = 0

def parseSongs(songString):
    songs = [song.strip().removeprefix("-").strip() for song in songString.split("\n") if song.strip().startswith("-")]
    return songs


if autofill:
    while True:
        user_input = input("How many songs should be generated? ")
        if user_input in ["quit", "exit", "stop", "bye", "goodbye", "done", ""]:
            break
        if user_input.isdigit():
            num_songs = int(user_input)
        counter = 0
        if num_songs > 0:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": system_message}, {"role": "user", "content": f"Generate {num_songs} songs."}] 
                )
                tokens += response["usage"]["total_tokens"]
                bot_response = response["choices"][0]["message"]["content"]
                parsed_bot_response = parseSongs(bot_response)
                for index, song in enumerate(parsed_bot_response):
                    if not song.strip():
                        continue
                    search_result = sp.search(song, limit=1, type="track")
                    
                    if search_result["tracks"]["items"]:
                        track = search_result["tracks"]["items"][0]
                        duration = round(track['duration_ms']/1000)
                        print(f"{index + 1}: ")
                        print(f"Searched for: [bold]{song}[/bold]")
                        print(f"[bold green]{track['name']}[/bold green] by [bold]{track['artists'][0]['name']}[/bold] ({floor(duration/60)}:{duration%60}) at {track['external_urls']['spotify']}")
                        print(f"Preview: {track['preview_url']}")
                        print()
                        counter += 1
                        sp.playlist_add_items(playlist["id"], [track["id"]])
                    else:
                        print(f"Could not find song: [bold]{song}[/bold]")
                print(f"Added {counter}/{num_songs} songs to playlist.\n")
                
else:
    while True:
        user_input = input("Prompt: ")
        if user_input in ["quit", "exit", "stop", "bye", "goodbye", "done", ""]:
            break
        context.append({"role": "user", "content": user_input})
        context_used = context[-5:] if len(context) > 5 else context
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system_message}] + context_used,
        )
        bot_response = response["choices"][0]["message"]["content"]
        context.append({"role": "assistant", "content": bot_response})
        tokens += response["usage"]["total_tokens"]
        parsed_bot_response = parseSongs(bot_response)
        # print(f"\n\n{parsed_bot_response}\n")

        for song in parsed_bot_response:
            if not song.strip():
                continue
            search_result = sp.search(song, limit=3, type="track")
            print(f"Searched for: [bold]{song}[/bold]")
            for index, track in enumerate(search_result["tracks"]["items"]):
                duration = round(track['duration_ms']/1000)
                print("Option " + str(index + 1) + ": ")
                print(f"[bold green]{track['name']}[/bold green] by [bold]{track['artists'][0]['name']}[/bold] ({floor(duration/60)}:{duration%60}) at {track['external_urls']['spotify']}")
                print(f"Preview: {track['preview_url']}")
                print()
            user_add_playlist = input("Add to playlist? (1/2/3/n): ")
            if user_add_playlist not in ["n", "N", "no", "No", "NO", ""] and user_add_playlist.isdigit() and int(user_add_playlist) <= len(search_result["tracks"]["items"]):
                track = search_result["tracks"]["items"][int(user_add_playlist) - 1]
                sp.playlist_add_items(playlist["id"], [track["id"]])
                print(f"Added option {int(user_add_playlist)} to playlist.\n")

    if sp.playlist(playlist["id"])["tracks"]["total"] == 0:
        sp.user_playlist_unfollow(sp.me()["id"], playlist["id"])
        print(f"[bold red]Playlist was empty, so it was deleted.[/bold red]")
        

print(f"[red]Cost: {tokens/5000} cents (with gpt-3.5-turbo)[/red]")


