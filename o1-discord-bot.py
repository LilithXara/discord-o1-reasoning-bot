# bot.py
import discord
from discord.ext import commands, tasks
import openai
import json
import os
import logging
import time
from collections import defaultdict
from dotenv import load_dotenv
import atexit

# ------------------------------------------------------------------------------
# 1. ENV & LOGGING
# ------------------------------------------------------------------------------

load_dotenv()  # Comment out if not using a .env
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# ------------------------------------------------------------------------------
# 2. CONFIGURATION CONSTANTS
# ------------------------------------------------------------------------------

DISCORD_TOKEN = 'TOKEN'
OPENAI_API_KEY = 'KEY'

ALLOWED_GUILD_ID = 768249758044127235   # Replace with your guild/server ID
REQUIRED_ROLE_ID = 1015063346233495613  # Replace with your Elite Role ID

USAGE_FILE = 'usage.json'
RATE_LIMIT = 10        # Max requests in TIME_WINDOW
TIME_WINDOW = 30      # Seconds
DEFAULT_QUOTA = 5000  # Daily token quota if not in USER_QUOTAS

USER_QUOTAS = {
	'901638041100222494': 100000,
	'511704573212229654': 100000,
	# Add or remove user IDs as needed
}

# ------------------------------------------------------------------------------
# 3. OPENAI & DISCORD INITIALIZATION
# ------------------------------------------------------------------------------

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='!',
	intents=intents,
	description="O1 Discord Bot",
	help_command=None  # We'll define our own help command
)

# ------------------------------------------------------------------------------
# 4. USAGE DATA (TOKEN TRACKING)
# ------------------------------------------------------------------------------

def load_usage():
	"""Load usage data (token usage) from disk."""
	if os.path.exists(USAGE_FILE):
		with open(USAGE_FILE, 'r') as f:
			return defaultdict(int, json.load(f))
	return defaultdict(int)

def save_usage():
	"""Save usage data (token usage) to disk."""
	with open(USAGE_FILE, 'w') as f:
		json.dump(user_token_usage, f)

user_token_usage = load_usage()
atexit.register(save_usage)

# ------------------------------------------------------------------------------
# 5. RATE LIMITING & QUOTAS
# ------------------------------------------------------------------------------

user_requests = defaultdict(list)

async def check_rate_limit(user_id: str) -> bool:
	"""Ensure user does not exceed RATE_LIMIT within TIME_WINDOW."""
	current_time = time.time()
	user_requests[user_id] = [
		t for t in user_requests[user_id]
		if current_time - t < TIME_WINDOW
	]

	if len(user_requests[user_id]) >= RATE_LIMIT:
		return False
	else:
		user_requests[user_id].append(current_time)
		return True

def get_user_quota(user_id: str) -> int:
	"""Get daily token quota for this user."""
	return USER_QUOTAS.get(user_id, DEFAULT_QUOTA)

async def check_quota(user_id: str) -> bool:
	"""Check if the user is within their daily token quota."""
	quota = get_user_quota(user_id)
	if user_token_usage[user_id] >= quota:
		return False
	return True

# ------------------------------------------------------------------------------
# 6. LONG RESPONSE SPLITTING
# ------------------------------------------------------------------------------

def split_reply_into_embeds(reply: str, footer_text: str):
	"""
	Splits the reply into multiple Discord embeds if it exceeds 2048 characters.
	Tries to avoid splitting in the middle of code blocks by toggling `in_code_block`.
	"""
	max_length = 2048
	embeds = []
	current_part = ""
	in_code_block = False

	lines = reply.split('\n')
	for line in lines:
		if line.strip().startswith('```'):
			in_code_block = not in_code_block

		potential_length = len(current_part) + len(line) + 1
		if potential_length > max_length and not in_code_block:
			embed = discord.Embed(
				title="🧠 O1 Response",
				description=current_part,
				color=discord.Color.green()
			)
			embed.set_footer(text=footer_text)
			embeds.append(embed)
			current_part = line + '\n'
		else:
			current_part += line + '\n'

	if current_part:
		embed = discord.Embed(
			title="🧠 O1 Response",
			description=current_part,
			color=discord.Color.green()
		)
		embed.set_footer(text=footer_text)
		embeds.append(embed)

	return embeds

# ------------------------------------------------------------------------------
# 7. USERS.JSON FOR PROMPTS & MODES
# ------------------------------------------------------------------------------

def read_user_data():
	if not os.path.exists('users.json'):
		with open('users.json', 'w') as f:
			json.dump({}, f)
	with open('users.json', 'r') as f:
		try:
			return json.load(f)
		except json.JSONDecodeError:
			logger.error("users.json is invalid. Reinitializing.")
			return {}

