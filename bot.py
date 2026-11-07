import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import re
import threading
from typing import Optional
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
    "kose_record_missing": "⚠️ Bu kategori için daha önce kayıt yok. İlk kayıtta sahip ve rol de girilmeli.",
    "kose_record_saved": "✅ Köşe kaydı log kanalına yazıldı: {category}",
    "kose_record_prefix_warning": "\n⚠️ Rol adı `[owner] - ` ile başlamıyor, yine de kaydedildi.",
    "kose_record_error": "❌ Kayıt yazılamadı: {error}",
    "kose_welcome": "{member} köşen hazır! Bu kategoride mesaj silme ve sabitleme yetkin var ({role}).\nKomutların: `/koseisim` `/kanalisim` `/kanalaciklama` `/kosedurum` `/koseizin` `/kosemute` `/koseban` `/koseunban` `/kosesil`",
    "kose_rate_limited": "⏳ Discord çok sık değişikliğe izin vermiyor, birkaç dakika sonra tekrar dene.",
    "kose_no_permission": "❌ Botun bunu yapmaya yetkisi yok.",
    "kose_edit_error": "❌ Hata oluştu: {error}",
    "kose_name_empty": "❌ Geçerli bir isim yaz.",
    "kose_izin_given": "✅ {member} artık köşen gizliyken de kanalları görebilir.",
    "kose_izin_removed": "✅ {member} için görme izni kaldırıldı.",
    "kose_izin_already": "ℹ️ {member} zaten izinli.",
    "kose_izin_none": "ℹ️ {member} için verilmiş bir izin yok.",
    "kose_izin_banned": "❌ {member} engelli. Önce `/koseunban` ile engeli kaldır.",
    "kose_mute_invalid": "❌ Kendini, bir botu ya da köşe sahibini susturamazsın.",
    "kose_mute_done": "🔇 {member} artık köşende yazamaz (kanalları görmeye devam eder).",
    "kose_mute_already": "ℹ️ {member} zaten susturulmuş.",
    "kose_unmute_done": "🔊 {member} köşende tekrar yazabilir.",
    "kose_unmute_not_muted": "ℹ️ {member} zaten susturulmuş değil.",
    "kose_category_renamed": "✅ Köşe adı güncellendi: **{name}**",
    "kose_channel_renamed": "✅ Kanal adı güncellendi: {channel}",
    "kose_channel_unsupported": "❌ Bu kanal türü bu komut için desteklenmiyor.",
    "kose_topic_updated": "✅ Kanal açıklaması güncellendi.",
    "kose_hidden": "🙈 Köşen artık herkesten gizli.",
    "kose_shown": "👀 Köşen tekrar herkese açık.",
    "kose_already_hidden": "ℹ️ Köşen zaten gizli.",
    "kose_already_visible": "ℹ️ Köşen zaten herkese açık.",
    "kose_ban_invalid": "❌ Kendini, bir botu ya da köşe sahibini engelleyemezsin.",
    "kose_ban_done": "🚫 {member} köşenden engellendi (köşen ondan gizlendi).",
    "kose_ban_already": "ℹ️ {member} zaten engelli.",
    "kose_unban_done": "✅ {member} için engel kaldırıldı.",
    "kose_unban_not_banned": "ℹ️ {member} zaten engelli değil.",
    "kose_delete_confirm": "⚠️ Köşen herkesten (senden de) gizlenip arşive taşınacak ve sahip rolün silinecek. Emin misin?",
    "kose_delete_working": "⏳ Köşe arşive taşınıyor...",
    "kose_delete_done": "🗑️ Köşe arşive taşındı. İstersen yeniden köşe isteyebilirsin.",
    "kose_delete_cancelled": "↩️ Vazgeçildi.",
    "kose_delete_unavailable": "❌ Arşiv kategorisi bulunamadı ya da dolu, köşe silinemedi.",
    "kose_delete_error": "❌ Köşe silinirken hata oluştu: {error}",
    "kose_not_yours": "Bu butonlar sana ait değil.",
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
KOSE_CATEGORY_EMOJI = "❤️"          # köşe kategorilerini ayırt etmek için
KOSE_DATA_CHANNEL_ID = 1568588462884520066  # köşe kayıtlarının yazıldığı kanal
KOSE_RECORD_SCAN_LIMIT = 3000       # açılışta kayıtlar için geriye doğru taranacak mesaj sayısı
KOSE_RECORD_TITLE = "🏡 **Köşe kaydı**"
KOSE_DELETED_TITLE = "🗑️ **Köşe silindi**"
KOSE_ANCHOR_CATEGORY_ID = 1568572007422099607   # köşeler bu kategorinin hemen altına dizilir
KOSE_ARCHIVE_CATEGORY_ID = 1506352969719873687  # silinen köşelerin kanalları buraya taşınır
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
kose_records = {}          # kategori id -> {"owner_id", "role_id", "text_id", "voice_id"}
pending_requests = {}      # kullanıcı id -> istek mesajı id
handled_requests = set()   # işlenmiş istek mesajı id'leri (çift onayı önler)

