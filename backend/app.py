from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import sqlite3
import json
import random
import os
import hashlib
from datetime import datetime, timedelta
import uuid
import time
from flask_cors import CORS
from functools import wraps

# Try to import dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not available. Using environment variables directly.")

# Try to import requests, but don't fail if it's not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not available. Some features may be limited.")

# Try to import OpenAI, but don't fail if it's not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. Using mock data.")

# Try to import Google OAuth, but don't fail if it's not available
try:
    from google_auth_oauthlib.flow import Flow
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    GOOGLE_OAUTH_AVAILABLE = True
    
    # Allow OAuth2 to work with HTTP for development
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False
    print("Warning: Google OAuth not available. Login will be disabled.")

# Load environment variables (already done in try/catch above)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app, supports_credentials=True)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = 'http://localhost:5000/auth/google/callback'

# OAuth 2.0 configuration
oauth_config = {
    'web': {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': [GOOGLE_REDIRECT_URI],
        'scopes': ['openid', 'email', 'profile']
    }
}

# Configure OpenAI
if OPENAI_AVAILABLE:
    openai.api_key = os.getenv('OPENAI_API_KEY')
    if not openai.api_key:
        print("Warning: OPENAI_API_KEY not found. Using mock data for itinerary generation.")
else:
    print("Warning: OpenAI not available. Using mock data for itinerary generation.")

# Database setup
DB_NAME = "trip_planner.db"

# User roles
ROLE_USER = 'user'
ROLE_ADMIN = 'admin'
ROLE_ROOT = 'root'

# Admin emails (you can modify these)
ADMIN_EMAILS = [
    'admin@travelplanner.com',
    'root@travelplanner.com'
]

def init_db():
    """Initialize the SQLite database with required tables (idempotent)."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            picture TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Trips table per spec
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            name TEXT,
            age INTEGER,
            gender TEXT,
            country TEXT,
            state TEXT,
            city TEXT,
            destination TEXT NOT NULL,
            start_date TEXT,
            days INTEGER NOT NULL,
            mood TEXT,
            budget_range_inr TEXT,
            interests TEXT,
            pois_json TEXT,
            hotels_json TEXT,
            itinerary_text TEXT,
            packing_list_json TEXT,
            weather_json TEXT,
            events_json TEXT,
            map_data_json TEXT,
            total_budget_inr TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Cache table for storing POIs/hotels lookups
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plan_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            destination TEXT NOT NULL,
            days INTEGER NOT NULL,
            mood TEXT NOT NULL,
            plan_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if not exists
    try:
        cursor.execute('SELECT * FROM users WHERE email = ?', ('admin@travelplanner.com',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (google_id, email, name, role) 
                VALUES (?, ?, ?, ?)
            ''', ('admin_default', 'admin@travelplanner.com', 'System Admin', ROLE_ROOT))
    except Exception as e:
        print(f"Error creating default admin: {e}")
    
    conn.commit()
    # Ensure schema has all expected columns even if an older DB exists
    try:
        expected_columns = {
            'user_id': 'INTEGER',
            'name': 'TEXT',
            'age': 'INTEGER',
            'gender': 'TEXT',
            'country': 'TEXT',
            'state': 'TEXT',
            'city': 'TEXT',
            'destination': 'TEXT',
            'start_date': 'TEXT',
            'days': 'INTEGER',
            'mood': 'TEXT',
            'budget_range_inr': 'TEXT',
            'interests': 'TEXT',
            'pois_json': 'TEXT',
            'hotels_json': 'TEXT',
            'itinerary_text': 'TEXT',
            'packing_list_json': 'TEXT',
            'weather_json': 'TEXT',
            'events_json': 'TEXT',
            'map_data_json': 'TEXT',
            'total_budget_inr': 'TEXT'
        }
        cursor.execute("PRAGMA table_info(trips)")
        existing = {row[1] for row in cursor.fetchall()}
        for col, coltype in expected_columns.items():
            if col not in existing:
                cursor.execute(f"ALTER TABLE trips ADD COLUMN {col} {coltype}")
        conn.commit()
    except Exception as e:
        print(f"Schema ensure error: {e}")
    finally:
        conn.close()

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_role = session['user'].get('role', ROLE_USER)
        if user_role not in [ROLE_ADMIN, ROLE_ROOT]:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def root_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_role = session['user'].get('role', ROLE_USER)
        if user_role != ROLE_ROOT:
            return jsonify({'error': 'Root access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Get current user ID from session"""
    if 'user' not in session:
        return None
    return session['user'].get('id')

def get_current_user_role():
    """Get current user role from session"""
    if 'user' not in session:
        return ROLE_USER
    return session['user'].get('role', ROLE_USER)

def can_access_plan(user_id, plan_user_id, user_role):
    """Check if user can access a specific plan"""
    if user_role in [ROLE_ADMIN, ROLE_ROOT]:
        return True
    return user_id == plan_user_id

# Initialize database on startup
init_db()

def _enable_pragmas(conn):
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass

