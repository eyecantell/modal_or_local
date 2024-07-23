from modal_or_local import ModalOrLocal
import os

import logging

logger = logging.getLogger("modal_or_local." + __name__)

"""
Provides utility functions for copying files to/from modal volumes and/or the local filesystem.
This is currently pretty rudimentary. Future improvements can include chunking and maintaining timestamps/permissions.
"""


def copy_file(
    source_mocal: ModalOrLocal,
    source_file_full_path: str,
    destination_mocal: ModalOrLocal,
    destination_full_path: str,
):
    """Copy the given file from the source_mocal to the destination_full_path on the destination_mocal.
    The destination_full_path can point to a file (will become the new name) or a directory."""

    if not source_mocal.isfile(source_file_full_path):
        raise RuntimeError(
            f"Could not locate {source_file_full_path=} in {source_mocal=}"
        )

    # Determine what the destination path will be
    if path_is_dir(destination_mocal, destination_full_path):
        # Destination path is a directory, the destination filename will be the same as the source filename
        destination_file_full_path = os.path.join(
            destination_full_path, os.path.basename(source_file_full_path)
        )
    else:
        # The destination path is what was passed
        destination_file_full_path = destination_full_path

    # Read the data from the source file
    file_data_encoded = source_mocal.read_file(source_file_full_path)

    # Write the data to the destination file
    destination_mocal.write_file(destination_file_full_path, file_data_encoded)


def copy_dir(
    source_mocal: ModalOrLocal,
    source_dir_full_path: str,
    destination_mocal: ModalOrLocal,
    destination_full_path: str,
):
    """Copy the given directory (and its contents) from the source_mocal source_dir_full_path to the destination_full_path on the destination_mocal.
    If the destination directory already exists, a copy of the source directory will be placed inside of it.
    If the destination directory does not exist, a copy of the source directory will be created as the destination directory"""

    # Make sure the source path exists and is a directory
    if not source_mocal.isdir(source_dir_full_path):
        raise RuntimeError(
            f"Could not locate dir {source_dir_full_path=} in {source_mocal=}"
        )

    # If the source dir had a slash at the end remove it
    if source_dir_full_path.strip().endswith("/"):
        source_dir_full_path = source_dir_full_path.strip()[:-1]

    # See if the destination directory already exists. If so a copy of the source directory will be placed inside of it
    resolved_destination_full_path = destination_full_path
    if destination_mocal.isdir(destination_full_path):
        resolved_destination_full_path = os.path.join(
            destination_full_path, source_dir_full_path.split("/")[-1]
        )
        # print(f"Destination dir {destination_full_path} already exists so {resolved_destination_full_path=}")

    # print(f"copy_dir: {destination_full_path=}, {resolved_destination_full_path=}")
    for path, dirs, files in source_mocal.walk(source_dir_full_path):
        # print ("copy_dir got entry:", path, dirs, files)
        for file in files:
            file_source_full_path = os.path.join(path, file)
            file_relative_path = file_source_full_path.replace(
                source_dir_full_path, ""
            ).replace("/", "", 1)
            file_destination_full_path = os.path.join(
                resolved_destination_full_path, file_relative_path
            )
            # print(f"Copying {file_source_full_path=} to {file_destination_full_path=}, {file_relative_path=}")
            copy_file(
                source_mocal,
                file_source_full_path,
                destination_mocal,
                file_destination_full_path,
            )
        for dir in dirs:
            # print(f"Making sure {dir=} exists")
            dir_source_full_path = os.path.join(path, dir)
            dir_relative_path = dir_source_full_path.replace(
                source_dir_full_path, ""
            ).replace("/", "", 1)
            dir_destination_full_path = os.path.join(
                resolved_destination_full_path, dir_relative_path
            )
            # print(f"Making sure {dir_relative_path=} exists at {dir_destination_full_path=}, {dir_relative_path=}")
            if not destination_mocal.isdir(dir_destination_full_path):
                destination_mocal.create_directory(dir_destination_full_path)


def copy(
    source_mocal: ModalOrLocal,
    source_path,
    destination_mocal: ModalOrLocal,
    destination_path,
):
    """Copy the source_path on the source volume or filesystem to the target_path on the destination volume or filesystem"""
    if source_mocal.isfile(source_path):
        copy_file(source_mocal, source_path, destination_mocal, destination_path)
    elif source_mocal.isdir(source_path):
        copy_dir(source_mocal, source_path, destination_mocal, destination_path)
    else:
        raise RuntimeError(f"Could not locate path {source_path=} in {source_mocal=}")


def path_is_dir(mocal: ModalOrLocal, full_path: str) -> bool:
    """Return true if the given full_path is a directory on the given mocal or is expected to be (ends with /)"""
    if full_path.endswith("/"):
        return True
    if mocal.isdir(full_path):
        return True
    return False
