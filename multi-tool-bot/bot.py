import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import asyncio
import requests
import re
import time
import random
import aiohttp

# Load the .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up the bot and disable the default help command
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all(), help_command=None)

# Dictionary to keep track of daily trivia scores
daily_trivia_scores = {}

# Dictionary to store users subscribed to voice channel join alerts
voice_channel_alerts_subscribers = set()

# Event: on_ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Custom help command
@bot.command()
async def help(ctx, *, command_name=None):
    if command_name is None:
        embed = discord.Embed(title="Help", description="Use !help <command> for extended information on a command.", color=0x00ff00)
        embed.add_field(name="poll", value="Create a poll with thumbs up and thumbs down reactions.", inline=False)
        embed.add_field(name="remindme", value="Set a reminder. Usage: !remindme <time> <reminder message>", inline=False)
        embed.add_field(name="count", value="Start a countdown. Usage: !count <time>", inline=False)
        embed.add_field(name="predict", value="Predict the nationality based on the name. Usage: !predict <name>", inline=False)
        embed.add_field(name="emojistats", value="Show the most used emojis in the channel. Usage: !emojistats", inline=False)
        embed.add_field(name="dailytrivia", value="Participate in a daily trivia challenge. Usage: !dailytrivia", inline=False)
        embed.add_field(name="anime", value="Search for an anime. Usage: !anime <title>", inline=False)
        embed.add_field(name="voicealerts", value="Subscribe or unsubscribe to voice channel join alerts. Usage: !voicealerts <subscribe/unsubscribe>", inline=False)
        await ctx.send(embed=embed)
    else:
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(title=f"Help: {command_name}", description=command.help, color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Command not found.")

# Poll command
@bot.command()
async def poll(ctx, *, question: str):
    """Create a poll with thumbs up and thumbs down reactions."""
    embed = discord.Embed(title="Poll", description=question, color=0x00ff00)
    embed.set_footer(text="React with 👍 or 👎")
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction('👍')
    await poll_message.add_reaction('👎')

# Remindme command
@bot.command()
async def remindme(ctx, time: str, *, reminder: str = None):
    """Set a reminder. Usage: !remindme <time> <reminder message>"""
    if reminder is None:
        await ctx.send('Error: reminder message is required. Usage: !remindme <time> <reminder message>')
        return

    time_seconds = parse_time(time)
    if time_seconds is None:
        await ctx.send('Invalid time format. Please specify time with units (e.g., 30s, 5m, 1h).')
        return

    await ctx.send(f'Reminder set for {time}.')
    await asyncio.sleep(time_seconds)
    await ctx.send(f'{ctx.author.mention} Reminder: {reminder}')

# Countdown task
countdown_task = None

@bot.command(name='count')
async def count(ctx, time: str):
    """Start a countdown. Usage: !count <time>"""
    global countdown_task

    if countdown_task is not None:
        countdown_task.cancel()

    time_seconds = parse_time(time)
    if time_seconds is None:
        await ctx.send('Invalid time format. Please specify time with units (e.g., 30s, 5m, 1h).')
        return

    countdown_task = bot.loop.create_task(countdown(ctx, time_seconds))

async def countdown(ctx, total_seconds):
    start_time = time.time()
    end_time = start_time + total_seconds
    message = await ctx.send(f'Countdown: {format_time(total_seconds)} remaining')

    while total_seconds > 0:
        await asyncio.sleep(1)
        current_time = time.time()
        total_seconds = int(end_time - current_time)
        await message.edit(content=f'Countdown: {format_time(total_seconds)} remaining')

    await message.edit(content='Countdown finished!')
    await ctx.send(f'{ctx.author.mention} Countdown finished!')

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours}h {minutes}m {seconds}s' if hours else f'{minutes}m {seconds}s'

def parse_time(time_str):
    pattern = r'(\d+)([smhd]?)'
    match = re.match(pattern, time_str)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == 's':
        return amount
    elif unit == 'm':
        return amount * 60
    elif unit == 'h':
        return amount * 3600
    elif unit == 'd':
        return amount * 86400
    else:
        return None

# Emoji statistics command
@bot.command()
async def emojistats(ctx):
    """Show the most used emojis in the channel. Usage: !emojistats"""
    emoji_counts = {}
    async for message in ctx.channel.history(limit=1000):
        for emoji in message.guild.emojis:
            if str(emoji) in message.content:
                if emoji not in emoji_counts:
                    emoji_counts[emoji] = 0
                emoji_counts[emoji] += 1

    sorted_emoji_counts = sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_emoji_counts:
        stats = '\n'.join([f'{str(emoji)}: {count}' for emoji, count in sorted_emoji_counts])
        await ctx.send(f'Most used emojis:\n{stats}')
    else:
        await ctx.send('No emoji usage data found.')

