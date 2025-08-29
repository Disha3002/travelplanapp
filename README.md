# AI Travel Planner (Flask)

Modern, AI-powered Travel Planner with grounded itineraries, real POIs/hotels, maps, weather, packing lists, budgets, and shareable plans.

## Features
- Inputs: destination, start date, days, mood, interests, budget slider
- AI itinerary via OpenAI with grounding: ONLY uses provided POIs and hotels
- 3–5 attractions with images and summaries (OpenTripMap + Wikimedia)
- 3 hotel tiers with images and price ranges
- Leaflet.js map with OSM tiles for POIs and hotels
- Live weather per day (OpenWeatherMap)
- Packing list (based on mood + weather)
- Budget estimate in INR
- Local events placeholder (you can wire a free API)
- Save to SQLite, edit, delete, share link, export PDF (print stylesheet)
- Collaborative sharing via public link

## Tech
- Backend: Flask, requests, python-dotenv, Flask-Cors, sqlite3
- APIs: OpenAI, OpenTripMap, Wikimedia, OpenWeatherMap, Frankfurter
- Frontend: HTML, CSS, JavaScript, Leaflet.js

## Quickstart
1. Create a virtualenv and install deps
```
pip install -r requirements.txt
```
2. Create `.env` in project root with:
```
OPENAI_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
OPENTRIPMAP_API_KEY=your_key
FRANKFURTER_URL=https://api.frankfurter.app
FLASK_SECRET_KEY=replace_me
```
3. Run
```
set FLASK_APP=backend/app.py (Windows)
flask run
```
4. Open http://127.0.0.1:5000/

## Endpoints
- GET /api/places?city=&interests=&days=
- GET /api/hotels?city=&budget_min=&budget_max=
- POST /api/itinerary
- POST /api/save
- GET /api/plans
- GET /api/plans/<id>
- PUT /api/plans/<id>
- DELETE /api/plans/<id>
- GET /plan/<id>

## DB
SQLite file `trip_planner.db` auto-initialized. Table `trips` includes fields requested. Caching is in-memory for 6h for POIs/hotels.

## Notes
- If API keys are missing, graceful fallbacks apply (mock weather, minimal AI JSON fallback).
- PDF export uses browser print.
- Login is optional and not included by default.
# AI Travel Planner - Enhanced Smart Trip Planning

A comprehensive AI-powered travel planning application with real-time data integration, caching, and structured JSON output.

## 🌟 Enhanced Features

### 🗺️ Location Selection
- **Global Coverage**: Choose any location in the world
- **Geocoding Integration**: Automatic coordinate detection using OpenWeatherMap Geocoding API
- **Smart Parsing**: AI agent can understand and extract destinations from natural language

### 📅 Accurate Itineraries
- **Structured Daily Plans**: Morning, Afternoon, Evening, Dinner, and Accommodation for each day
- **AI-Powered Generation**: Uses OpenAI GPT-3.5-turbo for realistic, verified itineraries
- **Mood-Based Customization**: Tailored activities based on trip mood (relaxing, adventurous, foodie, romantic, family-friendly)
- **No Repetition**: Ensures diverse activities across days

### 🖼️ Attraction Images
- **High-Quality Images**: Curated Unsplash images for each attraction
- **Real Attractions**: 3-5 must-visit attractions with verified information
- **Responsive Design**: Optimized image display with fallback handling

### 🏨 Hotel Recommendations
- **Real Budget Ranges**: Actual INR pricing for economy, mid-range, and luxury options
- **Booking Links**: Direct links to booking platforms
- **Hotel Images**: High-quality hotel photos
- **Multiple Options**: Various accommodation types for different budgets

### 🌤️ Weather Forecast
- **Live Weather Data**: Real-time weather from OpenWeatherMap API
- **Daily Forecasts**: Weather predictions for each day of the trip
- **Temperature & Conditions**: Detailed weather information with descriptions