# İstek mesajını tanımak için şablondan regex üret
_req_prefix, _req_suffix = RESPONSES["kose_request_message"].split("{member}")
REQUEST_RE = re.compile(re.escape(_req_prefix) + r"<@!?(\d+)>" + re.escape(_req_suffix))
KOSE_RECORD_RE = re.compile(r"KOSE_DATA owner=(\d+) role=(\d+) category=(\d+) text=(\d+) voice=(\d+)")
KOSE_DELETED_RE = re.compile(r"KOSE_DELETED category=(\d+)")

NO_PINGS = discord.AllowedMentions.none()

# /kosemute'un kaldırdığı yazma yetkileri (görme yetkisine dokunulmaz)
MUTE_PERMS = (
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
)

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


def get_kose_record(channel):
    """Kanalın bulunduğu köşenin kaydını döndürür (köşe değilse None)."""
    if isinstance(channel, discord.CategoryChannel):
        category = channel
    else:
        category = getattr(channel, "category", None)
    if category is None:
        return None
    return kose_records.get(category.id)


def get_kose_owner_role(channel):
    """Bir kanalın bulunduğu köşenin [owner] rolünü döndürür (köşe değilse None)."""
    record = get_kose_record(channel)
    if record is None:
        return None
    return channel.guild.get_role(record["role_id"])


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


async def save_kose_record(owner_id: int, role_id: int, category_id: int, text_id: int = 0, voice_id: int = 0):
    """Köşe bilgilerini log kanalına yeni bir mesaj olarak yazar ve belleği günceller."""
    channel = await get_channel_safe(KOSE_DATA_CHANNEL_ID)
    if channel is None:
        raise RuntimeError("köşe kayıt kanalı bulunamadı")

    def ch(channel_id: int) -> str:
        return f"<#{channel_id}>" if channel_id else "—"

    content = (
        f"{KOSE_RECORD_TITLE}\n"
        f"Sahip: <@{owner_id}> (`{owner_id}`)\n"
        f"Rol: <@&{role_id}> (`{role_id}`)\n"
        f"Kategori: <#{category_id}> (`{category_id}`)\n"
        f"Metin: {ch(text_id)} (`{text_id}`) • Ses: {ch(voice_id)} (`{voice_id}`)\n"
        f"`KOSE_DATA owner={owner_id} role={role_id} category={category_id} text={text_id} voice={voice_id}`"
    )
    await channel.send(content, allowed_mentions=NO_PINGS)
    kose_records[category_id] = {
        "owner_id": owner_id,
        "role_id": role_id,
        "text_id": text_id,
        "voice_id": voice_id,
    }


