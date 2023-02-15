from os import environ, makedirs

from flask import request

from app import app, oidc
from utils import require_role, sanity_check

@app.route('/publish-api-doc/<name>', methods=['POST'])
@require_role(oidc, environ['REQUIRED_OPENID_ROLE'])
def publish_api_doc(name):
    sanity_check(name)
    directory = f'/services/api-docs/{name}'
    makedirs(directory, exist_ok=True)
    # file = request.files['file'].save(f'{directory}/index.html')
    for filename, handle in request.files.items():
        request.files[filename].save(f'{directory}/{filename}')
    return 'Success', 200
