import os
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord.ui import View, Button

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

def create_embed(title: str, description: str, footer: str, image_url: str, color: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str(color)
    )
    embed.set_footer(text=footer)
    embed.set_image(url=image_url)

    return embed

def create_button(style, label: str):
    button = Button(style=style, label=label)

    return button

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = create_embed(
        title="🎫 - Ticket | Spectre Store",
        description="Para tirar alguma dúvida, problema com produtos ou concretizar uma compra, abra um Ticket!",
        footer="Spectre Store © 2025",
        image_url="https://images-ext-1.discordapp.net/external/QpqlzoPo9OOGCmundGBjnJiPpxivhRFhdB4KdtV8sUg/%3Fsize%3D240%26quot%3B%29%3B/https/cdn.discordapp.com/banners/1215534857254346782/a_b3c434f165c5cd01f3cfe385f85f07ca.gif",
        color="#840077"
    )

    buy_button = create_button(discord.ButtonStyle.green, '💲 Comprar')
    support_button = create_button(discord.ButtonStyle.gray, '🔧 Suporte')
    media_creator_button = create_button(discord.ButtonStyle.blurple, '🎥 Media Creator')

    async def buy_callback(interaction):
        await interaction.response.send_message("Você clicou no botão de comprar!", ephemeral=True)

    async def support_callback(interaction):
        await interaction.response.send_message("Você clicou no botão de suporte!", ephemeral=True)

    async def media_creator_callback(interaction):
        await interaction.response.send_message("Você clicou no botão de ticket!", ephemeral=True)

    buy_button.callback = buy_callback
    support_button.callback = support_callback
    media_creator_button.callback = media_creator_callback

    view = View()
    view.add_item(buy_button)
    view.add_item(support_button)
    view.add_item(media_creator_button)

    await ctx.send(embed=embed, view=view)







bot.run(os.getenv('DISCORD_TOKEN'))
