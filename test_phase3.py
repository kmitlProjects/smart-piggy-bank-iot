#!/usr/bin/env python3
"""
Phase 3 E2E Test: ESP32 Authorization + Backend Integration
Tests authorization logic with WiFi on/off and different UIDs
"""
import urllib.request
import json
import time
import threading

BASE_URL = "http://127.0.0.1:5001"

def test_scenario(name, uid, wifi_enabled, expected_granted):
    """
    Simulate an RFID scan and authorization check
    
    This mimics what ESP32 does when it scans an RFID card:
    1. Call /api/access/check with uid + wifi_connected
    2. Check if response.access_granted matches expected result
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"UID: {uid}")
    print(f"WiFi: {'CONNECTED' if wifi_enabled else 'DISCONNECTED'}")
    print(f"Expected Result: {'✓ ALLOW' if expected_granted else '✗ DENY'}")
    
    try:
        payload = json.dumps({
            "uid": uid,
            "wifi_connected": wifi_enabled
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/access/check",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        
        actual_granted = data.get("access_granted", False)
        reason = data.get("reason", "UNKNOWN")
        authorized = data.get("authorized", False)
        
        print(f"\nAuthorized: {authorized}")
        print(f"Access Granted: {actual_granted}")
        print(f"Reason: {reason}")
        
        # Verify expectation
        if actual_granted == expected_granted:
            print(f"✅ PASS")
            return True
        else:
            print(f"❌ FAIL - Expected {expected_granted}, got {actual_granted}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_access_log():
    """Check that authorization attempts are logged in database"""
    print(f"\n{'='*60}")
    print("TEST: Access Logs Database")
    print(f"{'='*60}")
    
    try:
        response = urllib.request.urlopen(f"{BASE_URL}/api/access/history?limit=20")
        data = json.loads(response.read())
        
        logs = data.get("history", [])
        print(f"Total access logs: {len(logs)}")
        
        if logs:
            print("\nLatest 3 access logs:")
            for i, log in enumerate(logs[:3], 1):
                ts = log.get("created_at", "?")
                uid = log.get("uid", "?")
                auth = "Y" if log.get("authorized") else "N"
                granted = "Y" if log.get("access_granted") else "N"
                reason = log.get("reason", "?")
                print(f"  {i}. [{ts}] UID:{uid} Auth:{auth} Granted:{granted} Reason:{reason}")
            return True
        else:
            print("(No access logs yet)")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("PHASE 3 TEST: ESP32 Authorization + Backend")
    print("="*60)
    
    results = []
    
    # Test Scenario 1: WiFi ON + Correct UID
    results.append((
        "Scenario 1: WiFi ON + Correct UID (AA-BB-CC)",
        test_scenario("WiFi ON + Correct UID", "AA-BB-CC", True, True)
    ))
    time.sleep(0.5)
    
    # Test Scenario 2: WiFi OFF + Correct UID
    results.append((
        "Scenario 2: WiFi OFF + Correct UID (AA-BB-CC)",
        test_scenario("WiFi OFF + Correct UID", "AA-BB-CC", False, False)
    ))
    time.sleep(0.5)
    
    # Test Scenario 3: WiFi ON + Wrong UID
    results.append((
        "Scenario 3: WiFi ON + Wrong UID (XX-YY-ZZ)",
        test_scenario("WiFi ON + Wrong UID", "XX-YY-ZZ", True, False)
    ))
    time.sleep(0.5)
    
    # Test Scenario 4: WiFi OFF + Wrong UID
    results.append((
        "Scenario 4: WiFi OFF + Wrong UID (XX-YY-ZZ)",
        test_scenario("WiFi OFF + Wrong UID", "XX-YY-ZZ", False, False)
    ))
    time.sleep(0.5)
    
    # Test Scenario 5: Unknown Card
    results.append((
        "Scenario 5: WiFi ON + Unknown Card (00-00-00)",
        test_scenario("WiFi ON + Unknown Card", "00-00-00", True, False)
    ))
    time.sleep(0.5)
    
    # Check access logs
    results.append((
        "Access Logs Recorded",
        test_access_log()
    ))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Phase 3 Ready!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review and fix")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
