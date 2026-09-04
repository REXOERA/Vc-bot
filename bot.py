import os
import discord
from discord import app_commands
from discord.ext import commands
import wavelink

TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}
now_playing = {}


def get_queue(guild_id):
    return queues.setdefault(guild_id, [])


async def search_track(query):
    # URL
    if query.startswith(("http://", "https://")):
        results = await wavelink.Playable.search(query)
        if results:
            return results[0]

    # YouTube
    try:
        results = await wavelink.Playable.search(f"ytsearch:{query}")
        if results:
            return results[0]
    except Exception as e:
        print("YouTube search error:", repr(e))

    # SoundCloud
    try:
        results = await wavelink.Playable.search(f"scsearch:{query}")
        if results:
            return results[0]
    except Exception as e:
        print("SoundCloud search error:", repr(e))

    raise Exception("Song nahi mila.")


async def play_next(guild):
    guild_id = guild.id
    player = guild.voice_client
    queue = get_queue(guild_id)

    if not isinstance(player, wavelink.Player):
        return

    if player.playing:
        return

    if not queue:
        now_playing.pop(guild_id, None)
        return

    track, requester = queue.pop(0)

    try:
        now_playing[guild_id] = {
            "track": track,
            "requester": requester
        }

        await player.play(track)

        try:
            await requester.channel.send(
                f"▶️ **Now Playing:** {track.title}\n"
                f"👤 Requested by {requester.mention}"
            )
        except Exception:
            pass

    except Exception as e:
        print("Play error:", repr(e))
        now_playing.pop(guild_id, None)
        await play_next(guild)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    try:
        if not wavelink.Pool.nodes:
            node = wavelink.Node(
                identifier="MAIN",
                uri=LAVALINK_URI,
                password=LAVALINK_PASSWORD
            )

            await wavelink.Pool.connect(
                nodes=[node],
                client=bot
            )

            print("✅ Lavalink connected")

    except Exception as e:
        print("❌ Lavalink error:", repr(e))

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print("❌ Command sync error:", repr(e))


@bot.event
async def on_wavelink_node_ready(payload):
    print(f"🎵 Lavalink ready: {payload.node.identifier}")


@bot.event
async def on_wavelink_track_end(payload):
    if payload.player.guild:
        await play_next(payload.player.guild)


@bot.tree.command(
    name="join",
    description="Join your voice
