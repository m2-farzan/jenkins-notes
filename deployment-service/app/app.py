from flask import Flask
from flask_oidc import OpenIDConnect

app = Flask(__name__)
app.config['OIDC_CLIENT_SECRETS'] = "client_secrets.json"
app.config['OIDC_RESOURCE_SERVER_ONLY'] = True
oidc = OpenIDConnect(app)
