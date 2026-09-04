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
starting = set()


def get_queue(guild_id):
    return queues.setdefault(guild_id, [])


async def search_track(query):
    # Direct YouTube / SoundCloud / Spotify URL
    if query.startswith(("http://", "https://")):
        results = await wavelink.Playable.search(query)

        if results:
            return results[0]

        raise Exception("Song nahi mila.")

    # YouTube search
    try:
        results = await wavelink.Playable.search(
            f"ytsearch:{query}"
        )

        if results:
            return results[0]

    except Exception as e:
        print("YouTube error:", repr(e))

    # SoundCloud fallback
    try:
        results = await wavelink.Playable.search(
            f"scsearch:{query}"
        )

        if results:
            return results[0]

    except Exception as e:
        print("SoundCloud error:", repr(e))

    raise Exception("YouTube aur SoundCloud dono par song nahi mila.")


async def play_next(guild):
    guild_id = guild.id

    if guild_id in starting:
        return

    player = guild.voice_client
    queue = get_queue(guild_id)

    if not isinstance(player, wavelink.Player):
        return

    if not queue:
        now_playing.pop(guild_id, None)
        return

    starting.add(guild_id)

    try:
        track, requester = queue.pop(0)

        now_playing[guild_id] = {
            "track": track,
            "requester": requester
        }

        await player.play(track)

        channel = guild.system_channel

        if channel:
            try:
                await channel.send(
                    f"▶️ Now playing **{track.title}** 🎵\n"
                    f"👤 Requested by {requester.mention}"
                )
            except Exception:
                pass

    except Exception as e:
        print("PLAY NEXT ERROR:", repr(e))

        now_playing.pop(guild_id, None)

        if queue:
            await play_next(guild)

    finally:
        starting.discard(guild_id)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

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

            print("✅ Lavalink connected.")

    except Exception as e:
        print("❌ Lavalink error:", repr(e))

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")

    except Exception as e:
        print("Sync error:", repr(e))


@bot.event
async def on_wavelink_node_ready(
    payload: wavelink.NodeReadyEventPayload
):
    print(f"🎵 Lavalink ready: {payload.node.identifier}")


@bot.event
async def on_wavelink_track_end(
    payload: wavelink.TrackEndEventPayload
):
    if payload.player.guild:
        await play_next(payload.player.guild)


@bot.tree.command(
    name="join",
    description="Join your voice channel"
)
async def join(interaction: discord.Interaction):

    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send(
            "❌ Pehle voice channel join karo."
        )
        return

    channel = interaction.user.voice.channel

    try:
        player = interaction.guild.voice_client

        if isinstance(player, wavelink.Player):

            if player.channel != channel:
                await player.move_to(channel)

        else:
            await channel.connect(cls=wavelink.Player)

        await interaction.followup.send(
            f"✅ Joined **{channel.name}** 🎵"
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Join error: `{e}`"
        )


@bot.tree.command(
    name="leave",
    description="Leave the voice channel"
)
async def leave(interaction: discord.Interaction):

    await interaction.response.defer()

    guild_id = interaction.guild.id
    player = interaction.guild.voice_client

    queues.pop(guild_id, None)
    now_playing.pop(guild_id, None)

    if isinstance(player, wavelink.Player):

        await player.disconnect()

        await interaction.followup.send(
    "👋 Voice channel se nikal gaya."
        )
       
