from flask import Flask, request, jsonify, render_template
from datetime import datetime
import requests
import json
import os
from urllib.parse import unquote


app = Flask(__name__)
DATA_FILE = "anime_list.json"
BASE_URL = "https://shikimori.one"

# Names months on russian language
russian_months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

# Foramting date
def format_date(date_str):
    if not date_str:
        # If not last date
        return "Не закончено"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Formating date
        return f"{dt.day} {russian_months[dt.month]} {dt.year}"
    except:
        # If error formating date
        return date_str

# Gets information about anime 
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

    # List variable 
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

    # Return json format variable
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

# Load inforation with json file anime_list.json
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# Save information to json file anime_list.json
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Function to get anime list from json file and generate data
@app.route("/api/anime-list")
def anime_list():
    page = int(request.args.get("page", 1))
    full = request.args.get("full")
    status_filter = request.args.get("status")
    search_query = request.args.get("search", "").lower()
    search_query_season = request.args.get("search_season", "").lower()
    status_filter_season = request.args.get("status_season")

    data = load_data()
    result = []

    for anime in data:
        match_anime = True

        # Filter name main list anime
        if search_query and not (
            search_query in anime.get("name", "").lower() or
            search_query in anime.get("russian", "").lower()
        ):
            match_anime = False

        # Filter status main list anime
        if status_filter:
            anime_status = anime.get("user_status") if status_filter not in ("вышло", "выходит", "анонсировано", "отменено") else anime.get("status", "").lower()
            if anime_status != status_filter:
                match_anime = False

        if not match_anime:
            continue

        filtered_seasons = []
        for season in anime.get("seasons", []):
            match_season = True

            # Filter name seasons
            if search_query_season and not (
                search_query_season in season.get("name", "").lower() or
                search_query_season in season.get("russian", "").lower()
            ):
                match_season = False

            #Filter status seasons
            if status_filter_season:
                season_status = season.get("user_status") if status_filter_season not in ("вышло", "выходит", "анонсировано", "отменено") else season.get("status", "").lower()
                if season_status != status_filter_season:
                    match_season = False

            if match_season:
                filtered_seasons.append(season)

        anime_copy = anime.copy()
        anime_copy["seasons"] = filtered_seasons
        result.append(anime_copy)

    # Off pagination on request with full=false in api
    if full == "false":
        # Return data without pagination
        return jsonify({
            "anime_list": result,
        })

    # Pagination
    per_page = 5
    total_items = len(result)
    total_pages = (total_items + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    anime_list = result[start:end]

    # Return data with pagination
    return jsonify({
        "anime_list": anime_list,
        "total_pages": total_pages,
    })

# Update anime variables
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
            if not info:
                return "Not found", 404

            # Update main anime
            anime["url"] = info.get("url", anime.get("url", ""))
            anime["user_status"] = new_status or anime.get("user_status", "буду смотреть")
            anime["episodes"] = info.get("episodes", anime.get("episodes", 0))

            seasons = anime.get("seasons", [])
            season_found = False

            # Add copy anime how one season
            for season in seasons:
                if season.get("name") == info["name"]:
                    season.update(info)
                    break
            else:
                seasons.insert(0, info.copy())

            anime["seasons"] = seasons
            data[i] = anime
            save_data(data)
            return "Updated"

        # Update seasons anime
        for j, season in enumerate(anime.get("seasons", [])):
            if season["name"] == name:
                info = get_shikimori_anime(name)
                if not info:
                    return "Not found", 404

                info["url"] = req.get("url", season.get("url", ""))
                info["user_status"] = new_status or season.get("user_status", "буду смотреть")
                anime["seasons"][j] = {**season, **info}
                data[i] = anime

                save_data(data)
                return "Updated (season)"

    return "Anime not found", 404

# Anime update user status
@app.route("/api/anime/<name>/status", methods=["PUT"])
def update_status(name):
    name = unquote(name)
    req = request.json
    new_status = req.get("user_status")
    if not new_status:
        return "Missing user_status", 400

    data = load_data()
    updated = False

    for anime in data:
        main_match = anime["name"] == name
        season_match = False

        if main_match:
            anime["user_status"] = new_status
            updated = True

        for season in anime.get("seasons", []):
            if season.get("name") == name:
                season["user_status"] = new_status
                season_match = True
                updated = True

        if main_match or season_match:
            if anime["name"] == name:
                for season in anime.get("seasons", []):
                    if season.get("name") == name:
                        season["user_status"] = new_status
            elif any(season.get("name") == name for season in anime.get("seasons", [])):
                anime["user_status"] = new_status

        if updated:
            break

    if not updated:
        return "Anime or season not found", 404

    save_data(data)
    return "Status updated"

# Update url in anime
@app.route("/api/anime/<name>/url", methods=["PUT"])
def update_url(name):
    req = request.json
    new_url = req.get("url")
    if not new_url:
        return "Missing URL", 400

    data = load_data()
    updated = False

    # Main
    for anime in data:
        if anime["name"] == name:
            anime["url"] = new_url
            updated = True
            break
        # Season
        if "seasons" in anime:
            for season in anime["seasons"]:
                if season["name"] == name:
                    season["url"] = new_url
                    updated = True
                    break

    if not updated:
        return "Anime or Season not found", 404

    save_data(data)
    return "URL updated"

# Delete anime
@app.route("/api/anime/<name>", methods=["DELETE"])
def delete_anime(name):
    data = load_data()
    new_data = []

    found = False
    
    # Main
    for anime in data:
        if anime["name"] == name:
            found = True
            continue

        # Season
        if "seasons" in anime:
            original_len = len(anime["seasons"])
            anime["seasons"] = [s for s in anime["seasons"] if s["name"] != name]
            if len(anime["seasons"]) != original_len:
                found = True

        new_data.append(anime)

    if not found:
        return "Anime or Season not found", 404

    save_data(new_data)
    return "Deleted"

# Add anime
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

    info["seasons"] = [info.copy()]

    data = load_data()
    if any(anime["name"] == info["name"] for anime in data):
        return "Already exists", 400

    data.append(info)
    save_data(data)
    return "OK"

# Move anime in main list
@app.route("/api/anime/<name>/move", methods=["PUT"])
def move_anime(name):
    direction = request.args.get("direction")
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

# Add season
@app.route("/api/anime/<name>/add_season", methods=["POST"])
def add_season(name):
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

    for anime in data:
        if anime["name"] == name:
            if "seasons" not in anime:
                anime["seasons"] = []

            # Проверка на дубликат по имени или URL
            if any(s["name"] == info["name"] for s in anime["seasons"]):
                return "Season already exists", 400

            anime["seasons"].append(info)
            save_data(data)
            return "Season added", 200

    return "Anime not found", 404

# Index.html file 
@app.route('/')
def serve_index():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) # For all interfaces
    #app.run(debug=True) # For localhost 127.0.0.1
