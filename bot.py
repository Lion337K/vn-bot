import os
import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID Tanımlamaları
LOG_CHANNEL_ID = 1381770621054091306       # Medya loglarının atılacağı kanal
WELCOME_CHANNEL_ID = 1488662459009994965   # Giriş ve çıkış mesajlarının atılacağı kanal

# Giriş mesajlarını takip etmek için sözlük
join_messages = {}

# Bump takip değişkenleri
last_bump_time = None
bump_channel_id = None
two_hour_reminder_sent = False
twelve_hour_reminder_sent = False
last_reminder_time = None

# ==================== WEB SUNUCUSU (Render / Uptime için) ====================
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print("Web sunucusu baslatildi.")

# ==================== BUMP HATIRLATMA GÖREVİ ====================
@tasks.loop(minutes=1)
async def check_bump_reminders():
    global two_hour_reminder_sent, twelve_hour_reminder_sent, last_bump_time, bump_channel_id, last_reminder_time
    if not bump_channel_id:
        return
        
    now = datetime.now()

    # 1. Aşama: Disboard mesajından 2 saat sonra "buuump" gönder
    if not two_hour_reminder_sent and last_bump_time and (now - last_bump_time >= timedelta(hours=2)):
        channel = bot.get_channel(bump_channel_id)
        if channel:
            await channel.send("buuump")
        two_hour_reminder_sent = True
        last_reminder_time = now

    # 2. Aşama: "buuump" atıldıktan 12 saat sonra hâlâ yeni bump gelmediyse "yapsaniza lan" gönder
    if two_hour_reminder_sent and not twelve_hour_reminder_sent and last_reminder_time and (now - last_reminder_time >= timedelta(hours=12)):
        channel = bot.get_channel(bump_channel_id)
        if channel:
            await channel.send("yapsaniza lan")
        twelve_hour_reminder_sent = True

# ==================== BOT ETKİNLİKLERİ ====================
@bot.event
async def on_ready():
    print(f"Bot giris yapti: {bot.user.name} (ID: {bot.user.id})")
    
    # Tüm eski slaş komutlarını temizle
    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("Tüm slaş komutları başarıyla silindi ve temizlendi.")
    except Exception as e:
        print(f"Slaş komutları temizlenirken hata oluştu: {e}")

    # Bump hatırlatıcı döngüsünü başlat
    if not check_bump_reminders.is_running():
        check_bump_reminders.start()

    # Log kanalına doğrudan "p" mesajı gönder
    try:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send("p")
    except Exception as e:
        print(f"Log kanalına 'p' mesajı gönderilemedi: {e}")

# ==================== GİRİŞ / ÇIKIŞ BİLDİRİMLERİ ====================
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        msg = await channel.send(f"{member.mention} aramiza katildi fln filan 😒")
        join_messages[member.id] = msg

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        if member.id in join_messages:
            try:
                msg = join_messages[member.id]
                await msg.edit(content=f"{member.mention} geri gitti... 😳")
                del join_messages[member.id]
                return
            except Exception:
                pass
        
        await channel.send(f"{member.mention} geri gitti... 😳")

# ==================== BUMP VE MEDYA LOG SİSTEMİ ====================
@bot.event
async def on_message(message):
    global last_bump_time, bump_channel_id, two_hour_reminder_sent, twelve_hour_reminder_sent, last_reminder_time

    if message.author.bot:
        # Disboard Bump kontrolü (ID: 302050872383242240)
        if message.author.id == 302050872383242240:
            for embed in message.embeds:
                description = embed.description or ""
                if "Bump done" in description or "başarıyla" in description.lower():
                    last_bump_time = datetime.now()
                    bump_channel_id = message.channel.id
                    two_hour_reminder_sent = False
                    twelve_hour_reminder_sent = False
                    last_reminder_time = None
                    await message.channel.send("Sunucu öne çıkarıldı! Teşekkürler.")
        return

    # Görsel ve video log sistemi (Doğrudan URL ile Cloudflare filtresi aşılır)
    if message.channel.id != LOG_CHANNEL_ID and message.attachments:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.mov', '.webm']):
                    log_text = f"Kullanıcı: {message.author} (`{message.author.id}`)\nKanal: {message.channel.mention}\n{attachment.url}"
                    try:
                        await log_channel.send(content=log_text)
                    except Exception as e:
                        print(f"Medya loglanırken hata oluştu: {e}")

    await bot.process_commands(message)

# ==================== ANA ÇALIŞTIRMA FONKSİYONU ====================
async def main():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("HATA: DISCORD_TOKEN bulunamadi!")
        return

    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    print("Bot baslatiliyor, sistem kontrol ediliyor...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot kapatılıyor...")
