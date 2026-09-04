import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}


def extract_audio(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "default_search": "ytsearch",
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if "entries" in info:
            info = info["entries"][0]

        return {
            "title": info.get("title", "Unknown"),
            "url": info["url"],
            "webpage": info.get("webpage_url", query),
        }


async def play_next(guild):
    voice = guild.voice_client

    if not voice or not voice.is_connected():
        return

    queue = queues.get(guild.id, [])

    if not queue:
        return

    song = queue.pop(0)

    try:
        data = await asyncio.to_thread(extract_audio, song["query"])

        source = discord.FFmpegPCMAudio(
            data["url"],
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn"
        )

        def after(error):
            if error:
                print("Player error:", error)

            asyncio.run_coroutine_threadsafe(
                play_next(guild),
                bot.loop
            )

        voice.play(source, after=after)

        await guild.system_channel.send(
            f"🎵 **Now Playing:** {data['title']}"
        ) if guild.system_channel else None

    except Exception as e:
        print("Playback error:", e)
        await play_next(guild)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Sync error:", e)

    print(f"Logged in as {bot.user}")


@bot.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ Pehle voice channel join karo."
        )
        return

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(
        f"🔊 Joined **{channel.name}**"
    )


@bot.tree.command(name="play", description="Play a song or URL")
@app_commands.describe(query="Song name, YouTube URL, or SoundCloud URL")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ Pehle voice channel join karo."
        )
        return

    await interaction.response.defer()

    voice = interaction.guild.voice_client

    if not voice:
        voice = await interaction.user.voice.channel.connect()

    queues.setdefault(interaction.guild.id, [])

    queues[interaction.guild.id].append({
        "query": query,
        "user": interaction.user.id
    })

    if voice.is_playing() or voice.is_paused():
        await interaction.followup.send(
            f"✅ Queue me add ho gaya: **{query}**"
        )
    else:
        await interaction.followup.send(
            f"🔎 Searching: **{query}**"
        )
        await play_next(interaction.guild)


@bot.tree.command(name="skip", description="Skip current song")
async def skip(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if not voice or not voice.is_playing():
        await interaction.response.send_message(
            "❌ Abhi koi song nahi baj raha."
        )
        return

    voice.stop()

    await interaction.response.send_message(
        "⏭️ Skipped!"
    )


@bot.tree.command(name="pause", description="Pause the music")
async def pause(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_playing():
        voice.pause()
        await interaction.response.send_message("⏸️ Paused!")
    else:
        await interaction.response.send_message(
            "❌ Koi song nahi baj raha."
        )


@bot.tree.command(name="resume", description="Resume the music")
async def resume(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_paused():
        voice.resume()
        await interaction.response.send_message("▶️ Resumed!")
    else:
        await interaction.response.send_message(
            "❌ Music paused nahi hai."
        )


@bot.tree.command(name="queue", description="Show music queue")
async def queue_command(interaction: discord.Interaction):
    queue = queues.get(interaction.guild.id, [])

    if not queue:
        await interaction.response.send_message(
            "📭 Queue empty hai."
        )
        return

    text = "\n".join(
        f"{i + 1}. {song['query']}"
        for i, song in enumerate(queue)
    )

    await interaction.response.send_message(
        f"📋 **Queue:**\n{text}"
    )


@bot.tree.command(name="stop", description="Stop music and clear queue")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    queues[interaction.guild.id] = []

    if voice:
        voice.stop()

    await interaction.response.send_message(
        "⏹️ Music stopped aur queue clear ho gayi."
    )


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if not voice:
        await interaction.response.send_message(
            "❌ Main voice channel me nahi hoon."
        )
        return

    queues[interaction.guild.id] = []
    await voice.disconnect()

    await interaction.response.send_message(
        "👋 Voice channel se leave kar diya."
    )


bot.run(TOKEN)
