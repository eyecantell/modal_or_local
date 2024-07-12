import modal
import json
import os
import datetime
from typing import Set
from modal_or_local import setup_image, ModalOrLocal, ModalOrLocalDir

# Call this with 'modal run tests/test_modal_or_local_dir.py'
# PRW todo - write custom runner for pytest to run this?

image = setup_image()
app = modal.App("test_modal_or_local_dir")

MODAL_VOLUME_NAME = "test_modal_or_local_dir_volume"
MODAL_VOLUME_MOUNT_DIR = "/test_mnt_dir"
mvol = ModalOrLocal(volume_name=MODAL_VOLUME_NAME, volume_mount_dir = MODAL_VOLUME_MOUNT_DIR)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume}) 
def test_get_changes():
    '''Write'''

    print("Running test_get_changes", "locally" if modal.is_local() else "remotely")
    
    temp_dir = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_get_changes_dir")
    mdir = ModalOrLocalDir(dir_full_path=temp_dir, volume_name=MODAL_VOLUME_NAME, volume_mount_dir=MODAL_VOLUME_MOUNT_DIR)
    print(f"mdir is {mdir}")
    
    test_json_data = json.loads('{"a":1, "b":2}')
    json_file_full_path = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_get_changes.json")
    mdir.write_json_file(json_file_full_path, test_json_data, force=True)
    assert mvol.file_or_dir_exists(json_file_full_path)

    read_data = mvol.read_json_file(json_file_full_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Get the changes
    print("Getting changes")
    changes = mdir.get_changes()
    print(changes)

    # Remove the test file
    mvol.remove_file_or_directory(temp_dir)

    # Check that file was actually deleted
    assert not mvol.file_or_dir_exists(json_file_full_path)

    print("Running test_get_changes", "locally" if modal.is_local() else "remotely", "finished")


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    test_get_changes.local()
    #test_get_changes.remote()

    