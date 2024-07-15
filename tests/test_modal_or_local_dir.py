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
mocal = ModalOrLocal(volume_name=MODAL_VOLUME_NAME, volume_mount_dir = MODAL_VOLUME_MOUNT_DIR)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mocal.volume}) 
def test_get_changes():
    '''Write'''

    print("\n\nRunning test_get_changes", "locally" if modal.is_local() else "remotely")
    
    # Define our temp dir for this test and make sure it does not yet exist
    temp_dir = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_get_changes_dir")
    if mocal.file_or_dir_exists(temp_dir) : mocal.remove_file_or_directory(temp_dir) # start fresh

    mdir = ModalOrLocalDir(dir_full_path=temp_dir, volume_name=MODAL_VOLUME_NAME, volume_mount_dir=MODAL_VOLUME_MOUNT_DIR)
   #print(f"mdir is {mdir}")
    
    # Create the following in temp_dir:
    # ./my_subdir/ - <subdir_relative_path> gets created with json file creation
    # ./my_subdir/test_get_changes.json - as <json_file_relative_path>
    # ./my_subdir/my_subdirs_subdir/ - as <subdirs_subdir_relative_path>
   #print("\ntest_get_changes: Creating ./my_subdir/test_get_changes.json and ./mysubdir/my_subdirs_subdir/")
    subdir_relative_path = "my_subdir"
    test_json_data = json.loads('{"a":1, "b":2}')
    json_file_relative_path = os.path.join(subdir_relative_path, "test_get_changes.json")
    mdir.write_json_file(json_file_relative_path, test_json_data, force=True) #Note this also creates parent dirs as needed
    assert mdir.file_or_dir_exists(json_file_relative_path)

    read_data = mdir.read_json_file(json_file_relative_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Create the subdirs subdir directory
    subdirs_subdir_relative_path = os.path.join(subdir_relative_path, "my_subdirs_subdir")
    mocal.create_directory(mdir.get_full_path(subdirs_subdir_relative_path))
    assert mdir.file_or_dir_exists(subdirs_subdir_relative_path)

    # Get the changes
    initial_changes = mdir.report_changes()

    # Check that we got the expected changes (in an order agnostic way)
    assert initial_changes.get('new_or_modified_files') == [mdir.get_full_path(json_file_relative_path)], f"Expected new_or_modified_files to be {[mdir.get_full_path(json_file_relative_path)]} but got {initial_changes.get('new_or_modified_files')}"
    for modified_dir in [mdir.get_full_path(subdir_relative_path), mdir.get_full_path(subdirs_subdir_relative_path)]:
        assert modified_dir in initial_changes.get('new_or_modified_directories'), f"Expected {modified_dir} to be in new_or_modified_directories but got {initial_changes.get('new_or_modified_directories')}"
    assert len(initial_changes.get('new_or_modified_directories')) == 2, f"Expected 2, but got {len(initial_changes.get('new_or_modified_directories'))} entries in new_or_modified_directories: {initial_changes.get('new_or_modified_directories')}"

    # Capture the mtime so we can use it to only get the next set of new files/dirs
    mtime = mdir.get_mtime(subdirs_subdir_relative_path) + .001  # add a smidge to not get the file mtime was pulled from in the next set, we will sleep it off next
    sleep(2) if modal.is_local() else sleep(.1) # pause momentarily to make sure mtimes actually differ (unfortunately modal mtime is int so requires 1s)

    #
    # Do the following in temp_dir:
    # Edit ./my_subdir/test_get_changes.json - <json_file_relative_path>
    #
   #print(f"\ntest_get_changes: Editing ./my_subdir/test_get_changes.json, mtime is {mtime}")

    mtime_before = {
        json_file_relative_path: mdir.get_mtime(json_file_relative_path),
        subdir_relative_path: mdir.get_mtime(subdir_relative_path),
        subdirs_subdir_relative_path: mdir.get_mtime(subdirs_subdir_relative_path),
    }

    # Edit (actually replace) our original json file and verify the changed data
    read_data["new_key"] = "my_new_value"
    mdir.write_json_file(json_file_relative_path, read_data)

    changed_read_data = mdir.read_json_file(json_file_relative_path)
    assert changed_read_data is not None
    assert changed_read_data.get('a') == 1
    assert changed_read_data.get('new_key') == "my_new_value"

    mtime_after = {
        json_file_relative_path: mdir.get_mtime(json_file_relative_path),
        subdir_relative_path: mdir.get_mtime(subdir_relative_path),
        subdirs_subdir_relative_path: mdir.get_mtime(subdirs_subdir_relative_path),
    }

    for path in mtime_before.keys():
        before = mtime_before.get(path)
        after = mtime_after.get(path)
        #print(f"    {path}: before {before}, after {after}, difference: {after-before}")

    after_edit_changes = mdir.report_changes(datetime.fromtimestamp(mtime))
   #print(f"After json edit {after_edit_changes=}, edited mtime of json_file is {mdir.get_mtime(json_file_relative_path)}")

    expected_changes = {
        'new_or_modified_files': [mdir.get_full_path(json_file_relative_path)], 
        #'new_or_modified_directories': [mdir.get_full_path(subdir_relative_path)] # currently ignored, since mtime changes on modified dirs seem inconsistent
    }
    
    assert after_edit_changes.get('new_or_modified_files') == expected_changes.get('new_or_modified_files'), \
        f"After json file edit expected new_or_modified_files:\n {expected_changes.get('new_or_modified_files')} but got\n {after_edit_changes.get('new_or_modified_files')}"

    # Capture the mtime so we can use it to only get the next set of new files/dirs
    mtime = mdir.get_mtime(json_file_relative_path) + .001  # add a smidge to not get the file mtime was pulled from in the next set
    sleep(1) if modal.is_local() else sleep(1) # pause momentarily to make sure mtimes actually differ (unfortunately modal mtime requires 1s)

    # Do the following in temp_dir:
    # Create ./my_subdir/my_subdirs_subdir/new_json_file.json - path relative to temp_dir saved as <new_json_file_relative_path>
   #print(f"\ntest_get_changes: Creating ./my_subdir/my_subdirs_subdir/new_json_file.json, mtime is {mtime}")

    # Create a new json file in ./my_subdir/my_subdirs_subdir
    new_json_file_relative_path = os.path.join(subdirs_subdir_relative_path, "new_json_file.json")
    mdir.write_json_file(new_json_file_relative_path, {"x":1})

    read_data = mdir.read_json_file(new_json_file_relative_path)
    assert read_data.get('x') == 1

    # Get changes again and verify the subdir and subdirs_subdir (since a file was added) and new json file are there
    after_new_json_changes = mdir.report_changes(datetime.fromtimestamp(mtime))
   #print(f"{after_new_json_changes=}")
    expected_changes = {
        'new_or_modified_files': [mdir.get_full_path(new_json_file_relative_path)], 
        #'new_or_modified_directories': [mdir.get_full_path(subdir_relative_path), mdir.get_full_path(subdirs_subdir_relative_path)]
    }
    
    assert after_new_json_changes.get('new_or_modified_files') == expected_changes.get('new_or_modified_files'), \
            f"After adding new json file expected new_or_modified_files\n {expected_changes.get('new_or_modified_files')} but got\n {after_new_json_changes.get('new_or_modified_files')}"
    #assert after_new_json_changes.get('new_or_modified_directories') == expected_changes.get('new_or_modified_directories') \
    #    or after_new_json_changes.get('new_or_modified_directories') == reversed(expected_changes.get('new_or_modified_directories')), \
    #    f"After adding new json file expected new_or_modified_directories\n {expected_changes.get('new_or_modified_directories')}\n or {reversed(expected_changes.get('new_or_modified_directories'))}\n but got\n {after_new_json_changes.get('new_or_modified_directories')}"
    
    
    # Remove the test directory and verify it was actually deleted
    mocal.remove_file_or_directory(temp_dir)
    assert not mocal.file_or_dir_exists(temp_dir)

    print("Running test_get_changes", "locally" if modal.is_local() else "remotely", "finished")


@app.local_entrypoint()
def main():  
    test_get_changes.local()
    test_get_changes.remote()

    