def migrate_trips_schema_if_needed():
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        _enable_pragmas(conn)
        cur = conn.cursor()
        # Detect existing trips table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trips'")
        if not cur.fetchone():
            conn.close()
            return
        cur.execute("PRAGMA table_info(trips)")
        cols = [row[1] for row in cur.fetchall()]
        expected = {"unique_id","user_id","name","age","gender","country","state","city","destination","start_date","days","mood","budget_range_inr","interests","pois_json","hotels_json","itinerary_text","packing_list_json","weather_json","events_json","map_data_json","total_budget_inr","created_at","updated_at"}
        needs_migration = ("plan" in cols) or (not expected.issubset(set(cols)))
        if not needs_migration:
            conn.close()
            return

        cur.execute("ALTER TABLE trips RENAME TO trips_old;")
        # Create new table per current schema
        cur.execute('''
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                name TEXT,
                age INTEGER,
                gender TEXT,
                country TEXT,
                state TEXT,
                city TEXT,
                destination TEXT NOT NULL,
                start_date TEXT,
                days INTEGER NOT NULL,
                mood TEXT,
                budget_range_inr TEXT,
                interests TEXT,
                pois_json TEXT,
                hotels_json TEXT,
                itinerary_text TEXT,
                packing_list_json TEXT,
                weather_json TEXT,
                events_json TEXT,
                map_data_json TEXT,
                total_budget_inr TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Determine old cols again
        cur.execute("PRAGMA table_info(trips_old)")
        old_cols = {row[1] for row in cur.fetchall()}

        def src(col, default):
            return col if col in old_cols else default

        # Build dynamic insert mapping excluding id
        target_cols = [
            'unique_id','user_id','name','age','gender','country','state','city','destination','start_date','days','mood','budget_range_inr',
            'interests','pois_json','hotels_json','itinerary_text','packing_list_json','weather_json','events_json','map_data_json','total_budget_inr','created_at','updated_at'
        ]

        select_exprs = [
            src('unique_id', "lower(hex(randomblob(16)))"),
            src('user_id', 'NULL'),
            src('name', "''"),
            src('age', 'NULL'),
            src('gender', "''"),
            src('country', "''"),
            src('state', "''"),
            src('city', "''"),
            src('destination', "'Unknown'"),
            src('start_date', "''"),
            src('days', '3'),
            src('mood', "''"),
            src('budget_range_inr', "''"),
            src('interests', "'[]'"),
            src('pois_json', "'[]'"),
            src('hotels_json', "'[]'"),
            ('COALESCE(plan, \"[]\")' if 'plan' in old_cols else (src('itinerary_text', "'[]'"))),
            src('packing_list_json', "'[]'"),
            src('weather_json', "'[]'"),
            src('events_json', "'[]'"),
            src('map_data_json', "'{}'"),
            src('total_budget_inr', "''"),
            src('created_at', 'CURRENT_TIMESTAMP'),
            'CURRENT_TIMESTAMP'
        ]

        insert_sql = f"INSERT INTO trips ({', '.join(target_cols)}) SELECT {', '.join(select_exprs)} FROM trips_old"
        cur.execute(insert_sql)
        cur.execute("DROP TABLE trips_old")
        conn.commit()
        conn.close()
        print("DB migration completed: trips schema updated")
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        print(f"DB migration error: {e}")

migrate_trips_schema_if_needed()

# In-memory caches for 6 hours
PLACES_CACHE = {}
HOTELS_CACHE = {}
CACHE_TTL_SECONDS = 6 * 60 * 60

def _cache_get(cache_dict, key):
    now = time.time()
    entry = cache_dict.get(key)
    if entry and now - entry['ts'] < CACHE_TTL_SECONDS:
        return entry['data']
    return None

def _cache_set(cache_dict, key, data):
    cache_dict[key] = {'data': data, 'ts': time.time()}

def generate_cache_key(destination, days, mood):
    """Generate a unique cache key for the plan"""
    key_string = f"{destination.lower().strip()}_{days}_{mood.lower()}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_cached_plan(destination, days, mood):
    """Get cached plan if it exists and is less than 24 hours old"""
    try:
        cache_key = generate_cache_key(destination, days, mood)
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Get plan from cache if it's less than 24 hours old
        cursor.execute('''
            SELECT plan_data FROM plan_cache 
            WHERE cache_key = ? AND created_at > datetime('now', '-24 hours')
        ''', (cache_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
        
    except Exception as e:
        print(f"Cache retrieval error: {e}")
        return None

def cache_plan(destination, days, mood, plan_data):
    """Cache the generated plan"""
    try:
        cache_key = generate_cache_key(destination, days, mood)
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO plan_cache (cache_key, destination, days, mood, plan_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (cache_key, destination, days, mood, json.dumps(plan_data)))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Cache storage error: {e}")

def get_destination_coordinates(destination):
    """Get coordinates for a destination using OpenWeatherMap Geocoding API"""
    try:
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            return None
        
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={destination}&limit=1&appid={api_key}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data and len(data) > 0:
            return {
                'lat': data[0]['lat'],
                'lon': data[0]['lon'],
                'name': data[0]['name'],
                'country': data[0]['country']
            }
        return None
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_weather_forecast(destination, days):
    """Get weather forecast for the destination with summary and highs/lows."""
    try:
        coords = get_destination_coordinates(destination)
        if not coords:
            return generate_mock_weather_forecast(destination, days)
        
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if not api_key:
            return generate_mock_weather_forecast(destination, days)
        
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'list' not in data:
            return generate_mock_weather_forecast(destination, days)
        
        # Aggregate 3-hourly forecasts into daily highs/lows and summary
        buckets = {}
        for item in data['list']:
            date_str = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            if date_str not in buckets:
                buckets[date_str] = {
                    'temps': [],
                    'descriptions': []
                }
            buckets[date_str]['temps'].append(item['main']['temp'])
            buckets[date_str]['descriptions'].append(item['weather'][0]['description'])

        daily_forecasts = []
        current_date = datetime.now().date()
        for i in range(days):
            day_date = (current_date + timedelta(days=i)).strftime('%Y-%m-%d')
            if day_date in buckets:
                temps = buckets[day_date]['temps']
                descs = buckets[day_date]['descriptions']
                high = round(max(temps))
                low = round(min(temps))
                summary = max(set(descs), key=descs.count).title()
                daily_forecasts.append({
                    "day": f"Day {i+1}",
                    "forecast": summary,
                    "temperature": f"{high}°C/{low}°C",
                    "high": f"{high}°C",
                    "low": f"{low}°C"
                })
            else:
                high = random.randint(24, 34)
                low = high - random.randint(4, 8)
                daily_forecasts.append({
                    "day": f"Day {i+1}",
                    "forecast": "Partly Cloudy",
                    "temperature": f"{high}°C/{low}°C",
                    "high": f"{high}°C",
                    "low": f"{low}°C"
                })
        
        return daily_forecasts
        
    except Exception as e:
        print(f"Weather forecast error: {e}")
        return generate_mock_weather_forecast(destination, days)

def generate_mock_weather_forecast(destination, days):
    """Generate mock weather forecast"""
    weather_types = [
        "Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear Sky",
        "Overcast", "Misty", "Foggy", "Thunderstorm", "Drizzle"
    ]
    
    forecast = []
    for i in range(days):
        high = random.randint(25, 34)
        low = high - random.randint(4, 8)
        forecast.append({
            "day": f"Day {i+1}",
            "forecast": random.choice(weather_types),
            "temperature": f"{high}°C/{low}°C",
            "high": f"{high}°C",
            "low": f"{low}°C"
        })
    
    return forecast

def get_opentripmap_coords(city):
    """Resolve city to coordinates using OpenTripMap geoname endpoint."""
    api_key = os.getenv('OPENTRIPMAP_API_KEY')
    if not api_key:
        return None
    try:
        url = f"https://api.opentripmap.com/0.1/en/places/geoname?name={requests.utils.quote(city)}&apikey={api_key}"
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if data and 'lat' in data and 'lon' in data:
                return {"lat": data['lat'], "lon": data['lon'], "name": data.get('name')}
    except Exception as e:
        print(f"OpenTripMap geoname error: {e}")
    return None

def _fetch_wikimedia_image(title):
    try:
        api = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + requests.utils.quote(title)
        r = requests.get(api, timeout=10)
        if r.status_code == 200:
            js = r.json()
            thumb = js.get('thumbnail', {})
            if thumb.get('source'):
                return thumb['source']
    except Exception as e:
        print(f"Wikimedia image error: {e}")
    return None

def fetch_pois_from_opentripmap(city, interests_csv, days, mood=None):
    api_key = os.getenv('OPENTRIPMAP_API_KEY')
    if not api_key:
        return []
    coords = get_opentripmap_coords(city)
    if not coords:
        return []
    kinds = 'interesting_places'
    # Mood influence (accept multiple synonyms/variants)
    mood_map = {
        'relaxing': 'gardens,parks,natural',
        'relax': 'gardens,parks,natural',
        'adventurous': 'sport,natural,cliffs,caves',
        'adventure': 'sport,natural,cliffs,caves',
        'foodie': 'foods,restaurants,marketplaces',
        'romantic': 'gardens,bridges,architecture',
        'family': 'amusements,zoos,aquariums,theme_parks',
        'office trip': 'museums,art_galleries,foods,shops'
    }
    if mood:
        mkey = mood.strip().lower()
        if mkey in mood_map:
            kinds = mood_map[mkey]
    if interests_csv:
        # Map simple interests to OpenTripMap kinds
        mapping = {
            'history': 'historic',
            'nature': 'natural',
            'art': 'museums,art_galleries',
            'food': 'foods',
            'shopping': 'shops',
            'adventure': 'sport',
            'family': 'amusements',
        }
        selected = []
        for token in interests_csv.split(','):
            token = token.strip().lower()
            if token in mapping:
                selected.append(mapping[token])
        if selected:
            kinds = ','.join(selected)
    radius = 15000
    limit = 30
    try:
        url = (
            f"https://api.opentripmap.com/0.1/en/places/radius?radius={radius}&lon={coords['lon']}&lat={coords['lat']}"
            f"&kinds={requests.utils.quote(kinds)}&rate=2&format=json&limit={limit}&apikey={api_key}"
        )
        r = requests.get(url, timeout=15)
        items = r.json() if r.status_code == 200 else []
        results = []
        for item in items[: max(5, min(5, len(items)) )]:
            xid = item.get('xid')
            detail = None
            if xid:
                try:
                    d = requests.get(f"https://api.opentripmap.com/0.1/en/places/xid/{xid}?apikey={api_key}", timeout=12)
                    if d.status_code == 200:
                        detail = d.json()
                except Exception as e:
                    print(f"OTM detail error: {e}")
            name = (detail or {}).get('name') or item.get('name') or 'Unknown'
            summary = None
            if detail:
                summary = (detail.get('wikipedia_extracts') or {}).get('text') or detail.get('info', {}).get('descr')
            photo = None
            if detail:
                photo = (detail.get('preview') or {}).get('source')
            if not photo:
                photo = _fetch_wikimedia_image(name)
            source_url = (detail or {}).get('url') or (detail or {}).get('otm')
            results.append({
                'name': name,
                'xid': xid,
                'lat': item.get('point', {}).get('lat') or item.get('lat'),
                'lon': item.get('point', {}).get('lon') or item.get('lon'),
                'category': item.get('kinds'),
                'summary': summary or 'No description found',
                'source_url': source_url or '',
                'photo_url': photo or ''
            })
        return results
    except Exception as e:
        print(f"OpenTripMap fetch error: {e}")
        return []

def fetch_hotels_from_opentripmap(city, budget_min=None, budget_max=None):
    api_key = os.getenv('OPENTRIPMAP_API_KEY')
    if not api_key:
        return []
    coords = get_opentripmap_coords(city)
    if not coords:
        return []
    try:
        url = (
            f"https://api.opentripmap.com/0.1/en/places/radius?radius=15000&lon={coords['lon']}&lat={coords['lat']}"
            f"&kinds=accomodations&rate=1&format=json&limit=40&apikey={api_key}"
        )
        r = requests.get(url, timeout=15)
        items = r.json() if r.status_code == 200 else []
        hotels = []
        for i, item in enumerate(items[:15]):
            name = item.get('name') or 'Hotel'
            lat = item.get('point', {}).get('lat') or item.get('lat')
            lon = item.get('point', {}).get('lon') or item.get('lon')
            dist = item.get('dist', None)
            photo = _fetch_wikimedia_image(name)
            # Rough price tiers by rank position if no budget
            if i < 5:
                price = 2000
                tier = 'Economy'
                rng = '₹2,000–₹5,000'
            elif i < 10:
                price = 8000
                tier = 'Mid-Range'
                rng = '₹5,000–₹12,000'
            else:
                price = 18000
                tier = 'Luxury'
                rng = '₹12,000–₹30,000'
            hotels.append({
                'id': item.get('xid') or f"hotel_{i}",
                'name': f"{name} ({tier})",
                'lat': lat,
                'lon': lon,
                'distance_km': round((dist or 0)/1000, 2) if dist else None,
                'price_in_inr_est': price,
                'budget_range_inr': rng,
                'source_url': item.get('otm', ''),
                'photo_url': photo or ''
            })
        # Filter by budget range if provided
        try:
            if budget_min is not None or budget_max is not None:
                bmin = int(budget_min) if budget_min is not None else 0
                bmax = int(budget_max) if budget_max is not None else 10**9
                hotels = [h for h in hotels if bmin <= int(h['price_in_inr_est']) <= bmax]
        except Exception:
            pass
        # Return three samples across tiers if many
        selected = []
        if len(hotels) >= 3:
            selected = [hotels[0], hotels[min(5, len(hotels)-1)], hotels[-1]]
        else:
            selected = hotels
        return selected
    except Exception as e:
        print(f"OpenTripMap hotels error: {e}")
        return []

def generate_map_link(destination):
    """Generate Google Maps link for the destination"""
    try:
        coords = get_destination_coordinates(destination)
        if coords:
            return f"https://www.google.com/maps?q={coords['lat']},{coords['lon']}"
        else:
            # Fallback to search-based link
            return f"https://www.google.com/maps/search/{destination.replace(' ', '+')}"
    except Exception as e:
        print(f"Map link error: {e}")
        return f"https://www.google.com/maps/search/{destination.replace(' ', '+')}"

def generate_grounded_ai_itinerary(payload):
    """Call OpenAI with a strict system prompt to return grounded structured JSON."""
    city = payload.get('city')
    start_date = payload.get('start_date')
    days = int(payload.get('days', 3))
    mood = payload.get('mood', 'relaxing')
    interests = payload.get('interests', [])
    pois = payload.get('pois', [])
    hotels = payload.get('hotels', [])
    user_age = payload.get('age')
    user_gender = payload.get('gender')

    if not openai.api_key:
        return generate_mock_ai_json(city, start_date, days, mood, pois, hotels, user_age, user_gender)

    system_prompt = (
        "You are a meticulous travel planner. Follow ALL rules strictly:\n"
        "- Use ONLY real, well-known attractions/places. Prefer those in provided POIs; do not invent.\n"
        "- No duplicates across days.\n"
        "- Blend selected interests across each day (e.g., History in morning, Nature in afternoon, Food in evening).\n"
        "- Keep activities geographically plausible for the city.\n"
        "- Vary activity types across the trip (museums, heritage walks, parks, galleries, food tours, shopping, adventure, family).\n"
        "- Keep JSON strictly to the required schema."
    )

    user_prompt = {
        "destination": city,
        "start_date": start_date,
        "days": days,
        "mood": mood,
        "interests": interests,
        "pois": pois,
        "hotels": hotels,
        "interest_activity_hints": {
            "history": ["museum", "heritage site", "fort", "guided walking tour"],
            "nature": ["national park", "lakeside walk", "botanical garden", "hike"],
            "art": ["art gallery", "street art tour", "handicraft workshop", "museum of modern art"],
            "food": ["food tour", "street food market", "cooking class", "local cafe"],
            "shopping": ["local bazaar", "handicraft center", "mall", "night market"],
            "adventure": ["trekking", "rafting", "paragliding", "water sports"],
            "family": ["zoo", "theme park", "aquarium", "kid-friendly museum"]
        },
        "required_schema": {
            "destination": "City, Country",
            "start_date": "YYYY-MM-DD",
            "days": days,
            "mood": mood,
            "itinerary": ["list of day objects with morning/afternoon/evening/dinner/accommodation/weather"],
            "famous_places": ["3-5 items with name, description, image, source"],
            "hotels": ["3 items with name, budget_range_in_inr, image, link"],
            "packing_list": ["items"],
            "events": ["name,date,link"],
            "map_embed_url": "",
            "total_budget_inr": "₹X"
        }
    }

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt)}
            ],
            max_tokens=1400,
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        # Try to extract JSON
        try:
            # Remove code fences if any
            if content.startswith('```'):
                content = '\n'.join([line for line in content.splitlines() if not line.strip().startswith('```')])
            parsed = json.loads(content)
            # Personalize/augment packing list
            try:
                weather_list = []
                for d in (parsed.get('itinerary') or []):
                    w = d.get('weather') or {}
                    if isinstance(w, dict) and ('high' in w or 'forecast' in w):
                        weather_list.append({
                            'forecast': w.get('summary') or w.get('forecast') or '',
                            'high': w.get('high') or '',
                            'low': w.get('low') or ''
                        })
                personalized = generate_packing_list(mood, weather_list, user_age, user_gender)
                base = parsed.get('packing_list') or []
                parsed['packing_list'] = list(dict.fromkeys([*base, *personalized]))
            except Exception:
                pass
            return parsed
        except Exception:
            # Attempt to find JSON substring
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start:end+1])
                except Exception:
                    pass
        return generate_mock_ai_json(city, start_date, days, mood, pois, hotels, user_age, user_gender)
    except Exception as e:
        print(f"OpenAI error: {e}")
        return generate_mock_ai_json(city, start_date, days, mood, pois, hotels)

def generate_mock_ai_json(city, start_date, days, mood, pois, hotels, age=None, gender=None):
    """Generate AI travel plan using the new comprehensive system."""
    
    try:
        # Get weather forecast
        weather = get_weather_forecast(city, days)
        
        # Generate AI travel plan
        ai_plan = generate_ai_travel_plan(
            destination=city,
            days=days,
            mood=mood,
            name=None,  # Will be filled by frontend
            age=age,
            gender=gender,
            interests=None,  # Will be filled by frontend
            country=None,  # Will be filled by frontend
            state=None,  # Will be filled by frontend
            city=city,
            start_date=start_date,
            end_date=None,  # Will be calculated by frontend
            weather=weather
        )
    except Exception as e:
        print(f"Error in generate_mock_ai_json: {e}")
        # Fallback to basic data
        weather = generate_mock_weather_forecast(city, days)
        ai_plan = {
            'itinerary': [],
            'packing_list': ['Comfortable clothes', 'Walking shoes', 'Camera', 'Water bottle'],
            'local_events': []
        }
    
    # Convert AI plan to expected format
    itinerary = []
    try:
        for day_plan in ai_plan.get('itinerary', []):
            # Find a POI for this day
            poi = pois[day_plan.get('day', 1) - 1 % max(1, len(pois))] if pois else {}
            hotel = hotels[day_plan.get('day', 1) - 1 % max(1, len(hotels))] if hotels else {}
            
            itinerary.append({
                'day': day_plan.get('day', 1),
                'morning': {'activity': day_plan.get('morning', 'Explore the city'), 'poi': {
                    'name': poi.get('name', ''), 'lat': poi.get('lat', 0), 'lon': poi.get('lon', 0), 
                    'image': poi.get('photo_url',''), 'source': poi.get('source_url','')
                }},
                'afternoon': {'activity': day_plan.get('afternoon', 'Visit local attractions'), 'poi': {
                    'name': poi.get('name', ''), 'lat': poi.get('lat', 0), 'lon': poi.get('lon', 0), 
                    'image': poi.get('photo_url',''), 'source': poi.get('source_url','')
                }},
                'evening': {'activity': day_plan.get('evening', 'Enjoy local cuisine'), 'poi': {
                    'name': poi.get('name', ''), 'lat': poi.get('lat', 0), 'lon': poi.get('lon', 0), 
                    'image': poi.get('photo_url',''), 'source': poi.get('source_url','')
                }},
                'dinner': {'suggestion': day_plan.get('dinner', 'Try local specialties'), 'restaurant_link': ''},
                'accommodation': {'name': day_plan.get('accommodation', 'Local Hotel'), 'price_in_inr': hotel.get('budget_range_inr','₹5,000–₹12,000'), 'link': hotel.get('source_url','')},
                'weather': {'summary': weather[day_plan.get('day', 1) - 1].get('forecast','') if day_plan.get('day', 1) - 1 < len(weather) else 'Pleasant weather', 'high': weather[day_plan.get('day', 1) - 1].get('high','') if day_plan.get('day', 1) - 1 < len(weather) else '25°C', 'low': weather[day_plan.get('day', 1) - 1].get('low','') if day_plan.get('day', 1) - 1 < len(weather) else '18°C'}
            })
    except Exception as e:
        print(f"Error converting itinerary: {e}")
        # Create a basic itinerary if conversion fails
        for i in range(days):
            itinerary.append({
                'day': i + 1,
                'morning': {'activity': 'Explore the city', 'poi': {'name': 'City Center', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                'afternoon': {'activity': 'Visit local attractions', 'poi': {'name': 'Local Attractions', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                'evening': {'activity': 'Enjoy local cuisine', 'poi': {'name': 'Local Restaurants', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                'dinner': {'suggestion': 'Try local specialties', 'restaurant_link': ''},
                'accommodation': {'name': 'Local Hotel', 'price_in_inr': '₹5,000–₹12,000', 'link': ''},
                'weather': {'summary': 'Pleasant weather', 'high': '25°C', 'low': '18°C'}
            })
    
    # Convert famous places with enhanced data
    famous = []
    try:
        # Get enhanced attractions data
        enhanced_attractions = generate_must_visit_attractions(city, mood, age, gender, None)
        
        # Use enhanced attractions if available, otherwise fall back to POIs
        if enhanced_attractions:
            for attraction in enhanced_attractions[:4]:
                famous.append({
                    'name': attraction.get('name', 'Attraction'),
                    'description': attraction.get('description', 'No description'),
                    'image': attraction.get('image', ''),
                    'source': attraction.get('google_maps_link', ''),
                    'entry_fee': attraction.get('entry_fee', 'Varies'),
                    'best_time': attraction.get('best_time', 'Morning or Evening'),
                    'rating': attraction.get('rating', '4.0'),
                    'google_maps_link': attraction.get('google_maps_link', ''),
                    'category': attraction.get('category', 'general')
                })
        else:
            # Fallback to POIs if no enhanced attractions
            for p in pois[:4]:
                famous.append({
                    'name': p.get('name', 'POI'),
                    'description': p.get('summary', 'No description'),
                    'image': p.get('photo_url', ''),
                    'source': p.get('source_url', ''),
                    'entry_fee': 'Varies',
                    'best_time': 'Morning or Evening',
                    'rating': '4.0',
                    'google_maps_link': f"https://maps.google.com/?q={p.get('name', '').replace(' ', '+')}+{city.replace(' ', '+')}",
                    'category': 'general'
                })
    except Exception as e:
        print(f"Error converting famous places: {e}")
        # Create basic attractions as fallback
        famous = [
            {
                'name': 'Local Attraction',
                'description': f'Explore the best of {city}',
                'image': 'https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop',
                'source': '',
                'entry_fee': 'Varies',
                'best_time': 'Morning or Evening',
                'rating': '4.0',
                'google_maps_link': f"https://maps.google.com/?q={city.replace(' ', '+')}",
                'category': 'general'
            }
        ]
    
    # Convert hotel cards
    hotel_cards = []
    try:
        for h in hotels[:3]:
            rng = h.get('budget_range_inr') or f"₹{int(h.get('price_in_inr_est', 5000)):,}"
            hotel_cards.append({
                'name': h.get('name'),
                'budget_range_in_inr': rng,
                'image': h.get('photo_url', ''),
                'link': h.get('source_url', '')
            })
    except Exception as e:
        print(f"Error converting hotel cards: {e}")
    
    # Calculate total budget
    try:
        total_budget = estimate_budget_inr(days, hotels)
    except Exception as e:
        print(f"Error calculating budget: {e}")
        total_budget = days * 5000  # Fallback budget
    
    try:
        # Compute budget breakdown using derived attractions/hotels
        budget_breakdown = compute_budget_breakdown(days, mood, None, famous, hotel_cards)
        return {
            'destination': city,
            'start_date': start_date,
            'days': days,
            'mood': mood,
            'itinerary': itinerary,
            'famous_places': famous,
            'hotels': hotel_cards,
            'packing_list': ai_plan.get('packing_list', ['Comfortable clothes', 'Walking shoes', 'Camera', 'Water bottle']),
            'events': ai_plan.get('local_events', []),
            'map_embed_url': '',
            'total_budget_inr': f"₹{budget_breakdown['total']:,}",
            'budget_breakdown': budget_breakdown,
            # Add AI plan data for frontend use
            'ai_plan': ai_plan
        }
    except Exception as e:
        print(f"Error in final return: {e}")
        # Return minimal working response
        # Still compute a simple breakdown for consistency
        fallback_breakdown = compute_budget_breakdown(days, mood, None, famous, hotel_cards)
        return {
            'destination': city,
            'start_date': start_date,
            'days': days,
            'mood': mood,
            'itinerary': itinerary,
            'famous_places': famous,
            'hotels': hotel_cards,
            'packing_list': ['Comfortable clothes', 'Walking shoes', 'Camera', 'Water bottle'],
            'events': [],
            'map_embed_url': '',
            'total_budget_inr': f"₹{fallback_breakdown['total']:,}",
            'budget_breakdown': fallback_breakdown,
            'ai_plan': {}
        }

def estimate_budget_inr(days, hotels):
    base_daily = 2500
    hotel_daily = 0
    if hotels:
        # Average estimated price
        vals = []
        for h in hotels:
            est = h.get('price_in_inr_est')
            try:
                if est:
                    vals.append(int(est))
            except Exception:
                continue
        if vals:
            hotel_daily = sum(vals) // len(vals)
    return days * (base_daily + hotel_daily)

def _parse_inr_value(value: str | int | float) -> int:
    """Parse Indian currency strings like '₹1,200–₹3,500' or '₹500' to an integer estimate (INR)."""
    try:
        if isinstance(value, (int, float)):
            return int(value)
        if not value:
            return 0
        s = str(value)
        # pick first number sequence
        digits = []
        current = ''
        for ch in s:
            if ch.isdigit():
                current += ch
            elif current:
                digits.append(current)
                current = ''
        if current:
            digits.append(current)
        if not digits:
            return 0
        # If range like 1200, 3500 → take average-ish first
        if len(digits) >= 2:
            try:
                low = int(digits[0])
                high = int(digits[1])
                return (low + high) // 2
            except Exception:
                return int(digits[0])
        return int(digits[0])
    except Exception:
        return 0

def compute_budget_breakdown(days: int, mood: str, interests, famous_places, hotels) -> dict:
    """Derive a realistic budget breakdown from must-visit attractions, interests, and mood.
    - activities cost from attractions' entry fees
    - accommodation from hotels price estimates
    - food/transport/shopping scaled by mood & interests
    Returns a dict with accommodation, food, transportation, activities, shopping, total (all in INR ints).
    """
    try:
        d = max(int(days or 1), 1)
    except Exception:
        d = 1

    mv = (mood or '').strip().lower()
    interests = interests or []
    if isinstance(interests, str):
        interests = [i.strip() for i in interests.split(',') if i.strip()]

    # Accommodation from hotels
    hotel_vals = []
    try:
        for h in hotels or []:
            est = h.get('price_in_inr_est') or h.get('price_est') or _parse_inr_value(h.get('budget_range_inr'))
            val = _parse_inr_value(est)
            if val:
                hotel_vals.append(val)
    except Exception:
        pass
    hotel_daily = (sum(hotel_vals) // len(hotel_vals)) if hotel_vals else 2500
    accommodation = hotel_daily * d

    # Activities from famous places entry fees; assume 1-2 paid entries per day depending on mood
    activity_fees = []
    for p in famous_places or []:
        fee = _parse_inr_value(p.get('entry_fee'))
        if fee:
            activity_fees.append(fee)
    avg_fee = (sum(activity_fees) // len(activity_fees)) if activity_fees else 300
    activities_per_day = 1
    if mv in ['adventure', 'adventurous', 'foodie']:
        activities_per_day = 2
    elif mv in ['family']:
        activities_per_day = 1.5
    activities = int(avg_fee * activities_per_day * d)

    # Food baseline per day
    food_daily = 700
    if mv in ['foodie'] or any(i.lower() == 'food' for i in interests):
        food_daily = int(food_daily * 1.5)
    if mv in ['romantic']:
        food_daily = int(food_daily * 1.3)
    if mv in ['adventure', 'adventurous']:
        food_daily = int(food_daily * 1.2)
    if mv in ['relax', 'relaxing']:
        food_daily = int(food_daily * 0.9)
    food = food_daily * d

    # Transportation baseline per day
    transport_daily = 500
    if mv in ['adventure', 'adventurous']:
        transport_daily = int(transport_daily * 1.4)
    if mv in ['family']:
        transport_daily = int(transport_daily * 1.2)
    transportation = transport_daily * d

    # Shopping/misc baseline per day
    shopping_daily = 300
    if 'shopping' in [i.lower() for i in interests]:
        shopping_daily = int(shopping_daily * 1.6)
    shopping = shopping_daily * d

    total = accommodation + food + transportation + activities + shopping
    return {
        'accommodation': accommodation,
        'food': food,
        'transportation': transportation,
        'activities': activities,
        'shopping': shopping,
        'total': total
    }

def generate_packing_list(mood, weather, age=None, gender=None):
    """Generate personalized packing list based on age, gender, mood, and weather."""
    
    # Base essential items for all travelers
    base_items = [
        '🪪 Passport/ID', '🧾 Tickets/Itinerary', '💳 Cash & Cards', '📱 Phone & Charger',
        '💊 Medications', '🫙 Reusable Water Bottle', '🧴 Toothbrush & Paste', '🧼 Soap/Shower Gel',
        '🧻 Toiletries', '👕 Underwear', '🧦 Socks', '🩹 First Aid Kit', '🔌 Power Adapters'
    ]
    
    # Weather-based items
    weather_items = []
    try:
        if any(str(w.get('forecast','')).lower().find('rain') != -1 for w in weather or []):
            weather_items.extend(['🧥 Light Rain Jacket', '☂️ Umbrella', '👢 Waterproof Shoes'])
        highs = []
        for w in weather or []:
            h = w.get('high')
            if isinstance(h, str):
                num = ''.join([c for c in h if c.isdigit()])
                highs.append(int(num) if num else None)
        if any((x or 0) >= 30 for x in highs):
            weather_items.extend(['🧴 Sunscreen', '🧢 Hat/Cap', '🕶️ Sunglasses', '👕 Light Clothes'])
        if any((x or 0) <= 10 for x in highs):
            weather_items.extend(['🧥 Warm Jacket', '🧣 Scarf', '🧤 Gloves', '👖 Warm Pants'])
    except Exception:
        pass
    
    # Mood-based items
    mood_items = []
    mv = (mood or '').strip().lower()
    if mv in ['adventure', 'adventurous']:
        mood_items.extend(['🥾 Hiking Shoes', '🎒 Daypack', '👕 Quick-dry Clothes', '🧭 Compass', '🔦 Flashlight'])
    if mv in ['foodie']:
        mood_items.extend(['🩹 Antacids', '🧻 Wet Wipes', '🍴 Travel Cutlery', '🥄 Spice Kit'])
    if mv in ['family', 'family-friendly']:
        mood_items.extend(['🍪 Snacks', '🎮 Travel Games', '📚 Books', '🎨 Coloring Supplies'])
    if mv in ['relax', 'relaxing']:
        mood_items.extend(['🧴 Body Lotion', '🧺 Light Clothes', '📖 Reading Material', '🎧 Relaxing Music'])
    if mv in ['romantic']:
        mood_items.extend(['🕯️ Scented Essentials', '📸 Camera', '💐 Flowers', '🍷 Wine Opener'])
    if mv in ['office trip', 'office']:
        mood_items.extend(['💻 Laptop', '🔌 Adapters', '👔 Formal Wear', '📄 Documents', '💼 Briefcase'])
    
    # Age and gender-based personalization
    personalized_items = []
    
    try:
        a = int(age) if age is not None and str(age).isdigit() else None
    except Exception:
        a = None
    
    g = (gender or '').strip().lower() if isinstance(gender, str) else None
    
    if a is not None:
        if a <= 12:  # Kids
            if a <= 3:  # Infants
                personalized_items.extend([
                    '🍼 Diapers', '👕 Baby Clothes', '🍼 Bottles', '💤 Pacifiers', '🎶 Rattles',
                    '🧸 Soft Toys', '🛏️ Cradle', '🧴 Powder', '🌸 Lotion', '🧦 Socks',
                    '🦷 Teething Rings', '🚼 Stroller', '🚿 Shampoo', '🍽️ Bibs', '🛌 Cushions',
                    '🛏️ Blankets', '🎨 Cartoon Bedsheets', '🍴 Feeding Chair', '👟 Baby Shoes', '🦟 Mosquito Net'
                ])
            elif 4 <= a <= 9:  # Children
                personalized_items.extend([
                    '🎒 School Bag', '🥤 Bottle', '🍱 Lunch Box', '✏️ Crayons', '🎨 Coloring Books',
                    '👟 Shoes', '🧸 Toys', '🚲 Bicycle', '📚 Story Books', '🧩 Puzzles',
                    '🍫 Chocolate', '🍦 Ice Cream', '📺 Cartoon Shows', '🎭 Fancy Dress', '🎉 Caps',
                    '🛏️ Cushions', '👕 Uniforms', '🌂 Umbrella', '🏸 Sports Kits', '⛓️ Swing Sets'
                ])
            else:  # Pre-teens (10-12)
                personalized_items.extend([
                    '🎒 School Bag', '📐 Geometry Box', '📓 Notebooks', '🖊️ Pens', '🚲 Bicycles',
                    '🪢 Skipping Rope', '🎮 Video Games', '⌚ Kids Smartwatch', '🏏 Sports Uniforms', '👟 Shoes',
                    '⌚ Fancy Watches', '📚 Comics', '🎨 Bedsheets', '🚗 RC Cars', '🎲 Board Games',
                    '🍿 Popcorn', '🍼 Cartoon Bottles', '🎧 Headphones', '⛸️ Roller Skates', '🍦 Ice Creams'
                ])
        
        elif g == 'female':  # Women
            if 10 <= a <= 20:  # Teenage
                personalized_items.extend([
                    '🎒 Bags', '✏️ Stationery', '📱 Phones', '🎧 Earphones', '💄 Makeup Starter Kits',
                    '👗 Hair Accessories', '👗 Casual Wear', '🏸 Sports Kits', '🚴‍♀️ Scooters', '📚 Books',
                    '📱 Social Media Apps', '📖 Study Apps', '💍 Jewelry', '🧴 Skincare Basics', '🍱 Lunch Boxes',
                    '👟 Sneakers', '📷 Cameras', '🎨 Hobby Kits', '🎮 Games', '👜 Trendy Handbags'
                ])
            elif 21 <= a <= 35:  # Young Adults
                personalized_items.extend([
                    '💻 Laptops', '📱 Smartphones', '👩‍💼 Office Wear', '👠 Heels', '🧘‍♀️ Fitness Gear',
                    '🏋️‍♀️ Gym Wear', '🧳 Travel Bags', '💅 Skincare/Beauty', '🌸 Perfumes', '💎 Jewelry',
                    '👰 Wedding Attire', '🍳 Cooking Gadgets', '⌚ Smartwatch', '💳 Cards', '🚗 Car',
                    '🎬 OTT Subs', '📦 Online Shopping', '☕ Coffee Mugs', '📘 Books', '🍼 Parenting Items'
                ])
            elif 36 <= a <= 50:  # Mid-life
                personalized_items.extend([
                    '🍲 Kitchen Gadgets', '👗 Sarees', '🏠 Home Decor', '🚴‍♀️ Fitness Machines', '🧴 Anti-aging Creams',
                    '👓 Spectacles', '📑 Insurance', '💊 Medicine Kits', '📚 Spiritual Books', '🌱 Gardening Tools',
                    '🍳 Utensils', '💍 Ornaments', '🚙 Family Cars', '👜 Handbags', '👗 Saree Accessories',
                    '🧘‍♀️ Meditation Mats', '📦 Household Organizers', '🧳 Travel Kits', '📖 Kids Books', '📲 WhatsApp Family Groups'
                ])
            else:  # Senior Women (51+)
                personalized_items.extend([
                    '👗 Sarees/Cotton Dresses', '🧥 Shawls', '🚶‍♀️ Walking Stick', '👓 Reading Glasses', '💊 Medicine Box',
                    '📖 Spiritual Books', '📿 Prayer Beads', '🍵 Herbal Teas', '🧶 Knitting Kits', '🪑 Rocking Chair',
                    '📻 Radio', '📸 Photo Albums', '👡 Slippers', '🌿 Ayurvedic Oils', '📺 TV Remote',
                    '🛕 Temple Visits', '🌼 Gardening', '🎶 Religious Songs', '👕 Saree Blouses', '👶 Toys for Grandchildren'
                ])
        
        elif g == 'male':  # Men
            if 10 <= a <= 20:  # Teenage
                personalized_items.extend([
                    '🎒 School Bags', '⚽ Sports Kits', '🚴 Cycles', '📱 Phones', '🎧 Earphones',
                    '🎮 Consoles', '👕 Jeans/T-shirts', '👟 Sneakers', '⌚ Watches', '🏋️ Gym Starter',
                    '💻 Laptops', '🏍️ Bikes (Dreaming)', '🧢 Caps', '🕶️ Sunglasses', '🔋 Gadgets',
                    '📚 Comics', '🎯 Online Games', '🎒 Backpacks', '🏀 Skateboards', '🍔 Fast Food'
                ])
            elif 21 <= a <= 35:  # Young Adults
                personalized_items.extend([
                    '👔 Formal Wear', '🤵 Blazers', '💻 Laptops', '📱 Smartphones', '🏋️ Gym Cards',
                    '🧴 Perfumes', '🚗 Cars', '🏍️ Bikes', '🧾 Wallets', '💳 Cards',
                    '⌚ Watches', '👞 Shoes', '💼 Office Bags', '🎧 Headphones', '🧳 Travel Bags',
                    '🎬 OTT Subs', '📘 Coding Books', '☕ Coffee Mugs', '⌚ Smartwatch', '🎧 AirPods'
                ])
            elif 36 <= a <= 50:  # Mid-life
                personalized_items.extend([
                    '💻 Office Laptops', '🚘 Cars', '🏡 Home Loans', '👔 Suits', '⌚ Watches',
                    '📑 Insurance', '🚴 Fitness Cycles', '📱 Smartphones', '🧾 School Fees', '📄 Newspapers',
                    '🌍 Family Holidays', '💊 Medicines', '🧘 Yoga Mats', '👓 Spectacles', '👞 Shoes',
                    '📲 Phone Apps', '🔋 Power Bank', '💰 Wallet', '🍱 Tiffin', '🪪 Office ID'
                ])
            else:  # Senior Men (51+)
                personalized_items.extend([
                    '👕 Dhoti/Kurta', '👓 Spectacles', '💊 Medicine Box', '🚶 Walking Stick', '📻 Radio',
                    '📖 Books', '📿 Prayer Items', '🌿 Ayurvedic Items', '🚲 Bicycle', '👡 Sandals',
                    '🧥 Warm Clothes', '♟️ Games', '☕ Tea Items', '📸 Albums', '🛕 Religious Items',
                    '🌱 Gardening Tools', '👶 Grandchildren Items', '🧴 Basic Toiletries', '👕 Clothes', '👖 Pants'
                ])
        
        else:  # Gender not specified, use age-based general items
            if 10 <= a <= 20:
                personalized_items.extend([
                    '🎒 School Bag', '📱 Phone', '🎧 Earphones', '👕 Casual Clothes', '👟 Sneakers',
                    '⌚ Watch', '💻 Laptop', '🧢 Cap', '🕶️ Sunglasses', '🔋 Gadgets',
                    '📚 Books', '🎮 Games', '🎒 Backpack', '🏀 Sports Gear', '🍔 Snacks',
                    '🧼 Toiletries', '💳 Cards', '🔌 Chargers', '📷 Camera', '🎨 Hobby Items'
                ])
            elif 21 <= a <= 35:
                personalized_items.extend([
                    '💻 Laptop', '📱 Smartphone', '👔 Formal Wear', '👞 Shoes', '🧴 Perfume',
                    '🚗 Car Keys', '💳 Cards', '⌚ Watch', '💼 Bag', '🎧 Headphones',
                    '🧳 Travel Bag', '📘 Books', '☕ Coffee Mug', '🔌 Adapters', '📷 Camera',
                    '🧴 Skincare', '💊 Medicine', '🧻 Toiletries', '👕 Clothes', '👖 Pants'
                ])
            elif 36 <= a <= 50:
                personalized_items.extend([
                    '💻 Office Laptop', '🚘 Car Keys', '👔 Suits', '⌚ Watch', '📑 Insurance',
                    '🚴 Fitness Gear', '📱 Smartphone', '💊 Medicines', '🧘 Yoga Mat', '👓 Spectacles',
                    '👞 Shoes', '📲 Phone Apps', '🔋 Power Bank', '💰 Wallet', '🍱 Food',
                    '🪪 Office ID', '📄 Documents', '🧴 Skincare', '👕 Clothes', '👖 Pants'
                ])
            else:  # 51+
                personalized_items.extend([
                    '👕 Traditional Wear', '👓 Spectacles', '💊 Medicine Box', '🚶 Walking Stick', '📻 Radio',
                    '📖 Books', '📿 Prayer Items', '🌿 Ayurvedic Items', '🚲 Bicycle', '👡 Sandals',
                    '🧥 Warm Clothes', '♟️ Games', '☕ Tea Items', '📸 Albums', '🛕 Religious Items',
                    '🌱 Gardening Tools', '👶 Grandchildren Items', '🧴 Basic Toiletries', '👕 Clothes', '👖 Pants'
                ])
    
    # Combine all items and ensure minimum 20 items
    all_items = base_items + weather_items + mood_items + personalized_items
    
    # Remove duplicates while preserving order
    unique_items = list(dict.fromkeys(all_items))
    
    # Ensure minimum 20 items by adding generic travel items if needed
    if len(unique_items) < 20:
        additional_items = [
            '🧳 Luggage', '🔑 Keys', '💼 Wallet', '📱 Phone Charger', '🔌 Power Bank',
            '📷 Camera', '🎧 Headphones', '📚 Reading Material', '🧴 Hand Sanitizer', '🩹 Bandages',
            '💊 Pain Relievers', '🧼 Face Wash', '🧴 Moisturizer', '👕 Extra Clothes', '👖 Extra Pants',
            '🧦 Extra Socks', '👟 Comfortable Shoes', '🧥 Jacket', '🧣 Scarf', '🧤 Gloves'
        ]
        for item in additional_items:
            if item not in unique_items:
                unique_items.append(item)
                if len(unique_items) >= 20:
                    break
    
    return unique_items[:max(20, len(unique_items))]

def generate_mock_itinerary(destination, days, mood):
    """Generate mock structured itinerary (kept for backward compatibility)"""
    # This function is now replaced by generate_ai_travel_plan
    # Keeping it for backward compatibility
    return generate_ai_travel_plan(destination, days, mood)

def generate_ai_travel_plan(destination, days, mood, name=None, age=None, gender=None, interests=None, country=None, state=None, city=None, start_date=None, end_date=None, weather=None):
    """Generate unique, personalized AI travel plan based on user details and preferences."""
    
    # Greeting based on user details
    user_name = name or "Traveler"
    greeting = f"Hi {user_name} 👋, here's your personalized {mood} getaway plan!"
    
    # Trip summary
    trip_summary = {
        "location": f"{city or destination}, {state or 'Unknown'}, {country or 'Unknown'}",
        "duration": f"{days} days",
        "mood": mood,
        "dates": f"{start_date or 'Not specified'} - {end_date or 'Not specified'}",
        "weather_forecast": weather or "No forecast available"
    }
    
    # Generate unique daily itinerary
    itinerary = generate_unique_daily_itinerary(destination, days, mood, age, gender, interests)
    
    # Generate must-visit attractions
    must_visit = generate_must_visit_attractions(destination, mood, age, gender, interests)
    
    # Generate hotel recommendations
    hotel_recommendations = generate_hotel_recommendations(destination, mood, age, gender, budget_preference(age, gender))
    
    # Generate budget estimate
    budget_estimate = generate_budget_estimate(days, hotel_recommendations, mood, age, gender)
    
    # Generate local events
    local_events = generate_local_events(destination, start_date, end_date, mood)
    
    # Generate personalized packing list
    packing_list = generate_packing_list(mood, weather, age, gender)
    
    return {
        "greeting": greeting,
        "trip_summary": trip_summary,
        "itinerary": itinerary,
        "must_visit": must_visit,
        "hotel_recommendations": hotel_recommendations,
        "budget_estimate": budget_estimate,
        "local_events": local_events,
        "packing_list": packing_list
    }

def generate_unique_daily_itinerary(destination, days, mood, age=None, gender=None, interests=None):
    """Generate unique daily itinerary with no two plans being identical."""
    
    # Base activities for different moods
    mood_activities = {
        "romantic": {
            "morning": [
                "Couples sunrise yoga session at the beach",
                "Romantic breakfast in bed with local delicacies",
                "Private garden meditation for two",
                "Couples spa treatment with aromatic oils",
                "Sunrise photography session at scenic viewpoints"
            ],
            "afternoon": [
                "Private wine tasting experience",
                "Couples cooking class with local chefs",
                "Romantic picnic in botanical gardens",
                "Private boat ride on serene waters",
                "Couples art workshop with local artists"
            ],
            "evening": [
                "Sunset dinner cruise with live music",
                "Private candlelit dinner under the stars",
                "Romantic stargazing session",
                "Couples dance class with local instructors",
                "Evening walk through illuminated gardens"
            ],
            "dinner": [
                "Intimate rooftop restaurant with city views",
                "Private dining room with personalized menu",
                "Beachfront restaurant with ocean sounds",
                "Mountain view restaurant with sunset backdrop",
                "Garden restaurant with fairy lights"
            ],
            "accommodation": [
                "Luxury couple's suite with private balcony",
                "Romantic boutique hotel with rose petals",
                "Private villa with infinity pool",
                "Treehouse accommodation for adventurous couples",
                "Historic palace converted to romantic retreat"
            ]
        },
        "adventure": {
            "morning": [
                "Early morning rock climbing session",
                "Sunrise mountain biking adventure",
                "Wildlife safari in natural reserves",
                "Waterfall rappelling experience",
                "Paragliding over scenic landscapes"
            ],
            "afternoon": [
                "White water rafting on challenging rapids",
                "Zip lining through dense forests",
                "Cave exploration with headlamps",
                "Mountain trekking with local guides",
                "Rock climbing on natural formations"
            ],
            "evening": [
                "Campfire storytelling with local legends",
                "Night hiking with stargazing",
                "Adventure photography workshop",
                "Outdoor survival skills training",
                "Mountain camping under the stars"
            ],
            "dinner": [
                "Adventure camp dining with local cuisine",
                "Mountain lodge restaurant with panoramic views",
                "Riverside barbecue with fresh catch",
                "Forest dining with natural ambiance",
                "Cliffside restaurant with adventure theme"
            ],
            "accommodation": [
                "Adventure lodge with rustic charm",
                "Mountain camp with basic amenities",
                "Eco-resort with sustainable practices",
                "Adventure hostel with shared experiences",
                "Treehouse accommodation in wilderness"
            ]
        },
        "relaxing": {
            "morning": [
                "Gentle yoga session with ocean breeze",
                "Meditation retreat in peaceful gardens",
                "Spa treatment with natural ingredients",
                "Peaceful bird watching in nature",
                "Mindful walking in serene landscapes"
            ],
            "afternoon": [
                "Leisurely lunch at organic farm restaurant",
                "Tea ceremony in traditional gardens",
                "Gentle nature walk with local guides",
                "Art therapy session with local artists",
                "Sound healing session with instruments"
            ],
            "evening": [
                "Sunset viewing from peaceful viewpoints",
                "Relaxing boat ride on calm waters",
                "Evening stroll through quiet streets",
                "Meditation session under the stars",
                "Gentle music performance in gardens"
            ],
            "dinner": [
                "Fine dining with farm-to-table cuisine",
                "Rooftop restaurant with city lights",
                "Garden restaurant with natural sounds",
                "Seaside restaurant with ocean views",
                "Mountain restaurant with valley views"
            ],
            "accommodation": [
                "Luxury spa resort with wellness programs",
                "Boutique wellness hotel with meditation rooms",
                "Peaceful retreat center in nature",
                "Serene mountain lodge with spa facilities",
                "Beachfront resort with yoga classes"
            ]
        },
        "foodie": {
            "morning": [
                "Local food market tour with tastings",
                "Cooking class with regional specialties",
                "Food photography walk through markets",
                "Breakfast food tour of local favorites",
                "Coffee plantation visit with tasting"
            ],
            "afternoon": [
                "Wine tasting session with local varieties",
                "Street food exploration with foodie guide",
                "Chef's table experience at top restaurants",
                "Food festival participation and tasting",
                "Local brewery tour with beer pairing"
            ],
            "evening": [
                "Fine dining experience with wine pairing",
                "Food and culture tour with local experts",
                "Culinary workshop with master chefs",
                "Gourmet dinner with seasonal ingredients",
                "Food truck gathering with diverse options"
            ],
            "dinner": [
                "Michelin-starred restaurant experience",
                "Local chef's restaurant with signature dishes",
                "Food truck gathering with international cuisine",
                "Traditional restaurant with family recipes",
                "Fusion restaurant with innovative combinations"
            ],
            "accommodation": [
                "Food-themed hotel with culinary programs",
                "Culinary retreat with cooking facilities",
                "Boutique food hotel with restaurant partnerships",
                "Gastronomic resort with wine cellars",
                "Farm stay with organic meal preparation"
            ]
        },
        "family": {
            "morning": [
                "Theme park adventure with family rides",
                "Zoo and aquarium tour with educational programs",
                "Family museum visit with interactive exhibits",
                "Interactive science center with hands-on activities",
                "Family-friendly wildlife sanctuary visit"
            ],
            "afternoon": [
                "Family cooking class with kid-friendly recipes",
                "Outdoor picnic with games and activities",
                "Educational tour with fun learning elements",
                "Family-friendly show with entertainment",
                "Adventure park with age-appropriate activities"
            ],
            "evening": [
                "Family dinner with entertainment options",
                "Evening entertainment suitable for all ages",
                "Family games and bonding activities",
                "Movie night with family-friendly films",
                "Cultural performance with family appeal"
            ],
            "dinner": [
                "Family restaurant with diverse menu options",
                "Kid-friendly dining with play areas",
                "Buffet restaurant with variety for all tastes",
                "Casual family eatery with relaxed atmosphere",
                "Interactive restaurant with entertainment"
            ],
            "accommodation": [
                "Family resort with kids club and activities",
                "Kid-friendly hotel with family suites",
                "Family suite with separate sleeping areas",
                "Resort with kids club and supervised activities",
                "Family-friendly accommodation with amenities"
            ]
        },
        "office trip": {
            "morning": [
                "Team building workshop in scenic location",
                "Conference hall setup and preparation",
                "Business networking breakfast meeting",
                "Corporate team challenge activities",
                "Professional development session outdoors"
            ],
            "afternoon": [
                "Business lunch with local partners",
                "Team collaboration session in meeting rooms",
                "Corporate team building exercises",
                "Business presentation practice sessions",
                "Strategic planning workshop in relaxed setting"
            ],
            "evening": [
                "Team dinner with local cuisine",
                "Business networking cocktail event",
                "Team bonding activities and games",
                "Corporate social responsibility activities",
                "Team celebration and recognition event"
            ],
            "dinner": [
                "Business dinner with formal atmosphere",
                "Team dining with local specialties",
                "Corporate event with entertainment",
                "Business networking dinner",
                "Team celebration meal with activities"
            ],
            "accommodation": [
                "Business hotel with conference facilities",
                "Corporate accommodation with meeting rooms",
                "Business center with work amenities",
                "Professional accommodation with business services",
                "Corporate retreat center with facilities"
            ]
        }
    }
    
    # Get base activities for the mood
    base_activities = mood_activities.get(mood.lower(), mood_activities["relaxing"])
    
    # Custom mood handling
    if mood.lower() not in mood_activities:
        base_activities = generate_custom_mood_activities(mood, interests, age, gender)
    
    # Generate unique itinerary for each day
    daily_itinerary = []
    used_activities = set()
    
    for day in range(1, days + 1):
        day_plan = {
            "day": day,
            "morning": select_unique_activity(base_activities["morning"], used_activities, day),
            "afternoon": select_unique_activity(base_activities["afternoon"], used_activities, day),
            "evening": select_unique_activity(base_activities["evening"], used_activities, day),
            "dinner": select_unique_activity(base_activities["dinner"], used_activities, day),
            "accommodation": select_unique_activity(base_activities["accommodation"], used_activities, day)
        }
        daily_itinerary.append(day_plan)
    
    return daily_itinerary

def generate_custom_mood_activities(mood, interests, age, gender):
    """Generate activities for custom mood based on interests."""
    
    # Analyze interests and create custom mood activities
    custom_activities = {
        "morning": [
            f"Explore {mood.lower()} interests in local settings",
            f"Visit {mood.lower()} themed locations",
            f"Participate in {mood.lower()} focused activities",
            f"Discover {mood.lower()} related attractions",
            f"Experience {mood.lower()} culture and traditions"
        ],
        "afternoon": [
            f"Immerse in {mood.lower()} experiences",
            f"Learn about {mood.lower()} from local experts",
            f"Practice {mood.lower()} related skills",
            f"Connect with {mood.lower()} community",
            f"Explore {mood.lower()} heritage and history"
        ],
        "evening": [
            f"Evening {mood.lower()} activities and events",
            f"Sunset {mood.lower()} experience",
            f"Night time {mood.lower()} exploration",
            f"Evening {mood.lower()} entertainment",
            f"Twilight {mood.lower()} activities"
        ],
        "dinner": [
            f"Dine at {mood.lower()} themed restaurants",
            f"Experience {mood.lower()} cuisine",
            f"Enjoy {mood.lower()} atmosphere dining",
            f"Taste {mood.lower()} inspired dishes",
            f"Relish {mood.lower()} cultural meals"
        ],
        "accommodation": [
            f"Stay at {mood.lower()} themed accommodation",
            f"Experience {mood.lower()} inspired lodging",
            f"Enjoy {mood.lower()} focused amenities",
            f"Relax in {mood.lower()} environment",
            f"Immerse in {mood.lower()} atmosphere"
        ]
    }
    
    return custom_activities

def select_unique_activity(activity_list, used_activities, day):
    """Select a unique activity, ensuring variety across days."""
    
    # Filter out already used activities
    available_activities = [act for act in activity_list if act not in used_activities]
    
    # If no unique activities left, add day-specific variations
    if not available_activities:
        base_activity = random.choice(activity_list)
        variations = [
            f"Day {day}: {base_activity}",
            f"Special {day} day: {base_activity}",
            f"Unique day {day} experience: {base_activity}",
            f"Day {day} exclusive: {base_activity}",
            f"Personalized day {day}: {base_activity}"
        ]
        return random.choice(variations)
    
    # Select unique activity and mark as used
    selected = random.choice(available_activities)
    used_activities.add(selected)
    return selected

def generate_must_visit_attractions(destination, mood, age, gender, interests):
    """Generate must-visit attractions with Google Maps links and photos."""
    
    # Comprehensive attractions database with Google Maps links and photos
    attractions_database = {
        "guntur": [
            {
                "name": "Amaravati Buddhist Site",
                "description": "Ancient Buddhist site with historical significance",
                "entry_fee": "₹50 for Indians, ₹500 for foreigners",
                "best_time": "Morning",
                "rating": "4.3",
                "google_maps_link": "https://maps.google.com/?q=Amaravati+Buddhist+Site+Guntur",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Undavalli Caves",
                "description": "Ancient rock-cut caves with beautiful architecture",
                "entry_fee": "₹25 for Indians, ₹300 for foreigners",
                "best_time": "Morning or Evening",
                "rating": "4.5",
                "google_maps_link": "https://maps.google.com/?q=Undavalli+Caves+Guntur",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Kondaveedu Fort",
                "description": "Historic hilltop fort with panoramic views",
                "entry_fee": "₹30 for Indians, ₹400 for foreigners",
                "best_time": "Evening",
                "rating": "4.2",
                "google_maps_link": "https://maps.google.com/?q=Kondaveedu+Fort+Guntur",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Guntur City Center",
                "description": "Modern shopping and entertainment hub",
                "entry_fee": "Free",
                "best_time": "Evening",
                "rating": "4.0",
                "google_maps_link": "https://maps.google.com/?q=Guntur+City+Center",
                "image": "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=400&h=300&fit=crop",
                "category": "modern"
            }
        ],
        "puri": [
            {
                "name": "Jagannath Temple",
                "description": "Sacred Hindu temple dedicated to Lord Jagannath",
                "entry_fee": "Free (Hindus only)",
                "best_time": "Early Morning",
                "rating": "4.7",
                "google_maps_link": "https://maps.google.com/?q=Jagannath+Temple+Puri",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "religious"
            },
            {
                "name": "Puri Beach",
                "description": "Famous beach known for its golden sand and waves",
                "entry_fee": "Free",
                "best_time": "Morning or Evening",
                "rating": "4.5",
                "google_maps_link": "https://maps.google.com/?q=Puri+Beach",
                "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
                "category": "nature"
            },
            {
                "name": "Konark Sun Temple",
                "description": "UNESCO World Heritage Site, architectural marvel",
                "entry_fee": "₹40 for Indians, ₹600 for foreigners",
                "best_time": "Morning",
                "rating": "4.6",
                "google_maps_link": "https://maps.google.com/?q=Konark+Sun+Temple",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Chilika Lake",
                "description": "Asia's largest brackish water lagoon",
                "entry_fee": "₹50",
                "best_time": "Morning for bird watching",
                "rating": "4.4",
                "google_maps_link": "https://maps.google.com/?q=Chilika+Lake",
                "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop",
                "category": "nature"
            }
        ],
        "mumbai": [
            {
                "name": "Gateway of India",
                "description": "Historic monument and popular tourist attraction",
                "entry_fee": "Free",
                "best_time": "Evening",
                "rating": "4.3",
                "google_maps_link": "https://maps.google.com/?q=Gateway+of+India+Mumbai",
                "image": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Marine Drive",
                "description": "Famous curved boulevard along the coast",
                "entry_fee": "Free",
                "best_time": "Evening",
                "rating": "4.6",
                "google_maps_link": "https://maps.google.com/?q=Marine+Drive+Mumbai",
                "image": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop",
                "category": "modern"
            },
            {
                "name": "Elephanta Caves",
                "description": "Ancient cave temples on Elephanta Island",
                "entry_fee": "₹40 for Indians, ₹600 for foreigners",
                "best_time": "Morning",
                "rating": "4.4",
                "google_maps_link": "https://maps.google.com/?q=Elephanta+Caves",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            }
        ],
        "delhi": [
            {
                "name": "Taj Mahal",
                "description": "Iconic white marble mausoleum",
                "entry_fee": "₹50 for Indians, ₹1100 for foreigners",
                "best_time": "Sunrise",
                "rating": "4.8",
                "google_maps_link": "https://maps.google.com/?q=Taj+Mahal+Agra",
                "image": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Red Fort",
                "description": "Historic fort complex in Old Delhi",
                "entry_fee": "₹35 for Indians, ₹500 for foreigners",
                "best_time": "Morning",
                "rating": "4.2",
                "google_maps_link": "https://maps.google.com/?q=Red+Fort+Delhi",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            },
            {
                "name": "Qutub Minar",
                "description": "Tallest brick minaret in the world",
                "entry_fee": "₹30 for Indians, ₹500 for foreigners",
                "best_time": "Morning",
                "rating": "4.3",
                "google_maps_link": "https://maps.google.com/?q=Qutub+Minar+Delhi",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            }
        ],
        "goa": [
            {
                "name": "Calangute Beach",
                "description": "Queen of Beaches, popular tourist destination",
                "entry_fee": "Free",
                "best_time": "Morning or Evening",
                "rating": "4.4",
                "google_maps_link": "https://maps.google.com/?q=Calangute+Beach+Goa",
                "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
                "category": "nature"
            },
            {
                "name": "Basilica of Bom Jesus",
                "description": "UNESCO World Heritage Site, famous church",
                "entry_fee": "Free",
                "best_time": "Morning",
                "rating": "4.5",
                "google_maps_link": "https://maps.google.com/?q=Basilica+of+Bom+Jesus+Goa",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "religious"
            },
            {
                "name": "Fort Aguada",
                "description": "17th-century Portuguese fort",
                "entry_fee": "₹25 for Indians, ₹300 for foreigners",
                "best_time": "Evening",
                "rating": "4.3",
                "google_maps_link": "https://maps.google.com/?q=Fort+Aguada+Goa",
                "image": "https://images.unsplash.com/photo-1542810634-71277d95dcbb?w=400&h=300&fit=crop",
                "category": "historical"
            }
        ]
    }
    
    # Get attractions for the specific destination
    destination_lower = destination.lower()
    specific_attractions = attractions_database.get(destination_lower, [])
    
    # If no specific attractions found, generate generic ones
    if not specific_attractions:
        # Base attractions for different moods
        mood_attractions = {
            "romantic": [
                "Sunset viewpoints for couples",
                "Romantic garden walks",
                "Couples spa and wellness centers",
                "Romantic boat rides",
                "Intimate dining spots"
            ],
            "adventure": [
                "Adventure sports centers",
                "Hiking and trekking trails",
                "Water sports facilities",
                "Rock climbing spots",
                "Adventure parks"
            ],
            "relaxing": [
                "Spa and wellness centers",
                "Peaceful meditation gardens",
                "Serene nature trails",
                "Relaxing beach spots",
                "Tranquil mountain viewpoints"
            ],
            "foodie": [
                "Local food markets",
                "Famous restaurants",
                "Street food hubs",
                "Food festivals",
                "Cooking class centers"
            ],
            "family": [
                "Amusement parks",
                "Zoos and aquariums",
                "Interactive museums",
                "Family entertainment centers",
                "Kid-friendly parks"
            ]
        }
        
        base_attractions = mood_attractions.get(mood.lower(), mood_attractions["relaxing"])
        
        # Convert to attraction objects with Google Maps links
        specific_attractions = []
        for i, attraction in enumerate(base_attractions[:4]):
            specific_attractions.append({
                "name": attraction,
                "description": f"Explore {attraction.lower()} in {destination}",
                "entry_fee": "Varies",
                "best_time": "Morning or Evening",
                "rating": f"4.{random.randint(0, 5)}",
                "google_maps_link": f"https://maps.google.com/?q={attraction.replace(' ', '+')}+{destination.replace(' ', '+')}",
                "image": f"https://images.unsplash.com/photo-{random.randint(1000000000, 9999999999)}?w=400&h=300&fit=crop",
                "category": mood.lower()
            })
    
    # Return top 4 attractions
    return specific_attractions[:4]

def generate_hotel_recommendations(destination, mood, age, gender, budget_pref):
    """Generate hotel recommendations based on mood, age, gender, and budget."""
    
    # Base hotel types for different moods
    mood_hotels = {
        "romantic": [
            "Luxury boutique hotels",
            "Romantic resorts",
            "Couples-only accommodations",
            "Intimate guesthouses",
            "Romantic bed and breakfasts"
        ],
        "adventure": [
            "Adventure lodges",
            "Eco-resorts",
            "Mountain camps",
            "Adventure hostels",
            "Wilderness accommodations"
        ],
        "relaxing": [
            "Wellness resorts",
            "Spa hotels",
            "Peaceful retreats",
            "Serene accommodations",
            "Meditation centers"
        ],
        "foodie": [
            "Food-themed hotels",
            "Culinary retreats",
            "Restaurant partnerships",
            "Food-focused accommodations",
            "Gastronomic experiences"
        ],
        "family": [
            "Family resorts",
            "Kid-friendly hotels",
            "Family suites",
            "Entertainment hotels",
            "Family-focused accommodations"
        ],
        "office trip": [
            "Business hotels",
            "Conference centers",
            "Corporate accommodations",
            "Professional facilities",
            "Business-focused lodging"
        ]
    }
    
    # Get base hotel types for the mood
    base_hotels = mood_hotels.get(mood.lower(), mood_hotels["relaxing"])
    
    # Custom mood hotels
    if mood.lower() not in mood_hotels:
        base_hotels = [
            f"{mood.title()} themed accommodations",
            f"{mood.title()} focused hotels",
            f"{mood.title()} experience lodging",
            f"{mood.title()} culture accommodations",
            f"{mood.title()} heritage stays"
        ]
    
    # Budget considerations
    budget_hotels = []
    if budget_pref == "budget":
        budget_hotels.extend([
            "Budget-friendly hostels",
            "Affordable guesthouses",
            "Economic accommodations",
            "Value-for-money hotels",
            "Budget resorts"
        ])
    elif budget_pref == "premium":
        budget_hotels.extend([
            "Luxury accommodations",
            "Premium resorts",
            "High-end hotels",
            "Exclusive stays",
            "Deluxe accommodations"
        ])
    else:  # mid-range
        budget_hotels.extend([
            "Mid-range hotels",
            "Comfortable accommodations",
            "Standard resorts",
            "Quality guesthouses",
            "Balanced value hotels"
        ])
    
    # Combine and return recommendations
    all_hotels = base_hotels + budget_hotels
    return list(dict.fromkeys(all_hotels))[:8]  # Return top 8

def budget_preference(age, gender):
    """Determine budget preference based on age and gender."""
    
    if age is None:
        return "mid-range"
    
    if age < 25:
        return "budget"
    elif age < 40:
        return "mid-range"
    else:
        return "premium"

def generate_budget_estimate(days, hotel_recommendations, mood, age, gender):
    """Generate budget estimate with daily breakdown."""
    
    # Base daily costs
    base_costs = {
        "lodging": 2000,
        "food": 800,
        "activities": 500,
        "transit": 300
    }
    
    # Mood-based adjustments
    mood_multipliers = {
        "romantic": {"lodging": 1.5, "food": 1.3, "activities": 1.2, "transit": 1.0},
        "adventure": {"lodging": 1.2, "food": 1.1, "activities": 1.5, "transit": 1.3},
        "relaxing": {"lodging": 1.4, "food": 1.2, "activities": 1.0, "transit": 1.0},
        "foodie": {"lodging": 1.1, "food": 1.6, "activities": 1.1, "transit": 1.0},
        "family": {"lodging": 1.3, "food": 1.2, "activities": 1.3, "transit": 1.2},
        "office trip": {"lodging": 1.2, "food": 1.1, "activities": 1.0, "transit": 1.1}
    }
    
    # Get multipliers for the mood
    multipliers = mood_multipliers.get(mood.lower(), mood_multipliers["relaxing"])
    
    # Age and gender adjustments
    if age and age < 25:
        multipliers = {k: v * 0.8 for k, v in multipliers.items()}
    elif age and age > 50:
        multipliers = {k: v * 1.2 for k, v in multipliers.items()}
    
    # Calculate daily costs
    daily_costs = {}
    for category, base_cost in base_costs.items():
        daily_costs[category] = int(base_cost * multipliers.get(category, 1.0))
    
    # Calculate totals
    total = sum(daily_costs.values()) * days
    
    return {
        "total": f"₹{total:,}",
        "lodging": f"₹{daily_costs['lodging']:,}/day",
        "food": f"₹{daily_costs['food']:,}/day",
        "activities": f"₹{daily_costs['activities']:,}/day",
        "transit": f"₹{daily_costs['transit']:,}/day"
    }

def generate_local_events(destination, start_date, end_date, mood):
    """Generate local events based on destination, dates, and mood."""
    
    # Base events for different moods
    mood_events = {
        "romantic": [
            "Couples workshops and retreats",
            "Romantic music performances",
            "Couples cooking classes",
            "Romantic photography tours",
            "Couples wellness sessions"
        ],
        "adventure": [
            "Adventure sports competitions",
            "Outdoor adventure festivals",
            "Adventure photography workshops",
            "Adventure training camps",
            "Adventure gear exhibitions"
        ],
        "relaxing": [
            "Wellness and meditation retreats",
            "Yoga and mindfulness workshops",
            "Spa and wellness festivals",
            "Peace and tranquility events",
            "Relaxation therapy sessions"
        ],
        "foodie": [
            "Food festivals and culinary events",
            "Wine tasting and pairing events",
            "Cooking competitions and workshops",
            "Food photography tours",
            "Culinary heritage celebrations"
        ],
        "family": [
            "Family entertainment festivals",
            "Children's cultural events",
            "Family-friendly workshops",
            "Educational family events",
            "Family bonding activities"
        ],
        "office trip": [
            "Business networking events",
            "Corporate team building activities",
            "Professional development workshops",
            "Business conferences and seminars",
            "Corporate entertainment events"
        ]
    }
    
    # Get base events for the mood
    base_events = mood_events.get(mood.lower(), mood_events["relaxing"])
    
    # Custom mood events
    if mood.lower() not in mood_events:
        base_events = [
            f"{mood.title()} themed events and workshops",
            f"{mood.title()} cultural celebrations",
            f"{mood.title()} focused activities",
            f"{mood.title()} community gatherings",
            f"{mood.title()} experience events"
        ]
    
    # Add seasonal and destination-specific events
    seasonal_events = [
        "Local cultural festivals",
        "Seasonal celebrations",
        "Destination-specific events",
        "Local community gatherings",
        "Traditional celebrations"
    ]
    
    # Combine and return events
    all_events = base_events + seasonal_events
    return list(dict.fromkeys(all_events))[:6]  # Return top 6

@app.route('/auth/google/login')
def google_login():
    """Initiate Google OAuth login"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return jsonify({'error': 'Google OAuth not available'}), 503
    
    try:
        flow = Flow.from_client_config(
            oauth_config,
            scopes=['openid', 'email', 'profile']
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        session['oauth_state'] = state
        return redirect(authorization_url)
        
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return jsonify({'error': 'Google OAuth not available'}), 503
    
    try:
        flow = Flow.from_client_config(
            oauth_config,
            scopes=['openid', 'email', 'profile']
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        
        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.url)
        
        # Get user info from ID token
        id_info = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Store or update user in database
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id, role FROM users WHERE email = ?', (id_info['email'],))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Update existing user
            user_id, user_role = existing_user
            cursor.execute('''
                UPDATE users SET 
                google_id = ?, name = ?, picture = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (id_info['sub'], id_info.get('name', ''), id_info.get('picture', ''), user_id))
        else:
            # Create new user
            # Determine role based on email
            user_role = ROLE_ROOT if id_info['email'] in ADMIN_EMAILS else ROLE_USER
            
            cursor.execute('''
                INSERT INTO users (google_id, email, name, picture, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (id_info['sub'], id_info['email'], id_info.get('name', ''), id_info.get('picture', ''), user_role))
            user_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Store user info in session
        session['user'] = {
            'id': user_id,
            'google_id': id_info['sub'],
            'email': id_info['email'],
            'name': id_info.get('name', ''),
            'picture': id_info.get('picture', ''),
            'given_name': id_info.get('given_name', ''),
            'family_name': id_info.get('family_name', ''),
            'role': user_role
        }
        
        # Store tokens securely (in production, use secure storage)
        session['access_token'] = flow.credentials.token
        session['refresh_token'] = flow.credentials.refresh_token
        
        # Redirect to dashboard with success message
        return redirect('/?auth=success')
        
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        return redirect('/?auth=error&message=' + str(e))

@app.route('/auth/google/logout')
def google_logout():
    """Logout user and clear session"""
    session.clear()
    return redirect('/')

@app.route('/api/user/profile')
def get_user_profile():
    """Get current user profile"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify(session['user'])

@app.route('/api/user/is-authenticated')
def check_authentication():
    """Check if user is authenticated"""
    if 'user' in session:
        return jsonify({
            'authenticated': True,
            'user': session['user']
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    """Get all users (admin only)"""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, google_id, email, name, picture, role, created_at, updated_at
            FROM users 
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'google_id': row[1],
                'email': row[2],
                'name': row[3] or 'Anonymous',
                'picture': row[4],
                'role': row[5],
                'created_at': row[6],
                'updated_at': row[7]
            })
        
        return jsonify(users)
    except Exception as e:
        print(f"Admin users error: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@root_required
def api_admin_update_user_role(user_id):
    """Update user role (root only)"""
    try:
        data = request.get_json(force=True)
        new_role = data.get('role')
        
        if new_role not in [ROLE_USER, ROLE_ADMIN, ROLE_ROOT]:
            return jsonify({'error': 'Invalid role'}), 400
        
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'User role updated successfully'})
    except Exception as e:
        print(f"Update user role error: {e}")
        return jsonify({'error': 'Failed to update user role'}), 500

@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    """Get admin statistics"""
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Get user counts
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (ROLE_USER,))
        regular_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (ROLE_ADMIN,))
        admin_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (ROLE_ROOT,))
        root_users = cursor.fetchone()[0]
        
        # Get plan counts
        cursor.execute('SELECT COUNT(*) FROM trips')
        total_plans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM trips WHERE user_id IS NOT NULL')
        plans_with_users = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'users': {
                'total': total_users,
                'regular': regular_users,
                'admin': admin_users,
                'root': root_users
            },
            'plans': {
                'total': total_plans,
                'with_users': plans_with_users,
                'orphaned': total_plans - plans_with_users
            }
        })
    except Exception as e:
        print(f"Admin stats error: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@app.route('/')
def index():
    # Check if user is authenticated
    user = session.get('user')
    auth_status = request.args.get('auth')
    auth_message = request.args.get('message', '')
    
    return render_template('index.html', 
                         user=user, 
                         auth_status=auth_status, 
                         auth_message=auth_message)

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel page"""
    return render_template('admin.html')

@app.route('/test-locations')
def test_locations():
    return send_from_directory('.', 'test_locations.html')

# ===================== API: Locations (Country → State → City) =====================
@app.route('/api/locations')
def api_locations():
    try:
        locations = {
            "India": {
                "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Kurnool"],
                "Arunachal Pradesh": ["Itanagar", "Tawang", "Pasighat", "Ziro", "Bomdila"],
                "Assam": ["Guwahati", "Silchar", "Dibrugarh", "Jorhat", "Tezpur"],
                "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Purnia"],
                "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur", "Korba", "Durg"],
                "Delhi": ["New Delhi", "Dwarka", "Saket", "Karol Bagh", "Connaught Place"],
                "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda"],
                "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
                "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Hisar"],
                "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala", "Solan", "Mandi"],
                "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla", "Leh"],
                "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh"],
                "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi", "Belagavi"],
                "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"],
                "Madhya Pradesh": ["Indore", "Bhopal", "Gwalior", "Jabalpur", "Ujjain"],
                "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad"],
                "Manipur": ["Imphal", "Thoubal", "Bishnupur"],
                "Meghalaya": ["Shillong", "Tura", "Jowai"],
                "Mizoram": ["Aizawl", "Lunglei", "Saiha"],
                "Nagaland": ["Kohima", "Dimapur", "Mokokchung"],
                "Odisha": [
                    "Bhubaneswar", "Cuttack", "Puri", "Rourkela", "Sambalpur", "Balasore",
                    "Berhampur", "Baripada", "Jharsuguda", "Jeypore", "Bhadrak", "Kendrapara",
                    "Dhenkanal", "Angul", "Koraput"
                ],
                "Punjab": ["Amritsar", "Ludhiana", "Jalandhar", "Patiala", "Bathinda"],
                "Rajasthan": ["Jaipur", "Udaipur", "Jodhpur", "Kota", "Ajmer"],
                "Sikkim": ["Gangtok", "Namchi", "Gyalshing"],
                "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
                "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar"],
                "Tripura": ["Agartala", "Udaipur", "Dharmanagar"],
                "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Noida"],
                "Uttarakhand": ["Dehradun", "Haridwar", "Rishikesh", "Haldwani", "Roorkee"],
                "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol"],
                "Andaman and Nicobar Islands": ["Port Blair", "Havelock Island", "Neil Island"],
                "Chandigarh": ["Chandigarh"],
                "Dadra and Nagar Haveli and Daman and Diu": ["Daman", "Diu", "Silvassa"],
                "Jammu and Kashmir (UT)": ["Srinagar", "Jammu", "Leh"],
                "Ladakh": ["Leh", "Kargil"],
                "Lakshadweep": ["Kavaratti", "Agatti"],
                "Puducherry": ["Puducherry", "Karaikal", "Mahe", "Yanam"]
            },
            "United States": {
                "California": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "San Jose"],
                "New York": ["New York", "Buffalo", "Rochester", "Albany"],
                "Texas": ["Houston", "Austin", "Dallas", "San Antonio"],
                "Florida": ["Miami", "Orlando", "Tampa", "Jacksonville"],
                "Illinois": ["Chicago", "Springfield", "Naperville"],
                "Washington": ["Seattle", "Spokane", "Tacoma"]
            },
            "United Kingdom": {
                "England": ["London", "Manchester", "Birmingham", "Liverpool", "Leeds"],
                "Scotland": ["Edinburgh", "Glasgow", "Aberdeen", "Inverness"],
                "Wales": ["Cardiff", "Swansea", "Newport"],
                "Northern Ireland": ["Belfast", "Derry", "Lisburn"]
            },
            "Canada": {
                "Ontario": ["Toronto", "Ottawa", "Mississauga", "Hamilton"],
                "British Columbia": ["Vancouver", "Victoria", "Kelowna", "Surrey"],
                "Quebec": ["Montreal", "Quebec City", "Laval"],
                "Alberta": ["Calgary", "Edmonton", "Banff"]
            },
            "Australia": {
                "New South Wales": ["Sydney", "Newcastle", "Wollongong"],
                "Victoria": ["Melbourne", "Geelong", "Ballarat"],
                "Queensland": ["Brisbane", "Gold Coast", "Cairns"],
                "Western Australia": ["Perth", "Fremantle"],
                "South Australia": ["Adelaide"]
            },
            "Japan": {
                "Tokyo": ["Tokyo"],
                "Osaka": ["Osaka"],
                "Kyoto": ["Kyoto"],
                "Hokkaido": ["Sapporo"],
                "Okinawa": ["Naha"]
            },
            "France": {
                "Île-de-France": ["Paris", "Versailles"],
                "Provence-Alpes-Côte d'Azur": ["Nice", "Marseille", "Cannes"],
                "Auvergne-Rhône-Alpes": ["Lyon", "Annecy"]
            },
            "Germany": {
                "Bavaria": ["Munich", "Nuremberg"],
                "Berlin": ["Berlin"],
                "Hesse": ["Frankfurt"],
                "North Rhine-Westphalia": ["Cologne", "Düsseldorf"]
            },
            "Italy": {
                "Lazio": ["Rome"],
                "Lombardy": ["Milan"],
                "Campania": ["Naples"],
                "Veneto": ["Venice", "Verona"]
            },
            "Spain": {
                "Community of Madrid": ["Madrid"],
                "Catalonia": ["Barcelona", "Girona"],
                "Andalusia": ["Seville", "Malaga", "Granada"]
            },
            "United Arab Emirates": {
                "Dubai": ["Dubai"],
                "Abu Dhabi": ["Abu Dhabi"],
                "Sharjah": ["Sharjah"]
            },
            "Singapore": {
                "Singapore": ["Singapore"]
            }
        }
        mood_to_interests = {
            "Foodie": ["Street Food", "Fine Dining", "Local Markets", "Cooking Classes", "Beverage Tours", "Food Shopping"],
            "Relaxing": ["Nature Walks", "Beach/Sunset Views", "Spa & Wellness", "Scenic Drives", "Art & Culture", "Light Shopping"],
            "Adventure": ["Trekking", "Water Sports", "Camping", "Wildlife Safari", "Extreme Sports", "Caving/Exploring"],
            "Family": ["Nature Parks", "Amusement Parks", "Cultural Shows", "Shopping", "Family Restaurants", "Light Adventure"],
            "Romantic": ["Sunset Points", "Candlelight Dinners", "Beaches", "Scenic Views", "Art & Culture", "Nature Walks"],
            "Office Trip": ["Team-Building Activities", "City Tours", "Workshops & Seminars", "Fine Dining", "Shopping", "Business Centers"]
        }
        return jsonify({"locations": locations, "mood_to_interests": mood_to_interests})
    except Exception as e:
        print(f"Locations endpoint error: {e}")
        return jsonify({"locations": {}, "mood_to_interests": {}})

# ===================== API: Places =====================
@app.route('/api/places')
def api_places():
    city = request.args.get('city', '').strip()
    days = int(request.args.get('days', 3) or 3)
    interests = request.args.get('interests', '').strip()
    mood = request.args.get('mood', '').strip()
    if not city:
        return jsonify({'places': []})
    cache_key = f"places::{city.lower()}::{days}::{(mood or '').lower()}::{interests.lower()}"
    cached = _cache_get(PLACES_CACHE, cache_key)
    if cached is not None:
        return jsonify({'places': cached})
    places = fetch_pois_from_opentripmap(city, interests, days, mood)
    _cache_set(PLACES_CACHE, cache_key, places)
    return jsonify({'places': places})

# ===================== API: Hotels =====================
@app.route('/api/hotels')
def api_hotels():
    city = request.args.get('city', '').strip()
    budget_min = request.args.get('budget_min')
    budget_max = request.args.get('budget_max')
    if not city:
        return jsonify({'hotels': []})
    mood = request.args.get('mood', '').strip()
    cache_key = f"hotels::{city.lower()}::{(mood or '').lower()}::{budget_min}::{budget_max}"
    cached = _cache_get(HOTELS_CACHE, cache_key)
    if cached is not None:
        return jsonify({'hotels': cached})
    hotels = fetch_hotels_from_opentripmap(city, budget_min, budget_max)
    _cache_set(HOTELS_CACHE, cache_key, hotels)
    return jsonify({'hotels': hotels})

# ===================== API: Itinerary (OpenAI) =====================
@app.route('/api/itinerary', methods=['POST'])
def api_itinerary():
    try:
        body = request.get_json(force=True) or {}
        print(f"Received itinerary request: {body.get('city', 'Unknown')}, {body.get('days', 3)} days, {body.get('mood', 'relaxing')}")
        
        ai_json = generate_grounded_ai_itinerary(body)
        if not isinstance(ai_json, dict) or not ai_json.get('itinerary'):
            raise Exception('Invalid AI response structure')
        
        # Attach personalization info for frontend greeting
        ai_json['name'] = body.get('name')
        ai_json['age'] = body.get('age')
        ai_json['gender'] = body.get('gender')
        
        print(f"Successfully generated itinerary for {body.get('city', 'Unknown')}")
        return jsonify(ai_json)
        
    except Exception as e:
        # Graceful fallback to mock grounded JSON so the UI still works
        print(f"Itinerary error: {e}")
        print(f"Falling back to mock data generation...")
        
        try:
            body = body if isinstance(body, dict) else {}
        except Exception:
            body = {}
            
        city = body.get('city') or 'Unknown'
        start_date = body.get('start_date')
        try:
            days = int(body.get('days', 3))
        except Exception:
            days = 3
        mood = body.get('mood', 'relaxing')
        pois = body.get('pois', [])
        hotels = body.get('hotels', [])
        
        try:
            fallback = generate_mock_ai_json(city, start_date, days, mood, pois, hotels, body.get('age'), body.get('gender'))
            fallback['name'] = body.get('name')
            fallback['age'] = body.get('age')
            fallback['gender'] = body.get('gender')
            print(f"Successfully generated fallback itinerary for {city}")
            return jsonify(fallback)
        except Exception as fallback_error:
            print(f"Fallback generation also failed: {fallback_error}")
            # Return a minimal working response
            return jsonify({
                'destination': city,
                'start_date': start_date,
                'days': days,
                'mood': mood,
                'itinerary': [{
                    'day': 1,
                    'morning': {'activity': 'Explore the city', 'poi': {'name': 'City Center', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                    'afternoon': {'activity': 'Visit local attractions', 'poi': {'name': 'Local Attractions', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                    'evening': {'activity': 'Enjoy local cuisine', 'poi': {'name': 'Local Restaurants', 'lat': 0, 'lon': 0, 'image': '', 'source': ''}},
                    'dinner': {'suggestion': 'Try local specialties', 'restaurant_link': ''},
                    'accommodation': {'name': 'Local Hotel', 'price_in_inr': '₹5,000–₹12,000', 'link': ''},
                    'weather': {'summary': 'Pleasant weather', 'high': '25°C', 'low': '18°C'}
                }],
                'famous_places': [],
                'hotels': [],
                'packing_list': ['Comfortable clothes', 'Walking shoes', 'Camera', 'Water bottle'],
                'events': [],
                'map_embed_url': '',
                'total_budget_inr': '₹15,000',
                'name': body.get('name'),
                'age': body.get('age'),
                'gender': body.get('gender')
            })

# ===================== API: Save/CRUD =====================
@app.route('/api/save', methods=['POST'])
@login_required
def api_save():
    data = request.get_json(force=True)
    current_user_id = get_current_user_id()
    
    try:
        unique_id = str(uuid.uuid4())
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trips (
                unique_id, user_id, name, age, gender, country, state, destination, start_date, days, mood, budget_range_inr, interests,
                pois_json, hotels_json, itinerary_text, packing_list_json, weather_json, events_json, map_data_json, total_budget_inr
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            unique_id,
            current_user_id,  # Use current user's ID
            (data.get('name') or '').strip() or None,
            int(data.get('age')) if str(data.get('age') or '').isdigit() else None,
            (data.get('gender') or ''),
            data.get('country') or '',
            data.get('state') or '',
            data.get('destination') or 'Unknown',
            data.get('start_date') or '',
            int(data.get('days', 3) or 3),
            data.get('mood') or '',
            data.get('budget_range_inr') or '',
            json.dumps(data.get('interests') or []),
            json.dumps(data.get('pois') or []),
            json.dumps(data.get('hotels') or []),
            json.dumps(data.get('itinerary') or {}),
            json.dumps(data.get('packing_list') or []),
            json.dumps(data.get('weather') or []),
            json.dumps(data.get('events') or []),
            json.dumps(data.get('map_data') or {}),
            str(data.get('total_budget_inr') or '')
        ))
        conn.commit()
        conn.close()
        return jsonify({
            'success': True, 
            'id': unique_id,
            'name': (data.get('name') or '').strip() or 'Anonymous'
        })
    except Exception as e:
        print(f"Save error: {e}")
        # Attempt schema ensure + dynamic save fallback
        try:
            init_db()
            fallback_id = _dynamic_save_trip(data, current_user_id)
            if fallback_id:
                return jsonify({'success': True, 'id': fallback_id})
        except Exception as ee:
            print(f"Dynamic save failed: {ee}")
            try:
                minimal_id = _minimal_save_trip(data, current_user_id)
                if minimal_id:
                    return jsonify({'success': True, 'id': minimal_id})
            except Exception as e3:
                print(f"Minimal save failed: {e3}")
        return jsonify({'error': f'Failed to save: {e}'}), 500

def _dynamic_save_trip(data, user_id):
    """Fallback: dynamically insert only columns that exist in the current trips table."""
    unique_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trips)")
    cols = [row[1] for row in cursor.fetchall()]
    payload = {
        'unique_id': unique_id,
        'user_id': user_id,
        'name': (data.get('name') or '').strip() or None,
        'age': int(data.get('age')) if str(data.get('age') or '').isdigit() else None,
        'gender': (data.get('gender') or ''),
        'country': data.get('country') or '',
        'state': data.get('state') or '',
        'destination': data.get('destination') or 'Unknown',
        'start_date': data.get('start_date') or '',
        'days': int(data.get('days', 3) or 3),
        'mood': data.get('mood') or '',
        'budget_range_inr': data.get('budget_range_inr') or '',
        'interests': json.dumps(data.get('interests') or []),
        'pois_json': json.dumps(data.get('pois') or []),
        'hotels_json': json.dumps(data.get('hotels') or []),
        'itinerary_text': json.dumps(data.get('itinerary') or {}),
        'packing_list_json': json.dumps(data.get('packing_list') or []),
        'weather_json': json.dumps(data.get('weather') or []),
        'events_json': json.dumps(data.get('events') or []),
        'map_data_json': json.dumps(data.get('map_data') or {}),
        'total_budget_inr': str(data.get('total_budget_inr') or '')
    }
    insert_cols = [c for c in payload.keys() if c in cols]
    placeholders = ','.join(['?'] * len(insert_cols))
    sql = f"INSERT INTO trips ({', '.join(insert_cols)}) VALUES ({placeholders})"
    print(f"Dynamic save columns: {insert_cols}")
    cursor.execute(sql, tuple(payload[c] for c in insert_cols))
    conn.commit()
    conn.close()
    return unique_id

def _minimal_save_trip(data, user_id):
    """Last-resort fallback insert with minimal subset of columns."""
    unique_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trips)")
    cols = {row[1] for row in cursor.fetchall()}
    field_values = {
        'unique_id': unique_id,
        'user_id': user_id,
        'country': data.get('country') or '',
        'state': data.get('state') or '',
        'destination': data.get('destination') or 'Unknown',
        'start_date': data.get('start_date') or '',
        'days': int(data.get('days', 3) or 3),
        'mood': data.get('mood') or '',
        'itinerary_text': json.dumps(data.get('itinerary') or {}),
        'total_budget_inr': str(data.get('total_budget_inr') or '')
    }
    use_cols = [c for c in ['unique_id','user_id','country','state','destination','start_date','days','mood','itinerary_text','total_budget_inr'] if c in cols]
    placeholders = ','.join(['?'] * len(use_cols))
    sql = f"INSERT INTO trips ({', '.join(use_cols)}) VALUES ({placeholders})"
    print(f"Minimal save columns: {use_cols}")
    cursor.execute(sql, tuple(field_values[c] for c in use_cols))
    conn.commit()
    conn.close()
    return unique_id

@app.route('/api/plans')
@login_required
def api_plans():
    try:
        current_user_id = get_current_user_id()
        current_user_role = get_current_user_role()
        
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Admin and root users can see all plans, regular users only see their own
        if current_user_role in [ROLE_ADMIN, ROLE_ROOT]:
            cursor.execute('''
                SELECT t.unique_id, t.destination, t.start_date, t.days, t.mood, t.total_budget_inr, 
                       t.created_at, t.country, t.state, t.name, t.city, t.updated_at, t.user_id,
                       u.name as creator_name, u.email as creator_email
                FROM trips t 
                LEFT JOIN users u ON t.user_id = u.id
                ORDER BY t.updated_at DESC, t.created_at DESC
            ''')
        else:
            cursor.execute('''
                SELECT t.unique_id, t.destination, t.start_date, t.days, t.mood, t.total_budget_inr, 
                       t.created_at, t.country, t.state, t.name, t.city, t.updated_at, t.user_id,
                       u.name as creator_name, u.email as creator_email
                FROM trips t 
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.user_id = ?
                ORDER BY t.updated_at DESC, t.created_at DESC
            ''', (current_user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        plans = []
        for r in rows:
            # Compute display destination if missing
            dest = r[1] if (r[1] and str(r[1]).strip()) else ', '.join([p for p in [r[10] if len(r)>10 else '', r[8] if len(r)>8 else '', r[7] if len(r)>7 else ''] if p and str(p).strip()])
            
            plan_data = {
                'id': r[0],
                'unique_id': r[0],
                'country': r[7] if len(r) > 7 else '',
                'state': r[8] if len(r) > 8 else '',
                'name': r[9] if len(r) > 9 else 'Anonymous',
                'city': r[10] if len(r) > 10 else '',
                'destination': dest,
                'start_date': r[2],
                'days': r[3],
                'mood': r[4],
                'total_budget_inr': r[5],
                'created_at': r[6],
                'updated_at': r[11] if len(r) > 11 else r[6],
                'user_id': r[12] if len(r) > 12 else None,
                'creator_name': r[13] if len(r) > 13 else 'Anonymous',
                'creator_email': r[14] if len(r) > 14 else '',
                'is_owner': current_user_id == r[12] if len(r) > 12 else False
            }
            
            # Add admin info for admin/root users
            if current_user_role in [ROLE_ADMIN, ROLE_ROOT]:
                plan_data['can_edit'] = True
                plan_data['can_delete'] = True
            else:
                plan_data['can_edit'] = plan_data['is_owner']
                plan_data['can_delete'] = plan_data['is_owner']
            
            plans.append(plan_data)
        
        return jsonify(plans)
    except Exception as e:
        print(f"List plans error: {e}")
        return jsonify([])

def _row_to_plan_dict(row):
    try:
        # Handle both tuple and Row objects
        if isinstance(row, sqlite3.Row):
            row_dict = dict(row)
        else:
            # Convert tuple to dict with column names
            columns = ['id', 'unique_id', 'user_id', 'name', 'age', 'gender', 'country', 'state', 'city',
                      'destination', 'start_date', 'days', 'mood', 'budget_range_inr', 'interests', 
                      'pois_json', 'hotels_json', 'itinerary_text', 'packing_list_json', 'weather_json', 
                      'events_json', 'map_data_json', 'total_budget_inr', 'created_at', 'updated_at']
            row_dict = dict(zip(columns, row))
        
        # Safe JSON parsing with fallbacks
        def safe_json_loads(value, default=None):
            if not value:
                return default
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return default
        
        return {
            'id': row_dict.get('id'),
            'unique_id': row_dict.get('unique_id'),
            'user_id': row_dict.get('user_id'),
            'name': row_dict.get('name'),
            'age': row_dict.get('age'),
            'gender': row_dict.get('gender'),
            'country': row_dict.get('country', ''),
            'state': row_dict.get('state', ''),
            'city': row_dict.get('city', ''),
            'destination': row_dict.get('destination', ''),
            'start_date': row_dict.get('start_date'),
            'days': row_dict.get('days'),
            'mood': row_dict.get('mood'),
            'budget_range_inr': row_dict.get('budget_range_inr'),
            'interests': safe_json_loads(row_dict.get('interests'), []),
            'pois': safe_json_loads(row_dict.get('pois_json'), []),
            'hotels': safe_json_loads(row_dict.get('hotels_json'), []),
            'itinerary': safe_json_loads(row_dict.get('itinerary_text'), {}),
            'packing_list': safe_json_loads(row_dict.get('packing_list_json'), []),
            'weather': safe_json_loads(row_dict.get('weather_json'), []),
            'events': safe_json_loads(row_dict.get('events_json'), []),
            'map_data': safe_json_loads(row_dict.get('map_data_json'), {}),
            'total_budget_inr': row_dict.get('total_budget_inr'),
            'created_at': row_dict.get('created_at'),
            'updated_at': row_dict.get('updated_at')
        }
    except Exception as e:
        print(f"Error converting row to dict: {e}")
        # Return a minimal valid structure
        return {
            'id': None,
            'unique_id': '',
            'destination': 'Unknown',
            'days': 1,
            'mood': 'Unknown',
            'interests': [],
            'pois': [],
            'hotels': [],
            'itinerary': {},
            'packing_list': [],
            'weather': [],
            'events': [],
            'map_data': {},
            'total_budget_inr': '0',
            'created_at': datetime.now().isoformat()
        }

@app.route('/api/plans/<plan_id>')
@login_required
def api_plan_get(plan_id):
    try:
        current_user_id = get_current_user_id()
        current_user_role = get_current_user_role()
        
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trips WHERE unique_id = ?', (plan_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Check access permissions
        plan_user_id = row['user_id']
        if not can_access_plan(current_user_id, plan_user_id, current_user_role):
            return jsonify({'error': 'Access denied'}), 403
        
        plan_data = _row_to_plan_dict(row)
        
        # Add creator information for admin/root users
        if current_user_role in [ROLE_ADMIN, ROLE_ROOT]:
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('SELECT name, email FROM users WHERE id = ?', (plan_user_id,))
            creator_info = cursor.fetchone()
            conn.close()
            
            if creator_info:
                plan_data['creator_name'] = creator_info[0] or 'Anonymous'
                plan_data['creator_email'] = creator_info[1] or ''
        
        return jsonify(plan_data)
    except Exception as e:
        print(f"Get plan error: {e}")
        return jsonify({'error': 'Failed to load plan'}), 500

@app.route('/api/plans/<plan_id>', methods=['PUT'])
@login_required
def api_plan_update(plan_id):
    data = request.get_json(force=True)
    current_user_id = get_current_user_id()
    current_user_role = get_current_user_role()
    
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check if plan exists and get user_id
        cursor.execute('SELECT id, destination, country, state, city, user_id FROM trips WHERE unique_id = ?', (plan_id,))
        existing_row = cursor.fetchone()
        if not existing_row:
            conn.close()
            return jsonify({'error': 'Plan not found'}), 404
        
        # Check access permissions
        plan_user_id = existing_row[5]  # user_id is at index 5
        if not can_access_plan(current_user_id, plan_user_id, current_user_role):
            conn.close()
            return jsonify({'error': 'Access denied'}), 403
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        # Fields that can be updated
        updatable_fields = {
            'destination': 'destination',
            'start_date': 'start_date', 
            'days': 'days',
            'mood': 'mood',
            'total_budget_inr': 'total_budget_inr',
            'budget_range_inr': 'budget_range_inr',
            'interests': 'interests',
            'country': 'country',
            'state': 'state',
            'city': 'city',
            'itinerary': 'itinerary_text',
            'pois': 'pois_json',
            'hotels': 'hotels_json',
            'packing_list': 'packing_list_json',
            'weather': 'weather_json',
            'events': 'events_json',
            'map_data': 'map_data_json'
        }
        
        for field, db_field in updatable_fields.items():
            if field in data:
                update_fields.append(f'{db_field} = ?')
                # Handle JSON fields
                if db_field.endswith('_json') or db_field == 'itinerary_text':
                    params.append(json.dumps(data[field]) if isinstance(data[field], (dict, list)) else data[field])
                else:
                    params.append(data[field])

        # If destination is missing or empty but city/state/country present, compute destination
        dest_in_payload = 'destination' in data and str(data.get('destination') or '').strip() != ''
        any_location_change = any(k in data for k in ('city','state','country'))
        if (not dest_in_payload) and any_location_change:
            # Use incoming values if provided, otherwise existing ones
            existing_dest, existing_country, existing_state, existing_city = existing_row[1], existing_row[2], existing_row[3], existing_row[4]
            city_val = (data.get('city') if 'city' in data else existing_city) or ''
            state_val = (data.get('state') if 'state' in data else existing_state) or ''
            country_val = (data.get('country') if 'country' in data else existing_country) or ''
            computed_destination = ', '.join([p for p in [city_val, state_val, country_val] if str(p).strip()])
            if computed_destination:
                update_fields.append('destination = ?')
                params.append(computed_destination)
        
        if not update_fields:
            conn.close()
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Add updated_at timestamp
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        
        # Add plan_id to params
        params.append(plan_id)
        
        # Execute update
        query = f'UPDATE trips SET {", ".join(update_fields)} WHERE unique_id = ?'
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Plan updated successfully'})
        
    except Exception as e:
        print(f"Update error: {e}")
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/api/plans/<plan_id>', methods=['DELETE'])
@login_required
def api_plan_delete(plan_id):
    current_user_id = get_current_user_id()
    current_user_role = get_current_user_role()
    
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        
        # Check if plan exists and get user_id
        cursor.execute('SELECT user_id FROM trips WHERE unique_id = ?', (plan_id,))
        existing_row = cursor.fetchone()
        if not existing_row:
            conn.close()
            return jsonify({'error': 'Plan not found'}), 404
        
        # Check access permissions
        plan_user_id = existing_row[0]
        if not can_access_plan(current_user_id, plan_user_id, current_user_role):
            conn.close()
            return jsonify({'error': 'Access denied'}), 403
        
        cursor.execute('DELETE FROM trips WHERE unique_id = ?', (plan_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({'error': 'Failed to delete'}), 500

# ===================== Public Share Page =====================
@app.route('/plan/<plan_id>')
def share_page(plan_id):
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trips WHERE unique_id = ?', (plan_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return render_template('share.html', plan=None)
        plan = _row_to_plan_dict(row)
        # Convert created_at to datetime for template formatting compatibility
        try:
            plan['created_at'] = datetime.fromisoformat(plan['created_at'])
        except Exception:
            plan['created_at'] = datetime.now()
        return render_template('share.html', plan=plan)
    except Exception as e:
        print(f"Share page error: {e}")
        return render_template('share.html', plan=None)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Removed duplicate function definition

def parse_ai_prompt(prompt):
    """Parse AI prompt to extract destination and days"""
    prompt_lower = prompt.lower()
    
    # Enhanced destination list with more locations
    destinations = [
        "goa", "mumbai", "delhi", "bangalore", "chennai", "kolkata", "pune", "hyderabad", 
        "jaipur", "udaipur", "varanasi", "agra", "kerala", "manali", "shimla", "darjeeling", 
        "ooty", "munnar", "kodaikanal", "gangtok", "amritsar", "jodhpur", "jaisalmer", 
        "bikaner", "pushkar", "khajuraho", "hampi", "mahabalipuram", "ellora", "ajanta", 
        "sarnath", "bodh gaya", "srinagar", "leh", "ladakh", "spiti", "rishikesh", 
        "haridwar", "kedarnath", "badrinath", "gangotri", "yamunotri", "puri", "bhubaneswar",
        "konark", "cuttack", "rourkela", "sambalpur", "berhampur", "balasore", "bhadrak",
        "jagatsinghpur", "kendrapara", "mayurbhanj", "keonjhar", "sundargarh", "angul",
        "dhenkanal", "nayagarh", "khordha", "gajapati", "ganjam", "kandhamal", "boudh",
        "sonepur", "balangir", "nuapada", "kalahandi", "rayagada", "koraput", "malkangiri",
        "nabarangpur", "jajpur", "deogarh", "jharsuguda", "bargarh", "subarnapur"
    ]
    
    destination = None
    for dest in destinations:
        if dest in prompt_lower:
            destination = dest.title()
            break
    
    if not destination:
        # Try to extract any capitalized word that might be a destination
        words = prompt.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                destination = word
                break
    
    if not destination:
        # Look for location indicators
        location_indicators = ["to", "in", "at", "visit", "go", "travel"]
        words = prompt.split()
        for i, word in enumerate(words):
            if word.lower() in location_indicators and i + 1 < len(words):
                potential_dest = words[i + 1].title()
                if len(potential_dest) > 2:
                    destination = potential_dest
                    break
    
    if not destination:
        destination = "Mumbai"  # Default destination
    
    # Extract number of days with more patterns
    import re
    day_patterns = [
        r'(\d+)\s*day',
        r'(\d+)\s*days',
        r'for\s*(\d+)\s*day',
        r'(\d+)\s*night',
        r'(\d+)\s*nights'
    ]
    
    days = 3  # Default to 3 days
    for pattern in day_patterns:
        day_matches = re.findall(pattern, prompt_lower)
        if day_matches:
            days = int(day_matches[0])
            break
    
    return destination, days

# ===================== AI Agent Endpoint =====================
@app.route('/ask-agent', methods=['POST'])
def ask_agent():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        mood = data.get('mood', 'relaxing')
        days = data.get('days', 3)
        name = data.get('name', '')
        age = data.get('age', '')
        gender = data.get('gender', '')
        destination = data.get('destination', '')
        country = data.get('country', '')
        state = data.get('state', '')
        city = data.get('city', '')
        
        if not prompt or not destination:
            return jsonify({'error': 'Prompt and destination are required'}), 400
        
        # Generate a comprehensive travel plan using AI
        ai_plan = generate_ai_travel_plan(prompt, destination, days, mood, name, age, gender, country, state, city)
        
        return jsonify(ai_plan)
        
    except Exception as e:
        print(f"AI Agent error: {e}")
        return jsonify({'error': 'Failed to generate AI plan'}), 500

def generate_ai_travel_plan(prompt: str = "", destination: str | None = None, days: int = 3, mood: str = "relaxing", name: str | None = None, age: str | None = None, gender: str | None = None, country: str = "", state: str = "", city: str = "", start_date: str | None = None, end_date: str | None = None, weather: dict | None = None, interests: list | None = None):
    """Generate a comprehensive travel plan using AI"""
    try:
        # Create a personalized prompt for the AI
        ai_prompt = f"""
        Create a detailed {days}-day travel plan for {destination} with a {mood} mood.
        
        Location Details:
        - Destination: {destination}
        - Country: {country}
        - State: {state}
        - City: {city}
        
        User Details:
        - Name: {name}
        - Age: {age}
        - Gender: {gender}
        - Special Request: {prompt}
        
        IMPORTANT: Focus specifically on {destination} and provide ONLY attractions and activities that are actually located in {destination}. Do not include generic attractions that could be anywhere.
        
        Please provide a comprehensive travel plan with:
        1. A personalized greeting using the user's name
        2. Daily itinerary with specific activities for morning, afternoon, evening, and dinner - all activities must be specific to {destination}
        3. Top 5-8 MOST FAMOUS and MUST-VISIT places in {destination} with:
           - Exact location within {destination}
           - Detailed descriptions of what makes them special
           - Realistic entry fees in INR
           - Best visiting times (morning/afternoon/evening)
           - Why they are famous in {destination}
        4. Weather information for each day with temperature ranges
        5. Detailed budget breakdown in INR including:
           - Accommodation (per night) - realistic for {destination}
           - Food (per day) - local cuisine costs in {destination}
           - Transportation (local and inter-city) - specific to {destination}
           - Activities and entry fees - actual costs for {destination} attractions
           - Shopping and miscellaneous - local market costs
           - Total budget
        6. Packing list based on the destination, weather, and mood
        7. Travel tips and recommendations specific to {destination} only
        8. Best time to visit each place in {destination}
        9. Local cuisine recommendations specific to {destination}
        10. Transportation options within {destination}
        
        CRITICAL: All attractions, activities, and recommendations must be specific to {destination}. Do not include generic or non-local attractions.
        
        Format the response as a structured JSON with the following fields:
        - destination: string
        - days: integer
        - mood: string
        - name: string
        - itinerary: array of day objects with morning, afternoon, evening, dinner fields
        - famous_places: array of place objects with name, description, entry_fee, best_time, image fields
        - weather: array of weather objects with day, temperature, forecast fields
        - budget_breakdown: object with accommodation, food, transportation, activities, shopping, total fields
        - total_budget_inr: string
        - packing_list: array of strings
        - travel_tips: array of strings
        - local_cuisine: array of strings
        - transportation_tips: string
        """
        
        # Use OpenAI to generate the plan
        if openai.api_key:
            try:
                client = openai.OpenAI(api_key=openai.api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"You are an expert travel planner specializing in {destination} and Indian destinations. You must provide ONLY location-specific attractions, activities, and recommendations that are actually found in {destination}. Do not include generic attractions that could be anywhere. Focus on the most famous, must-visit places that make {destination} unique. Provide realistic costs and practical information specific to {destination}."},
                        {"role": "user", "content": ai_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                # Parse the AI response
                ai_response = response.choices[0].message.content
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    import json
                    try:
                        plan_data = json.loads(json_match.group())
                        # Validate and enhance the plan with location-specific attractions
                        plan_data = validate_and_enhance_plan(plan_data, destination, city, state, country)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, create a structured plan from the text
                        plan_data = create_structured_plan_from_text(ai_response, destination, days, mood, name)
                        plan_data = validate_and_enhance_plan(plan_data, destination, city, state, country)
                else:
                    # If no JSON found, create a structured plan from the text
                    plan_data = create_structured_plan_from_text(ai_response, destination, days, mood, name)
                    plan_data = validate_and_enhance_plan(plan_data, destination, city, state, country)
                
                return plan_data
                
            except Exception as e:
                print(f"OpenAI API error: {e}")
                # Fallback to generated plan
                return create_fallback_plan(destination, days, mood, name, prompt)
        else:
            # No OpenAI API key, use fallback
            return create_fallback_plan(destination, days, mood, name, prompt)
            
    except Exception as e:
        print(f"Error generating AI plan: {e}")
        return create_fallback_plan(destination, days, mood, name, prompt)

def create_structured_plan_from_text(text, destination, days, mood, name):
    """Create a structured plan from AI text response"""
    return {
        'destination': destination,
        'days': days,
        'mood': mood,
        'name': name,
        'itinerary': generate_daily_itinerary(days, mood),
        'famous_places': get_location_specific_attractions(destination, '', '', ''),
        'weather': generate_weather_forecast(days),
        'total_budget_inr': f"₹{days * 5000:,}",
        'packing_list': get_packing_list(mood, destination),
        'travel_tips': get_travel_tips(destination)
    }

def validate_and_enhance_plan(plan_data, destination, city, state, country):
    """Validate and enhance the AI-generated plan with location-specific attractions"""
    try:
        # Ensure destination is set correctly
        plan_data['destination'] = destination
        
        # If no famous places or generic places, add location-specific ones
        if not plan_data.get('famous_places') or len(plan_data['famous_places']) == 0:
            plan_data['famous_places'] = get_location_specific_attractions(destination, city, state, country)
        
        # Validate that attractions are location-specific
        validated_places = []
        for place in plan_data.get('famous_places', []):
            if is_location_specific_attraction(place, destination, city, state, country):
                validated_places.append(place)
        
        # If no valid places, add default location-specific ones
        if not validated_places:
            plan_data['famous_places'] = get_location_specific_attractions(destination, city, state, country)
        else:
            plan_data['famous_places'] = validated_places
        
        return plan_data
    except Exception as e:
        print(f"Error validating plan: {e}")
        return plan_data

def is_location_specific_attraction(place, destination, city, state, country):
    """Check if an attraction is specific to the given location"""
    place_name = place.get('name', '').lower()
    place_desc = place.get('description', '').lower()
    
    # Check if the place name or description contains location-specific keywords
    location_keywords = [destination.lower(), city.lower(), state.lower(), country.lower()]
    
    for keyword in location_keywords:
        if keyword and (keyword in place_name or keyword in place_desc):
            return True
    
    # Check for common generic attractions that should be filtered out
    generic_attractions = ['mall', 'shopping center', 'park', 'garden', 'restaurant', 'hotel']
    for generic in generic_attractions:
        if generic in place_name and not any(keyword in place_name for keyword in location_keywords if keyword):
            return False
    
    return True

def get_location_specific_attractions(destination, city, state, country):
    """Get location-specific attractions based on the destination"""
    # Define location-specific attractions for major destinations
    location_attractions = {
        'mumbai': [
            {
                'name': 'Gateway of India',
                'description': 'Historic monument and popular tourist attraction in Mumbai',
                'entry_fee': 'Free',
                'best_time': 'Morning or Evening',
                'rating': '4.5'
            },
            {
                'name': 'Marine Drive',
                'description': 'Scenic 3.6-km-long curved boulevard along the coast',
                'entry_fee': 'Free',
                'best_time': 'Evening for sunset',
                'rating': '4.5'
            },
            {
                'name': 'Juhu Beach',
                'description': 'Famous beach known for street food and sunset views',
                'entry_fee': 'Free',
                'best_time': 'Evening',
                'rating': '4.3'
            },
            {
                'name': 'Elephanta Caves',
                'description': 'Ancient cave temples dedicated to Lord Shiva',
                'entry_fee': '₹40 for Indians, ₹600 for foreigners',
                'best_time': 'Morning',
                'rating': '4.4'
            },
            {
                'name': 'Colaba Causeway',
                'description': 'Famous shopping street and tourist hub',
                'entry_fee': 'Free',
                'best_time': 'Afternoon',
                'rating': '4.2'
            }
        ],
        'delhi': [
            {
                'name': 'Red Fort',
                'description': 'Historic fort and UNESCO World Heritage Site',
                'entry_fee': '₹35 for Indians, ₹500 for foreigners',
                'best_time': 'Morning',
                'rating': '4.5'
            },
            {
                'name': 'Qutub Minar',
                'description': 'Tallest brick minaret in the world',
                'entry_fee': '₹30 for Indians, ₹500 for foreigners',
                'best_time': 'Morning',
                'rating': '4.4'
            },
            {
                'name': 'India Gate',
                'description': 'War memorial and popular landmark',
                'entry_fee': 'Free',
                'best_time': 'Evening',
                'rating': '4.3'
            },
            {
                'name': 'Humayun\'s Tomb',
                'description': 'Mughal architecture masterpiece',
                'entry_fee': '₹30 for Indians, ₹500 for foreigners',
                'best_time': 'Morning',
                'rating': '4.4'
            },
            {
                'name': 'Chandni Chowk',
                'description': 'Historic market and food street',
                'entry_fee': 'Free',
                'best_time': 'Morning',
                'rating': '4.2'
            }
        ],
        'goa': [
            {
                'name': 'Calangute Beach',
                'description': 'Queen of Beaches, popular tourist destination',
                'entry_fee': 'Free',
                'best_time': 'Morning or Evening',
                'rating': '4.4'
            },
            {
                'name': 'Basilica of Bom Jesus',
                'description': 'UNESCO World Heritage Site with St. Francis Xavier\'s remains',
                'entry_fee': 'Free',
                'best_time': 'Morning',
                'rating': '4.5'
            },
            {
                'name': 'Fort Aguada',
                'description': '17th-century Portuguese fort with lighthouse',
                'entry_fee': '₹25',
                'best_time': 'Evening for sunset',
                'rating': '4.3'
            },
            {
                'name': 'Dudhsagar Falls',
                'description': 'Four-tiered waterfall in the Western Ghats',
                'entry_fee': '₹20',
                'best_time': 'Monsoon season',
                'rating': '4.6'
            },
            {
                'name': 'Anjuna Beach',
                'description': 'Famous for flea market and nightlife',
                'entry_fee': 'Free',
                'best_time': 'Evening',
                'rating': '4.2'
            }
        ],
        'puri': [
            {
                'name': 'Jagannath Temple',
                'description': 'Sacred Hindu temple dedicated to Lord Jagannath',
                'entry_fee': 'Free (Hindus only)',
                'best_time': 'Early Morning',
                'rating': '4.7'
            },
            {
                'name': 'Puri Beach',
                'description': 'Famous beach known for its golden sand and waves',
                'entry_fee': 'Free',
                'best_time': 'Morning or Evening',
                'rating': '4.5'
            },
            {
                'name': 'Konark Sun Temple',
                'description': 'UNESCO World Heritage Site, architectural marvel',
                'entry_fee': '₹40 for Indians, ₹600 for foreigners',
                'best_time': 'Morning',
                'rating': '4.6'
            },
            {
                'name': 'Chilika Lake',
                'description': 'Asia\'s largest brackish water lagoon',
                'entry_fee': '₹50',
                'best_time': 'Morning for bird watching',
                'rating': '4.4'
            },
            {
                'name': 'Gundicha Temple',
                'description': 'Garden House of Lord Jagannath',
                'entry_fee': 'Free',
                'best_time': 'Morning',
                'rating': '4.3'
            }
        ]
    }
    
    # Try to find attractions for the destination
    destination_lower = destination.lower()
    city_lower = city.lower() if city else ''
    
    # Check exact matches first
    if destination_lower in location_attractions:
        return location_attractions[destination_lower]
    elif city_lower in location_attractions:
        return location_attractions[city_lower]
    
    # Check partial matches
    for key, attractions in location_attractions.items():
        if key in destination_lower or destination_lower in key:
            return attractions
    
    # Return default attractions if no specific ones found
    return [
        {
            'name': f'Local Attraction in {destination}',
            'description': f'Explore the unique culture and heritage of {destination}',
            'entry_fee': 'Varies',
            'best_time': 'Morning',
            'rating': '4.0'
        }
    ]

def create_fallback_plan(destination, days, mood, name, prompt):
    """Create a fallback plan when AI is not available"""
    return {
        'destination': destination,
        'days': days,
        'mood': mood,
        'name': name,
        'itinerary': generate_daily_itinerary(days, mood),
        'famous_places': get_location_specific_attractions(destination, '', '', ''),
        'weather': generate_weather_forecast(days),
        'total_budget_inr': f"₹{days * 5000:,}",
        'packing_list': get_packing_list(mood, destination),
        'travel_tips': get_travel_tips(destination)
    }

def generate_daily_itinerary(days, mood):
    """Generate a daily itinerary based on mood and days"""
    itinerary = []
    
    mood_activities = {
        'relaxing': {
            'morning': ['Morning yoga or meditation', 'Light breakfast at a local cafe', 'Visit a peaceful temple or garden'],
            'afternoon': ['Spa treatment or wellness session', 'Leisurely lunch at a restaurant', 'Relaxing beach or park visit'],
            'evening': ['Sunset viewing', 'Evening stroll', 'Dinner at a fine dining restaurant'],
            'dinner': ['Traditional local cuisine', 'Rooftop dining with city views', 'Seafood feast']
        },
        'adventurous': {
            'morning': ['Early morning trek or hike', 'Adventure sports', 'Exploration of historical sites'],
            'afternoon': ['Water sports or outdoor activities', 'Local market exploration', 'Cultural activities'],
            'evening': ['Adventure photography', 'Local festival participation', 'Night safari or camping'],
            'dinner': ['Street food tour', 'Local tribal cuisine', 'Campfire dinner']
        },
        'foodie': {
            'morning': ['Cooking class with local chef', 'Breakfast at famous local eatery', 'Spice market visit'],
            'afternoon': ['Food tour of local specialties', 'Lunch at renowned restaurant', 'Tea/coffee plantation visit'],
            'evening': ['Wine tasting or brewery tour', 'Dinner at Michelin-starred restaurant', 'Dessert tasting'],
            'dinner': ['Multi-course traditional meal', 'Fusion cuisine experience', 'Street food adventure']
        },
        'romantic': {
            'morning': ['Couple spa session', 'Romantic breakfast in bed', 'Private boat ride'],
            'afternoon': ['Couple cooking class', 'Romantic lunch with wine', 'Private guided tour'],
            'evening': ['Sunset cruise', 'Romantic dinner under stars', 'Couple dance class'],
            'dinner': ['Candlelight dinner', 'Private dining experience', 'Romantic rooftop meal']
        },
        'family': {
            'morning': ['Family-friendly museum visit', 'Breakfast at family restaurant', 'Educational tour'],
            'afternoon': ['Amusement park or zoo visit', 'Family lunch', 'Interactive workshops'],
            'evening': ['Family games and activities', 'Evening entertainment show', 'Family dinner'],
            'dinner': ['Kid-friendly restaurant', 'Family-style dining', 'Traditional family meal']
        }
    }
    
    activities = mood_activities.get(mood, mood_activities['relaxing'])
    
    for day in range(1, days + 1):
        day_plan = {
            'day': day,
            'morning': {'activity': activities['morning'][day % len(activities['morning'])]},
            'afternoon': {'activity': activities['afternoon'][day % len(activities['afternoon'])]},
            'evening': {'activity': activities['evening'][day % len(activities['evening'])]},
            'dinner': {'activity': activities['dinner'][day % len(activities['dinner'])]}
        }
        itinerary.append(day_plan)
    
    return itinerary

def get_famous_places(destination):
    """Get famous places for the destination"""
    places_data = {
        'Mumbai': [
            {'name': 'Gateway of India', 'description': 'Historic monument and popular tourist attraction', 'image': '/static/placeholder.jpg'},
            {'name': 'Marine Drive', 'description': 'Scenic 3.6-km-long curved boulevard along the coast', 'image': '/static/placeholder.jpg'},
            {'name': 'Juhu Beach', 'description': 'Famous beach known for street food and sunset views', 'image': '/static/placeholder.jpg'}
        ],
        'Delhi': [
            {'name': 'Red Fort', 'description': 'Historic fort and UNESCO World Heritage site', 'image': '/static/placeholder.jpg'},
            {'name': 'Qutub Minar', 'description': 'Tallest brick minaret in the world', 'image': '/static/placeholder.jpg'},
            {'name': 'India Gate', 'description': 'War memorial and national monument', 'image': '/static/placeholder.jpg'}
        ],
        'Goa': [
            {'name': 'Calangute Beach', 'description': 'Queen of beaches with golden sand and clear waters', 'image': '/static/placeholder.jpg'},
            {'name': 'Basilica of Bom Jesus', 'description': 'UNESCO World Heritage site and church', 'image': '/static/placeholder.jpg'},
            {'name': 'Fort Aguada', 'description': '17th-century Portuguese fort with lighthouse', 'image': '/static/placeholder.jpg'}
        ],
        'Puri': [
            {'name': 'Jagannath Temple', 'description': 'Sacred Hindu temple and major pilgrimage site', 'image': '/static/placeholder.jpg'},
            {'name': 'Puri Beach', 'description': 'Famous beach known for its golden sand and waves', 'image': '/static/placeholder.jpg'},
            {'name': 'Konark Sun Temple', 'description': 'UNESCO World Heritage site and architectural marvel', 'image': '/static/placeholder.jpg'}
        ]
    }
    
    return places_data.get(destination, places_data['Mumbai'])

def generate_weather_forecast(days):
    """Generate weather forecast for the trip"""
    weather = []
    for day in range(1, days + 1):
        weather.append({
            'day': f'Day {day}',
            'temperature': '28°C/22°C',
            'forecast': 'Partly cloudy with occasional sunshine'
        })
    return weather

def get_packing_list(mood, destination):
    """Get packing list based on mood and destination"""
    base_items = ['Passport/ID', 'Phone charger', 'Camera', 'Comfortable walking shoes']
    
    mood_items = {
        'relaxing': ['Yoga mat', 'Meditation app', 'Comfortable clothes', 'Spa essentials'],
        'adventurous': ['Hiking boots', 'Water bottle', 'First aid kit', 'Adventure gear'],
        'foodie': ['Food diary', 'Comfortable clothes for eating', 'Camera for food photos'],
        'romantic': ['Romantic attire', 'Camera for memories', 'Special gifts', 'Elegant clothes'],
        'family': ['Kids entertainment', 'Family games', 'Comfortable clothes', 'Snacks']
    }
    
    destination_items = {
        'Goa': ['Beachwear', 'Sunscreen', 'Beach towel', 'Swimming gear'],
        'Mumbai': ['Light clothes', 'Umbrella', 'Local transport card'],
        'Delhi': ['Modest clothing', 'Scarf for temples', 'Comfortable shoes'],
        'Puri': ['Temple-appropriate clothes', 'Beachwear', 'Spiritual items']
    }
    
    all_items = base_items + mood_items.get(mood, []) + destination_items.get(destination, [])
    return all_items

def get_travel_tips(destination):
    """Get travel tips for the destination"""
    tips_data = {
        'Mumbai': [
            'Best time to visit: November to March',
            'Use local trains for efficient travel',
            'Try street food but be careful with hygiene',
            'Book hotels in advance during peak season'
        ],
        'Delhi': [
            'Best time to visit: October to March',
            'Use metro for convenient travel',
            'Bargain at markets for better prices',
            'Respect local customs and dress modestly'
        ],
        'Goa': [
            'Best time to visit: November to March',
            'Rent a scooter for easy exploration',
            'Try local seafood and Goan cuisine',
            'Beach safety: swim only in designated areas'
        ],
        'Puri': [
            'Best time to visit: October to March',
            'Respect temple customs and dress appropriately',
            'Try local Odia cuisine and seafood',
            'Visit during Rath Yatra for unique experience'
        ]
    }
    
    return tips_data.get(destination, tips_data['Mumbai'])

# The legacy endpoints below were removed/condensed in favor of /api/* routes.




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
