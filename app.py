from flask import Flask, request, jsonify, render_template
from datetime import datetime
import requests
import json
import os
from urllib.parse import unquote
import sqlite3


app = Flask(__name__)
# Database file
DB_FILE = 'anime_list.db'
BASE_URL = "https://shikimori.one"

# Names months on russian language
russian_months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

# Database initialization
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Anime table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anime (
        id INT,
        original_name TEXT,
        russian_name TEXT,
        preview_url TEXT,
        rating TEXT,
        episodes TEXT,
        start_date_label TEXT,
        start_date TEXT,
        last_date TEXT,
        status TEXT,
        anime_url TEXT,
        user_status TEXT,
        order_index INTEGER PRIMARY KEY AUTOINCREMENT
    )
    """)

    # Season table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id INT,
        parent_id INTEGER,
        original_name TEXT,
        russian_name TEXT,
        preview_url TEXT,
        rating TEXT,
        episodes TEXT,
        start_date_label TEXT,
        start_date TEXT,
        last_date TEXT,
        status TEXT,
        anime_url TEXT,
        user_status TEXT,
        order_index INTEGER,
        FOREIGN KEY(parent_id) REFERENCES anime(id)
    )
    """)

    conn.commit()
    conn.close()

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
    id_anime = anime["id"]

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
        "id": id_anime,
        "original_name": romaji_name,
        "russian_name": russian_name,
        "preview_url": preview,
        "rating": rating,
        "episodes": episodes,
        "start_date_label": label_aired,
        "start_date": aired,
        "last_date": released,
        "status": status_label
    }

