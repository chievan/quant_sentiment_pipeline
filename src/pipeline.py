#!/usr/bin/env python3
import os
import sys

# Clear environment proxies to prevent proxy blockages on the server
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    if key in os.environ:
        del os.environ[key]

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from generate_dh_brief import main as generate_dh_brief_main

def main():
    generate_dh_brief_main()

if __name__ == "__main__":
    main()
