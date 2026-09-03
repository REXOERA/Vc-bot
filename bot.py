    import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch1",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Sync error:", e)


@bot.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send("❌ Pehle voice channel join karo.")
        return

    channel = interaction.user.voice.channel

    try:
        voice = interaction.guild.voice_client

        if voice:
            await voice.move_to(channel)
        else:
            await channel.connect()

        await interaction.followup.send(f"✅ Joined **{channel.name}** 🎵")

    except Exception as e:
        await interaction.followup.send(f"❌ Join error: `{e}`")


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    await interaction.response.defer()

    voice = interaction.guild.voice_client

    if voice:
        await voice.disconnect()
        await interaction.followup.send("👋 Voice channel se nikal gaya.")
    else:
        await interaction.followup.send("❌ Main kisi voice channel mein nahi hoon.")


@bot.tree.command(name="play", description="Play a song")
@app_commands.describe(query="Song name or YouTube URL")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send("❌ Pehle voice channel join karo.")
        return

    channel = interaction.user.voice.channel
    voice = interaction.guild.voice_client

    try:
        if voice is None:
            voice = await channel.connect()
        elif voice.channel != channel:
            await voice.move_to(channel)

        loop = asyncio.get_running_loop()

        def get_audio():
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)

                if "entries" in info:
                    info = info["entries"][0]

                return info["url"], info.get("title", "Unknown Song")

        audio_url, title = await loop.run_in_executor(None, get_audio)

        if voice.is_playing():
            voice.stop()

        source = discord.FFmpegPCMAudio(
            audio_url,
            **FFMPEG_OPTIONS
        )

        voice.play(source)

        await interaction.followup.send(f"▶️ Playing **{title}** 🎵")

    except Exception as e:
        print("PLAY ERROR:", repr(e))
        await interaction.followup.send(
            "❌ Song play nahi ho saka. Railway logs me error check karo."
        )


@bot.tree.command(name="stop", description="Stop the current song")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_playing():
        voice.stop()
        await interaction.response.send_message("⏹️ Song stopped.")
    else:
        await interaction.response.send_message("❌ Abhi koi song nahi baj raha.")


bot.run(TOKEN)
