import requests
import time
import logging
import errors
import datetime
import itunes_app_scraper.scraper

class User:
    '''
    Representation of the User. Makes requests to different servers to get different tokens necessary to login/stay logged-in.
    '''

    token_url = 'https://accounts.nintendo.com/connect/1.0.0/api/token'
    gen_info_url = 'https://accounts.nintendo.com/2.0.0/users/me'
    login_url = 'https://api-lp1.znc.srv.nintendo.net/v3/Account/Login'
    friends_list_url = 'https://api-lp1.znc.srv.nintendo.net/v3/Friend/List'
    imink_url = 'https://api.imink.app/f'
    version = '1.0'

    def __init__(self, session_token):
        self.client_id = '71b963c1b7b6d119' ## magic number
        self.session_token = session_token
        self.logging = False ## logging default off
        self.version = str(User.version) ## needed for right version check

    def get_access_id_token(self):
        '''
        Makes a POST request to token_url and returns a dictionary containing the access_token and id_token which is necessary for future login attempts.
        '''
        token_headers = {
            'Host': 'accounts.nintendo.com',
            'Content-Type': 'application/json; charset=utf-8',
            'Connection': 'keep-alive',
            'User-Agent': 'OnlineLounge/1.0.4 NASDKAPI iOS',
            'Accept': 'application/json',
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip, deflate'
        }
        token_json = {
            'client_id': self.client_id,
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token',
            'session_token': self.session_token
        }
        access_id_response = self.get_request('post', User.token_url, headers=token_headers, json=token_json)
        try:
            self.access_token, self.id_token = access_id_response['access_token'], access_id_response['id_token']
        except KeyError:
            logging.error('Invalid response received. See above response details.')
            raise errors.InvalidAPIResponse()
    
    def get_birthday(self):
        '''
        Makes a GET request to gen_info_url and returns a dictionary containing the User's birthday which is necessary for future login attempts.
        '''
        gen_info_headers = {
            'Host': 'api.accounts.nintendo.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'User-Agent': 'OnlineLounge/1.0.4 NASDKAPI iOS',
            'Accept-Language': 'en-US',
            'Authorization': 'Bearer ' + self.access_token,
            'Accept-Encoding': 'gzip, deflate'
        }
        gen_info_response = self.get_request('get', User.gen_info_url, headers=gen_info_headers)
        try:
            self.birthday = gen_info_response['birthday']
        except KeyError:
            logging.error('Invalid response received. See above response details.')
            raise errors.InvalidAPIResponse()

    def get_imink(self):
        '''
        Makes a POST request to imink_url and returns a dictionary containing the User's f parameter, request_id, and timestamp, all necessary for logging in.
        '''
        imink_headers = {
            'User-Agent': 'DiscordRPC4Switch/1.0',
            'Content-Type': 'application/json; charset=utf-8'
        }
        imink_json = {
            'token': self.id_token,
            'hash_method': 1
        }
        imink_response = self.get_request('post', User.imink_url, headers=imink_headers, json=imink_json)
        try:
            self.f, self.request_id, self.timestamp = imink_response['f'], imink_response['request_id'], imink_response['timestamp']
        except KeyError:
            logging.error('Invalid response received. See above response details.')
            raise errors.InvalidAPIResponse()
    
    def get_login(self):
        '''
        Performs a login for the User by making a POST request to the login server. Returns a dictionary in the following format:
        {
            'status': 0,
            'result': {
                'user': {
                    'id': *id*,
                    'nsaId': *nsa id*,
                    'imageUri': *user icon link*,
                    'name': *name*,
                    'supportId': *support id*,
                    'isChildRestricted': False,
                    'etag': *etag*,
                    'links': {
                        'nintendoAccount': {
                            'membership': {
                                'active': False
                            }
                        },
                        'friendCode': {
                            'regenerable': True,
                            'regenerableAt': 1617590450,
                            'id': *friend id*
                        }
                    },
                    'permissions': {
                        'presence': 'FRIENDS'
                    },
                    'presence': {
                        'state': 'OFFLINE',
                        'updatedAt': 0,
                        'logoutAt': 0,
                        'game': {}
                    }
                },
                'webApiServerCredential': {
                    'accessToken': *webapi access token*,
                    'expiresIn': 7200
                },
                'firebaseCredential': {
                    'accessToken': '',
                    'expiresIn': 3600
                }
            },
            'correlationId': *correlation id*
        }
        Mostly interested in just the User's name, icon (for displaying to Discord), status (also for displaying to discord), and webApiServerCredential (needed to get friend status)
        '''
        current_time = time.time() ## used to figure out when to refresh
        if current_time - self.start_time_access_id > 800: ## refresh access_token and f parameter every 10 minutes
            self.get_access_id_token()
            self.get_imink()
            self.start_time_access_id = current_time

        ITUNES_APP_ID = 1234806557

        scraper = itunes_app_scraper.scraper.AppStoreScraper()
        nso_app_info = scraper.get_app_details(ITUNES_APP_ID, country = 'us')
        nsoAppVersion = nso_app_info.get('version')
        

        login_headers = {
            'Host': 'api-lp1.znc.srv.nintendo.net',
            'Accept-Language': 'en-US',
            'User-Agent': 'com.nintendo.znca/2.4.0 (iOS 16.2)',
            'Accept': 'application/json',
            'X-ProductVersion': nsoAppVersion,
            'Content-Type': 'application/json; charset=utf-8',
            'Connection': 'keep-alive',
            'Authorization': 'Bearer',
            'X-Platform': 'iOS',
            'Accept-Encoding': 'gzip, deflate'
        }
        login_json = { 
            "parameter": { 
                "language": "en-US", 
                "naBirthday": self.birthday, 
                "naCountry": "US", 
                "naIdToken": self.id_token, 
                "requestId": self.request_id, 
                "timestamp": self.timestamp, 
                "f": self.f
            } 
        }
        login_response = self.get_request('post', User.login_url, headers=login_headers, json=login_json)
        try:
            self.webApiServerCredential = login_response['result']['webApiServerCredential']['accessToken'] ## expires every 15 minutes
            self.name, self.icon, self.status = login_response['result']['user']['name'], login_response['result']['user']['imageUri'], login_response['result']['user']
        except KeyError:
            logging.error('Invalid response received. See above response details.')
            raise errors.InvalidAPIResponse()

    def login(self):
        '''
        Performs all the logging-in procedures all in one place. Need to separate each function because when refreshing, we don't need to perform every single step again, just some specific ones.
        '''
        self.start_time_access_id = time.time()
        self.start_time_webApi = time.time()
        self.get_access_id_token()
        self.get_birthday()
        self.get_imink()
        self.get_login()
    
    def get_request(self, type, url, headers={}, json={}):
        '''
        Performs a specified TYPE of API request to the provided URL given specific HEADERS and JSON, which are optional.
        Returns the response as a dictionary.
        '''
        request = None
        logging.info(f'Making a {type.upper()} request to {url} with headers {headers} and json {json}')
        
        try:
            if type == 'post':
                request = requests.post(url, headers=headers, json=json)
            elif type == 'get':
                request = requests.get(url, headers=headers, json=json)
        except requests.exceptions.ConnectionError:
            logging.error(f'Connection to {url} failed.')
            raise errors.ConnectionError() from None

        time = datetime.datetime.now()

        logging.info(f'Received the following response: {request.json()}')

        return request.json()

    def get_friends_list(self):
        '''
        Returns the Friends List as a list of dictionaries, each dictionary storing relevant information for each friend.

        Format of response (this is just one friend):
        [{
            'id': 0,
            'nsaId': *nsa id*,
            'imageUri': *user icon url*,
            'name': *name*,
            'isFriend': True,
            'isFavoriteFriend': False,
            'isServiceUser': False,
            'friendCreatedAt': 1629860977,
            'presence': {
                'state': 'OFFLINE',
                'updatedAt': 1671478749,
                'logoutAt': 1671478741,
                'game': {}
            }
        }]
        '''
        current_time = time.time() ## used to figure out when to refresh
        if current_time - self.start_time_webApi > 5400: ## refresh login every hour and thirty minutes
            self.get_login() ## refresh webApiServerCredential every 2 hours
            self.start_time_webApi = current_time
        friends_headers = {
            'Host':'api-lp1.znc.srv.nintendo.net',
            'Accept':'application/json',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept-Language': 'en-EN',
            'User-Agent': 'com.nintendo.znca/2.4.0 (iOS 16.2)',
            'Authorization': 'Bearer ' + self.webApiServerCredential 
        } 
        friends_response = self.get_request('post', self.friends_list_url, headers=friends_headers)
        self.friends_list = friends_response['result']['friends']
        return self.friends_list

    def get_name(self):
        '''
        Returns the name of this User.
        '''
        return self.name
    
    def get_status(self):
        '''
        Returns this User's status (currently broken because of changes to NSO API, always reports status as offline).
        '''
        self.get_login()
        return self.status
    
    def get_account_status(self, account_name):
        '''
        Returns the status of a specific friend (specified in ACCOUNT_NAME) as a dictionary.
        '''
        friends_list = self.get_all_status()
        for friend in friends_list:
            if friend['name'] == account_name:
                return friend
        return None
    
    def get_all_status(self):
        '''
        Returns the status of this User and this User's friends as a list of dictionaries. 
        '''
        friends = self.get_friends_list()[:]
        user = self.get_status()
        friends.append(user)
        return friends
    
    def toggle_log(self):
        '''
        Toggles the log feature.
        '''
        self.logging = True
        logging.getLogger(__name__)