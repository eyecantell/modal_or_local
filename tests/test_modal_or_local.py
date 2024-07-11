import modal
import json
import os
from typing import Set
from modal_or_local import setup_image, ModalOrLocal

# Call this with 'modal run tests/test_modal_or_local.py'
# PRW todo - write custom runner for pytest to run this?

image = setup_image()
app = modal.App("test_read_notices_in_modal_volume")

MODAL_VOLUME_NAME = "my_modal_test_volume"
MODAL_VOLUME_MOUNT_DIR = "/test_mnt_dir"
mvol = ModalOrLocal(volume_name=MODAL_VOLUME_NAME, volume_mount_dir = MODAL_VOLUME_MOUNT_DIR)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume}) 
def test_write_and_read_volume_json_file():
    '''Write a json file to a modal volume then read it (should be able to run both .local() and .remote())'''

    print("Running test_read_file_from_volume", "locally" if modal.is_local() else "remotely")
    test_json_data = json.loads('{"a":1, "b":2}')

    json_file_full_path = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_write_and_read_volume_json_file.json")

    mvol.write_json_file(json_file_full_path, test_json_data, force=True)

    assert mvol.file_or_dir_exists(json_file_full_path)

    read_data = mvol.read_json_file(json_file_full_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Remove the test file
    mvol.remove_file_or_directory(json_file_full_path)

    # Check that file was actually deleted
    assert not mvol.file_or_dir_exists(json_file_full_path)

    print("Running test_read_file_from_volume", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume}) 
def test_write_and_read_volume_txt_file():
    '''Write a text file to a modal volume then read it (should be able to run both .local() and .remote())'''

    print("Running test_write_and_read_volume_txt_file", "locally" if modal.is_local() else "remotely")

    file_full_path = os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_write_and_read_volume_txt_file.txt")
    text_to_encode = "This is some text"

    mvol.write_file(file_full_path, text_to_encode.encode(), force=True)

    assert mvol.file_or_dir_exists(file_full_path)

    content = mvol.read_file(file_full_path)
    file_text = content.decode('utf-8')

    assert file_text is not None
    assert file_text == text_to_encode

    # Remove the test file
    mvol.remove_file_or_directory(file_full_path)

    # Cannot check that file was actually deleted without a reload of the volume, not sure how to use reload() (get running function error) so commenting out
    assert not mvol.file_or_dir_exists(file_full_path)

    print("Running test_write_and_read_volume_txt_file", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume})
def test_create_or_remove_dir():
    '''Create and remove directory within a volume'''
    for dir_to_create in ["test_create_or_remove_dir_data", "/test_create_or_remove_dir_data/test/a/b/c"]:
        mvol.create_directory(dir_to_create)
        assert mvol.file_or_dir_exists(dir_to_create)
        mvol.remove_file_or_directory(dir_to_create)
        assert not mvol.file_or_dir_exists(dir_to_create)

    # Remove the "test_create_or_remove_dir_data" test dir
    mvol.remove_file_or_directory(os.path.join(MODAL_VOLUME_MOUNT_DIR, "test_create_or_remove_dir_data"))

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume})
def test_listdir():
    '''Create files in a temp directory, then read the list of files in the directory'''
    temp_dir = os.path.join(mvol.volume_mount_dir, "test_listdir_data")
    mvol.create_directory(temp_dir)

    # Add some files to the temp directory on the volume
    filenames_created = []
    for prefix in ["a", "b", "c"]:
        filename = prefix + ".txt"
        filenames_created.append(filename)
        full_path = os.path.join(temp_dir, filename)
        file_text = "this is some text in file " + prefix
        mvol.write_file(full_path, file_text.encode())

    # List the directory and check that all of the expected files are in the list
    found_filenames = mvol.listdir(temp_dir)
    #print(f"{found_filenames=}")
    for filename in filenames_created:
        assert filename in found_filenames, "Expected filename " + filename + " not found in listdir " + str(found_filenames)

    # List the directory with full path option and check that all of the expected files are in the list
    found_filenames_full_path = mvol.listdir(temp_dir, return_full_paths=True)
    #print(f"{found_filenames_full_path=}")
    for filename in filenames_created:
        full_path = os.path.join(temp_dir, filename)
        assert full_path in found_filenames_full_path, "Expected full path " + full_path + " not found in listdir " + str(found_filenames_full_path)

    # Remove the temp test dir
    mvol.remove_file_or_directory(temp_dir)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume})
