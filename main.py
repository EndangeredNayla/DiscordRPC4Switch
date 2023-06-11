#!/usr/bin/env python3

import argparse
import pickle
import user
import discordrpc
import time
import os
import re
import logging
import logging.config
import errors
import sessiontoken
import sys

def get_user(user_name):
    '''
    Finds the User with name USER_NAME from the users directory and returns the corresponding ACCOUNT.
    '''
    try:
        with open(f'users/{user_name}.pickle', 'rb') as read:
            account = pickle.load(read)
        assert account.version == user.User.version
    except FileNotFoundError: ## invalid user
        raise errors.InvalidRegisteredUser()
    except AssertionError:
        raise errors.OutdatedUser()

    return account

def accounts(args: argparse.Namespace): 
    '''
    Prints a series of account names from the accounts in the users directory.
    '''
    accounts = []
    account_files = [re.findall('(.*)\.pickle$', file)[0] for file in os.listdir('users/') if os.path.isfile(os.path.join("users/", file)) and re.search(".*\.pickle$", file)]
    for account_file in account_files:
        temp_user = get_user(account_file)
        accounts.append(temp_user.get_name())
    if len(accounts) == 0:
        print('You have no accounts. Please register one.')
    else:
        accounts_str = f"List of accounts: {', '.join(str(account) for account in accounts)}"
        print(accounts_str)

def friends(args: argparse.Namespace):
    '''
    Prints a series of friends of the specified user in ARGS.
    '''
    user = get_user(args.user)
    friends = user.get_friends_list()
    if len(friends) == 0:
        print('You have no friends on this account.')
    else:
        friends_str = f"List of friends: {', '.join(str(friend['name']) for friend in friends)}"
        print(friends_str)

def register(args: argparse.Namespace):
    '''
    Registers a user by generating a URL with help from a S256 code challenge directing the User to copy a link to paste here
    and create a new User object which is then serialized in the users directory (created if doesn't exist).
    '''
    session_token = sessiontoken.get_token()
    register_user = user.User(session_token)
    register_user.login()
    
    if os.path.exists(f'users/{register_user.get_name()}.pickle'): ## already exists
        print('Note: If you are trying to register a *different* account with the same name as a registered account, nxsence does not support that at the moment.')
        override = input('A user with this name already has been registered: Override? (y/n): ')
        if override.lower() != 'y':
            print('Quitting...')
            exit()

    if not os.path.exists('users'):
        os.mkdir('users')
    
    with open(f'users/{register_user.get_name()}.pickle', 'wb') as outfile: ## serialize user
        pickle.dump(register_user, outfile)

def discord(args: argparse.Namespace):
    '''
    Links with an active Discord instance and sends updates on the User's status every thirty seconds.
    '''
    main_user_name = args.main_user
    displayed_user_name = args.displayed_user
    main_user: user.User = get_user(main_user_name)
    main_user.login()
    
    ## check for who the displayed_user is: if it's None, display main_user status, otherwise display friend status
    if displayed_user_name is None:
        displayed_user_name = main_user_name

    ## used for knowing when to refresh webApiCredential
    start_time = time.time()

    ## set up logger
    if args.log:
        date = int(time.time())
        if not os.path.exists('logs'):
            os.mkdir('logs')
        logging.basicConfig(
            filename=f'logs/log_{date}.txt',
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S',
            force=True
        )
        main_user.toggle_log()
    
    discord = discordrpc.Discord(args.log) ## separate from User toggle_log because of how User is set up (serialization)

    discord.connect()

    print(f'Displaying status for {displayed_user_name}. To exist, press CTRL+C.')

    active_game: dict = {} ## used to figure out current game's playtime, key: game name, value: time started (need to know how long User has been playing)

    ## update Discord status
    while True:

        current_time = time.time()
        if current_time - start_time > 5400: ## refresh login every hour and thirty minutes
            logging.info("Attempting to refresh login...")
            main_user.login()
            start_time = current_time

        ## iterate and find user?
        displayed_user_status = main_user.get_account_status(displayed_user_name)
        try: ## ensure that this display user really exists (either is self or comes from friends list)
            assert isinstance(displayed_user_status, dict)
        except AssertionError:
            logging.error(f"Failed to find the user {displayed_user_name}.")
            raise errors.InvalidDisplayUser()
        
        logging.info("Fetching user status...")

        user_state = displayed_user_status['presence']['state']
        mii = displayed_user_status['imageUri']

        if user_state == 'ONLINE':
            try: ## figure out current playtime, assuming active_game has been updated to include this currently-playing game
                game = displayed_user_status['presence']['game']['name']
                start = active_game[game]
            except KeyError:
                game = displayed_user_status['presence']['game']['name']
                active_game = {} ## clear dictionary for new game
                active_game[game] = int(time.time())
                start = active_game[game]
                gameAsset = displayed_user_status['presence']['game']['imageUri']

                ## update the client
                discord.update(
                    large_image=gameAsset,
                    large_text=game,
                    small_image=mii,
                    small_text=displayed_user_status['name'],
                    status=f"Playing {game}",
                    start=start
                )
        elif user_state == 'INACTIVE':
            active_game = {}
            discord.update(
                large_image='switch',
                large_text='Home Screen',
                small_image=displayed_user_status['imageUri'],
                small_text=displayed_user_status['name'],
                status="Online"
            )
        else:
            pass
        time.sleep(30) ## update Discord status every thirty seconds

## parsing to identify subcommands
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(title='subcommands', description='Valid subcommands')

## register
parser_register = subparsers.add_parser('register', description='Register a new account to use.')
parser_register.set_defaults(func=register)

## discord
parser_discord = subparsers.add_parser('discord', description='Begin sharing Nintendo Switch game status to Discord')
parser_discord.add_argument('main_user', help='The user to login to.')
parser_discord.add_argument('displayed_user', nargs='?', default=None, help='The user whose status to share to Discord. Default the logged-in user')
parser_discord.add_argument('-log', action='store_true', help='Produces a log that can be useful in debugging issues. Default is False.')
parser_discord.set_defaults(func=discord)

## accounts
parser_accounts = subparsers.add_parser('accounts', description='Get a list of registered accounts.')
parser_accounts.set_defaults(func=accounts)

## friends
parser_friends = subparsers.add_parser('friends', description="Get a list of this user's friends.")
parser_friends.add_argument('user', help='The user whose friends you wish to see.')
parser_friends.set_defaults(func=friends)

args = parser.parse_args()


try:
    func = args.func
    func(args)
except AttributeError as e:
    print('No command inputted, try again.') 