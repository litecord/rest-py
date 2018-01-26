#!/usr/bin/env python3

import sys
import requests

API_BASE = 'http://localhost:8000'

def main(args):
    guild_name = args[1]

    r = requests.post(f'{API_BASE}/api/guilds', headers= json={
        'name': guild_name
    })

    print(r)
    print(r.json())

if __name__ == '__main__':
    main(sys.argv)
