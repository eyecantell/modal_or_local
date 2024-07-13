import modal
import json
import os
from datetime import datetime
from typing import Set
from time import sleep
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
    
    # Create the following in temp_dir:
    # ./my_subdir/ - <subdir_name> gets created with json file creation
    # ./my_subdir/test_get_changes.json - as <json_file_relative_path>
    # ./my_subdir/my_subdirs_subdir/ - as <subdirs_subdir_relative_path>
    subdir_name = "my_subdir"
    test_json_data = json.loads('{"a":1, "b":2}')
    json_file_relative_path = os.path.join(subdir_name, "test_get_changes.json")
    mdir.write_json_file(json_file_relative_path, test_json_data, force=True) #Note this also creates parent dirs as needed
    assert mdir.file_or_dir_exists(json_file_relative_path)

    read_data = mdir.read_json_file(json_file_relative_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Create another directory
    subdirs_subdir_name = "my_subdirs_subdir"
    subdirs_subdir_relative_path = os.path.join(subdir_name, subdirs_subdir_name)
    mvol.create_directory(mdir.get_full_path(subdirs_subdir_relative_path))
    assert mdir.file_or_dir_exists(subdirs_subdir_relative_path)

    # Get the changes
    print("Getting changes")
    changes = mdir.get_changes()
    print(changes)

    # Check that we got the expected changes (in an order agnostic way)
    assert changes.get('new_or_modified_files') == [mdir.get_full_path(json_file_relative_path)], f"Expected new_or_modified_files to be {[mdir.get_full_path(json_file_relative_path)]} but got {changes.get('new_or_modified_files')}"
    for modified_dir in [mdir.get_full_path(subdir_name), mdir.get_full_path(subdirs_subdir_relative_path)]:
        assert modified_dir in changes.get('new_or_modified_directories'), f"Expected {modified_dir} to be in new_or_modified_directories but got {changes.get('new_or_modified_directories')}"
    assert len(changes.get('new_or_modified_directories')) == 2, f"Expected 2, but got {len(changes.get('new_or_modified_directories'))} entries in new_or_modified_directories: {changes.get('new_or_modified_directories')}"

    # Capture the mtime so we can use it to only get the next set of new files/dirs
    mtime = mdir.get_mtime(subdirs_subdir_relative_path) + .001 # add a smidge to not get the subdir in next set
    sleep(.002) # pause momentarily to make sure mtimes actually differ

    # Do the following in temp_dir:
    # Edit ./my_subdir/test_get_changes.json - path relative to temp_dir is <json_file_relative_path>

    # Edit (actually replace) our original json file and verify the changed data
    read_data["new_key"] = "my_new_value"
    mdir.write_json_file(json_file_relative_path, read_data)

    changed_read_data = mdir.read_json_file(json_file_relative_path)
    assert changed_read_data is not None
    assert changed_read_data.get('a') == 1
    assert changed_read_data.get('new_key') == "my_new_value"

    new_changes = mdir.get_changes(datetime.fromtimestamp(mtime))
    print(f"After json edit {new_changes=}")

    expected_changes = {
        'new_or_modified_files': [mdir.get_full_path(json_file_relative_path)], 
        'new_or_modified_directories': [mdir.get_full_path(subdir_name)]}
    
    assert new_changes == expected_changes, f"After json file edit expected\n {expected_changes} but got\n {new_changes}"

    # Capture the mtime so we can use it to only get the next set of new files/dirs
    mtime = mdir.get_mtime(subdirs_subdir_relative_path) + .001  # add a smidge to not get teh subdir in next set
    sleep(.002) # pause momentarily to make sure mtimes actually differ

    # Do the following in temp_dir:
    # Create ./my_subdir/my_subdirs_subdir/new_json_file.json - path relative to temp_dir saved as <new_json_file_relative_path>

    # Create a new json file in ./my_subdir/my_subdirs_subdir
    new_json_file_relative_path = os.path.join(subdirs_subdir_relative_path, "new_json_file.json")
    mdir.write_json_file(new_json_file_relative_path, {"x":1})

    read_data = mdir.read_json_file(new_json_file_relative_path)
    assert read_data.get('x') == 1

    # Get changes again and verify the json file change, subdirs_subdir (since a file was added to it) and new json file are there
    new_changes = mdir.get_changes(datetime.fromtimestamp(mtime))
    print(f"{new_changes=}")
    expected_changes = {
        'new_or_modified_files': [mdir.get_full_path(new_json_file_relative_path)], 
        'new_or_modified_directories': [mdir.get_full_path(subdirs_subdir_name)]}
    
    assert new_changes == expected_changes, f"After adding new json file expected\n {expected_changes} but got\n {new_changes}"
    
    # Remove the test directory and verify it was actually deleted
    mvol.remove_file_or_directory(temp_dir)
    assert not mvol.file_or_dir_exists(temp_dir)

    print("Running test_get_changes", "locally" if modal.is_local() else "remotely", "finished")


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    #test_get_changes.local()
    test_get_changes.remote()

    