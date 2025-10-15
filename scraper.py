import re, csv, os, datetime
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import PeerChannel, DocumentAttributeAudio, MessageMediaDocument
from client_manager import get_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def extract_channel_id_from_url(url):
    match = re.match(r'https://t.me/c/(\d+)/\d*', url)
    if match:
        return int(match.group(1))
    else:
        match = re.match(r'https://t.me/([a-zA-Z0-9_]+)', url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid URL format")

def clean_text(text):
    if not text:
        return "No title"
    return text.strip()

def extract_channel_info_from_url(url):
    private_match = re.match(r'https://t.me/c/(\d+)(?:/(\d+))?', url)
    if private_match:
        channel_id = int(private_match.group(1))
        msg_id = int(private_match.group(2)) if private_match.group(2) else None
        return channel_id, msg_id, True

    public_post_match = re.match(r'https://t.me/([a-zA-Z0-9_]+)/(\d+)', url)
    if public_post_match:
        username = public_post_match.group(1)
        msg_id = int(public_post_match.group(2))
        return username, msg_id, False

    public_profile_match = re.match(r'https://t.me/([a-zA-Z0-9_]+)$', url)
    if public_profile_match:
        username = public_profile_match.group(1)
        return username, None, False

    raise ValueError("Invalid URL format")


# ✅ Updated function with stop_event
async def fetch_messages(post_urls, phone, logger=print, stop_event=None):
    client = get_client(phone)

    file_name = "telegram_data.csv"
    file_path = os.path.join(BASE_DIR, file_name)

    fieldnames = [
        'channel_url', 'channel_name', 'subscribers_count',
        'post_url', 'id', 'title', 'description', 'views',
        'date_time', 'audio_caption',
        'terabox_link_1', 'terabox_link_2', 'terabox_link_3', 'terabox_link_4', 'terabox_link_5',
        'telegram_link_1', 'telegram_link_2', 'telegram_link_3'
    ]

    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for url in post_urls:
            if stop_event and stop_event.is_set():
                logger("🛑 Stop signal received before processing new URL.")
                return file_name

            try:
                channel_identifier, msg_id, is_private = extract_channel_info_from_url(url)

                if isinstance(channel_identifier, int):
                    channel = await client.get_entity(PeerChannel(channel_identifier))
                else:
                    channel = await client.get_entity(channel_identifier)

                channel_name = getattr(channel, "title", channel_identifier)

                try:
                    full = await client(GetFullChannelRequest(channel))
                    subscribers_count = full.full_chat.participants_count
                except Exception:
                    subscribers_count = "N/A"

                channel_url = f"https://t.me/c/{channel_identifier}" if isinstance(channel_identifier, int) else f"https://t.me/{channel_identifier}"

                if msg_id:
                    logger(f"📌 Fetching single post from {url}")
                    message = await client.get_messages(channel, ids=msg_id)
                    if message:
                        writer.writerow(process_message(message, channel_identifier, channel_url, channel_name, subscribers_count))
                        logger(f"✅ Saved post {msg_id} from {channel_name}")
                else:
                    logger(f"➡️ Scraping channel/profile: {channel_name}")
                    count = 0
                    async for message in client.iter_messages(channel):
                        if stop_event and stop_event.is_set():
                            logger(f"🛑 Stop signal detected — stopping {channel_name}.")
                            return file_name

                        writer.writerow(process_message(message, channel_identifier, channel_url, channel_name, subscribers_count))
                        count += 1
                        if count % 50 == 0:
                            logger(f"[{channel_name}] Fetched {count} messages...")
                    logger(f"✅ Done scraping {channel_name}")

            except Exception as e:
                logger(f"❌ Error processing {url}: {e}")

    return file_name


def process_message(message, channel_identifier, channel_url, channel_name, subscribers_count):
    clean_title = clean_text(message.text.split("\n")[0] if message.text else None)
    full_description = message.text if message.text else "No description"

    audio_caption = "No audio"
    if isinstance(message.media, MessageMediaDocument):
        if message.media.document:
            for attr in message.media.document.attributes:
                if isinstance(attr, DocumentAttributeAudio):
                    audio_caption = clean_text(getattr(attr, "file_name", "No caption"))

    terabox_links = re.findall(r'https?://[a-zA-Z0-9.-]*terabox[a-zA-Z0-9./?=_-]+', full_description)
    telegram_links = re.findall(r'https?://t\.me/(?:\+|joinchat/)?[a-zA-Z0-9_-]+', full_description)

    terabox_links += ["-"] * (5 - len(terabox_links))
    telegram_links += ["-"] * (3 - len(telegram_links))

    msg_url = f"https://t.me/c/{channel_identifier}/{message.id}" if isinstance(channel_identifier, int) else f"https://t.me/{channel_identifier}/{message.id}"

    return {
        'channel_url': channel_url,
        'channel_name': channel_name,
        'subscribers_count': subscribers_count,
        'post_url': msg_url,
        'id': message.id,
        'title': clean_title,
        'description': full_description,
        'views': message.views if message.views else 0,
        'date_time': message.date.strftime('%Y-%m-%d %H:%M:%S'),
        'audio_caption': audio_caption,
        'terabox_link_1': terabox_links[0],
        'terabox_link_2': terabox_links[1],
        'terabox_link_3': terabox_links[2],
        'terabox_link_4': terabox_links[3],
        'terabox_link_5': terabox_links[4],
        'telegram_link_1': telegram_links[0],
        'telegram_link_2': telegram_links[1],
        'telegram_link_3': telegram_links[2],
    }
