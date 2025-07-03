#!/usr/bin/env python3
"""
Test script to verify all dashboard improvements are working correctly
"""

import requests
import json
from datetime import datetime

def test_usability_improvements():
    base_url = "http://localhost:5000"
    
    print("🚀 Testing RowCast Dashboard Usability Improvements")
    print("=" * 60)
    
    # Test 1: Hard cutoff at 13,000 cfs verification
    print("\n1️⃣ Testing Hard Cutoff at 13,000 CFS")
    try:
        response = requests.get(f"{base_url}/api/complete")
        if response.status_code == 200:
            data = response.json()
            current_flow = data['current']['water']['discharge']
            current_score = data['current']['rowcastScore']
            
            print(f"   Current flow: {current_flow:,} cfs")
            print(f"   Current score: {current_score}")
            
            if current_flow >= 13000 and current_score == 0:
                print("   ✅ Hard cutoff working - flow >= 13,000 cfs gives score = 0")
            elif current_flow < 13000:
                print(f"   ✅ Flow is below cutoff, score can be > 0: {current_score}")
            else:
                print("   ❌ Hard cutoff may not be working properly")
        else:
            print(f"   ❌ Failed to get current data: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing hard cutoff: {e}")

    # Test 2: Daily navigation elements
    print("\n2️⃣ Testing Daily Navigation in Dashboard")
    try:
        response = requests.get(f"{base_url}/dashboard")
        if response.status_code == 200:
            html = response.text
            
            # Check for daily navigation elements
            elements_to_check = [
                ('daily-quick-nav', 'Quick daily navigation container'),
                ('daily-quick-cards', 'Quick daily cards container'),
                ('forecast-grid', 'Forecast grid for easy day selection'),
                ('daily-navigation', 'Main daily navigation section'),
                ('daily-cards', 'Daily cards container')
            ]
            
            for element_id, description in elements_to_check:
                if element_id in html:
                    print(f"   ✅ {description} present")
                else:
                    print(f"   ❌ {description} missing")
        else:
            print(f"   ❌ Failed to load dashboard: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing daily navigation: {e}")

    # Test 3: Extended forecast for multi-day navigation
    print("\n3️⃣ Testing Extended Forecast for Multi-Day Navigation")
    try:
        response = requests.get(f"{base_url}/api/rowcast/forecast/extended")
        if response.status_code == 200:
            forecast_data = response.json()
            print(f"   ✅ Extended forecast available: {len(forecast_data)} data points")
            
            # Group by days to test daily navigation
            days = {}
            high_flow_days = 0
            
            for item in forecast_data[:48]:  # Check first 48 hours
                timestamp = item['timestamp']
                date_str = timestamp.split('T')[0]
                
                if date_str not in days:
                    days[date_str] = []
                
                days[date_str].append({
                    'score': item['score'],
                    'flow': item['conditions'].get('discharge', 0)
                })
                
                if item['conditions'].get('discharge', 0) >= 13000:
                    high_flow_days += 1
            
            print(f"   ✅ Data available for {len(days)} days")
            print(f"   ✅ High flow periods (>=13k cfs): {high_flow_days} hours")
            
            # Check if any day has varied scores
            for date, hours in days.items():
                scores = [h['score'] for h in hours]
                flows = [h['flow'] for h in hours]
                avg_flow = sum(flows) / len(flows) if flows else 0
                
                print(f"   📅 {date}: Avg flow {avg_flow:,.0f} cfs, Score range {min(scores):.1f}-{max(scores):.1f}")
                
        else:
            print(f"   ❌ Failed to get extended forecast: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing extended forecast: {e}")

    # Test 4: JavaScript functionality
    print("\n4️⃣ Testing JavaScript Dashboard Functions")
    try:
        response = requests.get(f"{base_url}/static/js/dashboard.js")
        if response.status_code == 200:
            js_content = response.text
            
            # Check for key functions
            key_functions = [
                'updateQuickDailyNavigation',
                'selectQuickDay', 
                'createQuickDailyCard',
                'toggleDailyDetails',
                'changeForecastPage',
                'updateForecastWidget'
            ]
            
            for func in key_functions:
                if func in js_content:
                    print(f"   ✅ {func} function available")
                else:
                    print(f"   ❌ {func} function missing")
                    
            # Check for high flow warning logic
            if 'quick-high-flow-warning' in js_content:
                print("   ✅ High flow warning styling available")
            else:
                print("   ❌ High flow warning styling missing")
                
        else:
            print(f"   ❌ Failed to load dashboard.js: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing JavaScript: {e}")

    # Test 5: CSS styling for usability
    print("\n5️⃣ Testing CSS Styling for Improved Usability")
    try:
        response = requests.get(f"{base_url}/static/css/dashboard.css")
        if response.status_code == 200:
            css_content = response.text
            
            # Check for key CSS classes
            key_classes = [
                '.daily-quick-nav',
                '.daily-quick-card',
                '.quick-high-flow-warning',
                '.daily-card',
                '.forecast-grid'
            ]
            
            for css_class in key_classes:
                if css_class in css_content:
                    print(f"   ✅ {css_class} styling available")
                else:
                    print(f"   ❌ {css_class} styling missing")
                    
        else:
            print(f"   ❌ Failed to load dashboard.css: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing CSS: {e}")

    print("\n" + "=" * 60)
    print("🎯 Usability Test Summary:")
    print("• Hard cutoff at 13,000 cfs for safety")
    print("• Daily navigation moved to main forecast widget")
    print("• Quick day selection without pagination")
    print("• High flow warnings for unsafe conditions")
    print("• Extended forecast for multi-day planning")
    print("\n🌐 Open dashboard at: http://localhost:5000/dashboard")
    print("📊 Click '7d' or 'Extended' to see daily navigation")

if __name__ == "__main__":
    test_usability_improvements()
