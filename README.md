# modal_or_local
File and directory utilities for working with modal volumes. The modal_or_local package gives the ability to use the same code to control files and directories from either a local run or remote run.

See scripts/example.py and tests/ for code samples.

This package is expected to work on any Linux type system and has been tested on WSL.  Working from Windows will have issues primarily because of the extensive use of os.path tools that are presumed to give Linux-style paths to work on Modal.

## Usage
```python
import modal
import os
from modal_or_local import setup_image, ModalOrLocal

image = setup_image()
app = modal.App("myapp")

MODAL_VOLUME_NAME = "my_modal_volume"
MODAL_VOLUME_MOUNT_DIR = "/volume_mnt_dir"
mvol = ModalOrLocal(volume_name=MODAL_VOLUME_NAME, volume_mount_dir=MODAL_VOLUME_MOUNT_DIR)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume})
def do_stuff():

    # Create or remove a directory on the volume - similar to os.mkdirs() and shutil.rmtree()
    mvol.create_directory("/volume_mnt_dir/my/set/of/created/directories")
    mvol.remove_file_or_directory("/volume_mnt_dir/my/set/of/created/directories")

    # List items in a directory on the volume
    filenames = mvol.listdir("/volume_mnt_dir")
    print("filenames in /volume_mnt_dir are", filenames)
    filenames_full_path = mvol.listdir("/volume_mnt_dir", return_full_paths=True)
    print("filenames with full path in /volume_mnt_dir are", filenames_full_path)

    # Create / overwrite a json file on the volume
    metadata = {"name": "Heather", "age": None}
    json_file_full_path = "/volume_mnt_dir/myfile.json"
    mvol.write_json_file(json_file_full_path, metadata)

    # Read a json file on the volume
    json_data = mvol.read_json_file(json_file_full_path)
    print("json_data is", json_data)

    # See tests/test_modal_or_local.py for more examples

@app.local_entrypoint()
def main():
    # The methods in modal_or_local will work for a modal volume whether running locally or remotely
    do_stuff.local()
    do_stuff.remote()
    