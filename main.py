import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from pytz import timezone

import discord
from discord.ext import commands
from discord.ui import View, Button

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

def create_embed(title: str, description: str, footer: str, color: str, image_url: str = ''):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str(color)
    )
    embed.set_footer(text=footer)
    embed.set_image(url=image_url)

    return embed

def create_button(style: discord.ButtonStyle, label: str):
    button = Button(style=style, label=label)

    return button

async def create_ticket_channel(category, ctx, interaction, name):
    category = discord.utils.get(interaction.guild.categories, id=category)

    if not category:
        return await interaction.response.send_message("❌ **Erro:** A categoria de tickets não foi encontrada!", ephemeral=True)

    for channel in category.text_channels:
        if channel.name == f'{name}-{interaction.user.name}':
            return await interaction.response.send_message("❌ **Erro:** Você já possui um ticket aberto!", ephemeral=True)

    creation_date = datetime.now(timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')

    ticket_channel = await category.create_text_channel(
        name=f'{name}-{interaction.user.name}',
        topic=f'Ticket criado em {creation_date} | {interaction.user.name} | ID: {interaction.user.id}',
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        }
    )

    await interaction.response.send_message(f"✅ **Ticket criado com sucesso!**\n👉 Acesse o seu ticket: {ticket_channel.mention}", ephemeral=True)

    await new_ticket_channel(ticket_channel, ctx, interaction)

async def new_ticket_channel(ticket_channel, ctx, interaction):
    embed_ticket_opened = create_embed(
        title="🎫 - Ticket | Spectre Store",
        description=f"Olá {interaction.user.mention}, seja bem-vindo ao seu ticket!\nTicket criado com sucesso! Em alguns instantes nossa equipe irá lhe atender.",
        footer="Spectre Store © 2025",
        color="#840077"
    )

    remember_button = create_button(discord.ButtonStyle.green, '🕒 Lembrar')
    close_button = create_button(discord.ButtonStyle.red, '❌ Fechar')

    def remember_callback(interaction):
        interaction.response.send_message("Você clicou no botão de lembrar!", ephemeral=True)

    def close_callback(interaction):
        interaction.response.send_message("Você clicou no botão de fechar!", ephemeral=True)
        ticket_channel.delete()

    remember_button.callback = remember_callback
    close_button.callback = close_callback

    view = View()
    view.add_item(remember_button)
    view.add_item(close_button)

    await ticket_channel.send(f'{discord.utils.get(ctx.guild.roles, id=1241829059617619988)} {interaction.user.mention}', embed=embed_ticket_opened, view=view)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    await ctx.channel.purge(limit=100)

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
        await create_ticket_channel(1354285201706061875, ctx, interaction, 'compra')

    async def support_callback(interaction):
        await create_ticket_channel(1354285215157059664, ctx, interaction, 'suporte')

    async def media_creator_callback(interaction):
        await create_ticket_channel(1354285244928229386, ctx, interaction, 'media-creator')

    buy_button.callback = buy_callback
    support_button.callback = support_callback
    media_creator_button.callback = media_creator_callback

    view = View()
    view.add_item(buy_button)
    view.add_item(support_button)
    view.add_item(media_creator_button)

    await ctx.send(embed=embed, view=view)







bot.run(os.getenv('DISCORD_TOKEN'))
