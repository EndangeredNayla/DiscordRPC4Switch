'''
All the errors needed for DiscordRPC4Switch.
'''

class ConnectionError(Exception):
    def __init__(self):
        self.message = 'Failed to make connection. Please make sure that you are connected to the internet.'

    def __str__(self):
        return self.message

class DiscordError(Exception):
    def __init__(self):
        self.message = 'No active Discord instance found. Please make sure Discord is open.'
    
    def __str__(self):
        return self.message

class InvalidDisplayUser(Exception):
    def __init__(self):
        self.message = 'Not a valid account. Please make sure you are typing in the name of the account you wish to display accurately.'

    def __str__(self):
        return self.message

class InvalidRegisteredUser(Exception):
    def __init__(self):
        self.message = 'User does not exist. Try registering this user.'
    
    def __str__(self):
        return self.message
    
class InvalidRegisterAttempt(Exception):
    def __init__(self):
        self.message = 'The link you have inserted is invalid. Please try again.'
    
    def __str__(self):
        return self.message

class InvalidAPIResponse(Exception):
    def __init__(self):
        self.message = 'Invalid response received. Refer to log for details (if toggled).'
    
    def __str__(self):
        return self.message

class OutdatedUser(Exception):
    def __init__(self):
        self.message = 'This user is on an older version. Please try registering this user again.'
    
    def __str__(self):
        return self.message