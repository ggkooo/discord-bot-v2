import asyncio
import os
import shutil
import time
import uuid

from datetime import datetime, timezone

import aiohttp
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.ui import View, Button
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pytz import timezone

load_dotenv()

class ModifiedBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(PersistentViewTicket())
        self.add_view(PersistentViewTicketChannel())

bot = ModifiedBot()

auto_message_tasks = {}

products = {}
product_names = []

channels = {}

# MongoDB connection
try:
    client = MongoClient(os.getenv('MONGODB_URI'), server_api=ServerApi('1'))

    database = client['spectre-store']
    collection = database['auto-messages']

    all_products = collection.find()
    for product in all_products:
        products[product["_name"]] = [
            product["name"],
            product["description"],
            product["image_url"],
            product["channel"]
        ]

        product_names.append(product["_name"])

    collection = database['channels']

    all_channels = collection.find()
    for channel in all_channels:
        channels[channel["_name"]] = channel["channel"]

    client.close()
except Exception as e:
    print(e)

class PersistentViewTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💲 Comprar", custom_id="button_buy")
    async def button_buy(self, interaction: discord.Interaction, button):
        await create_ticket_channel(channels['spectre-buy-category'], interaction, 'compra')

    @discord.ui.button(label="🔧 Suporte", custom_id="button_support")
    async def button_support(self, interaction: discord.Interaction, button):
        await create_ticket_channel(channels['spectre-support-category'], interaction, 'suporte')

    @discord.ui.button(label="🎥 Media Creator", custom_id="button_media_creator")
    async def button_media_creator(self, interaction: discord.Interaction, button):
        await create_ticket_channel(channels['spectre-media-creator-category'], interaction, 'media-creator')

