import functools

from flask import request, abort

def require_role(oidc, role):
    def role_check(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            # Read token (Copied from oidc.accept_token)
            token = None
            if 'Authorization' in request.headers and request.headers['Authorization'].startswith('Bearer '):
                token = request.headers['Authorization'].split(None,1)[1].strip()
            if 'access_token' in request.form:
                token = request.form['access_token']
            elif 'access_token' in request.args:
                token = request.args['access_token']
            
            # Get token info
            info = oidc._get_token_info(token)

            # Check token validity (Copied from oidc.accept_token)
            if not ('preferred_username' in info): # could be any common field in access token
                abort(401)
            # NOTE: Another slower way:
            # validity = oidc.validate_token(token) # From introspect endpoint
            # if not (validity is True):
            #     abort(401)

            # Check roles field
            roles = info.get('roles')
            if roles is None:
                abort(400, "No 'roles' field in access token.")
            
            # Check correct roles
            if not (role in roles):
                abort(403, f"'{role}' role is required.")

            # Pass
            return function(*args, **kwargs)
        return wrapper
    return role_check