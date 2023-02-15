from datetime import datetime
from os import environ
import threading
from subprocess import run, check_output

from flask import request

from app import app, oidc
from utils import require_gh_secret, sanity_check

# TODO: Zero-downtime version
# TODO: Return docker-compose errors in HTTP
@app.route('/docker-compose-rebuild', methods=['POST'])
@require_gh_secret(environ['GH_SECRET'])
def docker_compose_rebuild():
    data = request.json
    ref = data['ref']
    if ref != 'refs/heads/main':
        return 'Not main branch', 202
    directory = request.args['directory']
    sanity_check(directory)

    def async_task():
        with open('/var/log/dc-rebuild.logs', 'a+') as f:
            f.write(f"[{datetime.now()}] Started DC rebuild @ '{directory}'...\n")
            f.flush()
            try:
                run(['git', 'pull', 'origin', 'main'], cwd=directory, check=True)
                run(['docker-compose', 'build'], cwd=directory, check=True)
                run(['docker-compose', 'down'], cwd=directory, check=True)
                run(['docker-compose', 'up', '-d'], cwd=directory, check=True)
                commit = check_output(['git', 'log', '--format="%C(auto) %h: %s"', '-n1'], cwd=directory).decode('utf-8').replace('\n', '')
                f.write(f"[{datetime.now()}] Finished DC rebuild. '{commit}' is up!\n\n")
            except Exception as e:
                f.write(f'[{datetime.now()}] Rebuild failed. Login and check on "journalctl -u bare-metal-utils.service -n150 -f" for recent logs.\n\n')
                raise e
    
    thread = threading.Thread(target=async_task)
    thread.start()
    return 'Success', 200
