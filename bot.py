import os
import discord
from discord import app_commands
from discord.ext import commands
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=1526966069149831229)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Sync error:", e)

@bot.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Pehle voice channel join karo.")
        return

    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(f"Joined **{channel.name}**.")

@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message("Main kisi voice channel me nahi hoon.")
        return
    await vc.disconnect()
    await interaction.response.send_message("Voice channel se leave kar diya.")

@bot.tree.command(name="play", description="Play an audio URL")
@app_commands.describe(url="Direct audio URL (mp3/ogg/etc.)")
async def play(interaction: discord.Interaction, url: str):
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message("Pehle `/join` karo.")
        return

    if vc.is_playing():
        vc.stop()

    try:
        source = await discord.FFmpegOpusAudio.from_probe(url)
        vc.play(source)
        await interaction.response.send_message("▶️ Audio play ho raha hai.")
    except Exception as e:
        await interaction.response.send_message(
            "Audio play nahi ho saka. `/play` me direct audio URL (mp3/ogg) dena zaroori hai."
        )
        print("Play error:", e)

@bot.tree.command(name="stop", description="Stop the current audio")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏹️ Audio stopped.")
    else:
        await interaction.response.send_message("Abhi kuch play nahi ho raha.")

token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN environment variable missing.")

bot.run(token)
