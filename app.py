import os
import uuid
import subprocess
import threading
import json
import re
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    after_this_request,
)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

tasks = {}

APP_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(APP_DIR, "ffmpeg", "bin", "ffmpeg.exe")
YTDLP_PATH = os.path.join(APP_DIR, "ffmpeg", "bin", "yt-dlp.exe")


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name[:200]
    return name.strip()


def get_video_info(url):
    proc = subprocess.Popen(
        [YTDLP_PATH, "--dump-json", "--no-playlist", "--no-warnings", url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        return None
    try:
        return json.loads(stdout.decode("utf-8"))
    except:
        return None


def convert_video(output_path, task_id, url, format_type, quality, video_title):
    try:
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 5

        safe_title = (
            sanitize_filename(video_title) if video_title else f"video_{task_id[:8]}"
        )

        tasks[task_id]["video_title"] = safe_title
        tasks[task_id]["save_name"] = safe_title

        is_playlist = "playlist" in url.lower() or "&list=" in url

        if format_type == "mp3":
            if is_playlist:
                output_template = os.path.join(
                    DOWNLOADS_DIR, safe_title + "_%(playlist_index)s.%(ext)s"
                )
            else:
                output_template = os.path.join(DOWNLOADS_DIR, safe_title + ".%(ext)s")

            ytdlp_opts = [
                YTDLP_PATH,
                "--no-playlist" if not is_playlist else "--yes-playlist",
                "--no-warnings",
                "-x",
                "--audio-format",
                "mp3",
                "--output",
                output_template,
            ]

            if "320" in quality:
                ytdlp_opts.extend(["--audio-quality", "320k"])
            elif "192" in quality:
                ytdlp_opts.extend(["--audio-quality", "192k"])
            else:
                ytdlp_opts.extend(["--audio-quality", "128k"])

        else:
            height = quality.split("p")[0] if "p" in quality else "1080"

            if is_playlist:
                output_template = os.path.join(
                    DOWNLOADS_DIR, safe_title + "_%(playlist_index)s.%(ext)s"
                )
            else:
                output_template = os.path.join(DOWNLOADS_DIR, safe_title + ".%(ext)s")

            ytdlp_opts = [
                YTDLP_PATH,
                "--no-playlist" if not is_playlist else "--yes-playlist",
                "--no-warnings",
                "-f",
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                "--output",
                output_template,
            ]

        ytdlp_opts.append(url)

        tasks[task_id]["progress"] = 15

        proc = subprocess.Popen(
            ytdlp_opts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        total_bytes = 0
        downloaded_bytes = 0

        while True:
            ret = proc.poll()
            if ret is not None:
                break

            try:
                pass
            except:
                pass

            tasks[task_id]["progress"] = min(85, tasks[task_id]["progress"] + 1)
            time.sleep(0.5)

        tasks[task_id]["progress"] = 90

        if format_type == "mp4":
            for f in os.listdir(DOWNLOADS_DIR):
                if f.startswith(safe_title) and (
                    f.endswith(".webm") or f.endswith(".mkv") or f.endswith(".m4a")
                ):
                    input_path = os.path.join(DOWNLOADS_DIR, f)
                    output_mp4 = os.path.splitext(input_path)[0] + ".mp4"
                    subprocess.run(
                        [
                            FFMPEG_PATH,
                            "-i",
                            input_path,
                            "-c",
                            "copy",
                            output_mp4,
                            "-y",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                        ],
                        creationflags=subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0,
                    )
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    break

        final_files = [
            f
            for f in os.listdir(DOWNLOADS_DIR)
            if f.startswith(safe_title) and (f.endswith(".mp3") or f.endswith(".mp4"))
        ]

        if final_files:
            final_path = os.path.join(DOWNLOADS_DIR, final_files[0])
            tasks[task_id]["progress"] = 100
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["file_path"] = final_path
            tasks[task_id]["file_name"] = final_files[0]
        else:
            raise Exception("Failed to generate output file")

    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def get_video_info_api():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Please provide a URL"}), 400

    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    info = get_video_info(url)
    if not info:
        return jsonify(
            {
                "error": "Could not fetch video info. Video may be private or unavailable."
            }
        ), 400

    is_playlist = (
        info.get("playlist_count", 0) > 1
        or "&list=" in url
        or "playlist" in url.lower()
    )

    return jsonify(
        {
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "is_playlist": is_playlist,
            "playlist_count": info.get("playlist_count", 1),
        }
    )


@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.get_json()
    url = data.get("url", "").strip()
    format_type = data.get("format", "mp3").lower()
    quality = data.get("quality", "320kbps" if format_type == "mp3" else "1080p")

    if not url:
        return jsonify({"error": "Please provide a YouTube URL"}), 400

    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    task_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOADS_DIR, f"convert_{task_id}")

    video_info = get_video_info(url)
    video_title = video_info.get("title") if video_info else None

    tasks[task_id] = {
        "status": "starting",
        "progress": 0,
        "url": url,
        "format": format_type,
        "quality": quality,
    }

    thread = threading.Thread(
        target=convert_video,
        args=(output_path, task_id, url, format_type, quality, video_title),
    )
    thread.start()

    return jsonify(
        {
            "task_id": task_id,
            "message": "Conversion started",
            "video_title": video_title,
        }
    )


@app.route("/api/status/<task_id>", methods=["GET"])
def get_status(task_id):
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    task = tasks[task_id]
    return jsonify(
        {
            "status": task.get("status", "unknown"),
            "progress": task.get("progress", 0),
            "error": task.get("error", ""),
            "video_title": task.get("video_title", ""),
        }
    )


@app.route("/api/download/<task_id>", methods=["GET"])
def download(task_id):
    if task_id not in tasks:
        return jsonify({"error": "Task not found"}), 404

    task = tasks[task_id]
    if task["status"] != "completed":
        return jsonify(
            {"error": "Conversion not completed", "status": task.get("status")}
        ), 400

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    @after_this_request
    def remove_file(response):
        return response

    return send_file(file_path, as_attachment=True, download_name=task.get("file_name"))


@app.route("/api/cleanup", methods=["DELETE"])
def cleanup():
    count = 0
    for task_id in list(tasks.keys()):
        task = tasks.get(task_id)
        if task and task.get("file_path") and os.path.exists(task["file_path"]):
            try:
                os.remove(task["file_path"])
            except:
                pass
        tasks.pop(task_id, None)
        count += 1
    return jsonify({"message": f"Cleaned up {count} tasks"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
