import modal
import json
import os
from datetime import datetime
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
    
    # Define out temp dir for this test and make sure it does not yet exist
    temp_dir = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_get_changes_dir")
    if mvol.file_or_dir_exists(temp_dir) : mvol.remove_file_or_directory(temp_dir) # start fresh

    mdir = ModalOrLocalDir(dir_full_path=temp_dir, volume_name=MODAL_VOLUME_NAME, volume_mount_dir=MODAL_VOLUME_MOUNT_DIR)
    print(f"mdir is {mdir}")
    
    test_json_data = json.loads('{"a":1, "b":2}')
    json_filename = "test_get_changes.json"
    mdir.write_json_file(json_filename, test_json_data, force=True) #Note this also creates parent dirs as needed
    assert mdir.file_or_dir_exists(json_filename)

    read_data = mdir.read_json_file(json_filename)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Create another directory
    subdir_name = "my_subdir"
    mvol.create_directory(mdir.get_full_path(subdir_name))
    assert mdir.file_or_dir_exists(subdir_name)

    # Get the changes
    print("Getting changes")
    changes = mdir.get_changes()
    print(changes)

    # Check that we got the expected changes
    assert changes == {'new_or_modified_files': [mdir.get_full_path(json_filename)], 
                       'new_or_modified_directories': [mdir.get_full_path(subdir_name)]
                       }
    
    # Add a new file and edit our original json file then make sure those changes show up when we get_changes

    # Capture the mtime so we can use it
    mtime = mdir.get_mtime(json_filename) + 1 # Add one to not include the original

    # Edit (actually replace) our original json file and virfy the changed data
    new_data : dict = read_data
    new_data["new_key"] = "my_new_value"
    mdir.write_json_file(json_filename, new_data)

    read_data = mdir.read_json_file(json_filename)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('new_key') == "my_new_value"

    # Create a new json file in a new subdir
    subdirs_subdir_name = "my_subdirs_subdir"
    new_json_file = os.path.join(subdir_name, subdirs_subdir_name, json_filename)
    mdir.write_json_file(new_json_file, {"x":1})

    read_data = mdir.read_json_file(new_json_file)
    assert read_data.get('x') == 1

    # Get changes again and verify the json file change and the new subdir and json file are there
    new_changes = mdir.get_changes(datetime.fromtimestamp(mtime))
    print(f"{new_changes=}")
    expected_changes = {
        'new_or_modified_files': [mdir.get_full_path(json_filename), mdir.get_full_path(new_json_file)], 
        'new_or_modified_directories': [mdir.get_full_path(subdirs_subdir_name)]}
    
    # Check changes in an order agnostic way
    # Make sure new or modified files are correct
    for path in [mdir.get_full_path(json_filename), mdir.get_full_path(new_json_file)]:
        assert path in new_changes['new_or_modified_files'], f"{path} not in {new_changes['new_or_modified_files']=}"
    assert len(new_changes['new_or_modified_files']) == 2, f"Extra entries in {new_changes['new_or_modified_files']=}"
    
    assert new_changes['new_or_modified_directories'] == expected_changes['new_or_modified_directories'], f"Expected new_or_modified_directories:\n {expected_changes['new_or_modified_directories']} but got \n{new_changes['new_or_modified_directories']}"

    # Remove the test directory and verify it was actually deleted
    mvol.remove_file_or_directory(temp_dir)
    assert not mvol.file_or_dir_exists(temp_dir)

    print("Running test_get_changes", "locally" if modal.is_local() else "remotely", "finished")


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    #test_get_changes.local()
    test_get_changes.remote()

    