### 🗺️ Interactive Maps
- **Google Maps Integration**: Embedded map URLs showing attractions and hotels
- **Dynamic Loading**: Maps load based on destination coordinates
- **Responsive Design**: Mobile-friendly map display

### ⚡ Caching System
- **Smart Caching**: 24-hour cache based on destination, days, and mood
- **Performance Optimization**: Avoids redundant API calls for repeated requests
- **Database Storage**: SQLite-based cache with automatic cleanup

### 📊 Structured JSON Output
```json
{
  "destination": "Mumbai",
  "daily_itinerary": [
    {
      "day": 1,
      "morning": "Visit Gateway of India",
      "afternoon": "Explore Marine Drive",
      "evening": "Sunset at Juhu Beach",
      "dinner": "Fine dining at Taj Mahal Palace",
      "accommodation": "Luxury hotel in South Mumbai"
    }
  ],
  "attractions": [
    {
      "name": "Gateway of India",
      "image": "https://images.unsplash.com/...",
      "description": "Historic monument and popular tourist attraction"
    }
  ],
  "hotels": [
    {
      "name": "Taj Mahal Palace",
      "budget_in_inr": "₹25,000 - ₹50,000",
      "image": "https://images.unsplash.com/...",
      "link": "https://booking.com"
    }
  ],
  "weather": [
    {
      "day": "Day 1",
      "forecast": "Sunny",
      "temperature": "28°C"
    }
  ],
  "map_link": "https://www.google.com/maps?q=19.0760,72.8777"
}
```

## 🛠️ Tech Stack

### Backend
- **Flask**: Python web framework
- **SQLite**: Database for trip storage and caching
- **OpenAI API**: AI-powered itinerary generation
- **OpenWeatherMap API**: Real-time weather data
- **Requests**: HTTP client for API calls

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with gradients and animations
- **Vanilla JavaScript**: No frameworks, pure JS
- **Font Awesome**: Icons
- **Google Fonts**: Poppins typography
- **Leaflet.js**: Map integration (ready for future use)

### APIs & Services
- **OpenAI GPT-3.5-turbo**: AI itinerary generation
- **OpenWeatherMap**: Weather data and geocoding
- **Unsplash**: High-quality images
- **Google Maps**: Interactive maps

## 🚀 Installation & Setup

### Prerequisites
- Python 3.7+
- pip package manager

### 1. Clone the Repository
```bash
git clone <repository-url>
cd travel-planner-app
```

