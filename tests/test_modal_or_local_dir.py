import modal
import json
import os
from datetime import datetime
from time import sleep, time
from modal_or_local import setup_image, ModalOrLocal, ModalOrLocalDir

# Call this with 'modal run tests/test_modal_or_local_dir.py'
# PRW todo - write custom runner for pytest to run this?

image = setup_image()
app = modal.App("test_modal_or_local_dir")

mocal = ModalOrLocal(volume_name="test_modal_or_local_dir_volume", volume_mount_dir = "/test_mnt_dir")

@app.function(image=image, volumes={mocal.volume_mount_dir: mocal.volume}) 
def test_report_changes():
    '''Write'''

    print("\n\nRunning test_report_changes", "locally" if modal.is_local() else "remotely")
    
    # Define our temp dir for this test and make sure it does not yet exist
    temp_dir = os.path.join(mocal.volume_mount_dir, "test_report_changes_dir")
    if mocal.file_or_dir_exists(temp_dir) : mocal.remove_file_or_directory(temp_dir) # start fresh

    mdir = ModalOrLocalDir(dir_full_path=temp_dir, modal_or_local=mocal)
    #print(f"mdir is {mdir}")
    
    # Create the following in temp_dir:
    # ./my_subdir/ - <subdir_relative_path> gets created with json file creation
    # ./my_subdir/test_report_changes.json - as <json_file_relative_path>
    # ./my_subdir/my_subdirs_subdir/ - as <subdirs_subdir_relative_path>
    #print("\ntest_report_changes: Creating ./my_subdir/test_report_changes.json and ./mysubdir/my_subdirs_subdir/")
    subdir_relative_path = "my_subdir"
    test_json_data = json.loads('{"a":1, "b":2}')
    json_file_relative_path = os.path.join(subdir_relative_path, "test_report_changes.json")
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
    # Edit ./my_subdir/test_report_changes.json - <json_file_relative_path>
    #
   #print(f"\ntest_report_changes: Editing ./my_subdir/test_report_changes.json, mtime is {mtime}")

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

    #for path in mtime_before.keys():
        #before = mtime_before.get(path)
        #after = mtime_after.get(path)
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
   #print(f"\ntest_report_changes: Creating ./my_subdir/my_subdirs_subdir/new_json_file.json, mtime is {mtime}")

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

    print("Running test_report_changes", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={mocal.volume_mount_dir: mocal.volume}) 