def test_walk():
    '''Create files/dirs in a temp directory, then walk the list of files in the directory'''
    temp_dir = os.path.join(mvol.volume_mount_dir, "test_walk_data")
    mvol.create_directory(temp_dir)
    second_level_dir = os.path.join(temp_dir, "mydir")
    mvol.create_directory(second_level_dir)

    expected_tuples = []

    # Add some files to the temp directory on the volume
    filenames_created = []
    # Add some files to the temp_dir
    for prefix in ["a", "b", "c"]:
        filename = prefix + ".txt"
        full_path = os.path.join(temp_dir, filename)
        file_text = "this is some text in file " + prefix
        mvol.write_file(full_path, file_text.encode())
        filenames_created.append(filename)
    expected_tuples.append((temp_dir, [os.path.basename(second_level_dir)], filenames_created))

    # Add some files to temp_dir/second_level_dir
    filenames_created = []
    for prefix in ["aa", "bb", "cc"]:
        filename = prefix + ".txt"
        full_path = os.path.join(second_level_dir, filename)
        file_text = "this is some text in file " + prefix
        mvol.write_file(full_path, file_text.encode())
        filenames_created.append(filename)
    expected_tuples.append((second_level_dir, [], filenames_created))

    walk_tuples = []
    for tup in mvol.walk(temp_dir):
        walk_tuples.append(tup)

    print(f"{expected_tuples=}")
    print(f"{walk_tuples=}")

    assert walk_tuples_equal(walk_tuples, expected_tuples)

    # Remove the temp test dir
    mvol.remove_file_or_directory(temp_dir)

def convert_walk_tuple_lists_to_sets(tuples):
    return [(t[0], frozenset(t[1]), frozenset(t[2])) for t in tuples]

def walk_tuples_equal(expected, actual) -> bool:
    from collections import Counter
    expected_converted = convert_walk_tuple_lists_to_sets(expected)
    actual_converted = convert_walk_tuple_lists_to_sets(actual)
    return Counter(expected_converted) == Counter(actual_converted)

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR: mvol.volume})
def test_get_fileEntry():
    '''Create a file and dir on the volume, get mtime of each'''
    temp_dir = os.path.join(mvol.volume_mount_dir, "test_get_fileEntry", "second_level_dir")
    mvol.create_directory(temp_dir)
    json_file_full_path = os.path.join(temp_dir, "mytest.json")
    mvol.write_json_file(json_file_full_path, {"x":1, "y":2})

    for path in ["/", "/test_get_fileEntry", "test_get_fileEntry", temp_dir, json_file_full_path]:
        entry = mvol.get_FileEntry(path)
        print(f"mvol.get_FileEntry({path})=", mvol.get_FileEntry(path), "\n\n")
        
        # entry.path will not have a leading slash, so remove from path before testing equality
        if path != "/" and path.startswith('/'): path=path.replace("/","",1)
        assert entry.path == path, f"Expected '{path}' but got '{entry.path}' from {entry}"

    for path in ["", "/a", "mytest.json", "/second_level_dir"]:
        assert not mvol.get_FileEntry(path), f"Expected None but got {entry}"
    

    # Remove the temp test dir
    #mvol.remove_file_or_directory(temp_dir)

@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    '''test_write_and_read_volume_json_file.local()
    test_write_and_read_volume_json_file.remote()
    test_create_or_remove_dir.local()
    test_create_or_remove_dir.remote()
    test_write_and_read_volume_txt_file.local()
    test_write_and_read_volume_txt_file.remote()
    test_listdir.local()
    test_listdir.remote()
    test_walk.local()
    test_walk.remote()'''
    test_get_fileEntry.local()

    