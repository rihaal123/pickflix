import streamlit as st
import requests
import sqlite3
from contextlib import closing

# --- Database Setup ---
DATABASE = 'users.db'


def init_db():
    with closing(sqlite3.connect(DATABASE)) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                movie_id INTEGER,
                title TEXT,
                year TEXT,
                poster_url TEXT,
                UNIQUE(username, movie_id),
                FOREIGN KEY(username) REFERENCES users(username)
            )
        ''')
        conn.commit()


init_db()


# --- User Authentication Functions ---
def register_user(username, password):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users VALUES (?,?)', (username, password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def authenticate_user(username, password):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        return cursor.fetchone() is not None


# --- Watchlist Functions ---
def add_to_watchlist(username, movie_id, title, year, poster_url):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO watchlist (username, movie_id, title, year, poster_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, movie_id, title, year, poster_url))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_from_watchlist(username, movie_id):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM watchlist 
            WHERE username=? AND movie_id=?
        ''', (username, movie_id))
        conn.commit()
        return cursor.rowcount > 0


def get_watchlist(username):
    with closing(sqlite3.connect(DATABASE)) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT movie_id, title, year, poster_url 
            FROM watchlist 
            WHERE username=?
            ORDER BY id DESC
        ''', (username,))
        return cursor.fetchall()


# --- UI Configuration ---
st.set_page_config(page_title="Movie Recommender", layout="wide")

# --- Session State Management ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'show_register' not in st.session_state:
    st.session_state.show_register = False
if 'similar_movies' not in st.session_state:
    st.session_state.similar_movies = []
if 'show_watchlist' not in st.session_state:
    st.session_state.show_watchlist = False

# Show login form by default if not logged in
if not st.session_state.logged_in:
    if not st.session_state.show_register and not st.session_state.show_login:
        st.session_state.show_login = True

# --- Header Section ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    if st.session_state.logged_in:
        st.header(f"🎬    PickFlix | Movie Recommendation System")
        st.subheader(f"Hoady {st.session_state.username}!")
    else:
        st.header(f"🎬    PickFlix | Movie Recommendation System")

# --- Login/Register/Sign Out Buttons ---
with header_col2:
    if st.session_state.logged_in:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📺 Watchlist"):
                st.session_state.show_watchlist = not st.session_state.show_watchlist
        with col2:
            if st.button("Sign Out"):
                st.session_state.logged_in = False
                st.session_state.username = None
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Register"):
                st.session_state.show_register = True
        with col2:
            if st.button("Sign In"):
                st.session_state.show_login = True

# --- Registration Form ---
if st.session_state.show_register and not st.session_state.logged_in:
    with st.form("Register Form"):
        st.subheader("Register")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")

        if st.form_submit_button("Create Account"):
            if register_user(new_username, new_password):
                st.success("Account created! You can now login.")
                st.session_state.show_register = False
            else:
                st.error("Username already exists!")

# --- Login Form ---
if st.session_state.show_login and not st.session_state.logged_in:
    with st.form("Login Form"):
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.show_login = False
                st.rerun()
            else:
                st.error("Invalid credentials")

# --- Main App Content ---
if st.session_state.logged_in:
    # --- Watchlist Display ---
    if st.session_state.show_watchlist:
        st.subheader("🎥 Your Watchlist")
        watchlist = get_watchlist(st.session_state.username)

        if not watchlist:
            st.info("Your watchlist is empty. Add movies from recommendations!")
        else:
            cols = st.columns(5)
            for idx, (movie_id, title, year, poster_url) in enumerate(watchlist):
                with cols[idx % 5]:
                    st.subheader(title)
                    if poster_url:
                        st.image(poster_url)
                    else:
                        st.text("Poster not available 🖼️")
                    st.caption(f"Year: {year}" if year else "Year unknown")
                    if st.button(f"Remove {title}", key=f"remove_{movie_id}"):
                        if remove_from_watchlist(st.session_state.username, movie_id):
                            st.success(f"Removed {title} from watchlist!")
                            st.rerun()
                        else:
                            st.error("Failed to remove movie")

    # --- Updated Movie Recommendation Code with Descriptions ---
    API_KEY = "c3b0384541f672773a23574a68109f1c"


    def search_movies(query):
        url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}"
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return sorted(results, key=lambda x: x.get('popularity', 0), reverse=True)
        return []


    def fetch_poster(movie_id):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("poster_path"):
                return f"https://image.tmdb.org/t/p/w500/{data['poster_path']}"
        return None


    def fetch_similar_movies(movie_id):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/similar?api_key={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("results", [])[:5]
        return []


    def recommend(movie_id):
        similar_movies = fetch_similar_movies(movie_id)
        posters = [fetch_poster(movie["id"]) for movie in similar_movies]
        descriptions = [movie.get("overview", "No description available") for movie in similar_movies]
        return (
            [movie["title"] for movie in similar_movies],
            posters,
            descriptions,
            similar_movies
        )


    # --- Movie Search Interface ---
    search_query = st.text_input("Search for a movie to get recommendations:")

    if search_query:
        search_results = search_movies(search_query)
        if search_results:
            movie_options = []
            for movie in search_results:
                title = movie["title"]
                year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Year unknown"
                display_text = f"{title} ({year})" if year else title
                movie_options.append(display_text)

            selected_display = st.selectbox("Select a movie (sorted by popularity):", movie_options)
            selected_index = movie_options.index(selected_display)
            selected_movie = search_results[selected_index]
            movie_id = selected_movie["id"]

            if st.button('Show Recommendations'):
                names, posters, descriptions, similar_movies = recommend(movie_id)
                st.session_state.similar_movies = similar_movies
                st.session_state.posters = posters
                st.session_state.names = names
                st.session_state.descriptions = descriptions

    # --- Recommendations Display with Descriptions ---
    if st.session_state.similar_movies:
        cols = st.columns(5)
        for idx, col in enumerate(cols):
            if idx < len(st.session_state.names):
                movie_data = st.session_state.similar_movies[idx]
                with col:
                    # Generate TMDB URL
                    tmdb_url = f"https://www.themoviedb.org/movie/{movie_data['id']}"

                    # Clickable title only
                    st.markdown(f"[{st.session_state.names[idx]}]({tmdb_url})")

                    # Regular poster display
                    if st.session_state.posters[idx]:
                        st.image(st.session_state.posters[idx])
                    else:
                        st.text("Poster not available 🖼️")

                    # Rest remains the same
                    description = st.session_state.descriptions[idx]
                    st.markdown(
                        f"<div style='font-size: 14px; color: #666; height: 150px; overflow-y: auto; margin: 10px 0;'>"
                        f"{description}"
                        "</div>",
                        unsafe_allow_html=True
                    )

                    release_year = movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else ''
                    btn_key = f"add_{movie_data['id']}_{idx}"
                    if st.button("➕ Add to Watchlist", key=btn_key):
                        success = add_to_watchlist(
                            st.session_state.username,
                            movie_data['id'],
                            movie_data['title'],
                            release_year,
                            st.session_state.posters[idx]
                        )
                        if success:
                            st.success("Added to watchlist!")
                        else:
                            st.error("Movie already in watchlist!")

else:
    st.info("Please register or sign in to use the recommendation system")