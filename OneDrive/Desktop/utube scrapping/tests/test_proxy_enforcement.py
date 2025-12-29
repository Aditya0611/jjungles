"""
Test script for proxy enforcement in strict mode.
This script verifies that the scraper correctly enforces proxy usage.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.proxy import init_rotator, get_proxy, has_proxies, ProxyRotator
from src.logger import logger

# Non-strict mode tests removed per client requirement for guaranteed proxy enforcement.
def test_strict_mode_with_no_proxies():
    """Test that strict mode raises error when no proxies are provided."""
    print("\n" + "="*60)
    print("TEST 1: Strict Mode with NO Proxies (Should FAIL)")
    print("="*60)
    
    try:
        init_rotator("", strict_mode=True)
        print("❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✅ PASSED: Correctly raised ValueError")
        print(f"   Error message: {e}")
        return True

def test_strict_mode_with_proxies():
    """Test that strict mode works correctly with valid proxies."""
    print("\n" + "="*60)
    print("TEST 2: Strict Mode with Valid Proxies (Should SUCCEED)")
    print("="*60)
    
    try:
        test_proxies = "http://proxy1:8080,http://proxy2:8080,http://proxy3:8080"
        init_rotator(test_proxies, strict_mode=True)
        
        if not has_proxies():
            print("❌ FAILED: has_proxies() returned False")
            return False
        
        # Test rotation
        proxy1 = get_proxy()
        proxy2 = get_proxy()
        proxy3 = get_proxy()
        proxy4 = get_proxy()  # Should cycle back to first
        
        print(f"✅ PASSED: Proxy rotation working")
        print(f"   Proxy 1: {proxy1}")
        print(f"   Proxy 2: {proxy2}")
        print(f"   Proxy 3: {proxy3}")
        print(f"   Proxy 4 (cycled): {proxy4}")
        
        if proxy1 == proxy4:
            print("✅ PASSED: Proxy rotation cycles correctly")
            return True
        else:
            print("❌ FAILED: Proxy rotation did not cycle")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False

# Non-strict mode test removed to emphasize strict proxy enforcement requirement
# def test_non_strict_mode_with_no_proxies():
#     ...

def test_proxy_list_validation():
    """Test that proxy list is properly validated and cleaned."""
    print("\n" + "="*60)
    print("TEST 4: Proxy List Validation (Whitespace Handling)")
    print("="*60)
    
    try:
        # Test with whitespace and empty entries
        test_proxies = "http://proxy1:8080,  , http://proxy2:8080 ,  ,http://proxy3:8080  "
        rotator = ProxyRotator(test_proxies.split(","), strict_mode=False)
        
        proxies = rotator.get_all()
        expected_count = 3
        
        if len(proxies) == expected_count:
            print(f"✅ PASSED: Correctly cleaned proxy list")
            print(f"   Expected: {expected_count} proxies")
            print(f"   Got: {len(proxies)} proxies")
            print(f"   Proxies: {proxies}")
            return True
        else:
            print(f"❌ FAILED: Expected {expected_count} proxies, got {len(proxies)}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False

def main():
    """Run all proxy enforcement tests."""
    print("\n" + "="*60)
    print("PROXY ENFORCEMENT TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Strict Mode - No Proxies", test_strict_mode_with_no_proxies()))
    results.append(("Strict Mode - With Proxies", test_strict_mode_with_proxies()))
    # results.append(("Non-Strict Mode - No Proxies", test_non_strict_mode_with_no_proxies()))
    results.append(("Proxy List Validation", test_proxy_list_validation()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