### 2. Set Up Virtual Environment
```bash
cd backend
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the `backend` directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

### 5. Get API Keys

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

#### OpenWeatherMap API Key
1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Navigate to API Keys section
4. Copy your API key to your `.env` file

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 Usage Guide

### Manual Planning
1. **Select Destination**: Enter any city or location worldwide
2. **Choose Duration**: Select number of days (1-30)
3. **Pick Mood**: Choose from relaxing, adventurous, foodie, romantic, or family-friendly
4. **Generate Plan**: Click "Generate Smart Plan"

### AI Agent Planning
1. **Describe Your Trip**: Write a natural language description
   - Example: "Plan a 3-day relaxing trip to Goa with beaches and spa treatments"
2. **Select Mood**: Choose your preferred trip mood
3. **Ask AI Agent**: Click "Ask AI Agent"

### Plan Features
- **Weather Forecast**: Daily weather predictions
- **Attractions**: Must-visit places with images
- **Hotels**: Accommodation recommendations with pricing
- **Interactive Map**: Google Maps integration
- **Daily Itinerary**: Structured day-by-day activities

### Plan Actions
- **Save Plan**: Store plan in database
- **Export PDF**: Generate printable PDF
- **Copy to Clipboard**: Copy plan as text
- **Share via Email**: Send plan via email
- **Share via WhatsApp**: Share on WhatsApp
- **Share Link**: Generate shareable URL

## 🔧 API Endpoints

### Generate Plans
- `POST /plan-trip` - Manual trip planning
- `POST /ask-agent` - AI agent planning

### Manage Plans
- `GET /trips` - Get all saved trips
- `GET /trip/<unique_id>` - Get specific trip
- `PUT /trip/<unique_id>` - Update trip
- `DELETE /trip/<unique_id>` - Delete trip

### Health Check
- `GET /health` - Application health status

## 🏗️ Project Structure

```
travel-planner-app/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── .env                  # Environment variables
│   ├── trip_planner.db       # SQLite database
│   ├── static/
│   │   ├── style.css         # Enhanced CSS styles
│   │   └── script.js         # Frontend JavaScript
│   └── templates/
│       └── index.html        # Main HTML template
└── README.md                 # This file
```

## 🧠 Smart Features Explained

### AI Integration
- **OpenAI GPT-3.5-turbo**: Generates realistic, verified itineraries
- **Mood-Based Customization**: Tailors activities to user preferences
- **Natural Language Processing**: Understands complex trip descriptions
- **Fallback System**: Mock data when API is unavailable

### Weather Integration
- **OpenWeatherMap API**: Real-time weather data
- **Geocoding**: Automatic location coordinate detection
- **Daily Forecasts**: Weather predictions for trip duration
- **Caching**: Reduces API calls for repeated requests

### Data Accuracy
- **Verified Attractions**: Real, existing tourist destinations
- **Actual Hotel Data**: Real hotel names and pricing
- **Live Weather**: Current and forecasted weather conditions
- **Structured Output**: Consistent JSON format for all data

### Caching System
- **24-Hour Cache**: Plans cached for 24 hours
- **Key-Based Storage**: Unique cache keys for each request
- **Automatic Cleanup**: Old cache entries automatically removed
- **Performance Boost**: Faster response times for repeated requests

## 🔒 Security & Privacy

- **Environment Variables**: API keys stored securely
- **Input Validation**: All user inputs validated
- **Error Handling**: Comprehensive error management
- **No Data Collection**: User data not stored permanently
- **HTTPS Ready**: Configured for secure connections

## 🐛 Troubleshooting

### Common Issues

#### API Key Errors
```
Error: OpenAI API key not found
```
**Solution**: Ensure your `.env` file contains the correct API keys

#### Weather Data Not Loading
```
Error: Weather API error
```
**Solution**: Check your OpenWeatherMap API key and internet connection

#### Database Errors
```
Error: Database connection failed
```
**Solution**: Ensure SQLite is properly installed and the app has write permissions

#### Port Already in Use
```
Error: Port 5000 already in use
```
**Solution**: Change the port in `app.py` or kill the process using port 5000

### Performance Optimization
- **Enable Caching**: Plans are automatically cached for 24 hours
- **API Limits**: Respect OpenAI and OpenWeatherMap rate limits
- **Database Indexing**: SQLite tables are optimized for queries

## 🚀 Future Enhancements

### Planned Features
- **Real-time Flight Data**: Integration with flight APIs
- **Local Transportation**: Public transport and taxi information
- **Restaurant Recommendations**: Dining suggestions with reviews
- **Social Sharing**: Enhanced social media integration
- **Mobile App**: Native mobile application
- **Multi-language Support**: Internationalization
- **Advanced Maps**: Interactive maps with custom markers
- **Trip Collaboration**: Multiple users editing same plan

### API Integrations
- **Google Places API**: Enhanced location data
- **Booking.com API**: Real hotel availability
- **TripAdvisor API**: Reviews and ratings
- **Currency API**: Real-time exchange rates
- **Translation API**: Multi-language support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Test all new features thoroughly
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI**: For providing the GPT-3.5-turbo API
- **OpenWeatherMap**: For weather data and geocoding services
- **Unsplash**: For high-quality images
- **Font Awesome**: For beautiful icons
- **Google Fonts**: For the Poppins typography

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Happy Smart Travel Planning! ✈️🌍🤖**
