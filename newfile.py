import telebot
import requests
import os
import base64
import json
import logging
import random
import string
from datetime import datetime
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- Veritabanı Yapısı --- #
KULLANICI_DB = "kullanicilarr.json"
VIP_DB = "viip.json"
SORGULOG_DB = "sorguu_loglari.json"
ANAHTAR_DB = "anahtarlar.json"
BAN_DB = 'Banlistts.json'
LOG_CHANNEL = -1002746297023  # Log kanalı ID
ADMIN_IDS = [7775769727]  # Admin ID'leri
ZORUNLU_KANAL = "@lethanarsivs"
BOT_TOKEN = "7761053662:AAGWGgVsHAZuTd3oIc9PP2n4VIfPpbSSLeE"

# --- Sorgu Limitleri --- #
STANDART_LIMIT = 5
VIP_LIMIT = 100
gecici_duyurular = {}

# --- Loglama --- #
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

bot = telebot.TeleBot(BOT_TOKEN)

# --- Emoji Haritası --- #
EMOJI_MAP = {
    'ad': '👤',
    'soyad': '👤',
    'tam_ad': '👤',
    'tc': '🆔',
    'telefon': '📱',
    'gsm': '📱',
    'adres': '🏠',
    'dogum_tarihi': '📅',
    'dogum_tarih': '📅',
    'il': '📍',
    'ilce': '📍',
    'aile': '👨‍👩‍👧‍👦',
    'anne': '👩',
    'baba': '👨',
    'kardesler': '👫',
    'kardes': '👫',
    'es': '💍',
    'esler': '💍',
    'cep_tel': '📱',
    'ev_tel': '📞',
    'is_tel': '🏢',
    'eposta': '📧',
    'email': '📧',
    'okul': '🏫',
    'okul_no': '🎓',
    'sinif': '🎒',
    'bolum': '📚',
    'fakulte': '🎓',
    'universite': '🎓',
    'isyeri': '🏢',
    'meslek': '💼',
    'ehliyet': '📜',
    'ehliyet_no': '📜',
    'ehliyet_sinif': '🚗',
    'verilis_tarihi': '📅',
    'gecerlilik_tarihi': '📅',
    'vesika': '🖼️',
    'resim': '🖼️',
    'foto': '🖼️',
    'ip': '🌐',
    'domain': '🌐',
    'ulke': '🌍',
    'sehir': '🏙️',
    'il_plaka': '🚗',
    'kayitli_il': '🏠',
    'kayitli_ilce': '🏠',
    'kayitli_mahalle': '🏠',
    'kayitli_sokak': '🏠',
    'kayitli_no': '🏠',
}

# --- Veritabanı Yardımcıları --- #
def veritabani_yukle(dosya_adi, varsayilan=[]):
    if os.path.exists(dosya_adi):
        try:
            with open(dosya_adi, 'r') as f:
                return json.load(f)
        except:
            return varsayilan
    return varsayilan

def veritabani_kaydet(dosya_adi, veri):
    with open(dosya_adi, 'w') as f:
        json.dump(veri, f)

# --- Premium Sistemi --- #
def kullanici_premium_mu(user_id):
    vip_listesi = veritabani_yukle(VIP_DB, [])
    return str(user_id) in vip_listesi

def bugunku_sorgu_sayisi(user_id):
    logs = veritabani_yukle(SORGULOG_DB, [])
    bugun = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for log in logs if log.get('user_id') == str(user_id) and log.get('tarih') == bugun)

def sorgu_limiti(user_id):
    return VIP_LIMIT if kullanici_premium_mu(user_id) else STANDART_LIMIT

def kalan_sorgu(user_id):
    return sorgu_limiti(user_id) - bugunku_sorgu_sayisi(user_id)

def sorgu_logla(user_id):
    logs = veritabani_yukle(SORGULOG_DB, [])
    logs.append({
        'user_id': str(user_id),
        'tarih': datetime.now().strftime("%Y-%m-%d"),
        'zaman': datetime.now().strftime("%H:%M:%S")
    })
    veritabani_kaydet(SORGULOG_DB, logs)

# --- Decorators --- #
# --- Ban Sistemi --- #
def kullanici_banli_mi(user_id):
    ban_listesi = veritabani_yukle(BAN_DB, [])
    return str(user_id) in ban_listesi

# --- Decorators --- #
def ban_kontrol(func):
    def wrapper(message):
        user_id = message.from_user.id
        
        # Adminler için bypass
        if user_id in ADMIN_IDS:
            return func(message)
            
        if kullanici_banli_mi(user_id):
            bot.reply_to(
                message,
                "⛔ <b>HESABINIZ BANLANDI!</b>\n\n"
                "Bu botu kullanma yetkiniz bulunmamaktadır.\n\n"
                "• Tüm sorgu komutları devre dışı\n"
                "• Menü erişimi engellendi\n"
                "• Premium özellikler kullanılamaz\n\n"
                "İtiraz için destek ekibiyle iletişime geçin.",
                parse_mode="HTML"
            )
            return
        return func(message)
    return wrapper

