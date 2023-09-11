import discord

def create_embed(title, description):
    return discord.Embed(title=title, description=description, color=discord.Color.blurple())

def create_error_embed(error_msg):
    return discord.Embed(title="Error", description=error_msg, color=discord.Color.red())

def create_help_menu(commands):
    # Sort commands alphabetically by their names
    sorted_commands = sorted(commands, key=lambda x: x.name)

    embed = create_embed("Help Menu", "List of available commands:")
    for command in sorted_commands:
        embed.add_field(name=f"?{command.name}", value=command.description, inline=False)
    return embed