def write_user_data(data):
	with open('users.json', 'w') as f:
		json.dump(data, f, indent=4)

# ------------------------------------------------------------------------------
# 8. GUILD/ROLE CHECK & HELP
# ------------------------------------------------------------------------------

async def check_guild_and_role(ctx) -> bool:
	"""Check if in allowed guild & user has required role."""
	if ctx.guild is None or ctx.guild.id != ALLOWED_GUILD_ID:
		logger.info(f"Ignored cmd from guild ID {ctx.guild.id if ctx.guild else 'None'}")
		return False

	has_elite = any(r.id == REQUIRED_ROLE_ID for r in ctx.author.roles)
	if not has_elite:
		await ctx.send(
			"❌ **Elite Role Required** ❌\n"
			"You do not have permission to use this bot's commands."
		)
		logger.info(f"User {ctx.author} lacks Elite role.")
		return False

	return True

async def send_help(ctx):
	embed = discord.Embed(
		title="📚 O1 Discord Bot Help 📚",
		description="Prefix-based commands:",
		color=discord.Color.blue()
	)
	embed.add_field(name="`!o1`", value="Show your current prompt + mode or help if none set.", inline=False)
	embed.add_field(name="`!o1 <input>`", value="Generate a response with your stored prompt + input.", inline=False)
	embed.add_field(name="`!o1 prompt <prompt>`", value="Set your custom prompt.", inline=False)
	embed.add_field(name="`!o1 reset`", value="Clear your current prompt.", inline=False)
	embed.add_field(name="`!o1 mode <o1|mini>`", value="Switch to 'o1' or 'mini' (mini is default).", inline=False)
	embed.set_footer(text="Uses OpenAI’s o1 or mini. No slash commands!")
	await ctx.send(embed=embed)

async def send_prompt_confirmation(ctx, prompt):
	embed = discord.Embed(
		title="✅ Prompt Set Successfully ✅",
		description="Your custom prompt has been set as follows:",
		color=discord.Color.green()
	)
	embed.add_field(name="Your Prompt:", value=prompt, inline=False)
	embed.set_footer(text="Use `!o1 <your input>` to generate a response from this prompt.")
	await ctx.send(embed=embed)

async def send_reset_confirmation(ctx):
	embed = discord.Embed(
		title="✅ Prompt Reset Successfully ✅",
		description="Your custom prompt has been reset.",
		color=discord.Color.green()
	)
	embed.set_footer(text="Use `!o1 prompt <your prompt>` to set a new prompt.")
	await ctx.send(embed=embed)

# ------------------------------------------------------------------------------
# 9. BACKGROUND TASK: RESET DAILY USAGE
# ------------------------------------------------------------------------------

from discord.ext import tasks

@tasks.loop(hours=24)
async def reset_daily_usage():
	global user_token_usage
	user_token_usage = defaultdict(int)
	save_usage()
	logger.info("Daily token usage has been reset.")

# ------------------------------------------------------------------------------
# 10. BOT EVENTS
# ------------------------------------------------------------------------------

@bot.event
async def on_ready():
	logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
	print('------')
	if not reset_daily_usage.is_running():
		reset_daily_usage.start()
		logger.info("Background task 'reset_daily_usage' started.")

# ------------------------------------------------------------------------------
# 11. MAIN COMMAND GROUP: !o1
# ------------------------------------------------------------------------------

@bot.group(invoke_without_command=True)
async def o1(ctx, *, user_input: str = None):
	# Rate limit
	user_id = str(ctx.author.id)
	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	if user_input:
		await generate_o1(ctx, user_input)
	else:
		data = read_user_data()
		user_info = data.get(user_id, {})
		current_prompt = user_info.get('prompt')
		current_mode = user_info.get('mode', 'mini')  # default is 'mini'

		if current_prompt:
			embed = discord.Embed(
				title="📄 Your Current Prompt 📄",
				description=current_prompt,
				color=discord.Color.blue()
			)
			embed.add_field(name="Current Mode", value=current_mode, inline=False)
			embed.set_footer(text="Use `!o1 <input>` to generate a response.")
			await ctx.send(embed=embed)
		else:
			# no prompt => show help
			await send_help(ctx)

@o1.command(name='help')
async def o1_help(ctx):
	user_id = str(ctx.author.id)
	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	await send_help(ctx)

@o1.command(name='prompt')
async def set_prompt(ctx, *, prompt: str = None):
	user_id = str(ctx.author.id)
	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	if not prompt:
		await ctx.send("⚠️ **Invalid Usage** ⚠️\nPlease provide a prompt.")
		return

	data = read_user_data()
	if user_id not in data:
		data[user_id] = {}
	data[user_id]['prompt'] = prompt
	if 'mode' not in data[user_id]:
		data[user_id]['mode'] = 'mini'

	write_user_data(data)
	logger.info(f"User {ctx.author} set a new prompt.")
	await send_prompt_confirmation(ctx, prompt)

