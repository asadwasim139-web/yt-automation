from flask import Flask, request, jsonify
import requests
import os
import json
import subprocess
import tempfile
import re
from pathlib import Path

app = Flask(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "YOUR_PEXELS_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_YOUTUBE_KEY")

def get_pexels_image(query):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=portrait"
    res = requests.get(url, headers=headers)
    data = res.json()
    if data.get("photos"):
        return data["photos"][0]["src"]["portrait"]
    return None

def download_image(url, path):
    res = requests.get(url)
    with open(path, "wb") as f:
        f.write(res.content)

def get_free_music(tmpdir):
    music_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    music_path = os.path.join(tmpdir, "music.mp3")
    res = requests.get(music_url)
    with open(music_path, "wb") as f:
        f.write(res.content)
    return music_path

def create_video(script, title, description, tags, tmpdir):
    lines = [l.strip() for l in script.strip().split("\n") if l.strip()]
    top5_lines = []
    for line in lines:
        clean = re.sub(r'\*+', '', line).strip()
        if clean:
            top5_lines.append(clean)
    top5_lines = top5_lines[:5]

    slide_videos = []

    for i, line in enumerate(top5_lines):
        search_query = re.sub(r'^\d+[\.\)]\s*', '', line)
        search_query = re.sub(r'[^\w\s]', '', search_query).strip()

        img_url = get_pexels_image(search_query)
        if not img_url:
            img_url = get_pexels_image("nature landscape")

        img_path = os.path.join(tmpdir, f"img_{i}.jpg")
        download_image(img_url, img_path)

        subtitle_text = line[:60]
        slide_path = os.path.join(tmpdir, f"slide_{i}.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-vf", (
                f"scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,"
                f"drawtext=text='{subtitle_text}':fontsize=52:fontcolor=white:"
                f"x=(w-text_w)/2:y=h-200:"
                f"borderw=3:bordercolor=black:"
                f"box=1:boxcolor=black@0.5:boxborderw=10"
            ),
            "-t", "4",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            slide_path
        ]

        subprocess.run(cmd, capture_output=True)
        slide_videos.append(slide_path)

    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w") as f:
        for sv in slide_videos:
            f.write(f"file '{sv}'\n")

    silent_video = os.path.join(tmpdir, "silent_video.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        silent_video
    ], capture_output=True)

    music_path = get_free_music(tmpdir)
    final_video = os.path.join(tmpdir, "final_video.mp4")

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

    return final_video

@app.route("/create-video", methods=["POST"])
def create_video_endpoint():
    try:
        data = request.json
        script = data.get("script", "")
        title = data.get("title", "Top 5 Video")
        description = data.get("description", "")
        tags = data.get("tags", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = create_video(script, title, description, tags, tmpdir)

            with open(video_path, "rb") as f:
                video_bytes = f.read()

        return jsonify({
            "success": True,
            "message": "Video created successfully",
            "video_size": len(video_bytes),
            "title": title,
            "description": description,
            "tags": tags
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
