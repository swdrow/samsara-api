# RowCast API Documentation

## Overview
The RowCast API provides current weather conditions, 24-hour forecasts, water data predictions, and rowing condition scores.

## Base URL
```
http://localhost:5000
```

## Endpoints

### Weather Data

#### `GET /api/weather`
Returns complete weather data including current conditions and 24-hour forecast.

**Response:**
```json
{
  "current": {
    "windSpeed": 8.5,
    "windGust": 12.3,
    "windDir": "NW (315°)",
    "apparentTemp": 75.2,
    "uvIndex": 6,
    "precipitation": 0.0,
    "currentTemp": 73.4,
    "timestamp": "2025-07-01T14:00"
  },
  "forecast": [
    {
      "timestamp": "2025-07-01T15:00",
      "windSpeed": 9.1,
      "windGust": 13.2,
      "windDir": "NW (320°)",
      "apparentTemp": 76.1,
      "uvIndex": 5,
      "precipitation": 0.0,
      "currentTemp": 74.2
    }
    // ... 23 more hourly forecasts
  ]
}
```

#### `GET /api/weather/current`
Returns only current weather conditions.

#### `GET /api/weather/forecast`
Returns only the 24-hour weather forecast.

### Water Data

#### `GET /api/water`
Returns complete water data including current conditions, historical data, and predictions.

**Response:**
```json
{
  "current": {
    "gaugeHeight": 2.34,
    "waterTemp": 68.5,
    "discharge": 850
  },
  "historical": {
    "gaugeHeight": [
      {"timestamp": "2025-06-30T14:00", "value": 2.31},
      // ... more historical data
    ],
    "waterTemp": [...],
    "discharge": [...]
  },
  "predictions": [
    {
      "timestamp": "2025-07-01T15:00",
      "discharge": 845,
      "gaugeHeight": 2.33,
      "waterTemp": 68.7
    }
    // ... 23 more hourly predictions
  ]
}
```

#### `GET /api/water/current`
Returns only current water conditions.

#### `GET /api/water/predictions`
Returns only water predictions for the next 24 hours.

### RowCast Scores

#### `GET /api/rowcast`
Returns current rowing conditions score.

**Response:**
```json
{
  "rowcastScore": 8.45,
  "params": {
    "windSpeed": 8.5,
    "windGust": 12.3,
    "apparentTemp": 75.2,
    "uvIndex": 6,
    "precipitation": 0.0,
    "discharge": 850,
    "waterTemp": 68.5,
    "gaugeHeight": 2.34
  }
}
```

#### `GET /api/rowcast/forecast`
Returns RowCast scores for the next 24 hours.

**Response:**
```json
[
  {
    "timestamp": "2025-07-01T15:00",
    "score": 8.2,
    "conditions": {
      "windSpeed": 9.1,
      "windGust": 13.2,
      "apparentTemp": 76.1,
      // ... other parameters
    }
  }
  // ... 23 more hourly forecasts
]
```

#### `GET /api/rowcast/forecast/<time_offset>`
Returns RowCast score for a specific time offset from now.

**Parameters:**
- `time_offset`: Time offset (e.g., "2h", "30m", "1d")

**Examples:**
- `/api/rowcast/forecast/2h` - Score in 2 hours
- `/api/rowcast/forecast/30m` - Score in 30 minutes
- `/api/rowcast/forecast/1d` - Score in 1 day

#### `GET /api/rowcast/at/<timestamp>`
Returns RowCast score for a specific timestamp.

**Parameters:**
- `timestamp`: ISO 8601 timestamp

**Example:**
- `/api/rowcast/at/2025-07-01T16:00:00`

### Complete Data

#### `GET /api/complete`
Returns all current data, forecasts, and scores in one comprehensive response.

**Response:**
```json
{
  "current": {
    "weather": { /* current weather data */ },
    "water": { /* current water data */ },
    "rowcastScore": 8.45
  },
  "forecast": {
    "weather": [ /* 24-hour weather forecast */ ],
    "water": [ /* 24-hour water predictions */ ],
    "rowcastScores": [ /* 24-hour score forecasts */ ]
  },
  "lastUpdated": "2025-07-01T14:30:00"
}
```

## Data Update Intervals

- **Weather Data**: Updated every 10 minutes
- **Water Data**: Updated every 15 minutes  
- **Forecast Scores**: Updated every 10 minutes

## Error Responses

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful request
- `404 Not Found`: Data not available yet
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

Error responses include a JSON object with an error message:
```json
{
  "error": "Description of the error"
}
```

## Usage Examples

### Get Current Conditions
```bash
curl http://localhost:5000/api/complete
```

### Check Score in 2 Hours
```bash
curl http://localhost:5000/api/rowcast/forecast/2h
```

### Get Full Weather Forecast
```bash
curl http://localhost:5000/api/weather/forecast
```

## Notes

- All timestamps are in ISO 8601 format
- Temperature values are in Fahrenheit
- Wind speeds are in mph
- Water discharge is in cubic feet per second (cfs)
- Gauge height is in feet
- RowCast scores range from 0-10 (higher is better)
- UV Index ranges from 0-11+
- Precipitation is in inches
