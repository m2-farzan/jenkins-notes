from flask import request, Response
import requests

from app import app


@app.route('/get-token', methods=['POST'])
def get_token():
    data = request.json
    username = data['username']
    password = data['password']

    response = requests.post(
        'https://dev-login.cakerobotics.com/auth/realms/devs/protocol/openid-connect/token',
        {
            'client_id': 'deployment-utils',
            'client_secret': 'e5a0cbce-xxxx-xxxx-xxxx-7a6009c0b623',
            'username': username,
            'password': password,
            'grant_type': 'password',
        }
    )

    if response.status_code != 200:
        return Response(response.content, status=response.status_code)

    return response.json()['access_token']
