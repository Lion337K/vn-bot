import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import re
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse
import sys
sys.stdout.reconfigure(line_buffering=True)

# ───────────────────────────────────────────────
#  BOT YANITLARI VE MESAJLARI
# ───────────────────────────────────────────────

RESPONSES = {
    "welcome_message": "{member} aramiza katildi fln filan 😒",
    "bump_message": "buuuuump",
    "sendmsg_not_found": "🌌 Böyle bir kanal bulunamadı.",
    "sendmsg_success": "🦋 Mesaj başarıyla gönderildi.",
    "sendmsg_error": "❌ Hata oluştu: {error}",
    "err_missing_permissions": "yetkin yok kullanamazsin.",
    "err_cooldown": "yavasla biraz. {retry_after} saniye sonra bidaha dene.",
    "err_generic": "hata olustu: {error}",
    "err_not_kose_owner": "bu komutu sadece bu köşenin sahibi kullanabilir.",

    # ── Köşe sistemi ──
    "kose_panel_message": "kose olusturmak icin tiklayin",
    "kose_button_label": "olustur",
    "kose_request_message": "{member} kose olusturmak istiyor, approvluyoz mu",
    "kose_request_sent": "✅ İsteğin moderatörlere iletildi.",
    "kose_already_pending": "⏳ Zaten bekleyen bir köşe isteğin var.",
    "kose_already_owner": "🏡 Zaten bir köşen var.",
    "kose_owner_exists": "⚠️ {member} zaten bir köşeye sahip, istek iptal edildi.",
    "kose_request_error": "❌ İstek gönderilemedi, biraz sonra tekrar dene.",
    "kose_approved": "✅ {member} için köşe onaylandı ({mod}) → {channel}",
    "kose_denied": "❌ {member} için köşe isteği reddedildi ({mod})",
    "kose_user_missing": "⚠️ {member} sunucuda değil, istek iptal edildi.",
    "kose_create_failed": "⚠️ {member} için köşe oluşturulamadı: {error}",
    "kose_welcome": "{member} köşen hazır! Bu kategoride mesaj silme ve sabitleme yetkin var ({role}).",
}

# ───────────────────────────────────────────────
#  AYARLAR VE ID'LER
# ───────────────────────────────────────────────

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID             = 1381768080610426930
WELCOME_CHANNEL_ID   = 1480314604713414757
BUMP_CHANNEL_ID      = 1381771230964748370
IMAGE_LOG_CHANNEL_ID = 1480317488456536166

KOSE_CREATE_CHANNEL_ID  = 1568572421395718175   # "olustur" butonunun olduğu kanal
KOSE_REQUEST_CHANNEL_ID = 1568573627543068762   # moderatör onay kanalı

BUMP_BOT_ID = 302050872383242240  # Disboard

OWNER_ROLE_PREFIX = "[owner] - "
KOSE_TOPIC_TAG = "KOSE_OWNER_ROLE"   # köşenin metin kanalı konusuna yazılır
APPROVE_EMOJI = "✅"
DENY_EMOJI = "❌"

# Extensions used as a fallback when Discord doesn't send a content type
MEDIA_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".avif",
    ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v",
)

# GIF linkleri (Discord'un GIF seçicisi bunları yollar) ve doğrudan .gif linkleri
GIF_HOSTS = ("tenor.com", "giphy.com")
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
MAX_GIFS_PER_MESSAGE = 5

# ───────────────────────────────────────────────
#  MESAJ AYARLARI (değiştirmek için yukarıdaki RESPONSES'u düzenle)
# ───────────────────────────────────────────────

config = {
    "WELCOME_MESSAGE": RESPONSES["welcome_message"],
    "BUMP_MESSAGE": RESPONSES["bump_message"],
}

# ───────────────────────────────────────────────
#  KÖŞE DURUMU (bellekte; yeniden başlatınca istek kanalından yeniden kurulur)
# ───────────────────────────────────────────────

gif_logged = set()         # GIF'i loglanmış mesaj id'leri (çift loglamayı önler)
pending_requests = {}      # kullanıcı id -> istek mesajı id
handled_requests = set()   # işlenmiş istek mesajı id'leri (çift onayı önler)

# İstek mesajını tanımak için şablondan regex üret
_req_prefix, _req_suffix = RESPONSES["kose_request_message"].split("{member}")
REQUEST_RE = re.compile(re.escape(_req_prefix) + r"<@!?(\d+)>" + re.escape(_req_suffix))
KOSE_TOPIC_RE = re.compile(KOSE_TOPIC_TAG + r":(\d+)")

