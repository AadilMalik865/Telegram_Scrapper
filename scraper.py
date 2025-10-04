import re, csv, os, datetime
from telethon import TelegramClient
from telethon.tl.types import PeerChannel, DocumentAttributeAudio, MessageMediaDocument
from random import choice

# ✅ Multiple Telegram API credentials
API_CREDENTIALS = [
    {'api_id': '29670565', 'api_hash': 'ede130708ffc720e331e404db9fe623c'},
    {'api_id': '25256899', 'api_hash': '40504dd8254213ba34633438fa11112d'},
    {'api_id': '23917587', 'api_hash': 'd7eebb8d0a825d9ccece93ddc2249abc'},
    # Add more credentials here
]

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
    text = re.sub(r'[^\x00-\x7F]+', '', text)   # remove non-ASCII
    text = re.sub(r'http\S+|www\S+', '', text)  # remove links
    return text.strip()

# ✅ Get Telegram client using random credentials
def get_telegram_client():
    creds = choice(API_CREDENTIALS)
    session_name = f"session_{creds['api_id']}"  # unique session per api_id
    return TelegramClient(session_name, creds['api_id'], creds['api_hash'])

async def fetch_messages(post_url):
    client = get_telegram_client()  # pick random credentials
    await client.start()

    channel_identifier = extract_channel_id_from_url(post_url)

    if isinstance(channel_identifier, int):
        channel = await client.get_entity(PeerChannel(channel_identifier))
    else:
        channel = await client.get_entity(channel_identifier)

    channel_name = channel.title

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
            'channel_url', 'channel_name', 'subscribers_count',
            'post_url', 'id', 'title', 'description', 'views',
            'date_time', 'audio_caption'
        ])
        writer.writeheader()

        message_count = 0
        async for message in client.iter_messages(channel):
            clean_title = clean_text(message.text.split("\n")[0] if message.text else None)
            full_description = clean_text(message.text) if message.text else "No description"

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
                'description': full_description,
                'views': message.views if message.views else 0,
                'date_time': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                'audio_caption': audio_caption
            }
            writer.writerow(post_info)

            message_count += 1
            if message_count % 100 == 0:
                print(f"Fetched {message_count} messages...")

    await client.disconnect()
    return file_name
