#!/usr/bin/env python3

import sys
import requests

API_BASE = 'http://localhost:8000'


def main(args):
    email = args[1]
    password = args[2]
    username = args[3]

    r = requests.post(f'{API_BASE}/api/auth/users/add', json={
        'email': email,
        'password': password,
        'username': username,
    })

    print(r)
    print(r.json())

if __name__ == '__main__':
    main(sys.argv)