async def load_kose_records():
    """Açılışta kayıt kanalındaki köşe kayıtlarını okur. Aynı kategori için en yeni mesaj geçerlidir."""
    channel = await get_channel_safe(KOSE_DATA_CHANNEL_ID)
    if channel is None:
        return
    kose_records.clear()
    seen = set()  # son durumu belli olan kategoriler (kayıt ya da silinmiş işareti)
    try:
        async for msg in channel.history(limit=KOSE_RECORD_SCAN_LIMIT):
            if msg.author.id != bot.user.id:
                continue
            if msg.content.startswith(KOSE_DELETED_TITLE):
                match = KOSE_DELETED_RE.search(msg.content)
                if match:
                    seen.add(int(match.group(1)))
                continue
            if not msg.content.startswith(KOSE_RECORD_TITLE):
                continue
            match = KOSE_RECORD_RE.search(msg.content)
            if not match:
                continue
            owner_id, role_id, category_id, text_id, voice_id = (int(g) for g in match.groups())
            if category_id in seen:
                continue
            seen.add(category_id)
            kose_records[category_id] = {
                "owner_id": owner_id,
                "role_id": role_id,
                "text_id": text_id,
                "voice_id": voice_id,
            }
        print(f"✅ {len(kose_records)} köşe kaydı yüklendi.")
    except Exception as e:
        print(f"⚠️ Köşe kayıtları okunamadı: {e!r}")


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
            f"{KOSE_CATEGORY_EMOJI} Köşe • {member.display_name[:60]}",
            overwrites=overwrites,
            reason=f"Köşe: {member}",
        )
        created.append(category)
        await place_kose_category(guild, category)

        text_channel = await category.create_text_channel("sohbet", overwrites=overwrites)
        created.append(text_channel)

        voice_channel = await category.create_voice_channel("ses", overwrites=overwrites)
        created.append(voice_channel)

        # Rol <-> kategori bağlantısı log kanalına yazılır; yazılamazsa her şey geri alınır
        await save_kose_record(member.id, role.id, category.id, text_channel.id, voice_channel.id)

        return text_channel, role
    except Exception:
        for obj in reversed(created):
            try:
                await obj.delete(reason="Köşe oluşturma başarısız, geri alınıyor")
            except Exception as cleanup_error:
                print(f"⚠️ Geri alma hatası ({obj}): {cleanup_error!r}")
        raise


def tweak_overwrite(overwrites: dict, target, **perms):
    """Overwrite sözlüğünde bir hedefin yetkilerini günceller; boş kalırsa kaldırır."""
    ow = overwrites[target] if target in overwrites else discord.PermissionOverwrite()
    ow.update(**perms)
    if ow.is_empty():
        overwrites.pop(target, None)
    else:
        overwrites[target] = ow


async def apply_to_kose(category: discord.CategoryChannel, mutate):
    """Aynı yetki değişikliğini kategoriye ve içindeki tüm kanallara uygular."""
    for ch in [category, *category.channels]:
        overwrites = dict(ch.overwrites)
        mutate(overwrites)
        await ch.edit(overwrites=overwrites)


async def run_guarded(coro, timeout: float = 30):
    """Discord isteğini zaman aşımı ve hata yakalamayla çalıştırır. Hata metni ya da None döner."""
    try:
        await asyncio.wait_for(coro, timeout)
        return None
    except asyncio.TimeoutError:
        return RESPONSES["kose_rate_limited"]
    except discord.Forbidden:
        return RESPONSES["kose_no_permission"]
    except Exception as e:
        print(f"❌ Köşe komutu hatası: {e!r}")
        return RESPONSES["kose_edit_error"].format(error=e)


def current_kose(interaction: discord.Interaction):
    """Komutun kullanıldığı kanal, kategorisi ve köşe kaydı."""
    channel = interaction.channel
    if isinstance(channel, discord.CategoryChannel):
        category = channel
    else:
        category = getattr(channel, "category", None)
    return channel, category, get_kose_record(channel)


