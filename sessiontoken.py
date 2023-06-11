'''
Creates a URL for a webpage that facilitates registering a new account. Finds the session_token necessary to 
proceed with further registration.
'''

import base64
import requests
import webbrowser
import re
import secrets
import hashlib
import errors

def get_token():
    client_id = '71b963c1b7b6d119'
    session_token_code_url = 'https://accounts.nintendo.com/connect/1.0.0/authorize'
    session_token_url = 'https://accounts.nintendo.com/connect/1.0.0/api/session_token'

    ## setting up code challenge needed to generate URL of webpage with the 'Select this account' button.
    verifier = secrets.token_urlsafe()[:50]

    hash = hashlib.sha256(verifier.encode()).digest()
    encoded_hash = base64.urlsafe_b64encode(hash)
    session_token_code_challenge = encoded_hash.decode()[:-1]

    rand = secrets.token_urlsafe()[:50]

    headers = {
        'Accept-Encoding': 'gzip',
        'User-Agent': 'OnlineLounge/1.0.4 NASDKAPI Android'
    }
    params = {
        'client_id': client_id,
        'redirect_uri': f'npf{client_id}://auth',
        'response_type': 'session_token_code',
        'scope': 'openid user user.birthday user.mii user.screenName',
        'session_token_code_challenge': session_token_code_challenge,
        'session_token_code_challenge_method': 'S256',
        'state': rand,
        'theme': 'login_form'
    }
    link_url = requests.get(session_token_code_url, params=params, headers=headers).url
    webbrowser.open(link_url)

    link = input('Right click "Select this account" and paste the link here: ')
    session_token_code = re.findall('&session_token_code=(.*)&state=.*', link)
    data = {
        'client_id': client_id,
        'session_token_code': session_token_code,
        'session_token_code_verifier': verifier
    }
    response = requests.post(session_token_url, data=data, headers=headers).json()
    try:
        response['session_token']
    except KeyError:
        raise errors.InvalidRegisterAttempt()
    return response['session_token']