NO_PINGS = discord.AllowedMentions.none()

# ───────────────────────────────────────────────
#  BOT SETUP
# ───────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True          # Developer Portal'da da açık olmalı (Server Members Intent)
intents.message_content = True  # Developer Portal'da da açık olmalı (ek dosyaları görmek için de gerekli)


class MyBot(commands.Bot):
    async def setup_hook(self):
        # Slash komutları sadece bir kez, bot bağlanırken senkronize edilir
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            print(f"✅ {len(synced)} komut senkronize edildi.")
        except Exception as e:
            print(f"⚠️ Komut senkronizasyon hatası: {e}")

        # Kalıcı buton: bot yeniden başlasa da eski mesajdaki buton çalışır
        self.add_view(CreateKoseView())

        bump_check_loop.start()


bot = MyBot(command_prefix="!", intents=intents)

# ───────────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ───────────────────────────────────────────────


async def get_channel_safe(channel_id: int):
    """Cache'te yoksa API'den çekmeyi dener. Bulamazsa None döner."""
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"⚠️ Kanal {channel_id} alınamadı: {e!r}")
        return None


def is_media(attachment: discord.Attachment) -> bool:
    content_type = (attachment.content_type or "").lower()
    if content_type.startswith(("image/", "video/")):
        return True
    return attachment.filename.lower().endswith(MEDIA_EXTENSIONS)

# ───────────────────────────────────────────────
#  MEDYA LOG SİSTEMİ
# ───────────────────────────────────────────────


def log_header(message: discord.Message) -> str:
    return (
        f"📎 **Gönderen:** {message.author.mention} (`{message.author}`)\n"
        f"📍 **Kanal:** {message.channel.mention}\n"
        f"🔗 {message.jump_url}"
    )


async def log_media(message: discord.Message):
    media = [a for a in message.attachments if is_media(a)]
    if not media:
        return

    log_channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    header = log_header(message)
    size_limit = log_channel.guild.filesize_limit

    for attachment in media:
        try:
            if attachment.size > size_limit:
                # Too big to re-upload, so link to the original instead
                await log_channel.send(
                    f"{header}\n⚠️ Dosya çok büyük, yeniden yüklenemedi: {attachment.url}",
                    allowed_mentions=NO_PINGS,
                )
            else:
                await log_channel.send(
                    header,
                    file=await attachment.to_file(),
                    allowed_mentions=NO_PINGS,
                )
        except Exception as e:
            print(f"⚠️ '{attachment.filename}' log kanalına gönderilemedi: {e!r}")
            # Last resort: at least log who sent it and where, with the link
            try:
                await log_channel.send(
                    f"{header}\n⚠️ Dosya yüklenemedi: {attachment.url}",
                    allowed_mentions=NO_PINGS,
                )
            except Exception as e2:
                print(f"❌ Yedek log mesajı da gönderilemedi: {e2!r}")


def is_gif_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in GIF_HOSTS):
        return True
    return parsed.path.lower().endswith(".gif")


def collect_gif_urls(message: discord.Message) -> list:
    """Mesajdaki GIF linklerini bulur: önce metindeki linkler, yoksa gifv embed'leri."""
    urls = []
    for url in URL_RE.findall(message.content or ""):
        url = url.rstrip(".,;:!?)\"'")
        if is_gif_url(url):
            urls.append(url)
    if not urls:
        for embed in message.embeds:
            if embed.url and (
                embed.type == "gifv" or (embed.type == "image" and is_gif_url(embed.url))
            ):
                urls.append(embed.url)
    return list(dict.fromkeys(urls))[:MAX_GIFS_PER_MESSAGE]


