from os import environ
from subprocess import run

from flask import request

from app import app, oidc
from utils import require_role, sanity_check

# TODO: Zero-downtime version
# TODO: Return docker-compose errors in HTTP
@app.route('/docker-compose-deliver', methods=['POST'])
@require_role(oidc, environ['REQUIRED_OPENID_ROLE'])
def docker_compose_deliver():
    data = request.json
    service = data['service']
    directory = data['directory']
    sanity_check(service)
    sanity_check(directory)

    run(['docker-compose', 'pull', service], cwd=directory, check=True)
    run(['docker-compose', 'stop', service], cwd=directory, check=True)
    run(['docker-compose', 'rm', '-f', service], cwd=directory, check=True)
    run(['docker-compose', 'up', '-d', service], cwd=directory, check=True)

    return 'Success', 200