def test_copy_changes_from():
    '''Create directories locally and on a volume. Copy changes from volume to local. Tests ModalOrLocalDir.copy_changed_files_from()'''

    print("Running test_copy_changes_from", "locally" if modal.is_local() else "remotely", "started")

    if not modal.is_local():
        raise RuntimeError("Cannot run test_copy_changes_from remotely since /tmp is not mounted one the volume")
    
    mdir_on_volume = ModalOrLocalDir(dir_full_path=os.path.join(mocal.volume_mount_dir,"test_copy_changes_from"), modal_or_local=mocal)
    mdir_local = ModalOrLocalDir(dir_full_path="/tmp/test_copy_changes_from")

    # Make sure the temp directories do not exist yet
    mdir_local.remove_file_or_directory(mdir_local.dir_full_path, dne_ok=True)
    mdir_on_volume.remove_file_or_directory(mdir_on_volume.dir_full_path, dne_ok=True)

    # Create some files on the volume:
    # test_copy_changes_from/
    #    ├── a.json
    #    ├── b.json
    #    └── subdir
    #        ├── aa.json
    #        ├── bb.json

    expected_files_relative_path = []
     # Create a.json, b.json, c.json in /test_mnt_dir/test_copy_changes_from
    print("Creating files a.json, b.json, aa.json, bb.json locally")
    for prefix in ["a", "b"]:
        test_json_data = json.loads('{"' + prefix + '": "' + prefix + '_val"}') # e,g. {"a":"a_val"}
        test_file_on_volume_one = prefix + ".json"
        mdir_on_volume.write_json_file(test_file_on_volume_one, test_json_data) 
        assert mdir_on_volume.file_or_dir_exists(test_file_on_volume_one), f"Could not find file created on volume one {test_file_on_volume_one=}"
        expected_files_relative_path.append(test_file_on_volume_one)

    # Create aa.json, bb.json, cc.json in /test_mnt_dir_one/test_copy_file_from_volume_to_local_dir/subdir
    for prefix in ["aa", "bb"]:
        test_json_data = json.loads('{"' + prefix + '": "' + prefix + '_val"}') # e,g. {"aa":"aa_val"}
        test_file_on_volume_one = os.path.join("subdir", prefix + ".json")
        mdir_on_volume.write_json_file(test_file_on_volume_one, test_json_data) 
        assert mdir_on_volume.file_or_dir_exists(test_file_on_volume_one), f"Could not find file created on volume one {test_file_on_volume_one=}"
        expected_files_relative_path.append(test_file_on_volume_one)

    #print("Expected files are\n", "\n".join(expected_files_relative_path))

    print("Copying files a.json, b.json, aa.json, bb.json from volume to local")
    mdir_local.copy_changed_files_from(mdir_on_volume)
    
    # Make sure the expected files got copied to the local directory and change their mtimes to older to get around time difference between local and modal
    now_in_seconds = time()
    for file_relative_path in expected_files_relative_path:
        assert mdir_local.file_or_dir_exists(file_relative_path)

    # Add a file in each directory locally then update the modal volume with them
    # test_copy_changes_from/
    #    ├── a.json
    #    ├── b.json
    #    ├── c.json *new
    #    └── subdir
    #        ├── aa.json
    #        ├── bb.json
    #        ├── cc.json *new

    # Set back the mtimes of the existing files - this should cover any tiem discrpeancies between the modal servers and our machine
    backed_up_mtime = int(now_in_seconds-100)
    for file_relative_path in expected_files_relative_path:
        # Push the mtime back 100s to make sure its "older" than what is on the volume
        os.utime(os.path.join(mdir_local.dir_full_path, file_relative_path), (backed_up_mtime, backed_up_mtime))
        assert mdir_local.get_mtime(file_relative_path) == backed_up_mtime, f"Did not set backed_up_time on {file_relative_path} {backed_up_mtime=} {mdir_local.get_mtime(file_relative_path)=}"
        #print(f"Set mtime for {file_relative_path} to {backed_up_mtime}")

    print("Adding c.json locally")
    mdir_local.write_json_file("c.json", {"c":"c_val"})
    expected_files_relative_path.append("c.json")
    mdir_local.write_json_file("subdir/cc.json", {"cc":"cc_val"})
    expected_files_relative_path.append("subdir/cc.json")

    print("Copying new files (c.json, cc.json) from local to volume") 
    copied_files = mdir_on_volume.copy_changed_files_from(mdir_local)
    
    # Make sure the expected files got copied to the local directory
    for file_relative_path in expected_files_relative_path:
        assert mdir_on_volume.file_or_dir_exists(file_relative_path)

    # Make sure none of the other files changed
    for file_relative_path in expected_files_relative_path:
        if str(file_relative_path).endswith("c.json"): continue # skip c.json and cc.json since they changed
        assert file_relative_path not in copied_files

    # Remove one of the files (a.json) from the volume, and make sure it does not get copied over from local again
    print("Removing a.json from volume")
    mtime = mdir_local.get_mtime("subdir/cc.json")
    mdir_on_volume.remove_file_or_directory("a.json")
    assert not mdir_on_volume.file_or_dir_exists("a.json")

    mdir_on_volume.copy_changed_files_from(mdir_local, datetime.fromtimestamp(mtime))
    assert not mdir_on_volume.file_or_dir_exists("a.json")

    # Change the mtime of one of the files locally (b.json) and make sure it shows up as changed and gets copied
    # PRW todo - this is brittle
    print("Changing the mtime of b.json")
    b_json_mtime_initial_on_volume = mdir_on_volume.get_mtime("b.json")
    b_json_mtime_initial_local = mdir_local.get_mtime("b.json")

    if time() <= b_json_mtime_initial_on_volume:
        sleep(.01)
    if time() <= b_json_mtime_initial_on_volume:
        print(f"{b_json_mtime_initial_on_volume=} {time()=}")
        raise RuntimeError("need to fix time mismatch between volume and local machine")

    # Update the mtime on the local b.json to now and verify it got set
    now_in_seconds = time()
    os.utime(os.path.join(mdir_local.dir_full_path, "b.json"), (b_json_mtime_initial_local, now_in_seconds))
    assert mdir_local.get_mtime('b.json') == now_in_seconds, f"Expected mtime for b.json to be set to {now_in_seconds} but got {mdir_local.get_mtime('b.json')}"
    #print(f"{b_json_mtime_initial_local=}, {mdir_local.get_mtime('b.json')=}")

    # Perform the copy and make sure the b.json on the volume gets updated
    mdir_on_volume.copy_changed_files_from(mdir_local, datetime.fromtimestamp(mtime))
    assert mdir_on_volume.get_mtime("b.json") > b_json_mtime_initial_on_volume, f"Expected mtime for b.json to be greater than {b_json_mtime_initial_on_volume=} but got {mdir_local.get_mtime('b.json')}"
   
    # remove the temp directories
    mdir_local.remove_file_or_directory(mdir_local.dir_full_path)
    mdir_on_volume.remove_file_or_directory(mdir_on_volume.dir_full_path)

    print("Running test_copy_changes_from", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={mocal.volume_mount_dir: mocal.volume})
