import modal
from pathlib import Path
import os
from io import BytesIO
from time import sleep

image = modal.Image.debian_slim()
volume_name = "my_mtime_test_volume"
myvol = modal.Volume.from_name(volume_name, create_if_missing=True)

app = modal.App("test_mtime")


@app.function(image=image, volumes={"/test_mnt_dir": myvol})
def test_mtime():
    if modal.is_local():
        # Create mydir/ directory and mydir/tmp_local.txt
        new_file_path = "mydir/tmp_local.txt"
        with myvol.batch_upload(force=True) as batch:
            batch.put_file(
                BytesIO("file text written with modal batch.put_file()".encode()),
                new_file_path,
            )
        fe = myvol.listdir(new_file_path)[0]
        mydir_fe = myvol.listdir("/")[0]
        print(f"After mydir and tmp_local.txt created, running locally")
        print(f"mtime={fe.mtime} {new_file_path} {fe}")
        print(f"mtime={mydir_fe.mtime} mydir {mydir_fe}")
        sleep(2)

        new_file_path2 = "mydir/tmp_local2.txt"
        with myvol.batch_upload(force=True) as batch:
            batch.put_file(
                BytesIO("file text written with modal batch.put_file()".encode()),
                new_file_path2,
            )

        # Create another file and check the mtime of mydir/ again
        fe = myvol.listdir(new_file_path)[0]
        fe2 = myvol.listdir(new_file_path2)[0]
        mydir_fe = myvol.listdir("/")[0]
        print(f"\nAfter tmp_local2.txt added: ")
        print(f"mtime={fe.mtime} {new_file_path} {fe}")
        print(f"mtime={fe2.mtime} {new_file_path2} {fe2}")
        print(f"mtime={mydir_fe.mtime} mydir {mydir_fe}")

        print(f"{myvol.listdir('/', recursive=True)=}")

        # Cleanup
        myvol.remove_file("mydir", recursive=True)

    else:  # Running remotely, volume will be mounted at /test_mnt_dir
        new_file_full_path = "/test_mnt_dir/mydir/tmp_remote.txt"
        os.makedirs(os.path.dirname(new_file_full_path), exist_ok=True)
        with open(new_file_full_path, "wb") as f:
            f.write("file text written with open()".encode())

        print(f"After mydir and tmp_remote.txt created, running remotely")
        for f in [new_file_full_path, "/test_mnt_dir/mydir"]:
            path = Path(f)
            print(f"mtime={path.stat().st_mtime} {path}")
        sleep(2)

        new_file_full_path2 = "/test_mnt_dir/mydir/tmp_remote2.txt"
        with open(new_file_full_path2, "wb") as f:
            f.write("file text written with open()".encode())

        print(f"\nAfter tmp_remote2.txt added: ")
        for f in [new_file_full_path, new_file_full_path2, "/test_mnt_dir/mydir"]:
            path = Path(f)
            print(f"mtime={path.stat().st_mtime} {path}")

        print(f"{os.listdir('/test_mnt_dir')}")


@app.local_entrypoint()
def main():
    print("Running", __file__, "locally" if modal.is_local() else "remotely")

    # test_mtime.local()
    test_mtime.remote()
