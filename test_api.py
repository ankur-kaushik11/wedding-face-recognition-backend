"""Basic API testing script for Wedding Face Recognition Backend."""
import requests
import json
from io import BytesIO
from PIL import Image

# Configuration
BASE_URL = "http://localhost:8000"
EVENT_PASSWORD = "WeddingPassword123"  # Change to match your .env

# Test results
test_results = []


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    test_results.append({"name": name, "passed": passed, "message": message})
    print(f"{status}: {name}")
    if message:
        print(f"  {message}")


def test_health_check():
    """Test health check endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        log_test("Health Check", response.status_code == 200, f"Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        log_test("Health Check", False, str(e))
        return False


def test_login_admin():
    """Test admin login."""
    try:
        payload = {
            "password": EVENT_PASSWORD,
            "role": "admin"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            role = data.get("role")
            log_test("Admin Login", token is not None and role == "admin", 
                    f"Token received, role: {role}")
            return token
        else:
            log_test("Admin Login", False, f"Status: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        log_test("Admin Login", False, str(e))
        return None


def test_login_user():
    """Test user login."""
    try:
        payload = {
            "password": EVENT_PASSWORD,
            "role": "user"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            role = data.get("role")
            log_test("User Login", token is not None and role == "user", 
                    f"Token received, role: {role}")
            return token
        else:
            log_test("User Login", False, f"Status: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        log_test("User Login", False, str(e))
        return None


def test_login_invalid_password():
    """Test login with invalid password."""
    try:
        payload = {
            "password": "WrongPassword",
            "role": "admin"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        log_test("Invalid Password Rejection", response.status_code == 401, 
                f"Status: {response.status_code}")
    except Exception as e:
        log_test("Invalid Password Rejection", False, str(e))


def test_admin_stats(admin_token):
    """Test admin stats endpoint."""
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            has_required_fields = all(key in data for key in 
                ["total_photos", "total_users", "total_scans", "photos_by_day"])
            log_test("Admin Stats", has_required_fields, 
                    f"Total users: {data.get('total_users')}, Total photos: {data.get('total_photos')}")
        else:
            log_test("Admin Stats", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("Admin Stats", False, str(e))


def test_admin_activity(admin_token):
    """Test admin activity logs endpoint."""
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/admin/activity?limit=10", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            log_test("Admin Activity Logs", isinstance(data, list), 
                    f"Retrieved {len(data)} activity logs")
        else:
            log_test("Admin Activity Logs", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("Admin Activity Logs", False, str(e))


def test_admin_photos_summary(admin_token):
    """Test admin photos summary endpoint."""
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/admin/photos-summary", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            has_required_fields = "photos_by_day" in data and "total_photos" in data
            log_test("Admin Photos Summary", has_required_fields, 
                    f"Total photos: {data.get('total_photos')}")
        else:
            log_test("Admin Photos Summary", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("Admin Photos Summary", False, str(e))


def test_user_photos(user_token):
    """Test user photos endpoint."""
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/user/photos", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            log_test("User Photos", isinstance(data, list), 
                    f"Retrieved {len(data)} photos")
        else:
            log_test("User Photos", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("User Photos", False, str(e))


def test_user_scan_face(user_token):
    """Test user face scan endpoint with a dummy image."""
    try:
        # Create a dummy image
        img = Image.new('RGB', (300, 300), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        headers = {"Authorization": f"Bearer {user_token}"}
        files = {"file": ("test.jpg", img_bytes, "image/jpeg")}
        response = requests.post(f"{BASE_URL}/user/scan-face", headers=headers, files=files)
        
        # Note: This will likely find no matches since it's a blank image
        # But we're testing the endpoint works
        if response.status_code == 200:
            data = response.json()
            has_required_fields = all(key in data for key in 
                ["matched_photos", "total_matches", "grouped_by_day"])
            log_test("User Face Scan", has_required_fields, 
                    f"Matches: {data.get('total_matches')}")
        else:
            log_test("User Face Scan", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("User Face Scan", False, str(e))


def test_unauthorized_access():
    """Test accessing protected endpoint without token."""
    try:
        response = requests.get(f"{BASE_URL}/admin/stats")
        log_test("Unauthorized Access Blocked", response.status_code == 401, 
                f"Status: {response.status_code}")
    except Exception as e:
        log_test("Unauthorized Access Blocked", False, str(e))


def test_user_accessing_admin_endpoint(user_token):
    """Test user trying to access admin endpoint."""
    try:
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
        log_test("User Admin Access Blocked", response.status_code == 403, 
                f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Admin Access Blocked", False, str(e))


def main():
    """Run all tests."""
    print("=" * 60)
    print("Wedding Face Recognition Backend - API Tests")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Password: {EVENT_PASSWORD}")
    print("=" * 60)
    print()
    
    # Test 1: Health Check
    if not test_health_check():
        print("\n⚠ Server is not responding. Make sure the server is running.")
        return
    
    print()
    
    # Test 2-4: Authentication
    print("Testing Authentication...")
    admin_token = test_login_admin()
    user_token = test_login_user()
    test_login_invalid_password()
    print()
    
    # Test 5-7: Admin Endpoints
    if admin_token:
        print("Testing Admin Endpoints...")
        test_admin_stats(admin_token)
        test_admin_activity(admin_token)
        test_admin_photos_summary(admin_token)
        print()
    
    # Test 8-9: User Endpoints
    if user_token:
        print("Testing User Endpoints...")
        test_user_photos(user_token)
        test_user_scan_face(user_token)
        print()
    
    # Test 10-11: Security
    print("Testing Security...")
    test_unauthorized_access()
    if user_token:
        test_user_accessing_admin_endpoint(user_token)
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. Check the output above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