class PersistentViewTicketChannel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🕒 Lembrar", custom_id="button_remember")
    async def button_remember(self, interaction: discord.Interaction, button):
        try:
            creator_id = get_ticket_owner(interaction.channel)
            creator = interaction.guild.get_member(creator_id)
            interaction.response.send_message(f'{creator} | {creator_id}')
            try:
                await creator.send(
                    f'🕒 **Lembrete:** Não se esqueça do seu ticket aberto no servidor Spectre Store! {interaction.channel.mention}')
                await interaction.response.send_message('Lembrete enviado com sucesso!', ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message('Não consigui enviar, DMs desabilitadas.', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f'Um erro ocorreu ao tentar enviar a mensagem: {str(e)}', ephemeral=True)
        except Exception as error:
            await interaction.followup.send(f'Um erro ocorreu: {str(error)}', ephemeral=True)

    @discord.ui.button(label="❌ Fechar", custom_id="button_close")
    async def button_close(self, interaction: discord.Interaction, button):
        user = interaction.user
        creator_id = get_ticket_owner(interaction.channel)
        creator = interaction.guild.get_member(creator_id)

        folder_path = await save_transcript(interaction.channel)
        zip_path = f"{folder_path}.zip"
        shutil.make_archive(folder_path, 'zip', folder_path)

        await interaction.response.send_message('❌ **Ticket fechado!** Transcript salvo.', ephemeral=True)

        notification_channel = bot.get_channel(channels['spectre-logs-ticket'])
        embed = create_embed(
            title='Ticket Fechado',
            description=f'✅ **Aberto por:** {creator.mention if creator else "Unknown"}\n'
                        f'⏰ **Data:** {get_ticket_creation_date(interaction.channel)}\n\n'
                        f'❌ **Fechado por:** {interaction.user.mention}\n'
                        f'⏰ **Data:** {datetime.now(timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")}\n\n'
                        f'📰 **Transcript \t ⤵️**',
            color='#F91607',  # RED
        )

        await notification_channel.send(embed=embed)
        await notification_channel.send(file=discord.File(zip_path))

        time.sleep(3)
        await interaction.channel.delete()

def create_embed(title: str, description: str, color: str, image_url: str=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str(color),
    )

    embed.set_image(url=image_url)
    embed.set_footer(text='Spectre Store © 2025')

    return embed

async def create_ticket_channel(category, interaction, name):
    category = discord.utils.get(interaction.guild.categories, id=category)

    if not category:
        return await interaction.response.send_message("❌ **ERROR:** Categoria de tickets não encontrada!", ephemeral=True)

    for channel in category.text_channels:
        if channel.name == f'{name}-{interaction.user.name}':
            return await interaction.response.send_message("❌ **ERROR:** Você já possui um ticket aberto!", ephemeral=True)

    creation_date = datetime.now(timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')

    ticket_channel = await category.create_text_channel(
        name=f'{name}-{interaction.user.name}',
        topic=f"Ticket de {interaction.user.display_name} | User ID: {interaction.user.id} | Criado em: {creation_date}",
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        }
    )

    await interaction.response.send_message(f"✅ **Ticket criado com sucesso!**\n👉 Acesse seu ticket aqui: {ticket_channel.mention}", ephemeral=True)

    await new_ticket_channel(ticket_channel, interaction.user, interaction)

async def new_ticket_channel(ticket_channel, user, interaction):
    embed = create_embed(
        title="🎫 - Ticket | Spectre Store",
        description=f"Olá {interaction.user.mention}, seja bem-vindo ao seu ticket privado!\nTicket aberto com sucesso! Nossa equipe irá lhe atender em alguns instantes.",
        color="#840077" # PURPLE
    )

    await ticket_channel.send(f'{await get_role_mention(interaction, 1241829059617619988)} {await get_role_mention(interaction, 1241829061324574791)} {interaction.user.mention}', embed=embed, view=PersistentViewTicketChannel()) # f'{discord.utils.get(ctx.guild.roles, id=1354298874008834182).mention} {interaction.user.mention}'

async def get_role_mention(interaction: discord.Interaction, role_id):
    guild = interaction.guild
    role = discord.utils.get(guild.roles, id=role_id)
    if role:
        return role.mention
    return 'Role não encontrado.'

def get_ticket_creation_date(channel):
    if channel.topic:
        parts = channel.topic.split('|')
        if len(parts) > 2 and 'Criado em:' in parts[2]:
            return parts[2].split('Criado em:')[1].strip()
    return None

def get_ticket_owner(channel):
    if channel.topic:
        parts = channel.topic.split('|')
        if len(parts) > 1 and 'User ID:' in parts[1]:
            user_id_str = parts[1].split('User ID:')[1].strip()
            if user_id_str.isdigit():
                return int(user_id_str)
    return None

async def save_transcript(channel):
    messages = [message async for message in channel.history(limit=None)]
    messages.reverse()

    unique_id = uuid.uuid4()
    folder_path = os.path.join('transcripts', f"transcript-{channel.name}-{unique_id}")
    os.makedirs(folder_path, exist_ok=True)
    attachments_folder = os.path.join(folder_path, 'attachments')
    os.makedirs(attachments_folder, exist_ok=True)

    transcript = (f"<html>"
                  f"<head>"
                  f"<link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\" integrity=\"sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH\" crossorigin=\"anonymous\">"
                  f"<style>"
                  f".embed-card {{ max-width: 400px; margin: 10px 0; }}"
                  f"</style>"
                  f"</head>"
                  f"<body>"
                  f"<div class=\"container my-5\">"
                  f"<h1>Transcript of {channel.name}</h1>"
                  f"<ul class=\"list-unstyled\">")

    async with aiohttp.ClientSession() as session:
        for message in messages:
            avatar_url = message.author.avatar.url if message.author.avatar else 'default_avatar_url'
            transcript += f"<li class=\"my-2\"><span class=\"me-2\"><img class=\"rounded-circle\" width=\"35px\" src=\"{avatar_url}\"></span><strong>{message.author.display_name}</strong>: {message.content}</li>"

            # Include embeds
            for embed in message.embeds:
                color_hex = f"{embed.color.value:06x}"  # Convert color to hex
                transcript += f"<li class=\"my-2\"><div class=\"card embed-card\" style=\"border-left: 5px solid #{color_hex};\">"
                if embed.title:
                    transcript += f"<div class=\"card-header\"><strong>{embed.title}</strong></div>"
                if embed.description:
                    transcript += f"<div class=\"card-body\">{embed.description}</div>"
                if embed.footer:
                    transcript += f"<div class=\"card-footer text-muted\">{embed.footer.text}</div>"
                transcript += "</div></li>"

            # Include attachments
            for attachment in message.attachments:
                attachment_id = uuid.uuid4()
                attachment_extension = os.path.splitext(attachment.filename)[1]
                attachment_path = os.path.join(attachments_folder, f"{attachment_id}{attachment_extension}")
                async with session.get(attachment.url) as response:
                    with open(attachment_path, 'wb') as f:
                        f.write(await response.read())
                if attachment_extension.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                    transcript += f"<li class=\"my-2\"><strong>Attachment:</strong> <img src=\"{attachment_path}\" alt=\"{attachment.filename}\" style=\"max-width: 100%;\"></li>"
                else:
                    transcript += f"<li class=\"my-2\"><strong>Attachment:</strong> <a href=\"{attachment_path}\">{attachment_id}{attachment_extension}</a></li>"

    transcript += "</ul></div></body></html>"

    file_name = os.path.join(folder_path, f"transcript-{unique_id}.html")

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(transcript)

    return folder_path

@bot.event
async def on_ready():
    print('Logged in successfully.')

@bot.event
async def on_member_join(member):
    now = datetime.now(timezone('America/Sao_Paulo'))
    days_since_creation = (now - member.created_at).days

    embed = create_embed(
        title='Membro entrou',
        description=f'{member.mention} | {member.name}\n**Criação:** {days_since_creation} dias atrás',
        color='#1FFB2F' # GREEN
    )

    channel = bot.get_channel(channels['spectre-wellcome'])

    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    embed = create_embed(
        title='Membro saiu',
        description=f'{member.mention} | {member.name}',
        color='#F91607' # RED
    )

    channel = bot.get_channel(channels['spectre-left'])

    await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return

    notification_channel = bot.get_channel(channels['spectre-anti'])
    embed = create_embed(
        title='Menssagem editada',
        description=f'**Antes:** ```{before.content}```\n**Depois:** ```{after.content}```\n\n**Message ID:** {before.id}\n**Canal:** {before.channel.mention}\n**User ID:** {before.author.id}',
        color='#FB9800' # ORANGE
    )
    embed.set_author(name=before.author.display_name, icon_url=before.author.avatar.url)

    await notification_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    notification_channel = bot.get_channel(channels['spectre-anti'])
    embed = create_embed(
        title='Menssagem deletada',
        description=f'**Conteúdo:** ```{message.content}```\n\n**Message ID:** {message.id}\n**Canal:** {message.channel.mention}\n**User ID:** {message.author.id}',
        color='#F91607' # RED
    )
    embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
    embed.set_footer(text=f'')

    await notification_channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx: commands.Context):
    await ctx.channel.purge(limit=100)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member=0, *, reason=None):
    if member != 0:
        await member.ban(reason=reason)
        embed = create_embed(
            title='Banido',
            description=f'{member.mention} foi banido do servidor.',
            color='#BF1622'
        )
        await ctx.send(embed=embed)
    else:
        embed = create_embed(
            title='ERROR',
            description='!ban ID_USUÁRIO',
            color='#BF1622'
        )
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx: commands.Context):
    await ctx.channel.purge(limit=1)

    embed = create_embed(
        title="🎫 - Ticket | Spectre Store",
        description="Para tirar dúvidas, tiver algum problema com produtos ou concluir uma compra, abra um Ticket!",
        image_url="https://images-ext-1.discordapp.net/external/QpqlzoPo9OOGCmundGBjnJiPpxivhRFhdB4KdtV8sUg/%3Fsize%3D240%26quot%3B%29%3B/https/cdn.discordapp.com/banners/1215534857254346782/a_b3c434f165c5cd01f3cfe385f85f07ca.gif",
        color="#840077"
    )

    await ctx.send(embed=embed, view=PersistentViewTicket())

