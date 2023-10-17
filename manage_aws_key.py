import json
from decouple import config
import argparse

# Path to the JSON file
CONFIG_PATH = "pfctoolkit_config/GSP1000_MF_91v_3209c.json"

def update_aws_secret_key():
    """Update AWS_SECRET_ACCESS_KEY in the JSON config."""
    
    # Get the AWS_SECRET_ACCESS_KEY from the .env file
    aws_secret_key = config('AWS_SECRET_ACCESS_KEY')

    # Read the JSON file
    with open(CONFIG_PATH, 'r') as json_file:
        data = json.load(json_file)

    # Update the AWS_SECRET_ACCESS_KEY field
    data['AWS_SECRET_ACCESS_KEY'] = aws_secret_key

    # Write the updated data back to the file
    with open(CONFIG_PATH, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def remove_aws_secret_key():
    """Replace AWS_SECRET_ACCESS_KEY with an empty string in the JSON config."""

    # Read the JSON file
    with open(CONFIG_PATH, 'r') as json_file:
        data = json.load(json_file)

    # Set the AWS_SECRET_ACCESS_KEY to an empty string
    data['AWS_SECRET_ACCESS_KEY'] = ""

    # Write the updated data back to the file
    with open(CONFIG_PATH, 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage AWS Secret Key in JSON config.")
    parser.add_argument('action', choices=['update', 'remove'], help="Action to perform. 'update' to update the secret key or 'remove' to remove it.")
    
    args = parser.parse_args()

    if args.action == 'update':
        update_aws_secret_key()
        print("AWS_SECRET_ACCESS_KEY updated.")
    elif args.action == 'remove':
        remove_aws_secret_key()
        print("AWS_SECRET_ACCESS_KEY removed.")
