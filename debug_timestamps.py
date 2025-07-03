#!/usr/bin/env python3
"""
Debug timestamp matching between NOAA and weather data
"""

from datetime import datetime

def debug_timestamps():
    """Debug timestamp matching issues"""
    print("=" * 60)
    print(" TIMESTAMP DEBUGGING")
    print("=" * 60)
    
    try:
        from app.fetchers import fetch_noaa_stageflow_forecast, fetch_extended_weather_forecast
        
        # Get both datasets
        noaa_data = fetch_noaa_stageflow_forecast()
        weather_data = fetch_extended_weather_forecast()
        
        print(f"\nNOAA forecast points: {len(noaa_data.get('forecast', []))}")
        print(f"Weather forecast points: {len(weather_data.get('forecast', []))}")
        
        # Show sample timestamps
        print("\nSample NOAA timestamps (first 10):")
        for i, point in enumerate(noaa_data.get('forecast', [])[:10]):
            print(f"  {i+1}: {point.get('timestamp')}")
        
        print("\nSample Weather timestamps (first 10):")
        for i, point in enumerate(weather_data.get('forecast', [])[:10]):
            print(f"  {i+1}: {point.get('timestamp')}")
        
        # Create lookup and test matching
        noaa_lookup = {}
        noaa_timestamps = set()
        
        for point in noaa_data.get('forecast', []):
            timestamp = point.get('timestamp')
            if timestamp:
                noaa_lookup[timestamp] = point
                noaa_timestamps.add(timestamp)
        
        weather_timestamps = set()
        matches = 0
        
        for point in weather_data.get('forecast', [])[:50]:  # First 50 weather points
            timestamp = point.get('timestamp')
            if timestamp:
                weather_timestamps.add(timestamp)
                if timestamp in noaa_lookup:
                    matches += 1
        
        print(f"\nTimestamp Analysis:")
        print(f"  Unique NOAA timestamps: {len(noaa_timestamps)}")
        print(f"  Unique Weather timestamps (first 50): {len(weather_timestamps)}")
        print(f"  Exact matches: {matches}")
        
        # Check timestamp formats and time zones
        if noaa_data.get('forecast') and weather_data.get('forecast'):
            noaa_ts = noaa_data['forecast'][0]['timestamp']
            weather_ts = weather_data['forecast'][0]['timestamp']
            
            print(f"\nTimestamp Format Analysis:")
            print(f"  NOAA format: {noaa_ts}")
            print(f"  Weather format: {weather_ts}")
            
            # Parse and compare
            try:
                noaa_dt = datetime.fromisoformat(noaa_ts.replace('Z', '+00:00'))
                weather_dt = datetime.fromisoformat(weather_ts.replace('Z', '+00:00'))
                
                print(f"  NOAA parsed: {noaa_dt}")
                print(f"  Weather parsed: {weather_dt}")
                print(f"  Time difference: {abs((noaa_dt - weather_dt).total_seconds())} seconds")
                
            except Exception as e:
                print(f"  Parsing error: {e}")
        
        # Find closest matches
        print(f"\nLooking for closest timestamp matches...")
        closest_matches = []
        
        for weather_point in weather_data.get('forecast', [])[:10]:
            weather_ts = weather_point.get('timestamp')
            if not weather_ts:
                continue
                
            weather_dt = datetime.fromisoformat(weather_ts.replace('Z', '+00:00'))
            
            closest_noaa = None
            min_diff = float('inf')
            
            for noaa_point in noaa_data.get('forecast', []):
                noaa_ts = noaa_point.get('timestamp')
                if not noaa_ts:
                    continue
                    
                noaa_dt = datetime.fromisoformat(noaa_ts.replace('Z', '+00:00'))
                diff = abs((weather_dt - noaa_dt).total_seconds())
                
                if diff < min_diff:
                    min_diff = diff
                    closest_noaa = noaa_ts
            
            closest_matches.append((weather_ts, closest_noaa, min_diff))
        
        print("\nClosest matches (Weather -> NOAA, time diff in seconds):")
        for weather_ts, noaa_ts, diff in closest_matches[:5]:
            print(f"  {weather_ts} -> {noaa_ts} (diff: {diff}s)")
        
        # Suggest fixes
        print(f"\nSuggested fixes:")
        avg_diff = sum(match[2] for match in closest_matches) / len(closest_matches) if closest_matches else 0
        
        if avg_diff == 0:
            print("  ✓ Timestamps match exactly - check lookup logic")
        elif avg_diff < 1800:  # Less than 30 minutes
            print("  → Use closest timestamp matching instead of exact matching")
            print("  → Implement tolerance-based matching (±30 minutes)")
        else:
            print("  → Timestamps are significantly different")
            print("  → Check if time zones are consistent")
            print("  → Verify data source alignment")
        
    except Exception as e:
        print(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_timestamps()