# Function to get anime list from json file and generate data
@app.route("/api/anime-list")
def anime_list():
    page = int(request.args.get("page", 1))
    full = request.args.get("full")
    status_filter = request.args.get("status")
    search_query = request.args.get("search", "").lower()
    search_query_season = request.args.get("search_season", "").lower()
    status_filter_season = request.args.get("status_season")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM anime"
    conditions = []
    params = []

    if search_query:
        conditions.append("(LOWER(original_name) LIKE ? OR LOWER(russian_name) LIKE ?)")
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    if status_filter:
        if status_filter in ("Вышло", "Выходит", "Анонсировано", "Отменено"):
            conditions.append("status = ?")
            params.append(status_filter)
        else:
            conditions.append("user_status = ?")
            params.append(status_filter)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY order_index ASC"
    cursor.execute(query, params)
    anime_rows = cursor.fetchall()

    result = []

    for anime in anime_rows:
        anime_dict = dict(anime)
        anime_dict["number"] = anime_dict.get("order_index")

        season_query = "SELECT * FROM seasons WHERE parent_id = ?"
        season_conditions = []
        season_params = [anime["id"]]

        if search_query_season:
            season_conditions.append("(LOWER(original_name) LIKE ? OR LOWER(russian_name) LIKE ?)")
            season_params.extend([f"%{search_query_season}%", f"%{search_query_season}%"])

        if status_filter_season:
            if status_filter_season in ("Вышло", "Выходит", "Анонсировано", "Отменено"):
                season_conditions.append("status = ?")
                season_params.append(status_filter_season)
            else:
                season_conditions.append("user_status = ?")
                season_params.append(status_filter_season)

        if season_conditions:
            season_query += " AND " + " AND ".join(season_conditions)

        season_query += " ORDER BY order_index ASC"
        cursor.execute(season_query, season_params)
        seasons = cursor.fetchall()

        seasons_list = []
        for season in seasons:
            season_dict = dict(season)
            season_dict["number"] = season_dict.get("order_index")
            seasons_list.append(season_dict)

        anime_dict["seasons"] = seasons_list
        result.append(anime_dict)

    conn.close()

    # Off pagination on request with full=false in api
    if full == "false":
        return jsonify({
            "anime_list": result,
        })

    # Pagination
    per_page = 5
    total_items = len(result)
    total_pages = (total_items + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    anime_list_page = result[start:end]

    return jsonify({
        "anime_list": anime_list_page,
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

    info = get_shikimori_anime(name)
    if not info:
        return "Not found", 404

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM anime WHERE original_name = ? OR russian_name = ?
    """, (name, name))
    anime = cursor.fetchone()

    if anime:
        anime_id = anime["id"]

        cursor.execute("""
            UPDATE anime SET
                preview_url = ?,
                rating = ?,
                episodes = ?,
                start_date_label = ?,
                start_date = ?,
                last_date = ?,
                status = ?,
                anime_url = ?,
                user_status = ?
            WHERE id = ?
        """, (
            info.get("preview_url", anime["preview_url"]),
            info.get("rating", anime["rating"]),
            info.get("episodes", anime["episodes"]),
            info.get("start_date_label", anime["start_date_label"]),
            info.get("start_date", anime["start_date"]),
            info.get("last_date", anime["last_date"]),
            info.get("status", anime["status"]),
            info.get("anime_url", anime["anime_url"]),
            new_status or anime["user_status"],
            anime_id
        ))

        cursor.execute("""
            SELECT * FROM seasons WHERE parent_id = ? AND (original_name = ? OR russian_name = ?)
        """, (anime_id, info["original_name"], info["russian_name"]))
        season = cursor.fetchone()

        if not season:
            cursor.execute("""
                INSERT INTO seasons (
                    parent_id, original_name, russian_name,
                    preview_url, rating, episodes, start_date_label,
                    start_date, last_date, status, anime_url, user_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anime_id,
                info.get("original_name"),
                info.get("russian_name"),
                info.get("preview_url"),
                info.get("rating"),
                info.get("episodes"),
                info.get("start_date_label"),
                info.get("start_date"),
                info.get("last_date"),
                info.get("status"),
                req.get("anime_url", anime["anime_url"]),
                new_status or anime["user_status"]
            ))

        conn.commit()
        conn.close()
        return "Updated"

    cursor.execute("""
        SELECT * FROM seasons WHERE original_name = ? OR russian_name = ?
    """, (name, name))
    season = cursor.fetchone()

    if season:
        cursor.execute("""
            UPDATE seasons SET
                preview_url = ?,
                rating = ?,
                episodes = ?,
                start_date_label = ?,
                start_date = ?,
                last_date = ?,
                status = ?,
                anime_url = ?,
                user_status = ?
            WHERE id = ?
        """, (
            info.get("preview_url", season["preview_url"]),
            info.get("rating", season["rating"]),
            info.get("episodes", season["episodes"]),
            info.get("start_date_label", season["start_date_label"]),
            info.get("start_date", season["start_date"]),
            info.get("last_date", season["last_date"]),
            info.get("status", season["status"]),
            req.get("anime_url", season["anime_url"]),
            new_status or season["user_status"],
            season["id"]
        ))

        conn.commit()
        conn.close()
        return "Updated (season)"

    conn.close()
    return "Anime not found", 404

# Update url in anime
@app.route("/api/anime/<name>/url", methods=["PUT"])
def update_url(name):
    name = unquote(name)
    req = request.get_json()
    new_url = req.get("anime_url")
    if not new_url:
        return "Missing anime_url", 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE anime
        SET anime_url = ?
        WHERE original_name = ? OR russian_name = ?
    """, (new_url, name, name))

    if cursor.rowcount >= 0:
        cursor.execute("""
            UPDATE seasons
            SET anime_url = ?
            WHERE original_name = ? OR russian_name = ?
        """, (new_url, name, name))

        if cursor.rowcount == 0:
            conn.close()
            return "Anime or Season not found", 404

    conn.commit()
    conn.close()
    return "anime_url updated"


# Anime update user status
@app.route("/api/anime/<name>/status", methods=["PUT"])
def update_status(name):
    name = unquote(name)
    req = request.json
    new_status = req.get("user_status")
    if not new_status:
        return "Missing user_status", 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM anime WHERE original_name = ?", (name,))
    result = cursor.fetchone()

    if result:
        anime_id = result[0]
        
        cursor.execute("UPDATE anime SET user_status = ? WHERE id = ?", (new_status, anime_id))

        conn.commit()

        cursor.execute("UPDATE seasons SET user_status = ? WHERE parent_id = ? AND original_name = ?", 
                       (new_status, anime_id, name))

        conn.commit()
        conn.close()
        return "Status updated (anime + matching season)"

    cursor.execute("SELECT parent_id FROM seasons WHERE original_name = ?", (name,))
    season_result = cursor.fetchone()

    if season_result:
        parent_anime_id = season_result[0]
        
        cursor.execute("UPDATE seasons SET user_status = ? WHERE parent_id = ? AND original_name = ?", 
                       (new_status, parent_anime_id, name))

        conn.commit()
        conn.close()
        return "Status updated (season)"
    
    conn.close()
    return "Anime or season not found", 404



# Delete anime
@app.route("/api/anime/<name>", methods=["DELETE"])
def delete_anime(name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM anime WHERE original_name = ?", (name,))
    anime_result = cursor.fetchone()
    
    if anime_result:
        anime_id = anime_result[0]
        cursor.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
        cursor.execute("DELETE FROM seasons WHERE parent_id = ?", (anime_id,))
        conn.commit()
        conn.close()
        return "Deleted anime and its seasons"
    
    cursor.execute("SELECT id, parent_id FROM seasons WHERE original_name = ?", (name,))
    season_result = cursor.fetchone()
    
    if season_result:
        season_id = season_result[0]
        cursor.execute("DELETE FROM seasons WHERE id = ?", (season_id,))
        conn.commit()

        conn.close()
        return f"Deleted season from anime {parent_anime_id}"

    conn.close()
    return "Anime or Season not found", 404

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

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM anime WHERE original_name = ?", (info["original_name"],))

    existing_anime = cursor.fetchone()

    if existing_anime:
        return "Already exists", 400

    cursor.execute('''
        INSERT INTO anime (id, original_name, russian_name, preview_url, rating, episodes, start_date_label, start_date, last_date, status, anime_url, user_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        info.get("id", 0),
        info["original_name"],
        info.get("russian_name", ""),
        info.get("preview_url", ""),
        info.get("rating", 0),
        info.get("episodes", 0),
        info.get("start_date_label", ""),
        info.get("start_date", ""),
        info.get("last_date", ""),
        info.get("status", ""),
        info["url"],
        info["user_status"]
    ))

    cursor.execute('''
        INSERT INTO seasons (parent_id, id, original_name, russian_name, preview_url, rating, episodes, start_date_label, start_date, last_date, status, anime_url, user_status, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (

        info.get("id", 0),
        info.get("id", 0),
        info["original_name"],
        info.get("russian_name", ""),
        info.get("preview_url", ""),
        info.get("rating", 0),
        info.get("episodes", 0),
        info.get("start_date_label", ""),
        info.get("start_date", ""),
        info.get("last_date", ""),
        info.get("status", ""),
        info["url"],
        info["user_status"],
        1
    ))

    conn.commit()
    conn.close()

    return "OK"

# Move anime in main list
@app.route("/api/anime/<int:anime_id>/move", methods=["PUT"])
def move_anime(anime_id):
    direction = request.args.get("direction")
    if direction not in ("up", "down"):
        return "Invalid direction", 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT order_index FROM anime WHERE id = ?", (anime_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Anime not found", 404

    current_index = row[0]

    if direction == "up":
        cursor.execute("""
            SELECT id, order_index FROM anime
            WHERE order_index < ?
            ORDER BY order_index DESC
            LIMIT 1
        """, (current_index,))
    else:
        cursor.execute("""
            SELECT id, order_index FROM anime
            WHERE order_index > ?
            ORDER BY order_index ASC
            LIMIT 1
        """, (current_index,))

    neighbor = cursor.fetchone()

    if not neighbor:
        conn.close()
        return "Cannot move in that direction", 400

    neighbor_id, neighbor_index = neighbor

    try:
        temp_index = -1

        cursor.execute("UPDATE anime SET order_index = ? WHERE id = ?", (temp_index, anime_id))
        cursor.execute("UPDATE anime SET order_index = ? WHERE id = ?", (current_index, neighbor_id))
        cursor.execute("UPDATE anime SET order_index = ? WHERE id = ?", (neighbor_index, anime_id))

        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        return f"Database error: {e}", 500

    conn.close()
    return "Moved", 200


# Move anime in season list
@app.route("/api/season/<int:season_id>/move", methods=["PUT"])
def move_season(season_id):
    direction = request.args.get("direction")
    parent_id = request.args.get("parent_id")

    if direction not in ("up", "down"):
        return "Invalid direction", 400

    if not parent_id:
        return "Missing parent_id", 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT order_index FROM seasons WHERE id = ? AND parent_id = ?", (season_id, parent_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "Season not found", 404

    current_index = row[0]

    if direction == "up":
        cursor.execute("""
            SELECT id, order_index FROM seasons
            WHERE parent_id = ? AND order_index < ?
            ORDER BY order_index DESC
            LIMIT 1
        """, (parent_id, current_index))
    else:
        cursor.execute("""
            SELECT id, order_index FROM seasons
            WHERE parent_id = ? AND order_index > ?
            ORDER BY order_index ASC
            LIMIT 1
        """, (parent_id, current_index))

    neighbor = cursor.fetchone()

    if not neighbor:
        conn.close()
        return "Cannot move in that direction", 400

    neighbor_id, neighbor_index = neighbor

    try:
        temp_index = -1

        cursor.execute("UPDATE seasons SET order_index = ? WHERE id = ?", (temp_index, season_id))
        cursor.execute("UPDATE seasons SET order_index = ? WHERE id = ?", (current_index, neighbor_id))
        cursor.execute("UPDATE seasons SET order_index = ? WHERE id = ?", (neighbor_index, season_id))

        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        return f"Database error: {e}", 500

    conn.close()
    return "Moved", 200




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

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM anime WHERE original_name = ? OR russian_name = ?", (name, name))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return "Anime not found", 404

    parent_id = row[0]

    cursor.execute("""
        SELECT 1 FROM seasons
        WHERE parent_id = ? AND (original_name = ? OR russian_name = ?)
    """, (parent_id, info["original_name"], info["russian_name"]))
    if cursor.fetchone():
        conn.close()
        return "Season already exists", 400

    cursor.execute("SELECT MAX(order_index) FROM seasons WHERE parent_id = ?", (parent_id,))
    result = cursor.fetchone()
    max_index = result[0] if result[0] is not None else -1
    new_order_index = max_index + 1

    cursor.execute("""
        INSERT INTO seasons (
            id, parent_id, original_name, russian_name,
            preview_url, rating, episodes, start_date_label,
            start_date, last_date, status, anime_url,
            user_status, order_index
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        info["id"],
        parent_id,
        info["original_name"],
        info["russian_name"],
        info["preview_url"],
        info["rating"],
        info["episodes"],
        info["start_date_label"],
        info["start_date"],
        info["last_date"],
        info["status"],
        url,
        user_status,
        new_order_index
    ))

    conn.commit()
    conn.close()
    return "Season added", 200


# Index.html file 
@app.route('/')
def serve_index():
    return render_template('index.html')


if __name__ == "__main__":
    init_db()
    #app.run(host="0.0.0.0", port=5000, debug=True) # For all interfaces
    app.run(debug=True) # For localhost 127.0.0.1