def kanal_gerekli(func):
    def wrapper(message):
        try:
            user_id = message.from_user.id
            chat_member = bot.get_chat_member(ZORUNLU_KANAL, user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("✨ Kanala Katıl", url=f"https://t.me/{ZORUNLU_KANAL[1:]}"))
                bot.reply_to(message, f"🔒 Önce {ZORUNLU_KANAL} kanalına katılmalısınız!", reply_markup=kb)
                return
        except Exception as e:
            logging.error(f"Kanal kontrol hatası: {str(e)}")
        return func(message)
    return wrapper

def sorgu_limiti_kontrol(func):
    def wrapper(message):
        user_id = message.from_user.id
        if bugunku_sorgu_sayisi(user_id) >= sorgu_limiti(user_id):
            bot.reply_to(
                message,
                f"⚠️ Sorgu limitiniz doldu! (Günlük limit: {sorgu_limiti(user_id)})\n\n"
                "💎 Premium olmak için /premium komutunu kullanabilirsiniz."
            )
            return
        sorgu_logla(user_id)
        return func(message)
    return wrapper

# --- Menü Sistemleri --- #
def ana_menu(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Kullanıcıyı kaydet
    users = veritabani_yukle(KULLANICI_DB, [])
    if str(user_id) not in users:
        users.append(str(user_id))
        veritabani_kaydet(KULLANICI_DB, users)
        bot.send_message(LOG_CHANNEL, f"🌟 Yeni kullanıcı: {user_id} - {first_name}")
    
    # Premium durum
    premium_durum = "💎 PREMIUM" if kullanici_premium_mu(user_id) else "🔓 STANDART"
    
    # Inline keyboard oluştur
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 Sorgu Komutları", callback_data="komutlar"),
        InlineKeyboardButton("✨ Premium Bilgi", callback_data="premium"),
        InlineKeyboardButton("📊 İstatistiklerim", callback_data="istatistikler")
    )
    keyboard.add(InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{ZORUNLU_KANAL[1:]}"))
    
    text = (
        f"👋 Merhaba {first_name}!\n\n"
        f"🔹 Hesap Durumu: {premium_durum}\n"
        f"🔸 Bugünkü Sorgu: {bugunku_sorgu_sayisi(user_id)}/{sorgu_limiti(user_id)}\n"
        f"🔄 Kalan Sorgu: {kalan_sorgu(user_id)}\n\n"
        "Aşağıdaki menüden işlem seçebilirsiniz:"
    )
    
    if hasattr(message, 'message_id'):
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                reply_markup=keyboard
            )
        except:
            bot.send_message(message.chat.id, text, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, text, reply_markup=keyboard)

