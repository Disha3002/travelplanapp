-- SQLite schema for AI Travel Planner

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
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
);

CREATE TABLE IF NOT EXISTS plan_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    destination TEXT NOT NULL,
    days INTEGER NOT NULL,
    mood TEXT NOT NULL,
    plan_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

