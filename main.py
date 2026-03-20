import os
import subprocess
import requests
import re
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

TOPICS = [
    {"title": "Top 5 Fastest Cars in the World", "items": ["Bugatti Chiron Super Sport", "Koenigsegg Jesko Absolut", "Hennessey Venom F5", "SSC Tuatara", "Rimac Nevera"]},
    {"title": "Top 5 Tallest Buildings in the World", "items": ["Burj Khalifa Dubai", "Shanghai Tower China", "Abraj Al Bait Saudi Arabia", "Ping An Finance Center", "Lotte World Tower Korea"]},
    {"title": "Top 5 Richest People in the World", "items": ["Elon Musk", "Jeff Bezos", "Bernard Arnault", "Bill Gates", "Mark Zuckerberg"]},
    {"title": "Top 5 Most Beautiful Countries in the World", "items": ["Switzerland", "New Zealand", "Italy", "Norway", "Japan"]},
    {"title": "Top 5 Biggest Animals in the World", "items": ["Blue Whale", "African Elephant", "White Rhinoceros", "Hippopotamus", "Giraffe"]},
    {"title": "Top 5 Most Expensive Cars in the World", "items": ["Rolls Royce Boat Tail", "Bugatti La Voiture Noire", "Pagani Zonda HP Barchetta", "Lamborghini Veneno", "Koenigsegg CCXR Trevita"]},
    {"title": "Top 5 Strongest Militaries in the World", "items": ["United States", "Russia", "China", "India", "United Kingdom"]},
    {"title": "Top 5 Most Visited Countries in the World", "items": ["France", "Spain", "United States", "China", "Italy"]},
    {"title": "Top 5 Fastest Animals in the World", "items": ["Cheetah", "Pronghorn Antelope", "Springbok", "Wildebeest", "Lion"]},
    {"title": "Top 5 Most Expensive Houses in the World", "items": ["Buckingham Palace London", "Villa Leopolda France", "Antilia Mumbai", "The One Los Angeles", "Witanhurst London"]},
    {"title": "Top 5 Deepest Oceans in the World", "items": ["Pacific Ocean", "Atlantic Ocean", "Indian Ocean", "Southern Ocean", "Arctic Ocean"]},
    {"title": "Top 5 Longest Rivers in the World", "items": ["Nile River Africa", "Amazon River South America", "Yangtze River China", "Mississippi River USA", "Yenisei River Russia"]},
    {"title": "Top 5 Most Powerful Currencies in the World", "items": ["Kuwaiti Dinar", "Bahraini Dinar", "Omani Rial", "Jordanian Dinar", "British Pound"]},
    {"title": "Top 5 Rarest Gems in the World", "items": ["Pink Star Diamond", "Jadeite", "Red Diamond", "Alexandrite", "Blue Garnet"]},
    {"title": "Top 5 Most Popular Sports in the World", "items": ["Football Soccer", "Cricket", "Basketball", "Tennis", "Volleyball"]},
]

def clean_text(text):
    cleaned = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    cleaned = cleaned.strip()
    cleaned = ' '.join(cleaned.split())
    return cleaned

def get_pexels_image(query):
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=portrait"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("photos"):
            return data["photos"][0]["src"]["portrait"]
    except:
        pass
    return None

def download_image(url, path):
    res = requests.get(url, timeout=15)
    with open(path, "wb") as f:
        f.write(res.content)

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

def create_slide(img_path, number, item_text, title, slide_path):
    safe_title = clean_text(title)
    safe_item = clean_text(item_text)
    number_text = str(number) + ". " + safe_item

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "drawtext=text='" + safe_title + "':fontsize=44:fontcolor=white:"
        "x=(w-text_w)/2:y=80:"
        "borderw=3:bordercolor=black:"
        "box=1:boxcolor=black@0.6:boxborderw=10,"
        "drawtext=text='" + number_text + "':fontsize=56:fontcolor=yellow:"
        "x=(w-text_w)/2:y=h-160:"
        "borderw=4:bordercolor=black:"
        "box=1:boxcolor=black@0.7:boxborderw=14"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", img_path,
        "-vf", vf,
        "-t", "4",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        slide_path
    ]
    subprocess.run(cmd, capture_output=True)

@app.route("/create-video", methods=["POST"])
def create_video_endpoint():
    try:
        data = request.json
        day_index = int(data.get("day_index", 0))

        topic = TOPICS[day_index % len(TOPICS)]
        title = topic["title"]
        items = topic["items"]

        with tempfile.TemporaryDirectory() as tmpdir:
            slide_videos = []

            for i, item in enumerate(items):
                number = 5 - i
                search_query = clean_text(item)

                img_url = get_pexels_image(search_query)
                if not img_url:
                    img_url = get_pexels_image("nature landscape beautiful")

                img_path = os.path.join(tmpdir, "img_" + str(i) + ".jpg")

                if img_url:
                    download_image(img_url, img_path)
                else:
                    subprocess.run([
                        'ffmpeg', '-y', '-f', 'lavfi',
                        '-i', 'color=c=darkblue:size=1080x1920:rate=30',
                        '-frames:v', '1', img_path
                    ], capture_output=True)

                slide_path = os.path.join(tmpdir, "slide_" + str(i) + ".mp4")
                create_slide(img_path, number, item, title, slide_path)

                if os.path.exists(slide_path):
                    slide_videos.append(slide_path)

            if not slide_videos:
                return jsonify({"success": False, "error": "No slides created"}), 500

            concat_file = os.path.join(tmpdir, "concat.txt")
            with open(concat_file, "w") as f:
                for sv in slide_videos:
                    f.write("file '" + sv + "'\n")

            silent_video = os.path.join(tmpdir, "silent_video.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file, "-c", "copy", silent_video
            ], capture_output=True)

            music_path = get_free_music(tmpdir)
            final_video = os.path.join(tmpdir, "final_video.mp4")

            if music_path and os.path.exists(music_path):
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", silent_video,
                    "-i", music_path,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    "-af", "volume=0.3",
                    final_video
                ], capture_output=True)
            else:
                os.rename(silent_video, final_video)

            if not os.path.exists(final_video):
                return jsonify({"success": False, "error": "Final video not created"}), 500

            with open(final_video, "rb") as f:
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
