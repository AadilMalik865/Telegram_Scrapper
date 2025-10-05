import re, csv, os, datetime
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
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'http\S+|www\S+', '', text)
    return text.strip()

async def fetch_messages(post_url, phone):
    client = get_client(phone)  # ✅ single client instance

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

            audio_caption = "No audio"
            if isinstance(message.media, MessageMediaDocument):
                if message.media.document:
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeAudio):
                            audio_caption = clean_text(getattr(attr, "file_name", "No caption"))

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

    return file_name
