import modal
import json
import os
from modal_or_local import setup_image, ModalOrLocal, copy_file, copy_dir, copy

# Call this with 'modal run tests/test_modal_or_local_dir.py'
# PRW todo - write custom runner for pytest to run this?

image = setup_image()
app = modal.App("test_modal_or_local_dir")

MODAL_VOLUME_NAME_ONE = "test_modal_or_local_copy_volume_one"
MODAL_VOLUME_MOUNT_DIR_ONE = "/test_mnt_dir_one"

MODAL_VOLUME_NAME_TWO = "test_modal_or_local_copy_volume_two"
MODAL_VOLUME_MOUNT_DIR_TWO = "/test_mnt_dir_two"

mocal_for_volume1 = ModalOrLocal(volume_name=MODAL_VOLUME_NAME_ONE, volume_mount_dir = MODAL_VOLUME_MOUNT_DIR_ONE)
mocal_for_volume2 = ModalOrLocal(volume_name=MODAL_VOLUME_NAME_TWO, volume_mount_dir = MODAL_VOLUME_MOUNT_DIR_TWO)
mocal_for_local = ModalOrLocal()

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR_ONE: mocal_for_volume1.volume}) 
def test_copy_local_file_to_volume():
    '''Copy a file from local filesystem to a volume'''

    print("\n\nRunning test_copy_local_to_volume", "locally" if modal.is_local() else "remotely")

    # Create the test file locally
    temp_dir_name = "test_copy_local_file_to_volume_dir"
    temp_dir_local = os.path.join("/tmp", temp_dir_name)
    os.makedirs(temp_dir_local, exist_ok=True)

    test_json_data = json.loads('{"a":1, "b":2}')
    test_file_full_path_local = os.path.join(temp_dir_local, "test.json")
    mocal_for_local.write_json_file(test_file_full_path_local, test_json_data) 

    assert mocal_for_local.file_or_dir_exists(test_file_full_path_local), f"Count not find file created locally {test_file_full_path_local=}"

    # Set the name of the directory that will be used on the volume
    temp_dir_volume1 = os.path.join(mocal_for_volume1.volume_mount_dir, temp_dir_name)

    # Copy the file from the local filesystem to the modal volume, naming the destination file explicitly
    destination_file_full_path = os.path.join(temp_dir_volume1, "named_dest_test.json")
    copy_file(source_mocal=mocal_for_local, source_file_full_path=test_file_full_path_local, \
              destination_mocal=mocal_for_volume1, destination_full_path=destination_file_full_path)
    
    # Make sure the file was copied over and contains the expected info
    assert mocal_for_volume1.file_or_dir_exists(destination_file_full_path), f"Could not find named file copied to volume {destination_file_full_path=}"
    read_data = mocal_for_volume1.read_json_file(destination_file_full_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Copy the file from the local filesystem to the modal volume, naming the destination directory
    destination_directory = os.path.join(temp_dir_volume1)
    copy_file(source_mocal=mocal_for_local, source_file_full_path=test_file_full_path_local, \
              destination_mocal=mocal_for_volume1, destination_full_path=destination_directory)
    
    # Make sure the file was copied over and contains the expected info
    destination_file_full_path = os.path.join(destination_directory, "test.json")
    assert mocal_for_volume1.file_or_dir_exists(destination_file_full_path), f"Could not find file copied to volume dir {destination_file_full_path=}"
    read_data = mocal_for_volume1.read_json_file(destination_file_full_path)
    assert read_data is not None
    assert read_data.get('a') == 1
    assert read_data.get('b') == 2

    # Remove the temporary dirs and verify they are gone
    mocal_for_local.remove_file_or_directory(temp_dir_local)
    mocal_for_volume1.remove_file_or_directory(temp_dir_volume1)
    assert not mocal_for_local.file_or_dir_exists(temp_dir_local)
    assert not mocal_for_volume1.file_or_dir_exists(temp_dir_volume1)
    print("Running test_copy_local_to_volume", "locally" if modal.is_local() else "remotely", "finished")

@app.function(image=image, volumes={MODAL_VOLUME_MOUNT_DIR_ONE: mocal_for_volume1.volume, MODAL_VOLUME_MOUNT_DIR_TWO: mocal_for_volume2.volume}) 
def test_copy_from_volume_to_volume():
    pass
    
@app.local_entrypoint()
def main():  
    test_copy_local_file_to_volume.local()

    