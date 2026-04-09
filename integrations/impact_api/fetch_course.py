'''\
Impact Publisher API integration script
\
This script takes a source URL (e.g., a Udemy course link) and returns the "courselink"
provided by the Impact Publisher API.  The API uses HTTP Basic authentication where the
Account SID is the username and the Auth Token is the password.
\
The credentials are read from environment variables so they are not committed to the
repository.  Create a ``.env`` file (or set the variables in your environment) before
running the script.
\
Usage::
\
    python fetch_course.py https://www.udemy.com/course/example
\
The script prints the JSON response from the API which includes the ``courselink``
field.
'''\

import os
import sys
import json
import requests
from urllib.parse import quote_plus

def main():
    if len(sys.argv) != 2:
        print("Usage: python fetch_course.py <source_url>")
        sys.exit(1)
    source_url = sys.argv[1]

    # Load credentials from environment variables
    account_sid = os.getenv("IMPACT_ACCOUNT_SID")
    auth_token = os.getenv("IMPACT_AUTH_TOKEN")
    if not account_sid or not auth_token:
        print("Error: IMPACT_ACCOUNT_SID and IMPACT_AUTH_TOKEN must be set in the environment.")
        sys.exit(1)

    # Endpoint – based on Impact Publisher API documentation.
    # The exact path may differ; adjust ``ENDPOINT`` if necessary.
    ENDPOINT = "https://publisher-api.impact.com/v1/partner/course"

    # The API expects the source URL as a query parameter called ``sourceUrl``.
    # Some APIs use POST with a JSON body; here we use GET for simplicity.
    params = {"sourceUrl": source_url}

    try:
        response = requests.get(
            ENDPOINT,
            params=params,
            auth=(account_sid, auth_token),
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    # Print formatted JSON response
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except ValueError:
        print("Failed to parse JSON response")
        sys.exit(1)

if __name__ == "__main__":
    main()
