# Run this with 'modal run scripts/example.py'
#  
import modal
from modal_or_local import setup_image, ModalOrLocal, ModalOrLocalDir

image = setup_image()
app = modal.App("myapp")
mvol1 = ModalOrLocal(volume_name="my_modal_volume1", volume_mount_dir="/volume_mnt_dir1")
mvol2 = ModalOrLocal(volume_name="my_modal_volume2", volume_mount_dir="/volume_mnt_dir2")


@app.function(image=image, volumes={mvol1.volume_mount_dir: mvol1.volume})
def do_stuff_locally():
    # Set local directory to work with.
    mdir_local = ModalOrLocalDir(dir_full_path="/my_local_dir")  
    # Set remote directory to work with
    mdir_on_volume = ModalOrLocalDir(dir_full_path="/my_local_dir", modal_or_local=mvol1)

    # Create a json file on the volume and a text file locally
    mdir_on_volume.write_json_file("created_on_volume.json", {"a":1})
    mdir_local.write_file("created_locally.txt", str("this is some text").encode(), force=True)

    # Copy the files from the volume (created_on_volume.json) that are newer than whats in (or does not exist in) the local directory
    mdir_local.copy_changed_files_from(mdir_on_volume)

    # Give time for the files to age (mtime from modal api is only 1s precision)
    from time import sleep
    sleep(1)

    # Create a new file on the volume
    mdir_on_volume.write_file("newer_file_on_volume.txt",  str("this is some text").encode(), force=True)

    # Get the mtime of the file created on the volume, we will get any new files created since then
    mtime = mdir_on_volume.get_mtime("created_on_volume.json")
    
    # Get the files from the volume that were created after created_on_volume.json was created (this will copy newer_file_on_volume.txt to the local dir)
    from datetime import datetime
    mdir_local.copy_changed_files_from(mdir_on_volume, since_date=datetime.fromtimestamp(mtime))


@app.function(image=image, volumes={mvol1.volume_mount_dir: mvol1.volume, mvol2.volume_mount_dir: mvol2.volume})
def do_stuff_locally_or_remotely():

    mdir_on_volume1 = ModalOrLocalDir(dir_full_path="/my_local_dir_on_volume_one", modal_or_local=mvol1)
    mdir_on_volume2 = ModalOrLocalDir(dir_full_path="/my_local_dir_on_volume_two", modal_or_local=mvol2)

    # Create or remove a directory on the volume - similar to os.mkdirs() and shutil.rmtree()
    mvol1.create_directory("/volume_mnt_dir/my/set/of/created/directories")
    mvol1.remove_file_or_directory("/volume_mnt_dir/my/set/of/created/directories")

    # List items in a directory on the volume
    filenames = mvol1.listdir("/volume_mnt_dir")
    print("filenames in /volume_mnt_dir are", filenames)
    filenames_full_path = mvol1.listdir("/volume_mnt_dir", return_full_paths=True)
    print("filenames with full path in /volume_mnt_dir are", filenames_full_path)

    # Create / overwrite a json file on the volume
    metadata = {"name": "Heather", "age": None}
    json_file_full_path = "/volume_mnt_dir/myfile.json"
    mvol1.write_json_file(json_file_full_path, metadata)

    # Read a json file on the volume
    json_data = mvol1.read_json_file(json_file_full_path)
    print("json_data is", json_data)

    # See tests/test_modal_or_local.py for more examples

@app.local_entrypoint()
def main():
    # The methods in modal_or_local will work for a modal volume whether running locally or remotely
    do_stuff.local()
    do_stuff.remote()
    