import requests

url = 'http://localhost:5000/api/login'
data = {'username': 'admin', 'password': 'admin122'}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
