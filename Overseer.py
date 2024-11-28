import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
from collections import defaultdict, deque
import yt_dlp as youtube_dl

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Read tokens from token.txt
with open('token.txt', 'r') as file:
    lines = file.readlines()
    discord_token = lines[0].strip()
    google_api_key = lines[1].strip()

# Initialize per-guild song queues
song_queues = defaultdict(deque)

# Define ytdl_options globally
ytdl_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'restrictfilenames': True,
    'noprogress': True,
    'no_warnings': True,
    'source_address': '0.0.0.0'
}

# Define ffmpeg_options globally
ffmpeg_options = {
    'options': '-vn -hide_banner -loglevel error',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

# Initialize youtube_dl globally
ytdl = youtube_dl.YoutubeDL(ytdl_options)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        guild_ids = [257485892095180800, 718620999372767305]
        for guild_id in guild_ids:
            guild = discord.Object(id=guild_id)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands in guild {guild_id}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    change_activity.start()

@tasks.loop(minutes=5)
async def change_activity():
    # Your activity-changing logic here
    pass

@bot.tree.command(
    name='skip',
    description='Skip the current song',
    guilds=[
        discord.Object(id=257485892095180800),
        discord.Object(id=718620999372767305)
    ]
)
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped the current song.")
            # Proceed to the next song in the guild's queue
            await play_next_song(voice_client, guild_id)
            print(f"Skipped current song in guild {guild_id}.")
        else:
            await interaction.response.send_message("No song is currently playing.")
    else:
        await interaction.response.send_message("The bot is not connected to a voice channel.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the message ends with "dis", "deez", or "this" with optional punctuation
    if re.search(r'\b(dis|deez|this)[\?\!\.]*$', message.content, re.IGNORECASE):
        await message.channel.send("https://c.tenor.com/dvWBegOX1_0AAAAd/tenor.gif")

    await bot.process_commands(message)

bot.run(discord_token)