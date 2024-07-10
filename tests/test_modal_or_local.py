import modal
import json
import os
from modal_or_local import setup_image, ModalOrLocal

# Call this with 'modal run tests/test_modal_or_local.py'
# PRW todo - write custom runner for pytest to run this?

image = setup_image()
app = modal.App("test_read_notices_in_modal_volume")

REMOTE_NOTICES_VOLUME_NAME = "my_modal_test_volume"
volume = modal.Volume.from_name(REMOTE_NOTICES_VOLUME_NAME, create_if_missing=True)
REMOTE_NOTICES_MOUNT_DIR = "/test_mnt_dir"

mol_local = ModalOrLocal()
mol_remote = ModalOrLocal(volume_name=REMOTE_NOTICES_VOLUME_NAME, volume_mount_dir = REMOTE_NOTICES_MOUNT_DIR)

@app.function(image=image, volumes={REMOTE_NOTICES_MOUNT_DIR: volume}) 
def test_write_and_read_volume_file():
    '''Write a json file to a modal volume then read it (should be able to run both .local() and .remote())'''

    print("Running test_read_file_from_volume", "locally" if modal.is_local() else "remotely")
    test_json_data = json.loads('{"a":1, "b":2}')

    json_file_full_path = os.path.join(REMOTE_NOTICES_MOUNT_DIR, "test_write_and_read_volume_file.json")

    mol_remote.write_json_file(json_file_full_path, test_json_data, force=True)

    assert mol_remote.file_or_dir_exists(json_file_full_path)

    read_data = mol_remote.read_json_file(json_file_full_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Remove the test file
    mol_remote.remove_file_or_directory(json_file_full_path)

    # Cannot check that file was actually deleted without a reload of the volume, not sure how to use reload() (get running function error) so commenting out
    #assert not mol_remote.file_or_dir_exists(json_file_full_path)

    print("Running test_read_file_from_volume", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={REMOTE_NOTICES_MOUNT_DIR: volume})
def test_listdir():
    for prefix in ["a", "b", "c"]:
        full_path = os.path.join("/", mol_remote.volume_mount_dir, "test_listdir_data", prefix + ".txt")
        with open(full_path, 'w') as f:
            f.write(prefix + ": this is a test") 

@app.function(image=image, volumes={REMOTE_NOTICES_MOUNT_DIR: volume})
def test_create_or_remove_dir():
    '''Create and remove directory within a volume'''
    mol_remote.create_directory("/my/test")
    assert mol_remote.file_or_dir_exists("/my/test")
    mol_remote.remove_file_or_directory()


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    #test_write_and_read_volume_file.local()
    test_write_and_read_volume_file.remote()
    #test_listdir.remote()
    #test_create_or_remove_dir.local()
    