async def place_kose_category(guild: discord.Guild, category: discord.CategoryChannel):
    """Yeni köşeyi mevcut köşelerin en altına, arşiv kategorilerinin üstüne yerleştirir."""
    try:
        anchor = guild.get_channel(KOSE_ANCHOR_CATEGORY_ID)
        if not isinstance(anchor, discord.CategoryChannel):
            print("⚠️ Köşe konum kategorisi bulunamadı, yeni köşe en altta kaldı.")
            return
        reference = anchor
        for category_id in kose_records:
            if category_id == category.id:
                continue
            other = guild.get_channel(category_id)
            if (
                isinstance(other, discord.CategoryChannel)
                and other.position > anchor.position
                and other.position > reference.position
            ):
                reference = other
        await category.move(after=reference, reason="Köşe sıralaması")
    except Exception as e:
        print(f"⚠️ Köşe kategorisi yerleştirilemedi: {e!r}")


class ArchiveUnavailable(Exception):
    pass


async def archive_kose(guild: discord.Guild, category: discord.CategoryChannel, record: dict):
    """Köşeyi silmeden arşive taşır: kanallar herkesten gizlenir, sahip rolü silinir."""
    archive = await get_channel_safe(KOSE_ARCHIVE_CATEGORY_ID)
    channels = list(category.channels)
    if not isinstance(archive, discord.CategoryChannel) or len(archive.channels) + len(channels) > 50:
        raise ArchiveUnavailable()

    category_id = category.id
    category_name = category.name

    for ch in channels:
        await ch.edit(
            category=archive,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True),
            },
            reason="Köşe silindi (arşivlendi)",
        )

    # Kayıt kanalına "silindi" işareti: yeniden başlatınca eski kayıt geçerli sayılmasın
    kose_records.pop(category_id, None)
    try:
        data_channel = await get_channel_safe(KOSE_DATA_CHANNEL_ID)
        if data_channel is not None:
            mentions = " ".join(f"<#{ch.id}>" for ch in channels) or "—"
            await data_channel.send(
                f"{KOSE_DELETED_TITLE}\n"
                f"Sahip: <@{record['owner_id']}> (`{record['owner_id']}`)\n"
                f"Kategori: **{discord.utils.escape_markdown(category_name)}** (`{category_id}`)\n"
                f"Kanallar: {mentions}\n"
                f"`KOSE_DELETED category={category_id}`",
                allowed_mentions=NO_PINGS,
            )
    except Exception as e:
        print(f"⚠️ Silinme kaydı yazılamadı: {e!r}")

    role = guild.get_role(record["role_id"])
    if role is not None:
        try:
            await role.delete(reason="Köşe silindi")
        except Exception as e:
            print(f"⚠️ Sahip rolü silinemedi: {e!r}")
    try:
        await category.delete(reason="Köşe silindi (boş kategori)")
    except Exception as e:
        print(f"⚠️ Boş köşe kategorisi silinemedi: {e!r}")


