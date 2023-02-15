from flask import abort
import re

def sanity_check(text):
    if not re.match(r'^[a-zA-Z0-9_\-\/\.]+$', text):
        abort(400, 'Only a-z, A-Z, 0-9, dash, underscore are allowed.')