@bot.command()
@commands.has_permissions(administrator=True)
async def auto_msg(ctx, name: str='N', interval: int=0, channel: int=0):
    if name == 'N' or interval == 0:
        embed = create_embed(
            title='ERROR',
            description='!auto_msg PRODUCT_NAME INTERVAL CHANNEL',
            color='#BF1622'
        )
        await ctx.send(embed=embed)
        return

    global auto_message_tasks

    try:
        embed = create_embed(
            title=products[name][0],
            description=products[name][1],
            image_url=products[name][2],
            color='#840077'
        )

        target_channel = ctx.channel if channel == 0 else bot.get_channel(channel)

        if target_channel is None:
            await ctx.send("ERROR: Canal não encontrado.")
            return

        await target_channel.send(embed=embed)

        async def send_auto_message():
            while True:
                await target_channel.purge(limit=5)
                await target_channel.send(embed=embed)
                await asyncio.sleep(interval)

        if target_channel.id in auto_message_tasks and not auto_message_tasks[target_channel.id].done():
            auto_message_tasks[target_channel.id].cancel()

        auto_message_tasks[target_channel.id] = bot.loop.create_task(send_auto_message())
        await ctx.send(
            f'Task de mensagem automatica iniciada em {target_channel.name} em um intervalo de {interval} segundos.')

    except Exception as error:
        await ctx.send(f'Um erro ocorreu: {str(error)}', ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def all_auto_msg(ctx, interval: int=0):
    if interval == 0:
        embed = create_embed(
            title='ERROR',
            description='!all_auto_msg INTERVAL',
            color='#BF1622'
        )
        await ctx.send(embed=embed)
        return

    for name in product_names:
        p_channel = products[name][3]
        await auto_msg(ctx, name, interval, p_channel)

@bot.command()
@commands.has_permissions(administrator=True)
async def stop_auto_msg(ctx):
    global auto_message_tasks

    if auto_message_tasks:
        for task_id, task in auto_message_tasks.items():
            if not task.done():
                task.cancel()
        auto_message_tasks.clear()
        await ctx.send("Todas as mensagens automáticas foram canceladas.")
    else:
        await ctx.send("Nenhuma task de mensagem automatica encontrada.")

bot.run(os.getenv('DISCORD_TOKEN'))
