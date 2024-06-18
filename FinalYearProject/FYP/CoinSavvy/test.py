audio_url = 12
account_sid = 3
auth_token = 4

from requests.auth import HTTPBasicAuth
import requests

audio_response = requests.get(audio_url, auth=HTTPBasicAuth(account_sid, auth_token))
if audio_response.status_code == 200:
    audio_content = audio_response.content
else:
    print("Failed to download audio file. Status code:", audio_response.status_code)
