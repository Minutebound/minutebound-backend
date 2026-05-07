# ⚙️ WanderPlan US - Backend API

This is the backend service for WanderPlan US. Built with FastAPI, it serves as the core data processing engine, communicating with external travel APIs, managing geocoding, and returning optimized trip data to the frontend.

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Database**: PostgreSQL / PostGIS (via `app/db`)
- **Containerization**: Docker

## 🔑 Environment Variables (`.env`)

Create a `.env.backend` file in the `backend/` directory. Based on `app/core/config.py`, you will need to configure your API keys for external services.

env

# Server Configuration

HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development # or production

# Third-Party Travel APIs (Update with your actual keys)

AMADEUS_CLIENT_ID=your_amadeus_api_key_here
AMADEUS_CLIENT_SECRET=your_amadeus_secret_here

OPENWEATHER_API_KEY=your_openweather_api_key_here

# Replace with your specific Mapping/Geocoding API (e.g., TomTom, Mapbox, or Google)

MAP_API_KEY=your_mapping_api_key_here

# Tours & Attractions API (e.g., Viator, TripAdvisor, etc.)

TOUR_API_KEY=your_tour_api_key_here

# Database Configuration (if applicable)

DATABASE_URL=sqlite:///./sql_app.db # or your PostgreSQL connection string

## 📂 Directory Structure

- `app/api/v1/endpoints/`: Route handlers for specific domains (flights, driving, hotels, weather, locations, attractions, activities).
- `app/core/`: Security and configuration settings.
- `app/db/`: Database configuration and ORM models.
- `app/schemas/`: Pydantic models for request/response validation.
- `app/services/`: Business logic and external API clients.

## 🚀 Local Development

### 1. Install Dependencies

Create a virtual environment and install the required packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running with Docker 🐳

If you prefer to run the application using Docker, ensure you have Docker and Docker Compose installed.

To build the images and start the containers in the background (detached mode):

```bash
docker-compose up --build -d
```

To stop the containers and completely remove the associated volumes (useful for wiping the database clean):

```bash
docker-compose down -v
```

### Top 5 destinations check in redis:

http://localhost:8000/api/v1/locations/top