def komutlar_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔍 Temel Sorgular", callback_data="temel_sorgular"),
        InlineKeyboardButton("💎 Premium Sorgular", callback_data="premium_sorgular"),
        InlineKeyboardButton("🌐 Diğer Araçlar", callback_data="diger_araclar"),
        InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")
    )
    
    text = (
        "📜 <b>SORGULAMA MENÜSÜ</b> 📜\n\n"
        "Aşağıdaki kategorilerden sorgu türünü seçin:\n\n"
        "🔍 <b>Temel Sorgular</b> - Ücretsiz sorgular\n"
        "💎 <b>Premium Sorgular</b> - VIP üyelere özel\n"
        "🌐 <b>Diğer Araçlar</b> - Yardımcı araçlar"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def temel_sorgular_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Geri", callback_data="komutlar"))
    
    text = (
        "🔍 <b>TEMEL SORGULAR</b>\n\n"
        "/tc <code>kimlik no</code> - TC Kimlik Sorgusu\n"
        "/adsoyad <code>ad soyad</code> - Ad Soyad Sorgusu\n"
        "/adsoyad2 <code>ad soyad il ilçe</code> - Detaylı Ad Soyad Sorgusu\n"
        "/aile <code>tc</code> - Aile Sorgusu\n"
        "/sulale <code>tc</code> - Sülale Sorgusu\n"
        "/adres <code>tc</code> - Adres Sorgusu\n"
        "/tcgsm <code>tc</code> - TC'den GSM Sorgusu\n"
        "/gsmtc <code>gsm</code> - GSM'den TC Sorgusu\n"
        "/sgk <code>tc</code> - SGK Sorgusu\n"
        "/tapu <code>tc</code> - Tapu Sorgusu\n"
        "/okulno <code>tc</code> - Okul Numarası Sorgusu\n\n"
        "💡 <i>Komutları kullanmak için / ile başlayın</i>"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def premium_sorgular_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Geri", callback_data="komutlar"))
    
    text = (
        "💎 <b>PREMIUM SORGULAR</b>\n\n"
        "/isyeri <code>tc</code> - İş Yeri Sorgusu\n"
        "/ehliyet <code>tc</code> - Ehliyet Sorgusu\n"
        "/vesika <code>tc</code> - Vesika Sorgusu\n\n"
        "🔒 Bu sorgular sadece premium üyelere açıktır\n"
        "✨ Premium olmak için /premium komutunu kullanın"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def diger_araclar_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Geri", callback_data="komutlar"))
    
    text = (
        "🌐 <b>DİĞER ARAÇLAR</b>\n\n"
        "/kamera - Kamera Bağlantısı Oluştur\n"
        "/pubg - PUBG Pishing Bağlantısı\n"
        "/ip <code>ip</code> - IP Sorgulama\n"
        "/domain <code>domain</code> - Domain Sorgulama\n"
        "/gpt <code>soru</code> - GPT Sorusu\n"
        "/wormgpt <code>soru</code> - WormGPT Sorusu\n\n"
        "💡 <i>Komutları kullanmak için / ile başlayın</i>"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def premium_menu(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Satın Al", url="https://t.me/isteme"),
        InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")
    )
    
    text = (
        "✨ <b>PREMIUM ÜYELİK AVANTAJLARI</b> ✨\n\n"
        "✅ Günlük sorgu limiti: <b>100</b>\n"
        "🔓 Özel premium sorgulara erişim\n"
        "⚡ Öncelikli API erişimi\n\n"
        "💎 <b>FİYATLANDIRMA</b>\n"
        "• 1 Aylık Premium: <b>150 TL</b>\n"
        "• 3 Aylık Premium: <b>400 TL</b>\n"
        "• Ömür Boyu Premium: <b>1000 TL</b>\n\n"
        "Satın almak için aşağıdaki butonu kullanın:"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def istatistikler_menu(message):
    user_id = message.from_user.id
    premium_durum = "💎 Aktif" if kullanici_premium_mu(user_id) else "🔓 Aktif Değil"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 Yenile", callback_data="istatistikler"))
    keyboard.add(InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu"))
    
    text = (
        f"📊 <b>SORGULAMA İSTATİSTİKLERİNİZ</b>\n\n"
        f"🌟 Premium Durumu: {premium_durum}\n"
        f"📅 Bugünkü Sorgular: <b>{bugunku_sorgu_sayisi(user_id)}/{sorgu_limiti(user_id)}</b>\n"
        f"🔄 Kalan Sorgu Hakkı: <b>{kalan_sorgu(user_id)}</b>\n"
        f"⏱ Son Güncelleme: <code>{datetime.now().strftime('%H:%M:%S')}</code>"
    )
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# --- Komutlar --- #
@bot.message_handler(commands=['start'])
@kanal_gerekli
def start_handler(message):
    ana_menu(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "ana_menu":
            ana_menu(call.message)
        elif call.data == "komutlar":
            komutlar_menu(call.message)
        elif call.data == "temel_sorgular":
            temel_sorgular_menu(call.message)
        elif call.data == "premium_sorgular":
            premium_sorgular_menu(call.message)
        elif call.data == "diger_araclar":
            diger_araclar_menu(call.message)
        elif call.data == "premium":
            premium_menu(call.message)
        elif call.data == "istatistikler":
            istatistikler_menu(call.message)
    except Exception as e:
        logging.error(f"Menü hatası: {str(e)}")
    bot.answer_callback_query(call.id)

# --- Admin Komutları --- #
@bot.message_handler(commands=['anahtar'])
def anahtar_handler(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")
    
    # Anahtar oluştur
    anahtar = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    
    # Kaydet
    anahtarlar = veritabani_yukle(ANAHTAR_DB, {})
    anahtarlar[anahtar] = "kullanilmadi"
    veritabani_kaydet(ANAHTAR_DB, anahtarlar)
    
    bot.reply_to(
        message,
        f"🔑 <b>YENİ PREMIUM ANAHTARI</b>\n\n"
        f"<code>{anahtar}</code>\n\n"
        "Bu anahtar tek seferlik kullanım içindir.",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['toplam'])
def toplam_handler(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")
    
    users = veritabani_yukle(KULLANICI_DB, [])
    vips = veritabani_yukle(VIP_DB, [])
    bugun = datetime.now().strftime("%Y-%m-%d")
    sorgular = sum(1 for log in veritabani_yukle(SORGULOG_DB, []) if log.get('tarih') == bugun)
    
    bot.reply_to(
        message,
        f"📊 <b>BOT İSTATİSTİKLERİ</b>\n\n"
        f"👥 Toplam Kullanıcı: <b>{len(users)}</b>\n"
        f"💎 Premium Üye: <b>{len(vips)}</b>\n"
        f"🔍 Bugünkü Sorgular: <b>{sorgular}</b>",
        parse_mode="HTML"
    )

# --- Gelişmiş Sorgu Formatlama --- #
def format_sonuc(data, sorgu_turu):
    """Sorgu sonuçlarını emojili ve düzenli şekilde formatlar"""
    try:
        # Başlık oluştur
        emoji_baslik = {
            'tc': '🆔 TC Kimlik Sorgusu',
            'adsoyad': '👤 Ad Soyad Sorgusu',
            'adsoyad2': '👤 Detaylı Ad Soyad Sorgusu',
            'aile': '👨‍👩‍👧‍👦 Aile Sorgusu',
            'sulale': '🧬 Sülale Sorgusu',
            'adres': '🏠 Adres Sorgusu',
            'sgk': '🏥 SGK Sorgusu',
            'tapu': '🏡 Tapu Sorgusu',
            'okulno': '🎓 Okul Numarası Sorgusu',
            'tcgsm': '📱 TCden GSM Sorgusu',
            'gsmtc': '📱 GSMden TC Sorgusu',
            'isyeri': '🏢 İş Yeri Sorgusu',
            'ehliyet': '📜 Ehliyet Sorgusu',
            'vesika': '🖼️ Vesika Sorgusu',
            'ip': '🌐 IP Sorgusu',
            'domain': '🌐 Domain Sorgusu',
        }.get(sorgu_turu, f'🔍 {sorgu_turu.capitalize()} Sorgusu')
        
        sonuc = f"✨ <b>{emoji_baslik}</b>\n\n"
        
        # Eğer liste şeklinde sonuç geldiyse (aile, sülale gibi)
        if isinstance(data, list):
            for idx, item in enumerate(data, 1):
                sonuc += f"🔹 <b>Kayıt #{idx}</b>\n"
                for key, value in item.items():
                    emoji = EMOJI_MAP.get(key.lower(), 'ℹ️')
                    key_formatted = key.replace('_', ' ').title()
                    sonuc += f"{emoji} <b>{key_formatted}:</b> {value}\n"
                sonuc += "\n"
        
        # Tek sonuç geldiyse
        elif isinstance(data, dict):
            for key, value in data.items():
                emoji = EMOJI_MAP.get(key.lower(), 'ℹ️')
                key_formatted = key.replace('_', ' ').title()
                sonuc += f"{emoji} <b>{key_formatted}:</b> {value}\n"
        
        # Diğer formatlar
        else:
            sonuc += str(data)
        
        sonuc += f"\n🔎 @{bot.get_me().username}"
        return sonuc
    
    except Exception as e:
        logging.error(f"Formatlama hatası: {str(e)}")
        return f"⚠️ Sonuç formatlanırken hata oluştu: {str(e)}"

# --- Sorgu Komutları --- #
def api_sorgu_ve_gonder(message, url, cmd_name, caption):
    try:
        r = requests.get(url)
        r.raise_for_status()
        j = r.json()
        
        # API yanıt formatlarını işle
        if 'data' in j and j['data']:
            res = j['data']
        elif isinstance(j, list) and j:
            res = j
        elif isinstance(j, dict) and j.get('success', True):
            res = j
        else:
            bot.reply_to(message, "🔍 Sonuç bulunamadı.")
            return
        
        # Sonuçları formatla
        formatted = format_sonuc(res, cmd_name)
        
        # Eğer sonuç çok uzunsa dosya olarak gönder
        if len(formatted) > 2000:
            filename = f"{cmd_name}_sonuclari.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(formatted)
            
            with open(filename, 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"🔍 {caption} - Sonuçlar dosya olarak gönderildi",
                    reply_to_message_id=message.message_id
                )
            
            os.remove(filename)
        else:
            bot.reply_to(
                message, 
                formatted, 
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Sorgu hatası: {str(e)}")

# --- Temel Sorgu Komutları --- #
@bot.message_handler(commands=['adsoyad','adsoyad2'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def adsoyad_sorgu(message):
    parts = message.text.split()
    cmd = parts[0]
    args = parts[1:]
    
    if len(args) < 2:
        bot.reply_to(message, f"⚠️ Geçersiz format! Doğru kullanım:\n<code>{cmd} ad soyad</code>", parse_mode="HTML")
        return
    
    ad, soyad = (" ".join(args[:-1]), args[-1]) if cmd == '/adsoyad2' else (args[0], args[1])
    il = args[2] if len(args) > 2 else ""
    ilce = args[3] if len(args) > 3 else ""
    
    url = f"http://ramowlf.site/ramowlf/adsoyad.php?ad={ad}&soyad={soyad}&il={il}&ilce={ilce}"
    api_sorgu_ve_gonder(message, url, "adsoyad", "Ad Soyad Sorgu Sonuçları")

@bot.message_handler(commands=['tc','aile','sulale','adres','sgk','tapu','okulno','tcgsm','gsmtc'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def tek_sorgular(message):
    cmd = message.text.split()[0].lstrip('/')
    val = message.text.split()[1] if len(message.text.split()) > 1 else ''
    
    if not val:
        bot.reply_to(message, f"⚠️ Geçersiz format! Doğru kullanım:\n<code>/{cmd} deger</code>", parse_mode="HTML")
        return
    
    param_name = 'gsm' if cmd == 'gsmtc' else 'tc'
    url = f"http://ramowlf.site/ramowlf/{cmd}.php?{param_name}={val}"
    api_sorgu_ve_gonder(message, url, cmd, f"{cmd} Sorgu Sonuçları")

# --- Premium Sorgular --- #
@bot.message_handler(commands=['isyeri','ehliyet','vesika'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def premium_sorgular(message):
    user_id = message.from_user.id
    if not kullanici_premium_mu(user_id):
        bot.reply_to(
            message,
            "🔒 Bu özellik sadece premium üyeler içindir!\n\n"
            "💎 Premium olmak için /premium komutunu kullanabilirsiniz."
        )
        return
    
    cmd = message.text.split()[0].lstrip('/')
    val = message.text.split()[1] if len(message.text.split()) > 1 else ''
    
    if not val:
        bot.reply_to(message, f"⚠️ Geçersiz format! Doğru kullanım:\n<code>/{cmd} deger</code>", parse_mode="HTML")
        return
    
    url = f"http://ramowlf.site/ramowlf/{cmd}.php?tc={val}"
    api_sorgu_ve_gonder(message, url, cmd, f"Premium {cmd} Sorgu Sonuçları")

# --- Diğer Komutlar --- #
@bot.message_handler(commands=['gpt','wormgpt'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def gpt_sorgu(message):
    cmd = message.text.split()[0].lstrip('/')
    qry = " ".join(message.text.split()[1:])
    
    if not qry: 
        bot.reply_to(message, f"⚠️ Geçersiz format! Doğru kullanım:\n<code>/{cmd} soru</code>", parse_mode="HTML")
        return
    
    endpoint = "gpt" if cmd == "gpt" else "wormgpt"
    url = f"http://ramowlf.site/ramowlf/{endpoint}.php?msg={qry}"
    
    try:
        rep = requests.get(url).json()
        text = rep.get('reply') if endpoint == 'gpt' else rep.get('yanit')
        
        # Yanıtı formatla
        formatted = f"🧠 <b>{'GPT' if endpoint == 'gpt' else 'WormGPT'} Yanıtı</b>\n\n"
        formatted += f"❓ <b>Soru:</b> {qry}\n\n"
        formatted += f"💡 <b>Yanıt:</b>\n{text}\n\n"
        formatted += f"🔎 @{bot.get_me().username}"
        
        bot.reply_to(message, formatted, parse_mode="HTML")
    except:
        bot.reply_to(message, "⚠️ API hatası")

@bot.message_handler(commands=['ip','domain'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def ip_domain_sorgu(message):
    cmd = message.text.split()[0].lstrip('/')
    val = message.text.split()[1] if len(message.text.split()) > 1 else ''
    
    if not val:
        bot.reply_to(message, f"⚠️ Geçersiz format! Doğru kullanım:\n<code>/{cmd} deger</code>", parse_mode="HTML")
        return
    
    param = "ip" if cmd == "ip" else "domain"
    url = f"https://ramowlf.site/ramowlf/ipapi.php?{param}={val}"
    
    try:
        response = requests.get(url)
        data = response.json()
        client_data = data.get("data", {})
        
        # Formatla ve gönder
        formatted = format_sonuc(client_data, cmd)
        bot.reply_to(message, formatted, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"⚠️ {cmd} sorgu hatası: {str(e)}")

@bot.message_handler(commands=['vesika'])
@kanal_gerekli
@sorgu_limiti_kontrol
@ban_kontrol
def vesika_sorgu(message):
    tcs = message.text.split()[1] if len(message.text.split()) > 1 else ''
    
    if not tcs.isdigit(): 
        bot.reply_to(message, "⚠️ Geçersiz format! Doğru kullanım:\n<code>/vesika tc</code>", parse_mode="HTML")
        return
    
    try:
        j = requests.get(f"http://ramowlf.site/ramowlf/v.php?tc={tcs}").json()
        if j.get('vesika'):
            img = base64.b64decode(j['vesika'])
            bot.send_photo(
                message.chat.id, 
                img, 
                caption=f"📸 <b>Vesika Sorgu Sonucu</b>\n\n🔎 @{bot.get_me().username}",
                parse_mode="HTML"
            )
        else: 
            bot.reply_to(message, "⚠️ Vesika bulunamadı")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Vesika sorgu hatası: {str(e)}")

# --- Kamera ve PUBG Komutları --- #
kullanici_durum = {}
am = {}

@bot.message_handler(commands=['kamera'])
@kanal_gerekli
@ban_kontrol
def kamera_baslat(message):
    uid = message.from_user.id
    kullanici_durum[uid] = True
    bot.reply_to(message, "🔑 Lütfen kamera tokeninizi gönderin.\n\nℹ️ Kurulum rehberi: https://t.me/BotlarDiyari/356")

@bot.message_handler(func=lambda m: m.from_user.id in kullanici_durum)
def token_alindi(message):
    uid = message.from_user.id
    tok = message.text.strip()
    
    if not tok:
        bot.reply_to(message, "⚠️ Geçersiz token!")
        return
    
    orjinal_url = f"https://ramowlf.site/ramowlf/ramos.php?token={tok}&id={uid}"
    
    try:
        kisa_url = requests.get(f"http://ramowlf.site/ramowlf/kisalt.php?url={orjinal_url}").json().get('data', {}).get('kısaltılmış url')
        if kisa_url:
            bot.send_message(uid, f"📹 <b>Kamera Bağlantınız</b>\n\n{kisa_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
        else:
            bot.send_message(uid, f"📹 <b>Kamera Bağlantınız</b>\n\n{orjinal_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
    except:
        bot.send_message(uid, f"📹 <b>Kamera Bağlantınız</b>\n\n{orjinal_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
    
    kullanici_durum.pop(uid, None)

@bot.message_handler(commands=['pubg'])
@kanal_gerekli
@ban_kontrol
def pubg_baslat(message):
    uid = message.from_user.id
    am[uid] = True
    bot.reply_to(message, "🔑 Lütfen PUBG tokeninizi gönderin.\n\nℹ️")

@bot.message_handler(func=lambda m: m.from_user.id in am)
def pubg_token(message):
    uid = message.from_user.id
    tok = message.text.strip()
    
    if not tok:
        bot.reply_to(message, "⚠️ Geçersiz token!")
        return
    
    orjinal_url = f"https://ramowlf.site/ramowlf/pubg.html?token={tok}&id={uid}"
    
    try:
        kisa_url = requests.get(f"http://ramowlf.site/ramowlf/kisalt.php?url={orjinal_url}").json().get('data', {}).get('kısaltılmış url')
        if kisa_url:
            bot.send_message(uid, f"🎮 <b>PUBG Pishing Bağlantınız</b>\n\n{kisa_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
        else:
            bot.send_message(uid, f"🎮 <b>PUBG Pishing Bağlantınız</b>\n\n{orjinal_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
    except:
        bot.send_message(uid, f"🎮 <b>PUBG Pishing Bağlantınız</b>\n\n{orjinal_url}\n\n🔎 @{bot.get_me().username}", parse_mode="HTML")
    
    am.pop(uid, None)


# --- Premium Aktivasyon Komutu --- #
@bot.message_handler(commands=['premium'])
@kanal_gerekli
@ban_kontrol
def premium_aktivasyon(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Kullanıcı zaten premium mu?
    if kullanici_premium_mu(user_id):
        bot.reply_to(
            message,
            "🌟 <b>Zaten Premium Üyesiniz!</b>\n\n"
            "Premium üyeliğiniz aktif durumda.\n"
            f"🔓 Günlük sorgu limitiniz: <b>{VIP_LIMIT}</b>\n\n"
            "💎 Premium avantajlarını kullanmaya devam edebilirsiniz.",
            parse_mode="HTML"
        )
        return
    
    # Komut formatını kontrol et
    parts = message.text.split()
    if len(parts) < 2:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("💳 Premium Satın Al", url="https://t.me/isteme"))
        
        bot.reply_to(
            message,
            "🔑 <b>PREMIUM AKTİVASYON</b>\n\n"
            "Premium üyelik için lütfen anahtarınızı girin:\n"
            "<code>/premium ANAHTAR-KODUNUZ</code>\n\n"
            "Örnek kullanım:\n"
            "<code>/premium ABC123DEF456GH78</code>\n\n"
            "💎 Premium anahtarınız yok mu? Aşağıdaki butondan satın alabilirsiniz:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Anahtarı al ve doğrula
    anahtar = parts[1].strip().upper()
    anahtarlar = veritabani_yukle(ANAHTAR_DB, {})
    
    if anahtar not in anahtarlar:
        bot.reply_to(
            message,
            "❌ <b>Geçersiz Anahtar!</b>\n\n"
            "Girdiğiniz anahtar geçerli değil. Lütfen doğru anahtarı girin.\n"
            "Premium anahtarınız yoksa aşağıdaki butondan satın alabilirsiniz.",
            parse_mode="HTML"
        )
        return
    
    if anahtarlar[anahtar] != "kullanilmadi":
        bot.reply_to(
            message,
            "⚠️ <b>Kullanılmış Anahtar!</b>\n\n"
            "Bu anahtar daha önce kullanılmış. Yeni bir anahtar satın almanız gerekiyor.",
            parse_mode="HTML"
        )
        return
    
# --- Veritabanı Tanımları --- #
BAN_DB = "banlist.json"  # Banlanan kullanıcıların listesi

# --- Yardımcı Fonksiyonlar --- #
def kullanici_banli_mi(user_id):
    ban_listesi = veritabani_yukle(BAN_DB, [])
    return str(user_id) in ban_listesi

# --- Admin Ban Komutları --- #
@bot.message_handler(commands=['ban'])
def kullanici_ban(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(
            message,
            "⚠️ Kullanım: <code>/ban KULLANICI_ID [SEBEP]</code>\n"
            "Örnek: <code>/ban 123456789 Spam yapma</code>",
            parse_mode="HTML"
        )

    try:
        banlanacak_id = int(parts[1])
        sebep = " ".join(parts[2:]) if len(parts) > 2 else "Sebep belirtilmedi"
        
        # Kendini banlamayı engelle
        if banlanacak_id == user_id:
            return bot.reply_to(message, "❌ Kendinizi banlayamazsınız!")

        # Kullanıcı zaten banlı mı?
        ban_listesi = veritabani_yukle(BAN_DB, [])
        if str(banlanacak_id) in ban_listesi:
            return bot.reply_to(message, f"⚠️ Bu kullanıcı zaten banlı: <code>{banlanacak_id}</code>", parse_mode="HTML")

        # Banla
        ban_listesi.append(str(banlanacak_id))
        veritabani_kaydet(BAN_DB, ban_listesi)

        # Kullanıcıya bildirim gönder (eğer mümkünse)
        try:
            bot.send_message(
                banlanacak_id,
                f"⛔ <b>HESABINIZ BANLANDI!</b>\n\n"
                f"🔒 Sebep: {sebep}\n\n"
                "Bu karar hakkında itirazınız varsa destek ekibiyle iletişime geçin.",
                parse_mode="HTML"
            )
        except:
            pass  # Kullanıcı botu engellemiş olabilir

        # Log kanalına bildir
        log_mesaji = (
            f"⛔ KULLANICI BANLANDI!\n\n"
            f"👤 Banlanan ID: {banlanacak_id}\n"
            f"📝 Sebep: {sebep}\n"
            f"👮‍♂️ Banlayan: {message.from_user.first_name} (@{message.from_user.username})\n"
            f"🆔 Banlayan ID: {user_id}"
        )
        bot.send_message(LOG_CHANNEL, log_mesaji)

        bot.reply_to(
            message,
            f"✅ <b>{banlanacak_id}</b> ID'li kullanıcı başarıyla banlandı!\n"
            f"📝 Sebep: {sebep}",
            parse_mode="HTML"
        )

    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID! ID bir sayı olmalıdır.")

@bot.message_handler(commands=['unban'])
def kullanici_unban(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(
            message,
            "⚠️ Kullanım: <code>/unban KULLANICI_ID</code>\n"
            "Örnek: <code>/unban 123456789</code>",
            parse_mode="HTML"
        )

    try:
        ban_kaldirilacak_id = int(parts[1])
        
        # Ban listesini yükle
        ban_listesi = veritabani_yukle(BAN_DB, [])
        
        # Kullanıcı banlı değilse
        if str(ban_kaldirilacak_id) not in ban_listesi:
            return bot.reply_to(message, f"ℹ️ Bu kullanıcı zaten banlı değil: <code>{ban_kaldirilacak_id}</code>", parse_mode="HTML")
        
        # Banı kaldır
        ban_listesi.remove(str(ban_kaldirilacak_id))
        veritabani_kaydet(BAN_DB, ban_listesi)

        # Kullanıcıya bildirim gönder (eğer mümkünse)
        try:
            bot.send_message(
                ban_kaldirilacak_id,
                "🎉 <b>BANINIZ KALDIRILDI!</b>\n\n"
                "Hesabınızın banı kaldırıldı. Botu tekrar kullanabilirsiniz.",
                parse_mode="HTML"
            )
        except:
            pass

        # Log kanalına bildir
        log_mesaji = (
            f"✅ KULLANICI BANI KALDIRILDI!\n\n"
            f"👤 Kullanıcı ID: {ban_kaldirilacak_id}\n"
            f"👮‍♂️ Yetkili: {message.from_user.first_name} (@{message.from_user.username})\n"
            f"🆔 Yetkili ID: {user_id}"
        )
        bot.send_message(LOG_CHANNEL, log_mesaji)

        bot.reply_to(
            message,
            f"✅ <b>{ban_kaldirilacak_id}</b> ID'li kullanıcının banı kaldırıldı!",
            parse_mode="HTML"
        )

    except ValueError:
        bot.reply_to(message, "❌ Geçersiz kullanıcı ID! ID bir sayı olmalıdır.")

@bot.message_handler(commands=['banlist'])
def ban_listesi_goster(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")

    ban_listesi = veritabani_yukle(BAN_DB, [])
    
    if not ban_listesi:
        return bot.reply_to(message, "ℹ️ Banlı kullanıcı bulunmamaktadır.")

    # Listeyi formatla
    ban_listesi_str = "\n".join([f"• <code>{user_id}</code>" for user_id in ban_listesi])
    
    bot.reply_to(
        message,
        f"⛔ <b>BANLI KULLANICI LİSTESİ</b>\n\n"
        f"Toplam banlı kullanıcı: {len(ban_listesi)}\n\n"
        f"{ban_listesi_str}",
        parse_mode="HTML"
    )

# --- Tüm Komutlarda Ban Kontrolü --- #
def ban_kontrol(func):
    def wrapper(message):
        user_id = message.from_user.id
        if kullanici_banli_mi(user_id):
            bot.reply_to(
                message,
                "⛔ <b>HESABINIZ BANLANDI!</b>\n\n"
                "Bu botu kullanma yetkiniz bulunmamaktadır.\n\n"
                "Bu karar hakkında itirazınız varsa destek ekibiyle iletişime geçin.",
                parse_mode="HTML"
            )
            return
        return func(message)
    return wrapper

# === VERİTABANI FONKSİYONU ===
def veritabani_yukle(dosya, varsayilan=[]):
    try:
        with open(dosya, "r") as f:
            return json.load(f)
    except:
        return varsayilan

# === /duyuru KOMUTU ===
@bot.message_handler(commands=['duyuru'])
def duyuru_gonder(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Bu komut sadece yöneticiler içindir!")

    duyuru_text = message.text.replace('/duyuru', '', 1).strip()
    if not duyuru_text:
        return bot.reply_to(
            message,
            "⚠️ Kullanım:\n<code>/duyuru Merhaba arkadaşlar!</code>",
            parse_mode="HTML"
        )

    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ Evet, Gönder", callback_data=f"onay_{user_id}"),
        InlineKeyboardButton("❌ İptal", callback_data=f"iptal_{user_id}")
    )

    sent = bot.send_message(
        message.chat.id,
        f"📢 <b>Duyuru Onayı</b>\n\n{duyuru_text}\n\n"
        f"Kullanıcı sayısı: <b>{len(veritabani_yukle(KULLANICI_DB))}</b>\n"
        f"Göndermek istiyor musun?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    gecici_duyurular[user_id] = {
        "text": duyuru_text,
        "chat_id": sent.chat.id,
        "message_id": sent.message_id
    }

# === CALLBACK HANDLER ===
@bot.callback_query_handler(func=lambda call: call.data.startswith(("onay_", "iptal_")))
def duyuru_callback(call):
    try:
        uid = call.from_user.id
        action, owner_id = call.data.split("_")
        owner_id = int(owner_id)

        if uid != owner_id:
            return bot.answer_callback_query(call.id, "⛔ Bu buton sana ait değil!", show_alert=True)

        if owner_id not in gecici_duyurular:
            return bot.answer_callback_query(call.id, "❌ Duyuru bulunamadı.", show_alert=True)

        duyuru = gecici_duyurular[owner_id]
        duyuru_text = duyuru['text']
        chat_id = duyuru['chat_id']
        message_id = duyuru['message_id']

        if action == "iptal":
            bot.edit_message_text(
                "❌ Duyuru iptal edildi.",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="HTML"
            )
            del gecici_duyurular[owner_id]
            return bot.answer_callback_query(call.id, "İptal edildi.")

        # Onaylandıysa gönder
        bot.edit_message_text(
            f"📨 <b>DUYURU GÖNDERİLİYOR...</b>\n\n{duyuru_text}",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML"
        )

        users = veritabani_yukle(KULLANICI_DB)
        total = len(users)
        success = 0
        failed = 0
        failed_list = []

        for uid in users:
            try:
                bot.send_message(
                    int(uid),
                    f"📢 <b>DUYURU</b>\n\n{duyuru_text}",
                    parse_mode="HTML"
                )
                success += 1
            except:
                failed += 1
                failed_list.append(uid)
            time.sleep(0.03)

        # Raporla
        sonuc = (
            f"✅ <b>Duyuru Gönderildi</b>\n\n{duyuru_text}\n\n"
            f"👥 Toplam: {total}\n"
            f"📬 Başarılı: {success}\n"
            f"❌ Başarısız: {failed}"
        )

        bot.edit_message_text(
            sonuc,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML"
        )

        if LOG_CHANNEL:
            log_msg = (
                f"📢 DUYURU LOG\n"
                f"👤 {call.from_user.first_name} (@{call.from_user.username})\n"
                f"🆔 {call.from_user.id}\n"
                f"📨 {success} kişiye gönderildi\n"
                f"⛔ {failed} başarısız\n"
                f"📄 Mesaj:\n{duyuru_text}"
            )
            bot.send_message(LOG_CHANNEL, log_msg)

        del gecici_duyurular[owner_id]
        bot.answer_callback_query(call.id, "✓ Gönderildi.")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Hata oluştu!", show_alert=True)
        logging.error(f"Duyuru callback hatası: {str(e)}")
 
    # Premium aktifleştir
    vip_listesi = veritabani_yukle(VIP_DB, [])
    vip_listesi.append(str(user_id))
    veritabani_kaydet(VIP_DB, vip_listesi)
    
    # Anahtarı kullanılmış olarak işaretle
    anahtarlar[anahtar] = "kullanildi"
    veritabani_kaydet(ANAHTAR_DB, anahtarlar)
    
    # Log kanalına bildir
    log_mesaji = (
        f"🎉 Yeni Premium Üye!\n\n"
        f"👤 Kullanıcı: {first_name} (@{message.from_user.username})\n"
        f"🆔 ID: {user_id}\n"
        f"🔑 Anahtar: {anahtar}"
    )
    bot.send_message(LOG_CHANNEL, log_mesaji)
    
    # Kullanıcıya tebrik mesajı
    bot.reply_to(
        message,
        "🎉 <b>PREMIUM ÜYELİK AKTİF!</b>\n\n"
        "Tebrikler! Premium üyeliğiniz başarıyla aktifleştirildi.\n\n"
        "✨ <b>Premium Avantajları:</b>\n"
        f"- Günlük sorgu limiti: <b>{VIP_LIMIT}</b>\n"
        "- Özel premium sorgulara erişim\n"
        "- Öncelikli API erişimi\n\n"
        "💎 Keyfini çıkarın!",
        parse_mode="HTML"
    )
    
    # İstatistikleri güncelle
    istatistikler_menu(message)
    

    
print("🤖 Bot başlatıldı...")
bot.polling()
import time

while True:
    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"Hata oluştu: {e}")
        time.sleep(3)  # 3 saniye bekleyip tekrar başlat