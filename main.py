import asyncio
import os
import shutil
import uuid
import time
import aiohttp
from dotenv import load_dotenv
from datetime import datetime, timezone
from pytz import timezone

import discord
from discord.ext import commands
from discord.ui import View, Button

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

auto_message_tasks = {}

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
        topic=f"Ticket de {interaction.user.display_name} | Criado em: {creation_date}",
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        }
    )

    await interaction.response.send_message(f"✅ **Ticket criado com sucesso!**\n👉 Acesse o seu ticket: {ticket_channel.mention}", ephemeral=True)

    await new_ticket_channel(ticket_channel, interaction.user, ctx, interaction)

def get_ticket_creation_date(channel):
    if channel.topic:
        parts = channel.topic.split('|')
        if len(parts) > 1 and 'Criado em:' in parts[1]:
            return parts[1].split('Criado em:')[1].strip()
    return None

async def new_ticket_channel(ticket_channel, user, ctx, interaction):
    embed_ticket_opened = create_embed(
        title="🎫 - Ticket | Spectre Store",
        description=f"Olá {interaction.user.mention}, seja bem-vindo ao seu ticket!\nTicket criado com sucesso! Em alguns instantes nossa equipe irá lhe atender.",
        footer="Spectre Store © 2025",
        color="#840077" # PURPLE
    )

    remember_button = create_button(discord.ButtonStyle.green, '🕒 Lembrar')
    close_button = create_button(discord.ButtonStyle.red, '❌ Fechar')

    async def remember_callback(interaction_btn):
        try:
            await user.send(f'🕒 **Lembrete:** Não se esqueça do seu ticket em aberto no servidor Spectre Store! {interaction_btn.channel.mention}')
            await interaction_btn.response.send_message('Lembrete enviado no privado!', ephemeral=True)
        except Exception as error:
            await interaction_btn.followup.send(f'Ocorreu um erro: {str(error)}', ephemeral=True)

    async def close_callback(interaction_btn):
        folder_path = await save_transcript(interaction_btn.channel)
        zip_path = f"{folder_path}.zip"
        shutil.make_archive(folder_path, 'zip', folder_path)

        await interaction_btn.response.send_message('❌ **Ticket fechado!** Transcript salvo.', ephemeral=True)

        notification_channel = bot.get_channel(1354318256474951785)
        embed = create_embed(
            title='Ticket Fechado',
            description=f'✅ **Aberto por:** {user.mention}\n⏰ **Data:** {get_ticket_creation_date(interaction_btn.channel)}\n\n❌ **Fechado por:** {interaction_btn.user.mention}\n⏰ **Data:** {datetime.now(timezone('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')}\n\n📰 **Transcript \t ⤵️**',
            footer='Spectre Store © 2025',
            color='#F91607', # RED
        )

        await notification_channel.send(embed=embed)
        await notification_channel.send(file=discord.File(zip_path))

        time.sleep(3)
        await interaction_btn.channel.delete()

    remember_button.callback = remember_callback
    close_button.callback = close_callback

    view = View()
    view.add_item(remember_button)
    view.add_item(close_button)

    await ticket_channel.send(f'{discord.utils.get(ctx.guild.roles, id=1354298874008834182).mention} {interaction.user.mention}', embed=embed_ticket_opened, view=view)

async def save_transcript(channel):
    messages = [message async for message in channel.history(limit=None)]
    messages.reverse()  # Reverse the order of messages

    unique_id = uuid.uuid4()
    folder_path = os.path.join('transcripts', f"transcript-{unique_id}")
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
            transcript += f"<li class=\"my-2\"><span class=\"me-2\"><img class=\"rounded-circle\" width=\"35px\" src=\"{message.author.avatar.url}\"></span><strong>{message.author.display_name}</strong>: {message.content}</li>"

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
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_member_join(member):
    now = datetime.now(timezone.utc)
    days_since_creation = (now - member.created_at).days

    embed = create_embed(
        title='Entrada no servidor',
        description=f'{member.mention} | {member.name}\n**Criação:** {days_since_creation} dias atrás',
        footer='Spectre Store © 2025',
        color='#1FFB2F' # GREEN
    )

    channel = bot.get_channel(1354141477650825448)

    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    embed = create_embed(
        title='Saída do servidor',
        description=f'{member.mention} | {member.name}',
        footer='Spectre Store © 2025',
        color='#F91607' # RED
    )

    channel = bot.get_channel(1354316225404076163)

    await channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return

    notification_channel = bot.get_channel(1354320992180109312)
    embed = create_embed(
        title='Mensagem editada',
        description=f'**Antes:** ```{before.content}```\n**Depois:** ```{after.content}```\n\n**ID da mensagem:** {before.id}\n**Canal:** {before.channel.mention}\n**ID do usuário:** {before.author.id}',
        footer='Spectre Store © 2025',
        color='#FB9800' # ORANGE
    )
    embed.set_author(name=before.author.display_name, icon_url=before.author.avatar.url)

    await notification_channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    notification_channel = bot.get_channel(1354320992180109312)
    embed = create_embed(
        title='Mensagem deletada',
        description=f'**Conteúdo:** ```{message.content}```\n\n**ID da mensagem:** {message.id}\n**Canal:** {message.channel.mention}\n**ID do usuário:** {message.author.id}',
        footer='Spectre Store © 2025',
        color='#F91607' # RED
    )
    embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
    embed.set_footer(text=f'')

    await notification_channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    await ctx.channel.purge(limit=100)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member=0, *, reason=None):
    if member != 0:
        await member.ban(reason=reason)
        embed = create_embed(
            title='Banido',
            description=f'{member.mention} foi banido do servidor.',
            footer='Spectre Store © 2025',
            color='#BF1622'
        )
        await ctx.send(embed=embed)
    else:
        embed = create_embed(
            title='Erro',
            description='!ban ID_USUÁRIO',
            footer='Spectre Store © 2025',
            color='#BF1622'
        )
        await ctx.send(embed=embed)

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


