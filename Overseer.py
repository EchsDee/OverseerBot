import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Read tokens from token.txt
with open('token.txt', 'r') as file:
    lines = file.readlines()
    discord_token = lines[0].strip()
    giphy_token = lines[1].strip()


weather_code_mapping = {
    0: "☀️ Clear sky",
    1: "🌤️ Mainly clear",
    2: "⛅ Partly cloudy",
    3: "☁️ Overcast",
    45: "🌫️ Fog",
    48: "🌫️ Depositing rime fog",
    51: "🌦️ Drizzle: Light",
    53: "🌦️ Drizzle: Moderate",
    55: "🌦️ Drizzle: Dense intensity",
    56: "🌧️ Freezing Drizzle: Light",
    57: "🌧️ Freezing Drizzle: Dense intensity",
    61: "🌧️ Rain: Slight",
    63: "🌧️ Rain: Moderate",
    65: "🌧️ Rain: Heavy intensity",
    66: "🌧️ Freezing Rain: Light",
    67: "🌧️ Freezing Rain: Heavy intensity",
    71: "❄️ Snow fall: Slight",
    73: "❄️ Snow fall: Moderate",
    75: "❄️ Snow fall: Heavy intensity",
    77: "🌨️ Snow grains",
    80: "🌧️ Rain showers: Slight",
    81: "🌧️ Rain showers: Moderate",
    82: "🌧️ Rain showers: Violent",
    85: "❄️ Snow showers: Slight",
    86: "❄️ Snow showers: Heavy",
    95: "⛈️ Thunderstorm: Slight or moderate",
    96: "⛈️ Thunderstorm with slight hail",
    99: "⛈️ Thunderstorm with heavy hail"
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=257485892095180800))
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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
                print(f"Bot has Manage Roles permission.")
                if payload.emoji.name == '🟢':
                    role = guild.get_role(348285157805129728)
                    if bot_member.top_role > role:
                        await target_member.add_roles(role)
                        print(f"Assigned role {role.name} to {target_member.name}")
                    else:
                        print(f"Bot's role is not higher than {role.name}")
                elif payload.emoji.name == '🔵':
                    role = guild.get_role(297355904461045767)
                    if bot_member.top_role > role:
                        await target_member.add_roles(role)
                        print(f"Assigned role {role.name} to {target_member.name}")
                    else:
                        print(f"Bot's role is not higher than {role.name}")
                elif payload.emoji.name == '🟡':
                    role1 = guild.get_role(348285157805129728)
                    role2 = guild.get_role(819726936090869781)
                    if bot_member.top_role > role1 and bot_member.top_role > role2:
                        await target_member.add_roles(role1, role2)
                        print(f"Assigned roles {role1.name} and {role2.name} to {target_member.name}")
                    else:
                        print(f"Bot's role is not higher than {role1.name} or {role2.name}")
            else:
                print("Bot does not have permission to manage roles.")

@bot.tree.command(name='weather', guild=discord.Object(id=257485892095180800))
async def weather(interaction: discord.Interaction):
    locations = {
        "Guarapuava - PR": {"latitude": -25.3902, "longitude": -51.4622},
        "Pelotas - RS": {"latitude": -31.7719, "longitude": -52.3420},
        "São Francisco do Sul - SC": {"latitude": -26.2433, "longitude": -48.6333}
    }
    weather_data = ["Overseer:\n"]
    for location, coords in locations.items():
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['latitude']}&longitude={coords['longitude']}&current_weather=true"
        response = requests.get(url)
        data = response.json()
        weather = data['current_weather']
        weather_description = weather_code_mapping.get(weather['weathercode'], "Unknown")
        weather_data.append(f"**{location}:**\n{weather_description}, {weather['temperature']}°C\n")

    await interaction.response.send_message("\n".join(weather_data))

@bot.tree.command(name='search', description='Search Google and return the first result', guild=discord.Object(id=257485892095180800))
async def search_google(interaction: discord.Interaction, query: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(f"https://www.google.com/search?q={query}", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    answer = soup.find("div", class_="BNeawe").text
    if answer:
        await interaction.response.send_message(answer)
    else:
        await interaction.response.send_message("No results found.")

@bot.tree.command(name='gif', description='Search for a GIF and return the first result', guild=discord.Object(id=257485892095180800))
async def gif(interaction: discord.Interaction, query: str):
    url = f"https://api.giphy.com/v1/gifs/search?api_key={giphy_token}&q={query}&limit=1"
    response = requests.get(url)
    data = response.json()
    if data['data']:
        gif_url = data['data'][0]['images']['original']['url']
        await interaction.response.send_message(gif_url)
    else:
        await interaction.response.send_message("No GIFs found.")

# Run the bot with the Discord token
bot.run(discord_token)