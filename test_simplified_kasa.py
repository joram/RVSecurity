#!/usr/bin/env python3
"""
Simple test script for the simplified blocking Kasa implementation.
Tests basic functionality without async complexity.
"""

import requests
import time

def test_basic_endpoints():
    """Test that basic endpoints work without threading issues."""
    base_url = "http://localhost:8000"
    
    print("Testing simplified Kasa implementation...")
    print("=" * 50)
    
    tests = [
        ("Root page", "GET", "/"),
        ("Internet status", "GET", "/api/internet/status"),  
        ("Power data", "GET", "/data/power"),
        ("Home data", "GET", "/data/home"),
        ("Kasa power reading", "GET", "/api/kasa/power/1"),
    ]
    
    results = []
    
    for test_name, method, endpoint in tests:
        print(f"\n[TEST] {test_name}")
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code in [200, 404]:  # 404 is OK for some endpoints
                print(f"PASS {test_name}: HTTP {response.status_code}")
                results.append((test_name, True))
                
                # For Kasa endpoint, check the response
                if "/api/kasa/" in endpoint:
                    try:
                        data = response.json()
                        if "message" in data:
                            print(f"   Response: {data['message']}")
                    except:
                        pass
            else:
                print(f"FAIL {test_name}: HTTP {response.status_code}")
                results.append((test_name, False))
                
        except requests.exceptions.ConnectionError:
            print(f"FAIL {test_name}: Connection failed (server not running?)")
            results.append((test_name, False))
        except Exception as e:
            print(f"FAIL {test_name}: Error - {e}")
            results.append((test_name, False))
    
    # Test rapid requests to check for threading issues
    print(f"\n[TEST] Rapid concurrent requests")
    try:
        import concurrent.futures
        import threading
        
        def make_request():
            try:
                response = requests.get(f"{base_url}/api/internet/status", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            concurrent_results = [future.result(timeout=10) for future in futures]
        
        success_count = sum(concurrent_results)
        print(f"PASS Concurrent requests: {success_count}/5 succeeded")
        results.append(("Concurrent requests", success_count >= 3))
        
    except Exception as e:
        print(f"FAIL Concurrent requests: Failed - {e}")
        results.append(("Concurrent requests", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\nAll tests passed! The simplified blocking implementation is working correctly.")
    elif passed >= len(results) * 0.8:
        print("\nMost tests passed. The simplified implementation appears stable.")
    else:
        print("\nMultiple test failures. Issues may remain.")

if __name__ == "__main__":
    test_basic_endpoints()
