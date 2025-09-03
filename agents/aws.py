"""
aws.py
Simple script to test AWS connection using boto3 and a specific profile.
Works with virtual environment.
"""

import boto3
import sys

def main():
    # Set AWS profile name
    profile_name = "myisb01_IsbUsersPS-371061166839"

    try:
        # Start a session with the profile
        session = boto3.Session(profile_name=profile_name)
        
        # Use STS to verify credentials
        sts_client = session.client("sts")
        identity = sts_client.get_caller_identity()
        
        print("AWS Identity info:")
        print(identity)

    except Exception as e:
        print("Error connecting to AWS:")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()

