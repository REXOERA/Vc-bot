import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", 
                   intents=intents)



GUILD_ID = 15269660691498312


@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands")
        print(f"Logged in as {bot.user}")
    except Exception as e:
        print("Sync error:", e)


@bot.tree.command(
    name="join",
    description="Join your voice channel",
    guild=discord.Object(id=GUILD_ID)
)
async def join(interaction: discord.Interaction):

    if not interaction.user.voice:
        await interaction.response.send_message(
            "Abe phele voice channel join kr."
        )
        return

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(
        f"Joined **{channel.name}** 🎵"
    )


@bot.tree.command(
    name="leave",
    description="Leave the voice channel",
    guild=discord.Object(id=GUILD_ID)
)
async def leave(interaction: discord.Interaction):

    vc = interaction.guild.voice_client

    if not vc:
        await interaction.response.send_message(
            "Bot voice channel me nahi hai."
        )
        return

    await vc.disconnect()
    await interaction.response.send_message(
        "Voice channel leave kar diya."
    )


@bot.tree.command(
    name="play",
    description="Play a YouTube video",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(url="YouTube video URL")
async def play(interaction: discord.Interaction, url: str):

    vc = interaction.guild.voice_client

    if not vc:
        await interaction.response.send_message(
            "Pehle `/join` use karo."
        )
        return

    await interaction.response.defer()

    if vc.is_playing():
        vc.stop()

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        def get_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await asyncio.to_thread(get_info)

        stream_url = info["url"]
        title = info.get("title", "Unknown")

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }

        source = discord.FFmpegPCMAudio(
            stream_url,
            **ffmpeg_options
        )

        vc.play(source)

        await interaction.followup.send(
            f"▶️ Playing: **{title}**"
        )

    except Exception as e:
        print("Play error:", e)
        await interaction.followup.send(
            "❌ YouTube audio play nahi ho saka."
        )


@bot.tree.command(
    name="stop",
    description="Stop the current song",
    guild=discord.Object(id=GUILD_ID)
)
async def stop(interaction: discord.Interaction):

    vc = interaction.guild.voice_client

    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message(
            "⏹️ Song stopped."
        )
    else:
        await interaction.response.send_message(
            "Abhi koi song nahi baj raha."
        )


token = os.getenv("DISCORD_TOKEN")

if not token:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable missing!"
    )

bot.run(token)
