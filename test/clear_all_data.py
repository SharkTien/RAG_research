import requests

BASE_URL = "http://localhost:18765"
s = requests.Session()

# Login as admin
r = s.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "matkhausieudai123"})
if r.status_code == 200:
    csrf = r.json().get("csrf_token")
    s.headers.update({"x-csrf-token": csrf})
    print("Logged in as admin.")

    # Call bulk delete all
    del_res = s.delete(f"{BASE_URL}/api/documents/bulk/all?filter=all")
    print("Delete all status:", del_res.status_code, del_res.text)

    # Check remaining documents
    docs = s.get(f"{BASE_URL}/api/documents").json()
    print("Remaining documents count:", len(docs.get("items", [])))
else:
    print("Login failed:", r.status_code, r.text)
