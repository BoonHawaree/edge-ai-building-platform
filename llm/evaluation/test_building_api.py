#!/usr/bin/env python3
"""
Test script to check if your building data API is responding
"""

import httpx
import json

def test_building_api():
    """Test all the endpoints your tools use"""
    
    print("🔧 Testing Building Data API at localhost:8000")
    print("=" * 50)
    
    # Test endpoints that your tools call
    endpoints_to_test = [
        ("IAQ Sensor 8", "http://localhost:8000/api/current/iaq/8"),
        ("Power Meter 2", "http://localhost:8000/api/current/power/2"), 
        ("Recent Alerts", "http://localhost:8000/api/alerts/recent"),
        ("Historical Energy", "http://localhost:8000/api/historical/energy_consumption?hours_ago=1")
    ]
    
    all_working = True
    
    for name, url in endpoints_to_test:
        try:
            print(f"Testing {name}: {url}")
            response = httpx.get(url, timeout=5.0)  # 5 second timeout
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ SUCCESS - Status: {response.status_code}")
                print(f"  📊 Sample data: {str(data)[:100]}...")
            else:
                print(f"  ❌ FAILED - Status: {response.status_code}")
                print(f"  📄 Response: {response.text[:100]}...")
                all_working = False
                
        except httpx.TimeoutException:
            print(f"  ⏰ TIMEOUT - API took longer than 5 seconds")
            all_working = False
            
        except httpx.ConnectError:
            print(f"  🔌 CONNECTION ERROR - Cannot reach {url}")
            all_working = False
            
        except Exception as e:
            print(f"  💥 UNEXPECTED ERROR: {str(e)}")
            all_working = False
            
        print()
    
    print("=" * 50)
    if all_working:
        print("🎉 All API endpoints working! Your building data API is ready.")
    else:
        print("⚠️  Some API endpoints failed. This might cause LangGraph to hang.")
        print("💡 Make sure your building data server is running on localhost:8000")
    
    return all_working

if __name__ == "__main__":
    test_building_api()