async def log_gifs(message: discord.Message):
    if message.id in gif_logged:
        return
    urls = collect_gif_urls(message)
    if not urls:
        return

    log_channel = await get_channel_safe(IMAGE_LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    gif_logged.add(message.id)
    if len(gif_logged) > 5000:
        gif_logged.clear()

    header = log_header(message)
    for url in urls:
        try:
            # Link olarak atılır, Discord log kanalında GIF'i kendisi gösterir
            await log_channel.send(f"{header}\n🎞️ **GIF:** {url}", allowed_mentions=NO_PINGS)
        except Exception as e:
            print(f"⚠️ GIF log kanalına gönderilemedi: {e!r}")

# ───────────────────────────────────────────────
#  KÖŞE SİSTEMİ
# ───────────────────────────────────────────────


def is_moderator(member: discord.Member) -> bool:
    """İstekleri onaylayabilecek kişiler: yönetici veya kanalları yönetebilenler."""
    perms = member.guild_permissions
    return perms.administrator or perms.manage_channels


def has_owner_role(member: discord.Member) -> bool:
    return any(r.name.startswith(OWNER_ROLE_PREFIX) for r in member.roles)


def owner_overwrite() -> discord.PermissionOverwrite:
    """Köşe sahibinin yetkileri: mesaj silme + sabitleme."""
    try:
        return discord.PermissionOverwrite(manage_messages=True, pin_messages=True)
    except (ValueError, TypeError):
        # Eski discord.py sürümlerinde ayrı pin yetkisi yok; manage_messages yeterli
        return discord.PermissionOverwrite(manage_messages=True)


def get_kose_owner_role(channel):
    """Bir kanalın bulunduğu köşenin [owner] rolünü döndürür (köşe değilse None)."""
    category = getattr(channel, "category", None)
    if category is None:
        return None
    for text_channel in category.text_channels:
        if text_channel.topic:
            match = KOSE_TOPIC_RE.search(text_channel.topic)
            if match:
                return channel.guild.get_role(int(match.group(1)))
    return None


def is_kose_owner(member: discord.Member, channel) -> bool:
    """Üye, bu kanalın köşesinin sahibi mi? (sahip komutları için)"""
    role = get_kose_owner_role(channel)
    return role is not None and role in member.roles


class NotKoseOwner(app_commands.CheckFailure):
    pass


def kose_owner_only():
    """Sahip komutları için dekoratör: @kose_owner_only() ekle, yeter."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and is_kose_owner(
            interaction.user, interaction.channel
        ):
            return True
        raise NotKoseOwner()
    return app_commands.check(predicate)


async def create_kose(guild: discord.Guild, member: discord.Member):
    """Rol + kategori + metin kanalı + ses kanalı oluşturur. Hata olursa geri alır."""
    if len(guild.channels) > 495:
        raise RuntimeError("sunucu kanal limitine çok yakın")

    created = []
    try:
        role = await guild.create_role(
            name=f"{OWNER_ROLE_PREFIX}{member.name}"[:100],
            permissions=discord.Permissions.none(),
            reason=f"Köşe sahibi rolü: {member}",
        )
        created.append(role)
        await member.add_roles(role, reason="Köşe onaylandı")

        # Yetkiler role verilir; @everyone için bir şey değiştirmiyoruz (herkes görür/yazar)
        overwrites = {role: owner_overwrite()}

        category = await guild.create_category(
            f"Köşe • {member.display_name[:60]}",
            overwrites=overwrites,
            reason=f"Köşe: {member}",
        )
        created.append(category)

        text_channel = await category.create_text_channel(
            "sohbet",
            topic=f"{KOSE_TOPIC_TAG}:{role.id} OWNER:{member.id}",
            overwrites=overwrites,
        )
        created.append(text_channel)

        voice_channel = await category.create_voice_channel("ses", overwrites=overwrites)
        created.append(voice_channel)

        return text_channel, role
    except Exception:
        for obj in reversed(created):
            try:
                await obj.delete(reason="Köşe oluşturma başarısız, geri alınıyor")
            except Exception as cleanup_error:
                print(f"⚠️ Geri alma hatası ({obj}): {cleanup_error!r}")
        raise


async def finish_request(message: discord.Message, text: str):
    """İstek mesajını sonuçla günceller ve tepkileri temizler."""
    try:
        await message.edit(content=text, allowed_mentions=NO_PINGS)
    except Exception as e:
        print(f"⚠️ İstek mesajı düzenlenemedi: {e!r}")
    try:
        await message.clear_reactions()
    except Exception:
        pass


async def approve_request(message: discord.Message, requester_id: int, approver: discord.Member):
    guild = message.guild
    mention = f"<@{requester_id}>"

    member = guild.get_member(requester_id)
    if member is None:
        try:
            member = await guild.fetch_member(requester_id)
        except Exception:
            member = None
    if member is None:
        await finish_request(message, RESPONSES["kose_user_missing"].format(member=mention))
        return

    if has_owner_role(member):
        await finish_request(message, RESPONSES["kose_owner_exists"].format(member=mention))
        return

    try:
        text_channel, role = await create_kose(guild, member)
    except Exception as e:
        print(f"❌ Köşe oluşturulamadı: {e!r}")
        await finish_request(
            message, RESPONSES["kose_create_failed"].format(member=mention, error=e)
        )
        return

    await finish_request(
        message,
        RESPONSES["kose_approved"].format(
            member=mention, mod=approver.mention, channel=text_channel.mention
        ),
    )

    try:
        await text_channel.send(
            RESPONSES["kose_welcome"].format(member=member.mention, role=role.mention),
            allowed_mentions=discord.AllowedMentions(users=[member], roles=False, everyone=False),
        )
    except Exception as e:
        print(f"⚠️ Köşe karşılama mesajı gönderilemedi: {e!r}")


async def deny_request(message: discord.Message, requester_id: int, approver: discord.Member):
    await finish_request(
        message,
        RESPONSES["kose_denied"].format(member=f"<@{requester_id}>", mod=approver.mention),
    )


class CreateKoseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label=RESPONSES["kose_button_label"],
        style=discord.ButtonStyle.success,
        custom_id="kose:create",
    )
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        if (
            interaction.guild is None
            or interaction.guild.id != GUILD_ID
            or not isinstance(member, discord.Member)
        ):
            return

        if has_owner_role(member):
            await interaction.response.send_message(RESPONSES["kose_already_owner"], ephemeral=True)
            return
        if member.id in pending_requests:
            await interaction.response.send_message(RESPONSES["kose_already_pending"], ephemeral=True)
            return

        # Yeri hemen ayır (araya await girmeden) ki çift tıklama ikinci istek açmasın
        pending_requests[member.id] = 0
        await interaction.response.defer(ephemeral=True)

        channel = await get_channel_safe(KOSE_REQUEST_CHANNEL_ID)
        if channel is None:
            pending_requests.pop(member.id, None)
            await interaction.followup.send(RESPONSES["kose_request_error"], ephemeral=True)
            return

        request_msg = None
        try:
            request_msg = await channel.send(
                RESPONSES["kose_request_message"].format(member=member.mention),
                allowed_mentions=NO_PINGS,
            )
            await request_msg.add_reaction(APPROVE_EMOJI)
            await request_msg.add_reaction(DENY_EMOJI)
        except Exception as e:
            print(f"❌ Köşe isteği gönderilemedi: {e!r}")
            pending_requests.pop(member.id, None)
            if request_msg is not None:
                try:
                    await request_msg.delete()
                except Exception:
                    pass
            await interaction.followup.send(RESPONSES["kose_request_error"], ephemeral=True)
            return

        pending_requests[member.id] = request_msg.id
        await interaction.followup.send(RESPONSES["kose_request_sent"], ephemeral=True)


async def ensure_kose_panel():
    """Oluşturma kanalında 'olustur' butonlu mesaj yoksa gönderir."""
    channel = await get_channel_safe(KOSE_CREATE_CHANNEL_ID)
    if channel is None:
        print("⚠️ Köşe oluşturma kanalı bulunamadı.")
        return
    try:
        async for msg in channel.history(limit=50):
            if msg.author.id == bot.user.id and msg.content == RESPONSES["kose_panel_message"]:
                return
        await channel.send(RESPONSES["kose_panel_message"], view=CreateKoseView())
        print("✅ Köşe paneli gönderildi.")
    except Exception as e:
        print(f"⚠️ Köşe paneli gönderilemedi: {e!r}")


async def rebuild_pending_requests():
    """Yeniden başlatma sonrası bekleyen istekleri istek kanalından geri yükler."""
    channel = await get_channel_safe(KOSE_REQUEST_CHANNEL_ID)
    if channel is None:
        return
    pending_requests.clear()
    try:
        async for msg in channel.history(limit=200):
            if msg.author.id != bot.user.id:
                continue
            match = REQUEST_RE.fullmatch(msg.content)
            if match:
                pending_requests.setdefault(int(match.group(1)), msg.id)
        print(f"✅ {len(pending_requests)} bekleyen köşe isteği yüklendi.")
    except Exception as e:
        print(f"⚠️ Bekleyen istekler okunamadı: {e!r}")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.channel_id != KOSE_REQUEST_CHANNEL_ID or payload.guild_id != GUILD_ID:
        return
    if payload.user_id == bot.user.id:
        return
    emoji = str(payload.emoji)
    if emoji not in (APPROVE_EMOJI, DENY_EMOJI):
        return

    channel = await get_channel_safe(KOSE_REQUEST_CHANNEL_ID)
    if channel is None:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return
    if message.author.id != bot.user.id:
        return
    match = REQUEST_RE.fullmatch(message.content)
    if not match:
        return  # zaten sonuçlanmış ya da istek mesajı değil

    reactor = payload.member
    if reactor is None or reactor.bot:
        return

    if not is_moderator(reactor):
        try:
            await message.remove_reaction(payload.emoji, reactor)
        except Exception:
            pass
        return

    # Kontrol + işaretleme arasında await yok: iki moderatör aynı anda tıklasa bile tek işlem çalışır
    if message.id in handled_requests:
        return
    handled_requests.add(message.id)

    requester_id = int(match.group(1))
    if pending_requests.get(requester_id) == message.id:
        pending_requests.pop(requester_id, None)

    if emoji == APPROVE_EMOJI:
        await approve_request(message, requester_id, reactor)
    else:
        await deny_request(message, requester_id, reactor)


@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    # Moderatör istek mesajını silerse kullanıcı sonsuza kadar "bekleyen" kalmasın
    if payload.channel_id != KOSE_REQUEST_CHANNEL_ID:
        return
    for user_id, message_id in list(pending_requests.items()):
        if message_id == payload.message_id:
            pending_requests.pop(user_id, None)

# ───────────────────────────────────────────────
#  BUMP KONTROL
# ───────────────────────────────────────────────


async def perform_bump_check():
    channel = await get_channel_safe(BUMP_CHANNEL_ID)
    if channel is None:
        return "Kanal bulunamadı (ID yanlış veya bot kanalı göremiyor)"

    try:
        messages = [msg async for msg in channel.history(limit=100)]

        last_disboard_msg = next(
            (m for m in messages if m.author.id == BUMP_BOT_ID), None
        )
        if not last_disboard_msg:
            return "Disboard mesajı yok"

        # Disboard mesajından sonra bot hatırlatma attı mı?
        for msg in messages:  # yeniden eskiye
            if msg.id == last_disboard_msg.id:
                break
            if msg.author.id == bot.user.id and msg.content == config["BUMP_MESSAGE"]:
                return "Zaten hatırlatma atılmış"

        elapsed = (datetime.now(timezone.utc) - last_disboard_msg.created_at).total_seconds()

        if elapsed >= 2 * 60 * 60:
            await channel.send(config["BUMP_MESSAGE"])
            print("📢 2 saatlik süre dolmuş! Hatırlatma gönderildi.")
            return "Hatırlatma gönderildi"

        kalan = int((2 * 60 * 60 - elapsed) / 60)
        return f"Süre henüz dolmadı (~{kalan} dk kaldı)"

    except discord.Forbidden:
        return "Yetki hatası: botun kanalda 'Kanalı Gör', 'Mesaj Geçmişini Oku' ve 'Mesaj Gönder' yetkisi olmalı"
    except Exception as e:
        print(f"❌ Bump kontrolü hatası: {e}")
        return str(e)


@tasks.loop(minutes=1)
async def bump_check_loop():
    await perform_bump_check()


@bump_check_loop.before_loop
async def before_bump_check():
    await bot.wait_until_ready()

# ───────────────────────────────────────────────
#  EVENTS
# ───────────────────────────────────────────────

kose_initialized = False


@bot.event
async def on_ready():
    global kose_initialized
    print(f"✅ Giriş yapıldı: {bot.user} (ID: {bot.user.id})")
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("⚠️ Bot GUILD_ID'deki sunucuda değil veya ID yanlış!")
        return

    # Startup self-check: reports missing channels/permissions in the logs
    gp = guild.me.guild_permissions
    for perm in ("manage_channels", "manage_roles", "manage_messages"):
        if not (getattr(gp, perm) or gp.administrator):
            print(f"⚠️ Botun sunucu genelinde '{perm}' yetkisi yok (köşe sistemi için gerekli).")

    checks = {
        "Karşılama kanalı": (WELCOME_CHANNEL_ID, ["view_channel", "send_messages"]),
        "Log kanalı": (IMAGE_LOG_CHANNEL_ID, ["view_channel", "send_messages", "attach_files"]),
        "Bump kanalı": (BUMP_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Köşe oluşturma kanalı": (KOSE_CREATE_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Köşe istek kanalı": (KOSE_REQUEST_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history", "add_reactions"]),
    }
    for name, (channel_id, needed) in checks.items():
        channel = guild.get_channel(channel_id)
        if channel is None:
            print(f"⚠️ {name} ({channel_id}) bulunamadı: ID yanlış ya da bot kanalı göremiyor.")
            continue
        perms = channel.permissions_for(guild.me)
        missing = [p for p in needed if not getattr(perms, p)]
        if missing:
            print(f"⚠️ {name} (#{channel.name}) için eksik yetkiler: {', '.join(missing)}")
        else:
            print(f"✅ {name} (#{channel.name}) tamam.")

    # on_ready yeniden bağlanmalarda tekrar tetiklenir; köşe kurulumu bir kez yapılır
    if not kose_initialized:
        kose_initialized = True
        await rebuild_pending_requests()
        await ensure_kose_panel()


@bot.event
async def on_member_join(member: discord.Member):
    print(f"👋 Yeni üye: {member} (sunucu: {member.guild.id})")
    if member.guild.id != GUILD_ID:
        return

    channel = await get_channel_safe(WELCOME_CHANNEL_ID)
    if channel is None:
        print("⚠️ Karşılama kanalı bulunamadı veya botun görme yetkisi yok.")
        return

    try:
        msg = config["WELCOME_MESSAGE"].replace("{member}", member.mention)
        await channel.send(msg)
        print("✅ Karşılama mesajı gönderildi.")
    except discord.Forbidden:
        print("⚠️ Karşılama mesajı gönderilemedi: botun kanalda 'Mesaj Gönder' yetkisi yok.")
    except Exception as e:
        print(f"⚠️ Karşılama mesajı gönderilemedi: {e!r}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if (
        message.guild is not None
        and message.guild.id == GUILD_ID
        and not message.author.bot
        and message.channel.id != IMAGE_LOG_CHANNEL_ID
    ):
        if message.attachments:
            await log_media(message)
        await log_gifs(message)

    await bot.process_commands(message)


@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    # Discord, link önizlemelerini (GIF embed'lerini) mesajdan sonra düzenleme olarak ekler
    if payload.guild_id != GUILD_ID or payload.message_id in gif_logged:
        return
    if payload.channel_id == IMAGE_LOG_CHANNEL_ID:
        return
    embeds = payload.data.get("embeds") or []
    if not any(e.get("type") in ("gifv", "image") for e in embeds):
        return

    channel = await get_channel_safe(payload.channel_id)
    if channel is None:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return
    if message.author.bot:
        return
    await log_gifs(message)

# ───────────────────────────────────────────────
#  SLASH COMMANDS
# ───────────────────────────────────────────────


@bot.tree.command(name="testwelcome", description="Hoş geldin mesajını test et.")
@app_commands.checks.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
    msg = config["WELCOME_MESSAGE"].replace("{member}", interaction.user.mention)
    await interaction.response.send_message(msg)


@bot.tree.command(name="sendmsg", description="Belirli bir kanala mesaj gönder.")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, channel_id: str, message: str):
    try:
        target = await get_channel_safe(int(channel_id))
    except ValueError:
        target = None
    if target is None:
        await interaction.response.send_message(RESPONSES["sendmsg_not_found"], ephemeral=True)
        return

    try:
        await target.send(message)
        await interaction.response.send_message(RESPONSES["sendmsg_success"], ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            RESPONSES["sendmsg_error"].format(error=e), ephemeral=True
        )


@bot.tree.command(name="checkbump", description="Bump durumunu ve zamanlayıcıyı manuel test eder (Debug).")
@app_commands.checks.has_permissions(administrator=True)
async def check_bump(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result = await perform_bump_check()
    await interaction.followup.send(f"🔍 **Debug Sonucu:**\n```text\n{result}\n```", ephemeral=True)

# ───────────────────────────────────────────────
#  HATA YAKALAYICI
# ───────────────────────────────────────────────


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = RESPONSES["err_missing_permissions"]
    elif isinstance(error, NotKoseOwner):
        msg = RESPONSES["err_not_kose_owner"]
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = RESPONSES["err_cooldown"].format(retry_after=round(error.retry_after, 1))
    else:
        print(f"❌ Komut hatası: {error!r}")
        msg = RESPONSES["err_generic"].format(error=error)

    # Cevap zaten verilmişse (defer vb.) followup kullan
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# ───────────────────────────────────────────────
#  WEB SUNUCUSU (Render + UptimeRobot için)
# ───────────────────────────────────────────────


def run_web():
    from flask import Flask

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Bot aktif ve ayakta!"

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()

    if not TOKEN:
        print("HATA: DISCORD_TOKEN bulunamadı! Render > Environment kısmından ekle.")
    else:
        bot.run(TOKEN)
