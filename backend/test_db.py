#!/usr/bin/env python
"""Test script to debug database issues"""

import os

# Remove old database
if os.path.exists('server_monitor.db'):
    os.remove('server_monitor.db')
    print('Deleted old database file')

# Now test with actual module
print('\n1. Testing with database.py module...')
import database as db

print('   - Initializing database...')
db.init_db()
print('   ✓ Database initialized')

print('   - Getting all servers...')
servers = db.get_all_servers()
print(f'   ✓ Found {len(servers)} servers')

print('   - Adding new server...')
server_id = db.add_server('Test 2', 'https://test.com')
print(f'   ✓ Server ID: {server_id}')

print('   - Getting all servers again...')
servers = db.get_all_servers()
print(f'   ✓ Found {len(servers)} servers')
for s in servers:
    print(f'   - {s}')
