import re, csv, os, datetime
from telethon import TelegramClient
from telethon.tl.types import PeerChannel, DocumentAttributeAudio, MessageMediaDocument

# Telegram API credentials
api_id = '29670565'
api_hash = 'ede130708ffc720e331e404db9fe623c'

# File path base
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
    import re
    text = re.sub(r'[^\x00-\x7F]+', '', text)   # remove non-ASCII
    text = re.sub(r'http\S+|www\S+', '', text) # remove links
    return text.strip()

async def fetch_messages(post_url):
    # ✅ Create a new client each time
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start()

    channel_identifier = extract_channel_id_from_url(post_url)

    if isinstance(channel_identifier, int):
        channel = await client.get_entity(PeerChannel(channel_identifier))
    else:
        channel = await client.get_entity(channel_identifier)

    channel_name = channel.title

    # try subscribers count
    try:
        participants = await client.get_participants(channel, limit=0)
        subscribers_count = len(participants)
    except Exception:
        subscribers_count = "N/A"

    if isinstance(channel_identifier, int):
        channel_url = f"https://t.me/c/{channel_identifier}"
    else:
        channel_url = f"https://t.me/{channel_identifier}"

    # ✅ make unique file name with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"telegram_posts_{timestamp}.csv"
    file_path = os.path.join(BASE_DIR, file_name)

    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            'channel_url','channel_name','subscribers_count',
            'post_url','id','title','views','date_time','audio_caption'
        ])
        writer.writeheader()

        message_count = 0
        async for message in client.iter_messages(channel):  # ✅ all posts
            clean_title = clean_text(message.text.split("\n")[0] if message.text else None)

            # default
            audio_caption = "No audio"
            if isinstance(message.media, MessageMediaDocument):
                if message.media.document:
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeAudio):
                            audio_caption = clean_text(
                                getattr(attr, "file_name", "No caption")
                            )

            if isinstance(channel_identifier, int):
                post_url = f"https://t.me/c/{channel_identifier}/{message.id}"
            else:
                post_url = f"https://t.me/{channel_identifier}/{message.id}"

            post_info = {
                'channel_url': channel_url,
                'channel_name': channel_name,
                'subscribers_count': subscribers_count,
                'post_url': post_url,
                'id': message.id,
                'title': clean_title,
                'views': message.views if message.views else 0,
                'date_time': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                'audio_caption': audio_caption
            }
            writer.writerow(post_info)

            message_count += 1
            if message_count % 100 == 0:
                print(f"Fetched {message_count} messages...")

    await client.disconnect()  # ✅ close client properly
    return file_name
