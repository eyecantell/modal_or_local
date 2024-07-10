import modal
import json
import os
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


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")
    
    test_write_and_read_volume_json_file.local()
    test_write_and_read_volume_json_file.remote()
    test_create_or_remove_dir.local()
    test_create_or_remove_dir.remote()
    test_write_and_read_volume_txt_file.local()
    test_write_and_read_volume_txt_file.remote()
    test_listdir.local()
    test_listdir.remote()
    