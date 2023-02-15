import functools
import hmac
import hashlib
from flask import request, abort

def require_gh_secret(secret):
    def require_the_secret(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if not request.headers.get('X-Hub-Signature'):
                return 'X-Hub-Signature header is required', 403
            key = bytes(secret, 'utf-8')
            expected_signature = hmac.new(key=key, msg=request.data, digestmod=hashlib.sha1).hexdigest()
            incoming_signature = request.headers.get('X-Hub-Signature').split('sha1=')[-1].strip()
            if not hmac.compare_digest(incoming_signature, expected_signature):
                return 'Invalid X-Hub-Signature was provided.', 403
            return function(*args, **kwargs)
        return wrapper
    return require_the_secret