products = {
    'plus': [
        '🟢・SPECTRE PLUS',
        '**Compatibilidade:**\n🇧🇷 Compativel com Windows 10 / Windows 11.\n🇧🇷 Processador : Intel / Amd\n\n**┍Aimbot**\n・Aimbot\n・Recoil Control\n・Draw Fov\n・Draw Crosshair\n・Visibility Check\n・Smoothing Aim\n\n**┍Visuals**\n・Box (3D Box, 2D Box)\n・Team Check\n・Remove Dormant\n・Health\n・Snaplines\n・Distance\n・Skeleton\n・Head Circle\n・Max Distance\n・Visible Color\n・Non Visible Color\n\n**┍Misc**\n・Stream Mode\n・Watermark\n\n```\nR$25.00 - 1 Dia\nR$110.00 - 1 Semana\nR$180.00 - 1 Mês\nR$260.00 - Lifetime```',
        'https://media.discordapp.net/attachments/1354984897470533812/1354985577253965884/plus.jpg?ex=67e74828&is=67e5f6a8&hm=feaed8433c0b4c0c882da5fcb02fb4478523bf72d4eced1ea633ceb179ab5e27&=&format=webp&width=864&height=864',
        1354624568190304467
    ],
    'aim': [
        '🟢・SPECTRE AIM',
        'Compatibilidade:\n🇧🇷 Compativel com Windows 10 / Windows 11.\n🇧🇷 Processador : Intel / Amd\n\n┍Aimbot\n・Aimbot\n・Recoil Control\n・Draw Fov\n・Draw Crosshair\n・Visibility Check\n・Smoothing Aim\n\n┍Misc\n・Stream Mode\n・Watermark\n\n```\nR$20.00 - 1 Dia\nR$40.00 - 1 Semana\nR$70.00 - 1 Mês\nR$150.00 - Lifetime```',
        'https://media.discordapp.net/attachments/1354984897470533812/1354985573651320962/aim.jpg?ex=67e899a7&is=67e74827&hm=83d5e063837448079c1519328e6e8d1880490e70de65ff9ae3582f90029215cf&=&format=webp&width=864&height=864',
        1354617502021455985
    ]
}

@bot.command()
@commands.has_permissions(administrator=True)
async def auto_msg(ctx, name: str='N', interval: int=0, channel: int=0):
    if name == 'N' or interval == 0:
        embed = create_embed(
            title='Erro',
            description='!auto_msg NOME_PRODUTO INTERVALO CANAL',
            footer='Spectre Store © 2025',
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
            footer='Spectre Store © 2025',
            color='#840077'
        )

        target_channel = ctx.channel if channel == 0 else bot.get_channel(channel)

        if target_channel is None:
            await ctx.send("Erro: Canal inválido ou não encontrado.")
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
            f'Auto message task started in {target_channel.name} with an interval of {interval} seconds.')

    except Exception as error:
        await ctx.send(f'Ocorreu um erro: {str(error)}', ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def all_auto_msg(ctx, interval: int=0):
    if interval == 0:
        embed = create_embed(
            title='Erro',
            description='!all_auto_msg INTERVALO',
            footer='Spectre Store © 2025',
            color='#BF1622'
        )
        await ctx.send(embed=embed)
        return

    product_names = ['plus', 'aim']

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
        await ctx.send("Todas as tarefas de mensagens automáticas foram canceladas.")
    else:
        await ctx.send("Nenhuma tarefa de mensagem automática está em execução.")



bot.run(os.getenv('DISCORD_TOKEN'))