# Daily trivia command
@bot.command()
async def dailytrivia(ctx):
    """Participate in a daily trivia challenge. Usage: !dailytrivia"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://opentdb.com/api.php?amount=1&type=multiple') as resp:
            data = await resp.json()

    question = data['results'][0]['question']
    correct_answer = data['results'][0]['correct_answer']
    incorrect_answers = data['results'][0]['incorrect_answers']
    answers = incorrect_answers + [correct_answer]
    random.shuffle(answers)

    embed = discord.Embed(title="Daily Trivia Challenge!", description=question, color=0x00ff00)
    for i, answer in enumerate(answers, 1):
        embed.add_field(name=f"Option {i}", value=answer, inline=False)

    trivia_message = await ctx.send(embed=embed)

    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
    except asyncio.TimeoutError:
        await ctx.send(f'Time is up! The correct answer was: {correct_answer}')
        return

    user = ctx.author
    if msg.content.lower() == correct_answer.lower():
        daily_trivia_scores[user.id] = daily_trivia_scores.get(user.id, 0) + 1
        await ctx.send(f'Correct! 🎉 Your daily score: {daily_trivia_scores[user.id]}')
    else:
        await ctx.send(f'Sorry, the correct answer was: {correct_answer}')

# Anime command
@bot.command()
async def anime(ctx, *, title: str):
    """Search for an anime. Usage: !anime <title>"""
    response = requests.get(f'https://api.jikan.moe/v4/anime?q={title}&limit=1')
    data = response.json()['data'][0]
    embed = discord.Embed(title=data['title'], url=data['url'], description=data['synopsis'], color=0x00ff00)
    embed.set_thumbnail(url=data['images']['jpg']['image_url'])
    embed.add_field(name='Episodes', value=data['episodes'])
    embed.add_field(name='Score', value=data['score'])
    embed.add_field(name='Start Date', value=data['aired']['from'])
    embed.add_field(name='End Date', value=data['aired']['to'])
    await ctx.send(embed=embed)

# Command to subscribe/unsubscribe to voice channel join alerts
@bot.command()
async def voicealerts(ctx, action: str = None):
    """Subscribe or unsubscribe to voice channel join alerts. Usage: !voicealerts <subscribe/unsubscribe>"""
    if action == "subscribe":
        if ctx.author.id not in voice_channel_alerts_subscribers:
            voice_channel_alerts_subscribers.add(ctx.author.id)
            await ctx.send(f"{ctx.author.mention} You have subscribed to voice channel join alerts.")
        else:
            await ctx.send(f"{ctx.author.mention} You are already subscribed to voice channel join alerts.")
    elif action == "unsubscribe":
        if ctx.author.id in voice_channel_alerts_subscribers:
            voice_channel_alerts_subscribers.remove(ctx.author.id)
            await ctx.send(f"{ctx.author.mention} You have unsubscribed from voice channel join alerts.")
        else:
            await ctx.send(f"{ctx.author.mention} You are not subscribed to voice channel join alerts.")
    else:
        await ctx.send(f"Invalid action. Please use !voicealerts <subscribe/unsubscribe>.")

# Event: on_voice_state_update to monitor users joining voice channels
@bot.event
async def on_voice_state_update(member, before, after):
    # Check if the user joined a voice channel
    if before.channel is None and after.channel is not None:
        # Notify all subscribers via DM
        for subscriber_id in voice_channel_alerts_subscribers:
            try:
                subscriber = await bot.fetch_user(subscriber_id)
                await subscriber.send(f"{member.name} has joined the voice channel {after.channel.name}.")
            except Exception as e:
                print(f"Failed to send DM to {subscriber_id}: {e}")

# Helper instructions for wrong commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        helper_text = ("Invalid command. Here are some commands you can use:\n"
                       "!poll <question> - Create a poll with thumbs up and thumbs down reactions.\n"
                       "!remindme <time> <reminder> - Set a reminder.\n"
                       "!count <time> - Start a countdown.\n"
                       "!predict <name> - Predict the nationality based on the name.\n"
                       "!emojistats - Show the most used emojis in the channel.\n"
                       "!dailytrivia - Participate in a daily trivia challenge.\n"
                       "!anime <title> - Search for an anime.\n"
                       "!voicealerts <subscribe/unsubscribe> - Subscribe or unsubscribe to voice channel join alerts.")
        await ctx.send(helper_text)
    else:
        await ctx.send(f"An error occurred: {str(error)}")

# Nationality prediction functions
def get_country_prediction(name):
    # Replace spaces with + to fit the API requirement
    formatted_name = name.replace(" ", "+")
    url = f"https://api.nationalize.io/?name={formatted_name}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_country_flag(country_code):
    OFFSET = 127397
    return chr(ord(country_code[0]) + OFFSET) + chr(ord(country_code[1]) + OFFSET)

def display_country_predictions(predictions):
    if not predictions:
        return "No predictions available."

    result = f"Name: {predictions['name']}\n"
    for country in predictions['country']:
        country_id = country['country_id']
        probability = country['probability']
        country_flag = get_country_flag(country_id)
        result += f"Country: {country_id} {country_flag}, Probability: {probability:.2f}\n"

    return result

# Predict command
@bot.command(name='predict')
async def predict(ctx, *, name: str):
    """Predict the nationality based on the name. Usage: !predict <name>"""
    predictions = get_country_prediction(name)

    if predictions:
        result = display_country_predictions(predictions)
        await ctx.send(result)
    else:
        await ctx.send("Error retrieving predictions.")

# Run the bot
bot.run(TOKEN)
