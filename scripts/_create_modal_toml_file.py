import os
import json
import toml

# This script recreates the ~/.modal.toml file from the previously set MODAL_TOKEN_INFO environment variable
# The .modal.toml file holds the token id and secret for running modal

# Get the MODAL_TOKEN_INFO environment variable
modal_token_info = (
    os.getenv("MODAL_TOKEN_INFO").replace("'", '"').replace("True", "true")
)

# print(f"{modal_token_info=}")

# Check if the environment variable is set
if modal_token_info:
    # Create a dictionary from the JSON string
    modal_config = json.loads(modal_token_info.replace("'", '"'))

    # Determine the home directory
    home_dir = os.path.expanduser("~")

    # Construct the path to the .modal.toml file
    modal_toml_path = os.path.join(home_dir, ".modal.toml")

    # Write the TOML data to the .modal.toml file
    with open(modal_toml_path, "w") as f:
        toml.dump(modal_config, f)
    print(f"The .modal.toml file has been recreated at {modal_toml_path}")
else:
    print("The MODAL_TOKEN_INFO environment variable is not set.")
