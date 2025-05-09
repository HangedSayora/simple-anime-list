from flask import Flask, request, jsonify, render_template
from datetime import datetime
import requests
import json
import os
from urllib.parse import unquote


app = Flask(__name__)
DATA_FILE = "anime_list.json"
BASE_URL = "https://shikimori.one"

russian_months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

def format_date(date_str):
    if not date_str:
        return "Не закончено"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {russian_months[dt.month]} {dt.year}"
    except:
        return date_str

def get_shikimori_anime(title):
    response = requests.get(
        f"{BASE_URL}/api/animes",
        headers={"User-Agent": "Anime-Finder/1.0"},
        params={"search": title}
    )
    data = response.json()
    if not data:
        return None
    anime = data[0]

    romaji_name = anime["name"]
    russian_name = anime["russian"]
    preview = BASE_URL + anime["image"]["original"]
    rating = anime["score"]
    episodes = anime["episodes"]

    aired = format_date(anime["aired_on"])
    released = format_date(anime["released_on"])

    if anime["status"] in ("ongoing", "released"):
        label_aired = "Начало выходить: "
    else:
        label_aired = "Анонсировано: "
    

    status = anime["status"]
    if status == "ongoing":
        status_label = "Выходит"
    elif status == "released" and released != "Не закончено":
        status_label = "Вышло"
    elif status == "anons":
        status_label = "Анонсировано"
    else:
        status_label = "Отменено"

    return {
        "name": romaji_name,
        "russian": russian_name,
        "image_original": preview,
        "score": rating,
        "episodes": episodes,
        "aired_label": label_aired,
        "aired_on": aired,
        "released_on": released,
        "status": status_label
    }

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/api/anime-list")
def anime_list():
    page = int(request.args.get("page", 1))
    status_filter = request.args.get("status")
    search_query = request.args.get("search", "").lower()
    data = load_data()

    if status_filter:
        print(status_filter)
        if status_filter in ("вышло", "выходит", "анонсировано", "отменено"):
           data = [a for a in data if a.get("status", "").lower() == status_filter]
        else:
           data = [a for a in data if a.get("user_status") == status_filter]

    if search_query:
        data = [
            a for a in data
            if search_query in a.get("name", "").lower() or
               search_query in a.get("russian", "").lower()
        ]

    per_page = 5
    total_items = len(data)
    total_pages = (total_items + per_page - 1) // per_page

    start = (page - 1) * per_page
    end = start + per_page
    anime_list = data[start:end]

    return jsonify({
        "anime_list": anime_list,
        "total_pages": total_pages,
    })

@app.route("/api/anime", methods=["POST"])
def add_anime():
    req = request.json
    title = req.get("title")
    url = req.get("url")
    user_status = req.get("user_status", "буду смотреть")
    if not title or not url:
        return "Missing title or URL", 400
    info = get_shikimori_anime(title)
    if not info:
        return "Not found", 404
    info["url"] = url
    info["user_status"] = user_status
    data = load_data()
    if any(anime["name"] == info["name"] for anime in data):
        return "Already exists", 400
    data.append(info)
    save_data(data)
    return "OK"

@app.route("/api/anime/<name>", methods=["PUT"])
def update_anime(name):
    name = unquote(name)
    req = request.get_json()
    if not req:
        return "Invalid JSON", 400

    new_status = req.get("user_status")
    data = load_data()
    for i, anime in enumerate(data):
        if anime["name"] == name:
            info = get_shikimori_anime(name)
            if info:
                info["url"] = anime["url"]
                info["user_status"] = new_status or anime.get("user_status", "буду смотреть")
                data[i] = info
                save_data(data)
                return "Updated"
            return "Not found", 404
    return "Anime not found", 404

@app.route("/api/anime/<name>/status", methods=["PUT"])
def update_status(name):
    req = request.json
    new_status = req.get("user_status")
    data = load_data()
    for i, anime in enumerate(data):
        if anime["name"] == name:
            data[i]["user_status"] = new_status
            save_data(data)
            return "Status updated"
    return "Anime not found", 404

@app.route("/api/anime/<name>", methods=["DELETE"])
def delete_anime(name):
    data = load_data()
    data = [a for a in data if a["name"] != name]
    save_data(data)
    return "Deleted"

@app.route("/api/anime/<name>/move", methods=["PUT"])
def move_anime(name):
    direction = request.args.get("direction")  # "up" или "down"
    if direction not in ("up", "down"):
        return "Invalid direction", 400

    data = load_data()
    index = next((i for i, a in enumerate(data) if a["name"] == name), None)
    
    if index is None:
        return "Anime not found", 404

    if direction == "up" and index > 0:
        data[index], data[index - 1] = data[index - 1], data[index]
    elif direction == "down" and index < len(data) - 1:
        data[index], data[index + 1] = data[index + 1], data[index]
    else:
        return "Cannot move in that direction", 400

    save_data(data)
    return "Moved"


@app.route('/')
def serve_index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