def test_listdir():
    '''Create some files on the volume, then use listdir to verify it is working properly'''

    mdir_on_volume = ModalOrLocalDir(dir_full_path=os.path.join(mocal.volume_mount_dir,"test_listdir"), modal_or_local=mocal)
   
    # Create some files on the volume:
    # test_copy_changes_from/
    #    ├── a.json
    #    ├── b.json
    #    └── subdir
    #        ├── aa.json
    #        ├── bb.json

    expected_files_relative_path = []
     # Create a.json, b.json, c.json in /test_mnt_dir/test_copy_changes_from
    print("Creating files a.json, b.json, aa.json, bb.json on volume")
    for prefix in ["a", "b"]:
        test_file_on_volume_one = prefix + ".json"
        mdir_on_volume.write_json_file(test_file_on_volume_one, {prefix:1}) 
        assert mdir_on_volume.file_or_dir_exists(test_file_on_volume_one), f"Could not find file created on volume one {test_file_on_volume_one=}"
        expected_files_relative_path.append(test_file_on_volume_one)

    # Create aa.json, bb.json, cc.json in /test_mnt_dir_one/test_copy_file_from_volume_to_local_dir/subdir
    for prefix in ["aa", "bb"]:
        test_file_on_volume_one = os.path.join("subdir", prefix + ".json")
        mdir_on_volume.write_json_file(test_file_on_volume_one, {prefix:2}) 
        assert mdir_on_volume.file_or_dir_exists(test_file_on_volume_one), f"Could not find file created on volume one {test_file_on_volume_one=}"
        expected_files_relative_path.append(test_file_on_volume_one)

    assert sorted(mdir_on_volume.listdir()) == sorted(['subdir', 'b.json', 'a.json']), f"Expected listdir() to return ['subdir', 'b.json', 'a.json'] but got {mdir_on_volume.listdir()}"
    assert mdir_on_volume.listdir('a.json') == ['a.json'], f"Expected listdir() to return ['a.json'] but got {mdir_on_volume.listdir('a.json')}"
    assert sorted(mdir_on_volume.listdir('subdir')) == sorted(['bb.json', 'aa.json']), f"Expected listdir('subdir') to return ['bb.json', 'aa.json'] but got {mdir_on_volume.listdir('subdir')}"
    assert sorted(mdir_on_volume.listdir('subdir', return_full_paths=True)) == sorted(['/test_mnt_dir/test_listdir/subdir/bb.json', '/test_mnt_dir/test_listdir/subdir/aa.json']), f"Expected mdir_on_volume.listdir('subdir', return_full_paths=True) to return ['/test_mnt_dir/test_listdir/subdir/bb.json', '/test_mnt_dir/test_listdir/subdir/aa.json'] but got {mdir_on_volume.listdir('subdir', return_full_paths=True)}"

@app.local_entrypoint()
def main():  
    test_report_changes.local()
    test_report_changes.remote()
    test_copy_changes_from.local()
    test_listdir.local()
