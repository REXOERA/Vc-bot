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
    "default_search": "ytsearch",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# guild_id -> list of (query, requested_by)
queues = {}
now_playing = {}


def get_queue(guild_id):
    return queues.setdefault(guild_id, [])


async def extract_song(query):
    loop = asyncio.get_running_loop()

    def work():
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            # URL: use it directly. Normal text: search YouTube.
            target = query if query.startswith(("http://", "https://")) else "ytsearch1:" + query
            info = ydl.extract_info(target, download=False)

            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                if not entries:
                    raise Exception("Song nahi mila.")
                info = entries[0]

            return info["url"], info.get("title", "Unknown Song")

    return await loop.run_in_executor(None, work)


async def play_next(guild):
    guild_id = guild.id
    voice = guild.voice_client
    q = get_queue(guild_id)

    if voice is None or not q:
        now_playing.pop(guild_id, None)
        return

    query, requester = q.pop(0)

    try:
        audio_url, title = await extract_song(query)

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

        now_playing[guild_id] = {
            "title": title,
            "requester": requester,
        }

        def after(error):
            if error:
                print("PLAYER ERROR:", repr(error))
            asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)

        voice.play(source, after=after)

        channel = guild.system_channel
        if channel:
            try:
                await channel.send(
                    f"▶️ Now playing **{title}** 🎵\n"
                    f"👤 Requested by {requester.mention}"
                )
            except Exception:
                pass

    except Exception as e:
        print("PLAY NEXT ERROR:", repr(e))
        channel = guild.system_channel
        if channel:
            try:
                await channel.send(f"❌ Song play nahi ho saka: `{e}`")
            except Exception:
                pass
        await play_next(guild)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print("Sync error:", repr(e))


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
        print("JOIN ERROR:", repr(e))
        await interaction.followup.send(f"❌ Join error: `{e}`")


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    await interaction.response.defer()

    voice = interaction.guild.voice_client
    if voice:
        queues.pop(interaction.guild.id, None)
        now_playing.pop(interaction.guild.id, None)
        await voice.disconnect()
        await interaction.followup.send("👋 Voice channel se nikal gaya.")
    else:
        await interaction.followup.send("❌ Main kisi voice channel mein nahi hoon.")


@bot.tree.command(name="play", description="Play/search a song from YouTube")
@app_commands.describe(query="Song name, YouTube URL, or supported URL")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    if not interaction.user.voice:
        await interaction.followup.send("❌ Pehle voice channel join karo.")
        return

    channel = interaction.user.voice.channel
    guild = interaction.guild

    try:
        voice = guild.voice_client

        if voice is None:
            voice = await channel.connect()
        elif voice.channel != channel:
            await voice.move_to(channel)

        q = get_queue(guild.id)

        # If nothing is playing, start immediately.
        if not voice.is_playing() and not voice.is_paused():
            q.insert(0, (query, interaction.user))
            await interaction.followup.send("🔎 Song search ho raha hai...")
            await play_next(guild)
        else:
            q.append((query, interaction.user))
            position = len(q)
            await interaction.followup.send(
                f"➕ Queue me add kar diya!\n"
                f"📍 Position: **{position}**\n"
                f"🎵 **{query}**"
            )

    except Exception as e:
        print("PLAY ERROR:", repr(e))
        await interaction.followup.send(
            f"❌ Song play nahi ho saka.\nError: `{e}`"
        )


@bot.tree.command(name="queue", description="Show the current music queue")
async def queue_command(interaction: discord.Interaction):
    q = get_queue(interaction.guild.id)
    current = now_playing.get(interaction.guild.id)

    lines = []

    if current:
        lines.append(f"▶️ **Now playing:** {current['title']}")

    if q:
        lines.append("\n📋 **Up next:**")
        for i, (query, requester) in enumerate(q[:15], start=1):
            lines.append(f"`{i}.` {query} — {requester.display_name}")
        if len(q) > 15:
            lines.append(f"\n…and **{len(q)-15}** more.")
    elif not current:
        lines.append("📭 Queue empty hai.")

    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and (voice.is_playing() or voice.is_paused()):
        voice.stop()
        await interaction.response.send_message("⏭️ Song skipped.")
    else:
        await interaction.response.send_message("❌ Abhi koi song nahi baj raha.")


@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_playing():
        voice.pause()
        await interaction.response.send_message("⏸️ Song paused.")
    else:
        await interaction.response.send_message("❌ Abhi koi song play nahi ho raha.")


@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_paused():
        voice.resume()
        await interaction.response.send_message("▶️ Song resumed.")
    else:
        await interaction.response.send_message("❌ Koi paused song nahi hai.")


@bot.tree.command(name="stop", description="Stop music and clear the queue")
async def stop(interaction: discord.Interaction):
    voice = interaction.guild.voice_client
    queues.pop(interaction.guild.id, None)
    now_playing.pop(interaction.guild.id, None)

    if voice and (voice.is_playing() or voice.is_paused()):
        voice.stop()
        await interaction.response.send_message("⏹️ Song stopped aur queue clear kar di.")
    else:
        await interaction.response.send_message("❌ Abhi koi song nahi baj raha.")


if not TOKEN:
    print("❌ DISCORD_TOKEN variable nahi mila!")
else:
    bot.run(TOKEN)


    
