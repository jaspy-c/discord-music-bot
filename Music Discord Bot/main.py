# main.py
import discord
from discord.ext import commands
from music import Music
from responses import create_embed, create_help_menu

import os
from dotenv import load_dotenv

load_dotenv()

def main():

    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix='?', intents=intents)

    # Remove the default help command
    bot.remove_command("help")

    cogs = [Music(bot)]

    async def setup_cogs():
        for cog in cogs:
            await bot.add_cog(cog)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name}')
        await setup_cogs()
        await bot.change_presence(activity=discord.Game(name="?help"))

    @bot.command(name="help", description="Shows the bot's help menu")
    async def bot_help(ctx):
        commands_list = bot.commands
        help_menu = create_help_menu(commands_list)
        await ctx.send(embed=help_menu)

    @bot.event
    async def on_message(message):
        # Convert user input to lowercase
        message.content = message.content.lower()
        await bot.process_commands(message)

    bot.run(os.getenv("TOKEN"))

if __name__ == "__main__":
    main()
