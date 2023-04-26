import os
from pathlib import Path
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
from colorama import Fore, Back, Style
from rich import pretty, print
from math import floor

import yaml

pretty.install()


with open("config.yml") as config_file:
    config = yaml.load(config_file, Loader=yaml.FullLoader)

    # Read spotipy config
    spotipy_cfg = config["spotipy"]
    os.environ["SPOTIPY_CLIENT_ID"] = Path(spotipy_cfg["client_id_file"]).read_text()
    os.environ["SPOTIPY_CLIENT_SECRET"] = Path(
        spotipy_cfg["client_secret_file"]
    ).read_text()
    os.environ["SPOTIPY_REDIRECT_URI"] = spotipy_cfg["redirect_uri"]
    spotipy_scope = spotipy_cfg["scope"]

    # Read openai config
    openai_cfg = config["openai"]
    openai.api_key = Path(openai_cfg["api_key_file"]).read_text()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=spotipy_scope))

specialization = input("What should the DJ specialize in? ")
system_message = f"You are a DJ who {'specializes in ' + specialization if specialization else ''}outputs a list of songs based on a given input, with no explanation whatsoever and in bullet point format, and sticks to strictly real song names, trying to avoid repeat songs, and doesn't comment on any of selections."

DEFAULT_PLAYLIST_NAME = f"DJ Playlist {str(random.randint(0, 99999))}"
playlist_name = input("What should the playlist name be? ")
if not playlist_name:
    playlist_name = DEFAULT_PLAYLIST_NAME

DEFAULT_PLAYLIST_DESCRIPTION = "A playlist generated by a DJ AI."
playlist_description = input("What should the playlist description be? ")
if not playlist_description:
    playlist_description = DEFAULT_PLAYLIST_DESCRIPTION

playlist = sp.user_playlist_create(
    sp.me()["id"],
    playlist_name,
    public=False,
    collaborative=False,
    description=playlist_description,
)


context = []
tokens = 0


def parseSongs(songString):
    songs = [song.strip().removeprefix("-").strip() for song in songString.split("\n")]
    return songs


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
        if not song:
            continue
        search_result = sp.search(song, limit=1, type="track")
        for track in search_result["tracks"]["items"]:
            duration = round(track["duration_ms"] / 1000)
            print(f"Searched for: [bold]{song}[/bold]")
            print(
                f"[bold green]{track['name']}[/bold green] by [bold]{track['artists'][0]['name']}[/bold] ({floor(duration/60)}:{duration%60}) at {track['external_urls']['spotify']}"
            )
            print(f"Preview: {track['preview_url']}")
            print()
        user_add_playlist = input("Add to playlist? (Y/n): ")
        if user_add_playlist not in ["n", "N", "no", "No", "NO"]:
            sp.playlist_add_items(playlist["id"], [track["id"]])
            print(f"Added to playlist.\n")

if sp.playlist(playlist["id"])["tracks"]["total"] == 0:
    sp.user_playlist_unfollow(sp.me()["id"], playlist["id"])
    print(f"[bold red]Playlist was empty, so it was deleted.[/bold red]")


print(f"[red]Cost: {tokens/5000} cents (with gpt-3.5-turbo)[/red]")
