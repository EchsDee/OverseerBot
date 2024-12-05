import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import json
import random
import asyncio
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
import yt_dlp as youtube_dl  # Ensure yt-dlp is installed
from collections import defaultdict, deque  # Use defaultdict for song queues
from discord.ui import View, Button  # Import View and Button for UI components

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Read tokens from token.txt
with open('token.txt', 'r') as file:
    lines = file.readlines()
    discord_token = lines[0].strip()
    google_api_key = lines[1].strip()

# Load activities from activities.json with UTF-8 encoding
with open('activities.json', 'r', encoding='utf-8') as file:
    activities = json.load(file)



# Initialize per-guild song queues
song_queues = defaultdict(deque)

# Define ytdl_options globally
ytdl_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',  # Allows automatic search if not a URL
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'restrictfilenames': True,
    'noprogress': True,
    'no_warnings': True,
    'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
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
    activity = random.choice(activities)
    activity_name = activity["name"]
    activity_type = activity["type"]

    if activity_type == "playing":
        await bot.change_presence(activity=discord.Game(name=activity_name))
    elif activity_type == "watching":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_name))
    elif activity_type == "listening":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=activity_name))
    elif activity_type == "streaming":
        await bot.change_presence(activity=discord.Streaming(name=activity_name, url="https://twitch.tv/your_channel"))
    elif activity_type == "competing":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.competing, name=activity_name))
    elif activity_type == "custom":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name=activity_name))

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(767580883002589214)
    if channel:
        message = await channel.send(f"New Member: {member.mention} has joined! React to this message to get roles.")
        await message.add_reaction('🟢')
        await message.add_reaction('🔵')
        await message.add_reaction('🟡')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id == 767580883002589214:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        admin_role = guild.get_role(257626079576064010)  # Replace with the actual admin role ID

        if admin_role in member.roles:
            target_member = message.mentions[0]  # Assuming the message mentions the new member
            bot_member = guild.get_member(bot.user.id)

            if bot_member.guild_permissions.manage_roles:
                print(f"Bot has Manage Roles permission in guild {guild.id}.")
                if payload.emoji.name == '🟢':
                    role = guild.get_role(348285157805129728)
                    if bot_member.top_role > role:
                        await target_member.add_roles(role)
                        print(f"Assigned role {role.name} to {target_member.name} in guild {guild.id}.")
                    else:
                        print(f"Bot's role is not higher than {role.name} in guild {guild.id}.")
                elif payload.emoji.name == '🔵':
                    role = guild.get_role(297355904461045767)
                    if bot_member.top_role > role:
                        await target_member.add_roles(role)
                        print(f"Assigned role {role.name} to {target_member.name} in guild {guild.id}.")
                    else:
                        print(f"Bot's role is not higher than {role.name} in guild {guild.id}.")
                elif payload.emoji.name == '🟡':
                    role1 = guild.get_role(348285157805129728)
                    role2 = guild.get_role(819726936090869781)
                    if bot_member.top_role > role1 and bot_member.top_role > role2:
                        await target_member.add_roles(role1, role2)
                        print(f"Assigned roles {role1.name} and {role2.name} to {target_member.name} in guild {guild.id}.")
                    else:
                        print(f"Bot's role is not higher than {role1.name} or {role2.name} in guild {guild.id}.")
            else:
                print(f"Bot does not have permission to manage roles in guild {guild.id}.")