@o1.command(name='reset')
async def reset_prompt(ctx):
	user_id = str(ctx.author.id)
	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	data = read_user_data()
	user_info = data.get(user_id, {})

	if 'prompt' in user_info:
		del user_info['prompt']
		data[user_id] = user_info
		write_user_data(data)
		logger.info(f"User {ctx.author} reset their prompt.")
		await send_reset_confirmation(ctx)
	else:
		await ctx.send("ℹ️ **No Prompt Found** ℹ️\nYou do not have a prompt set.")

@o1.command(name='mode')
async def set_mode(ctx, mode: str = None):
	"""Toggle between 'o1' or 'mini' modes. 'mini' is default if none is set."""
	user_id = str(ctx.author.id)
	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	if mode not in ['o1', 'mini']:
		await ctx.send("⚠️ **Invalid Mode** ⚠️\nChoose either `o1` or `mini`.")
		return

	data = read_user_data()
	if user_id not in data:
		data[user_id] = {}

	data[user_id]['mode'] = mode
	write_user_data(data)
	logger.info(f"User {ctx.author} set mode to {mode}.")
	await ctx.send(f"✅ **Mode Set to `{mode}`** ✅\nYou can now use the bot in `{mode}` mode.")

# ------------------------------------------------------------------------------
# 12. GENERATE RESPONSE
# ------------------------------------------------------------------------------

async def generate_o1(ctx, user_input: str):
	"""Use 'o1-preview' if user_mode == 'o1'; else 'o1-mini' if 'mini'."""
	user_id = str(ctx.author.id)

	if not await check_rate_limit(user_id):
		await ctx.send("🚫 **Rate Limit Exceeded** 🚫\nPlease wait a moment before trying again.")
		return

	if not await check_quota(user_id):
		await ctx.send("🚫 **Quota Exceeded** 🚫\nYou've reached your daily token limit.")
		return

	can_use = await check_guild_and_role(ctx)
	if not can_use:
		return

	data = read_user_data()
	user_info = data.get(user_id, {})
	user_prompt = user_info.get('prompt')
	user_mode = user_info.get('mode', 'mini')

	if not user_prompt:
		await ctx.send("ℹ️ **No Prompt Found** ℹ️\nUse `!o1 prompt <your prompt>` to set one.")
		return

	prompt = f"{user_prompt}\n{user_input}"

	await ctx.send("🔄 **Processing** 🔄\nGenerating response, please wait...")

	# Switch model based on user_mode
	if user_mode == 'o1':
		model = "o1-preview"   # Internally, but user sees just 'o1'
		max_comp_tokens = 5000 # Enough overhead for reasoning + visible text
	else:
		model = "o1-mini"      # 'mini'
		max_comp_tokens = 2000

	try:
		response = openai.ChatCompletion.create(
			model=model,
			messages=[{"role": "user", "content": prompt}],
			max_completion_tokens=max_comp_tokens
		)

		reply = response.choices[0].message.content.strip()
		usage = response.usage

		# Update user token usage
		user_token_usage[user_id] += usage.get('total_tokens', 0)

		# Prepare usage footer
		completion_tokens = usage.get('completion_tokens', 0)
		prompt_tokens = usage.get('prompt_tokens', 0)
		total_tokens = usage.get('total_tokens', 0)
		reasoning_tokens = usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)

		footer_text = (
			f"📝 Prompt Tokens: {prompt_tokens} | 🧠 Reasoning Tokens: {reasoning_tokens} | "
			f"🪄 Completion Tokens: {completion_tokens} | 🔢 Total Tokens: {total_tokens}"
		)

		# Split if reply is too long
		embeds = split_reply_into_embeds(reply, footer_text)
		for embed in embeds:
			await ctx.send(embed=embed)

		logger.info(f"User {ctx.author} used {total_tokens} tokens. Mode: {user_mode}.")

	except openai.error.OpenAIError as e:
		await ctx.send(f"❌ **Error** ❌\nAn error occurred while generating the response: {str(e)}")
		logger.error(f"OpenAIError: {e}")
	except Exception as e:
		await ctx.send(f"❌ **Unexpected Error** ❌\nAn unexpected error occurred: {str(e)}")
		logger.error(f"Unexpected error: {e}")

# ------------------------------------------------------------------------------
# 13. START THE BOT
# ------------------------------------------------------------------------------

if __name__ == '__main__':
	bot.run(DISCORD_TOKEN)