class ConfirmDeleteView(discord.ui.View):
    def __init__(self, invoker_id: int, category_id: int):
        super().__init__(timeout=60)
        self.invoker_id = invoker_id
        self.category_id = category_id
        self.done = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(RESPONSES["kose_not_yours"], ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Evet, sil", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.done:
            return
        self.done = True
        self.stop()
        await interaction.response.edit_message(content=RESPONSES["kose_delete_working"], view=None)

        guild = interaction.guild
        category = guild.get_channel(self.category_id) if guild else None
        record = kose_records.get(self.category_id)
        if (
            not isinstance(category, discord.CategoryChannel)
            or record is None
            or not is_kose_owner(interaction.user, category)
        ):
            await interaction.edit_original_response(content=RESPONSES["err_not_kose_owner"])
            return

        try:
            await archive_kose(guild, category, record)
        except ArchiveUnavailable:
            await interaction.edit_original_response(content=RESPONSES["kose_delete_unavailable"])
        except Exception as e:
            print(f"❌ Köşe arşivlenemedi: {e!r}")
            await interaction.edit_original_response(
                content=RESPONSES["kose_delete_error"].format(error=e)
            )
        else:
            await interaction.edit_original_response(content=RESPONSES["kose_delete_done"])

    @discord.ui.button(label="Vazgeç", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.done = True
        self.stop()
        await interaction.response.edit_message(content=RESPONSES["kose_delete_cancelled"], view=None)


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
        "Köşe kayıt kanalı": (KOSE_DATA_CHANNEL_ID, ["view_channel", "send_messages", "read_message_history"]),
        "Köşe konum kategorisi": (KOSE_ANCHOR_CATEGORY_ID, ["view_channel", "manage_channels"]),
        "Köşe arşiv kategorisi": (KOSE_ARCHIVE_CATEGORY_ID, ["view_channel", "manage_channels"]),
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
        await load_kose_records()
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


# ── Köşe sahibi komutları (sadece kendi köşesinde, rolü olan kişi kullanabilir) ──


@bot.tree.command(name="koseisim", description="Köşenin kategori adını değiştirir.")
@app_commands.describe(isim="Yeni kategori adı")
@kose_owner_only()
async def kose_isim(interaction: discord.Interaction, isim: app_commands.Range[str, 1, 100]):
    _, category, _ = current_kose(interaction)
    new_name = isim.strip()
    if not new_name:
        await interaction.response.send_message(RESPONSES["kose_name_empty"], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(category.edit(name=new_name, reason=f"/koseisim: {interaction.user}"))
    await interaction.followup.send(
        error or RESPONSES["kose_category_renamed"].format(name=new_name), ephemeral=True
    )


@bot.tree.command(name="kanalisim", description="Komutu kullandığın kanalın adını değiştirir.")
@app_commands.describe(isim="Yeni kanal adı")
@kose_owner_only()
async def kanal_isim(interaction: discord.Interaction, isim: app_commands.Range[str, 1, 100]):
    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
        await interaction.response.send_message(RESPONSES["kose_channel_unsupported"], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(channel.edit(name=isim.strip(), reason=f"/kanalisim: {interaction.user}"))
    await interaction.followup.send(
        error or RESPONSES["kose_channel_renamed"].format(channel=channel.mention), ephemeral=True
    )


@bot.tree.command(name="kanalaciklama", description="Komutu kullandığın kanalın açıklamasını değiştirir.")
@app_commands.describe(aciklama="Yeni kanal açıklaması")
@kose_owner_only()
async def kanal_aciklama(interaction: discord.Interaction, aciklama: app_commands.Range[str, 1, 1024]):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(RESPONSES["kose_channel_unsupported"], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(channel.edit(topic=aciklama, reason=f"/kanalaciklama: {interaction.user}"))
    await interaction.followup.send(error or RESPONSES["kose_topic_updated"], ephemeral=True)


@bot.tree.command(name="kosedurum", description="Köşeni herkesten gizle ya da tekrar göster.")
@app_commands.describe(durum="goster ya da gizle")
@app_commands.choices(durum=[
    app_commands.Choice(name="goster", value="goster"),
    app_commands.Choice(name="gizle", value="gizle"),
])
@kose_owner_only()
async def kose_durum(interaction: discord.Interaction, durum: app_commands.Choice[str]):
    _, category, record = current_kose(interaction)
    guild = interaction.guild
    want_hidden = durum.value == "gizle"
    hidden_now = category.overwrites_for(guild.default_role).view_channel is False

    if want_hidden == hidden_now:
        key = "kose_already_hidden" if hidden_now else "kose_already_visible"
        await interaction.response.send_message(RESPONSES[key], ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    owner_role = guild.get_role(record["role_id"])

    def mutate(overwrites):
        tweak_overwrite(overwrites, guild.default_role, view_channel=False if want_hidden else None)
        if owner_role is not None:
            tweak_overwrite(overwrites, owner_role, view_channel=True if want_hidden else None)
        if want_hidden:
            tweak_overwrite(overwrites, guild.me, view_channel=True)  # bot kanalı görmeye devam etsin

    error = await run_guarded(apply_to_kose(category, mutate), timeout=60)
    await interaction.followup.send(
        error or RESPONSES["kose_hidden" if want_hidden else "kose_shown"], ephemeral=True
    )


@bot.tree.command(name="koseban", description="Bir kişiyi köşenden engeller (köşeni ondan gizler).")
@app_commands.describe(kullanici="Engellenecek kişi")
@kose_owner_only()
async def kose_ban(interaction: discord.Interaction, kullanici: discord.Member):
    _, category, record = current_kose(interaction)
    guild = interaction.guild
    owner_role = guild.get_role(record["role_id"])

    if (
        kullanici.bot
        or kullanici.id == interaction.user.id
        or kullanici.id == record["owner_id"]
        or (owner_role is not None and owner_role in kullanici.roles)
    ):
        await interaction.response.send_message(RESPONSES["kose_ban_invalid"], ephemeral=True)
        return
    if category.overwrites_for(kullanici).view_channel is False:
        await interaction.response.send_message(
            RESPONSES["kose_ban_already"].format(member=kullanici.mention), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(
        apply_to_kose(category, lambda ov: tweak_overwrite(ov, kullanici, view_channel=False)),
        timeout=60,
    )
    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    # Köşenin ses kanalındaysa bağlantısını kes
    voice = kullanici.voice
    if voice is not None and voice.channel is not None and voice.channel.category_id == category.id:
        try:
            await kullanici.move_to(None, reason="Köşeden engellendi")
        except Exception:
            pass

    await interaction.followup.send(
        RESPONSES["kose_ban_done"].format(member=kullanici.mention), ephemeral=True
    )


@bot.tree.command(name="koseunban", description="Köşenden engellediğin kişinin engelini kaldırır.")
@app_commands.describe(kullanici="Engeli kaldırılacak kişi")
@kose_owner_only()
async def kose_unban(interaction: discord.Interaction, kullanici: discord.Member):
    _, category, _ = current_kose(interaction)

    if category.overwrites_for(kullanici).view_channel is not False:
        await interaction.response.send_message(
            RESPONSES["kose_unban_not_banned"].format(member=kullanici.mention), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    error = await run_guarded(
        apply_to_kose(category, lambda ov: tweak_overwrite(ov, kullanici, view_channel=None)),
        timeout=60,
    )
    await interaction.followup.send(
        error or RESPONSES["kose_unban_done"].format(member=kullanici.mention), ephemeral=True
    )


@bot.tree.command(name="koseizin", description="Köşen gizliyken de kanalları görebilecek kişi ekler (ya da kaldırır).")
@app_commands.describe(kullanici="İzin verilecek kişi", islem="ver (varsayılan) ya da kaldir")
@app_commands.choices(islem=[
    app_commands.Choice(name="ver", value="ver"),
    app_commands.Choice(name="kaldir", value="kaldir"),
])
@kose_owner_only()
async def kose_izin(
    interaction: discord.Interaction,
    kullanici: discord.Member,
    islem: Optional[app_commands.Choice[str]] = None,
):
    _, category, _ = current_kose(interaction)
    removing = islem is not None and islem.value == "kaldir"
    current = category.overwrites_for(kullanici).view_channel

    if current is False:
        # Engelli kişinin yetkisine dokunma: engeli /koseunban kaldırır
        await interaction.response.send_message(
            RESPONSES["kose_izin_banned"].format(member=kullanici.mention), ephemeral=True
        )
        return
    if removing and current is not True:
        await interaction.response.send_message(
            RESPONSES["kose_izin_none"].format(member=kullanici.mention), ephemeral=True
        )
        return
    if not removing and current is True:
        await interaction.response.send_message(
            RESPONSES["kose_izin_already"].format(member=kullanici.mention), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    value = None if removing else True
    error = await run_guarded(
        apply_to_kose(category, lambda ov: tweak_overwrite(ov, kullanici, view_channel=value)),
        timeout=60,
    )
    key = "kose_izin_removed" if removing else "kose_izin_given"
    await interaction.followup.send(
        error or RESPONSES[key].format(member=kullanici.mention), ephemeral=True
    )


@bot.tree.command(name="kosemute", description="Bir kişinin köşende yazmasını engeller (kanalları görmeye devam eder).")
@app_commands.describe(kullanici="Susturulacak kişi", islem="mute (varsayılan) ya da unmute")
@app_commands.choices(islem=[
    app_commands.Choice(name="mute", value="mute"),
    app_commands.Choice(name="unmute", value="unmute"),
])
@kose_owner_only()
async def kose_mute(
    interaction: discord.Interaction,
    kullanici: discord.Member,
    islem: Optional[app_commands.Choice[str]] = None,
):
    _, category, record = current_kose(interaction)
    guild = interaction.guild
    unmuting = islem is not None and islem.value == "unmute"
    owner_role = guild.get_role(record["role_id"])

    if (
        kullanici.bot
        or kullanici.id == interaction.user.id
        or kullanici.id == record["owner_id"]
        or (owner_role is not None and owner_role in kullanici.roles)
    ):
        await interaction.response.send_message(RESPONSES["kose_mute_invalid"], ephemeral=True)
        return

    muted_now = category.overwrites_for(kullanici).send_messages is False
    if unmuting and not muted_now:
        await interaction.response.send_message(
            RESPONSES["kose_unmute_not_muted"].format(member=kullanici.mention), ephemeral=True
        )
        return
    if not unmuting and muted_now:
        await interaction.response.send_message(
            RESPONSES["kose_mute_already"].format(member=kullanici.mention), ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    value = None if unmuting else False
    perms = {name: value for name in MUTE_PERMS}
    error = await run_guarded(
        apply_to_kose(category, lambda ov: tweak_overwrite(ov, kullanici, **perms)),
        timeout=60,
    )
    key = "kose_unmute_done" if unmuting else "kose_mute_done"
    await interaction.followup.send(
        error or RESPONSES[key].format(member=kullanici.mention), ephemeral=True
    )


@bot.tree.command(name="kosesil", description="Köşeni arşive kaldırır (herkesten gizlenir, sahip rolü silinir).")
@kose_owner_only()
async def kose_sil(interaction: discord.Interaction):
    _, category, _ = current_kose(interaction)
    view = ConfirmDeleteView(interaction.user.id, category.id)
    await interaction.response.send_message(RESPONSES["kose_delete_confirm"], view=view, ephemeral=True)


# ── Yönetici komutları ──


@bot.tree.command(name="kosekaydet", description="Köşe bilgilerini (eksik id'leri) log kanalına yeni kayıt olarak yazar.")
@app_commands.describe(
    kategori="Köşe kategorisi",
    sahip="Köşe sahibi (boş bırakırsan eski kayıttan alınır)",
    rol="Köşenin [owner] rolü (boş bırakırsan eski kayıttan alınır)",
)
@app_commands.checks.has_permissions(administrator=True)
async def kose_kaydet(
    interaction: discord.Interaction,
    kategori: discord.CategoryChannel,
    sahip: Optional[discord.Member] = None,
    rol: Optional[discord.Role] = None,
):
    old = kose_records.get(kategori.id, {})
    owner_id = sahip.id if sahip else old.get("owner_id")
    role_id = rol.id if rol else old.get("role_id")
    if not owner_id or not role_id:
        await interaction.response.send_message(RESPONSES["kose_record_missing"], ephemeral=True)
        return

    # Eksik kanal id'leri kategorinin içinden tamamlanır
    text_id = old.get("text_id") or (kategori.text_channels[0].id if kategori.text_channels else 0)
    voice_id = old.get("voice_id") or (kategori.voice_channels[0].id if kategori.voice_channels else 0)

    await interaction.response.defer(ephemeral=True)
    try:
        await save_kose_record(owner_id, role_id, kategori.id, text_id, voice_id)
    except Exception as e:
        await interaction.followup.send(RESPONSES["kose_record_error"].format(error=e), ephemeral=True)
        return

    reply = RESPONSES["kose_record_saved"].format(category=kategori.mention)
    role_obj = interaction.guild.get_role(role_id)
    if role_obj is None or not role_obj.name.startswith(OWNER_ROLE_PREFIX):
        reply += RESPONSES["kose_record_prefix_warning"]
    await interaction.followup.send(reply, ephemeral=True)


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