@bot.tree.command(
    name='play',
    description='Play a YouTube video or search term in voice channel',
    guilds=[
        discord.Object(id=257485892095180800),
        discord.Object(id=718620999372767305)
    ]
)
async def play(interaction: discord.Interaction, *, query: str):
    guild_id = interaction.guild.id
    voice_state = interaction.user.voice
    if not voice_state or not voice_state.channel:
        await interaction.response.send_message("You are not connected to a voice channel.")
        return

    voice_channel = voice_state.channel

    await interaction.response.defer()

    # Check if the input is a URL
    if not re.match(r'https?://', query):
        query = f"ytsearch:{query}"

    try:
        info = ytdl.extract_info(query, download=False)
    except Exception as e:
        await interaction.followup.send("An error occurred while processing your request.")
        print(f"yt-dlp error in guild {guild_id}: {e}")
        return

    # Add videos to the queue
    if 'entries' in info:
        for entry in info['entries']:
            audio_source = entry['url']
            title = entry.get('title', 'Unknown Title')
            song_queues[guild_id].append({'source': audio_source, 'title': title})
        await interaction.followup.send(f"Added {len(info['entries'])} songs to the queue from the playlist.")
    else:
        audio_source = info['url']
        title = info.get('title', 'Unknown Title')
        song_queues[guild_id].append({'source': audio_source, 'title': title})
        await interaction.followup.send(f"Added to queue: {title}")

    # Ensure the bot is connected to voice
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if not voice_client or not voice_client.is_connected():
        voice_client = await voice_channel.connect()

    # Send the control buttons
    view = MusicControlView(guild_id)
    await interaction.followup.send("Control playback:", view=view)

    # Start playing if not already
    if not voice_client.is_playing():
        await play_next_song(voice_client, guild_id)

async def play_next_song(voice_client, guild_id):
    if song_queues[guild_id]:
        song = song_queues[guild_id].popleft()
        try:
            # Use FFmpegOpusAudio for optimized streaming
            source = discord.FFmpegOpusAudio(song['source'], **ffmpeg_options)
        except Exception as e:
            print(f"Error initializing audio source for guild {guild_id}: {e}")
            await play_next_song(voice_client, guild_id)  # Attempt to play the next song
            return

        def after_playing(error):
            if error:
                print(f"Error in after_playing for guild {guild_id}: {error}")
            # Schedule the next song
            fut = asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id), bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error scheduling next song for guild {guild_id}: {e}")

        try:
            voice_client.play(source, after=after_playing)
            print(f"Now playing in guild {guild_id}: {song['title']}")
        except Exception as e:
            print(f"Error playing song in guild {guild_id}: {e}")
            await play_next_song(voice_client, guild_id)  # Attempt to play the next song
    else:
        await voice_client.disconnect()
        print(f"Song queue is empty for guild {guild_id}. Disconnected from voice channel.")

@bot.tree.command(
    name='stop',
    description='Stop the music and clear the queue',
    guilds=[
        discord.Object(id=257485892095180800),
        discord.Object(id=718620999372767305)
    ]
)
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        # Clear the guild's song queue
        song_queues[guild_id].clear()
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
        await interaction.response.send_message("Music has been stopped and the queue has been cleared.")
        print(f"Music stopped and queue cleared in guild {guild_id}.")
    else:
        await interaction.response.send_message("The bot is not connected to a voice channel.")

@bot.tree.command(
    name='queue',
    description='Display the current song queue',
    guilds=[
        discord.Object(id=257485892095180800),
        discord.Object(id=718620999372767305)
    ]
)
async def queue_command(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if song_queues[guild_id]:
        queue_list = [f"{idx+1}. {song['title']}" for idx, song in enumerate(song_queues[guild_id])]
        queue_message = "\n".join(queue_list)
        await interaction.response.send_message(f"Current Queue for this server:\n{queue_message}")
    else:
        await interaction.response.send_message("The song queue is currently empty.")

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

class MusicControlView(View):
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    @discord.ui.button(label='Play', style=discord.ButtonStyle.green)
    async def play_button(self, interaction: discord.Interaction, button: Button):
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice_client and not voice_client.is_playing():
            await play_next_song(voice_client, self.guild_id)
            await interaction.response.send_message("Resumed playback.", ephemeral=True)
        else:
            await interaction.response.send_message("Music is already playing.", ephemeral=True)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Stopped the music.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is playing.", ephemeral=True)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.blurple)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped the track.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is playing.", ephemeral=True)

bot.run(discord_token)