import os
import requests
import re
import tempfile
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

TOPICS = [
    {"title": "Top 5 Fastest Cars in the World", "items": ["Bugatti Chiron Super Sport", "Koenigsegg Jesko Absolut", "Hennessey Venom F5", "SSC Tuatara", "Rimac Nevera"]},
    {"title": "Top 5 Tallest Buildings in the World", "items": ["Burj Khalifa Dubai", "Shanghai Tower China", "Abraj Al Bait Saudi Arabia", "Ping An Finance Center", "Lotte World Tower Korea"]},
    {"title": "Top 5 Richest People in the World", "items": ["Elon Musk", "Jeff Bezos", "Bernard Arnault", "Bill Gates", "Mark Zuckerberg"]},
    {"title": "Top 5 Most Beautiful Countries", "items": ["Switzerland", "New Zealand", "Italy", "Norway", "Japan"]},
    {"title": "Top 5 Biggest Animals in the World", "items": ["Blue Whale", "African Elephant", "White Rhinoceros", "Hippopotamus", "Giraffe"]},
    {"title": "Top 5 Most Expensive Cars", "items": ["Rolls Royce Boat Tail", "Bugatti La Voiture Noire", "Pagani Zonda HP Barchetta", "Lamborghini Veneno", "Koenigsegg CCXR Trevita"]},
    {"title": "Top 5 Strongest Militaries", "items": ["United States", "Russia", "China", "India", "United Kingdom"]},
    {"title": "Top 5 Most Visited Countries", "items": ["France", "Spain", "United States", "China", "Italy"]},
    {"title": "Top 5 Fastest Animals in the World", "items": ["Cheetah", "Pronghorn Antelope", "Springbok", "Wildebeest", "Lion"]},
    {"title": "Top 5 Most Expensive Houses", "items": ["Buckingham Palace London", "Villa Leopolda France", "Antilia Mumbai", "The One Los Angeles", "Witanhurst London"]},
    {"title": "Top 5 Longest Rivers in the World", "items": ["Nile River Africa", "Amazon River South America", "Yangtze River China", "Mississippi River USA", "Yenisei River Russia"]},
    {"title": "Top 5 Most Powerful Currencies", "items": ["Kuwaiti Dinar", "Bahraini Dinar", "Omani Rial", "Jordanian Dinar", "British Pound"]},
    {"title": "Top 5 Rarest Gems in the World", "items": ["Pink Star Diamond", "Jadeite", "Red Diamond", "Alexandrite", "Blue Garnet"]},
    {"title": "Top 5 Most Popular Sports", "items": ["Football Soccer", "Cricket", "Basketball", "Tennis", "Volleyball"]},
    {"title": "Top 5 Deepest Oceans in the World", "items": ["Pacific Ocean", "Atlantic Ocean", "Indian Ocean", "Southern Ocean", "Arctic Ocean"]},
]

def get_pexels_image(query):
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = "https://api.pexels.com/v1/search?query=" + query + "&per_page=1&orientation=portrait"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("photos"):
            return data["photos"][0]["src"]["portrait"]
    except:
        pass
    return None

def download_image(url):
    from io import BytesIO
    res = requests.get(url, timeout=15)
    img = Image.open(BytesIO(res.content)).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)
    return img

def add_text_to_image(img, title, number, item):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        item_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
    except:
        title_font = ImageFont.load_default()
        item_font = ImageFont.load_default()

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (w - title_w) // 2

    draw.rectangle([title_x - 15, 50, title_x + title_w + 15, 130], fill=(0, 0, 0, 160))
    draw.text((title_x, 60), title, font=title_font, fill=(255, 255, 255, 255))

    item_text = str(number) + ". " + item
    item_bbox = draw.textbbox((0, 0), item_text, font=item_font)
    item_w = item_bbox[2] - item_bbox[0]
    item_x = (w - item_w) // 2

    draw.rectangle([item_x - 15, h - 200, item_x + item_w + 15, h - 120], fill=(0, 0, 0, 180))
    draw.text((item_x, h - 190), item_text, font=item_font, fill=(255, 220, 0, 255))

    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")

def get_free_music(tmpdir):
    music_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    music_path = os.path.join(tmpdir, "music.mp3")
    try:
        res = requests.get(music_url, timeout=30)
        with open(music_path, "wb") as f:
            f.write(res.content)
        return music_path
    except:
        return None

@app.route("/create-video", methods=["POST"])
def create_video_endpoint():
    try:
        data = request.json
        day_index = int(data.get("day_index", 0))
        topic = TOPICS[day_index % len(TOPICS)]
        title = topic["title"]
        items = topic["items"]

        with tempfile.TemporaryDirectory() as tmpdir:
            clips = []

            for i, item in enumerate(items):
                number = 5 - i
                search_query = re.sub(r'[^a-zA-Z0-9 ]', '', item).strip()

                img_url = get_pexels_image(search_query)
                if not img_url:
                    img_url = get_pexels_image("nature landscape")

                if img_url:
                    img = download_image(img_url)
                else:
                    img = Image.new("RGB", (1080, 1920), color=(0, 50, 100))

                img = add_text_to_image(img, title, number, item)
                img_path = os.path.join(tmpdir, "slide_" + str(i) + ".jpg")
                img.save(img_path, quality=95)

                clip = ImageClip(img_path, duration=4)
                clips.append(clip)

            final_clip = concatenate_videoclips(clips, method="compose")

            music_path = get_free_music(tmpdir)
            if music_path:
                audio = AudioFileClip(music_path).with_subclip(0, min(20, final_clip.duration))
                audio = audio.with_multiply_volume(0.3)
                final_clip = final_clip.with_audio(audio)

            output_path = os.path.join(tmpdir, "final_video.mp4")
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )

            with open(output_path, "rb") as f:
                video_bytes = f.read()

        return jsonify({
            "success": True,
            "message": "Video created successfully",
            "title": title,
            "video_size": len(video_bytes)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
