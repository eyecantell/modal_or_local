from modal import Image, is_local
import pathlib
import os

# Get the path of the current module
current_module_path = pathlib.Path(__file__).resolve().parent
parent_dir = current_module_path.parent

# Construct the path to the requirements.txt file
requirements_file = os.path.join(parent_dir,'requirements.txt')

# Check if the requirements.txt file exists
if is_local() and os.path.isfile(requirements_file):
    with open(requirements_file, 'r') as f:
        requirements = [req for req in f.read().splitlines() if req]
        #print(f"{requirements=}")
else:
    requirements = []

def setup_image()->Image:
    '''Prepares an Image to be run on Modal that has all things needed to support the modal_or_local project'''

    # Note the image.run_commands() etc do not change the image value but return a new image
    # This means if additional changes are to be made, they can be made here or post with image = image.<new commands>
    image = (
        Image.debian_slim(python_version="3.10")
        .apt_install("git")
        .pip_install(*requirements)
        .workdir("/root")
        .env({"MY_ENV_VAR": "value"})
        .run_commands("pwd && git clone https://github.com/eyecantell/modal_or_local.git", force_build=True)
    )

    return image
