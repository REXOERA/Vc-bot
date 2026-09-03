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

# SoundCloud / yt-dlp settings
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
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


# =========================
# JOIN
# =========================

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
        voice = interaction.guild.voice_client

        if voice:
            await voice.move_to(channel)
        else:
            await channel.connect()

        await interaction.followup.send(
            f"✅ Joined **{channel.name}** 🎵"
        )

    except Exception as e:
        print("JOIN ERROR:", repr(e))

        await interaction.followup.send(
            f"❌ Join error: `{e}`"
        )


# =========================
# LEAVE
# =========================

@bot.tree.command(
    name="leave",
    description="Leave the voice channel"
)
async def leave(interaction: discord.Interaction):

    await interaction.response.defer()

    voice = interaction.guild.voice_client

    if voice:
        await voice.disconnect()

        await interaction.followup.send(
            "👋 Voice channel se nikal gaya."
        )
    else:
        await interaction.followup.send(
            "❌ Main kisi voice channel mein nahi hoon."
        )


# =========================
# PLAY
# =========================

@bot.tree.command(
    name="play",
    description="Play a SoundCloud song"
)
@app_commands.describe(
    query="Song name or SoundCloud URL"
)
async def play(
    interaction: discord.Interaction,
    query: str
):

    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send(
            "❌ Pehle voice channel join karo."
        )
        return

    channel = interaction.user.voice.channel

    try:

        # Connect / move bot
        voice = interaction.guild.voice_client

        if voice is None:
            voice = await channel.connect()

        elif voice.channel != channel:
            await voice.move_to(channel)

        loop = asyncio.get_running_loop()

        # Get SoundCloud audio
        def get_audio():

            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:

                # If URL is provided
                if query.startswith(
                    ("http://", "https://")
                ):
                    search_query = query

                # Otherwise search SoundCloud
                else:
                    search_query = "scsearch1:" + query

                info = ydl.extract_info(
                    search_query,
                    download=False
                )

                if "entries" in info:
                    entries = info["entries"]

                    if not entries:
                        raise Exception(
                            "Song nahi mila."
                        )

                    info = entries[0]

                return (
                    info["url"],
                    info.get(
                        "title",
                        "Unknown Song"
                    )
                )

        audio_url, title = await loop.run_in_executor(
            None,
            get_audio
        )

        # Stop previous song
        if voice.is_playing():
            voice.stop()

        # Create audio source
        source = discord.FFmpegPCMAudio(
            audio_url,
            **FFMPEG_OPTIONS
        )

        # Play
        voice.play(source)

        await interaction.followup.send(
            f"▶️ Playing **{title}** 🎵\n"
            f"🔊 Source: SoundCloud"
        )

    except Exception as e:

        print("PLAY ERROR:", repr(e))

        await interaction.followup.send(
            "❌ Song play nahi ho saka.\n"
            f"Error: `{e}`"
        )


# =========================
# STOP
# =========================

@bot.tree.command(
    name="stop",
    description="Stop the current song"
)
async def stop(interaction: discord.Interaction):

    voice = interaction.guild.voice_client

    if voice and voice.is_playing():

        voice.stop()

        await interaction.response.send_message(
            "⏹️ Song stopped."
        )

    else:

        await interaction.response.send_message(
            "❌ Abhi koi song nahi baj raha."
        )


# =========================
# START BOT
# =========================

if not TOKEN:
    print("❌ DISCORD_TOKEN variable nahi mila!")
else:
    bot.run(TOKEN)
