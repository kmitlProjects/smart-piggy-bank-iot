#!/usr/bin/env python3
"""
Phase 1 Test: MQTT -> SQLite -> API
"""
import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:5001"

def test_status():
    """Test GET /api/status"""
    print("\n=== GET /api/status ===")
    response = urllib.request.urlopen(f"{BASE_URL}/api/status")
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
    return data

def test_coins_summary():
    """Test GET /api/coins/summary"""
    print("\n=== GET /api/coins/summary ===")
    response = urllib.request.urlopen(f"{BASE_URL}/api/coins/summary")
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
    return data

def test_coins_history():
    """Test GET /api/coins/history?limit=3"""
    print("\n=== GET /api/coins/history (latest 3) ===")
    response = urllib.request.urlopen(f"{BASE_URL}/api/coins/history?limit=3")
    data = json.loads(response.read())
    print(f"Total events: {len(data['history'])}")
    if data['history']:
        print("Latest event:")
        print(json.dumps(data['history'][0], indent=2))
    return data

def test_access_check(uid, wifi_connected):
    """Test POST /api/access/check"""
    print(f"\n=== POST /api/access/check (uid={uid}, wifi={wifi_connected}) ===")
    payload = json.dumps({"uid": uid, "wifi_connected": wifi_connected}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/access/check",
                                data=payload,
                                headers={"Content-Type": "application/json"},
                                method="POST")
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
    return data

def test_access_history():
    """Test GET /api/access/history"""
    print("\n=== GET /api/access/history ===")
    response = urllib.request.urlopen(f"{BASE_URL}/api/access/history?limit=10")
    data = json.loads(response.read())
    print(f"Total access logs: {len(data['history'])}")
    if data['history']:
        print("Latest access log:")
        print(json.dumps(data['history'][0], indent=2))
    else:
        print("(No access logs yet)")
    return data

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 TEST: MQTT -> SQLite -> API")
    print("=" * 60)
    
    # Test 1: Check basic status
    test_status()
    
    # Test 2: Check coins summary (proves MQTT data in SQLite)
    test_coins_summary()
    
    # Test 3: Check recent coin events
    test_coins_history()
    
    # Test 4: Authorization checks
    print("\n" + "=" * 60)
    print("AUTHORIZATION TESTS")
    print("=" * 60)
    
    test_access_check("AA-BB-CC", True)   # WiFi ON + correct UID = ALLOW
    test_access_check("AA-BB-CC", False)  # WiFi OFF + correct UID = DENY
    test_access_check("XX-YY-ZZ", True)   # WiFi ON + wrong UID = DENY
    
    # Test 5: Check access history
    test_access_history()
    
    print("\n" + "=" * 60)
    print("✅ PHASE 1 TEST COMPLETE")
    print("=" * 60)
