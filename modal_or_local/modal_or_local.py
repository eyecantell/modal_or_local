import json
import os
import modal
from typing import List, Dict, Any
from io import BytesIO

import logging
import modal_or_local.logging_config
logger = logging.getLogger("modal_or_local." + __name__)

# Class can use either local directory or a modal volumne to store/retrieve files, create directories, etc.
class ModalOrLocal:
    '''Class to allow directory/file calls to be made to a modal volume or a local filesystem'''

    def __init__(self, volume_name : str = None, volume_mount_dir : str = None):
        self.volume_name = volume_name # Name of the volume to be used. If None the local filesystem will be used
        self.volume_mount_dir = volume_mount_dir  # Directory used to mount this volume
        self.volume = None
        if volume_name:
            self.volume = modal.Volume.from_name(volume_name, create_if_missing=True)

        print(f"ModalOrLocal init setting {volume_name=}, {volume_mount_dir=}")


    def read_json_file(self, json_file_full_path : str) -> Any:
        '''Load json from the given file - works on filesystem or on volume'''
        if modal.is_local() and self.volume:
            # Read using the modal volume tools - volume.read_file() apparently expects a "relative" path from / and does not use the volume mount dir in path
            prepped_path = self.path_without_volume_mount_dir(json_file_full_path)
            if prepped_path.startswith('/'): prepped_path=prepped_path.replace("/","",1)
            print(f"Reading {prepped_path=} with read_file() from {self.volume_name=}", "locally" if modal.is_local() else "remotely")
            file_contents = b''
            for chunk in self.volume.read_file(path=prepped_path):
                file_contents += chunk

            metadata = json.loads(file_contents)
        else: 
            # Reading from local filesystem, or reading (from mounted volume) while running remotely
            print(f"Reading {json_file_full_path=} with open()", "locally" if modal.is_local() else "remotely")
            with open(json_file_full_path, 'r') as f:
                metadata = json.load(f)
        return metadata
        
    def write_json_file(self, new_json_file_full_path: str, metadata : Any, force: bool = True):
        '''Write a json file to either the local filesystem or to a volume'''

        if modal.is_local() and self.volume:
            # Reading locally from volume
            prepped_path = self.path_without_volume_mount_dir(new_json_file_full_path)
            prepped_path = os.path.normpath(os.path.join('/', prepped_path))
            logger.debug("write_json_file: prepped path is '%s'", prepped_path)

            json_encoded = json.dumps(metadata, indent=4).encode()
            
            with self.volume.batch_upload(force=force) as batch:
                batch.put_file(BytesIO(json_encoded), prepped_path)
            print("Put json metadata file to", prepped_path)

        else: # Writing to local filesystem or writing to mounted volume while running remotely

            with open(new_json_file_full_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            print("Wrote metadata to", new_json_file_full_path)

    def write_file(self, new_file_full_path: str, encoded_content : Any, force: bool = True):
        '''Write the encoded content to a file in either the local filesystem or to a volume'''

        if modal.is_local() and self.volume:
            # Reading locally from volume
            prepped_path = self.path_without_volume_mount_dir(new_file_full_path)
            prepped_path = os.path.normpath(os.path.join('/', prepped_path))
            logger.debug("write_file: prepped path is '%s'", prepped_path)
            
            with self.volume.batch_upload(force=force) as batch:
                batch.put_file(BytesIO(encoded_content), prepped_path)
            print("Put encoded_content to file at", prepped_path)

        else: # Writing to local filesystem or writing to mounted volume while running remotely

            with open(new_file_full_path, 'w') as f:
                f.write(encoded_content)
            print("Wrote encoded_content to", new_file_full_path)

    def read_file(self, file_full_path : str) -> Any:
        '''Load content from the given file - works on filesystem or on volume'''
        if modal.is_local() and self.volume:
            # Read using the modal volume tools - volume.read_file() apparently expects a "relative" path from / and does not use the volume mount dir in path
            prepped_path = self.path_without_volume_mount_dir(file_full_path)
            if prepped_path.startswith('/'): prepped_path=prepped_path.replace("/","",1)
            print(f"Reading {prepped_path=} with read_file() from {self.volume_name=}", "locally" if modal.is_local() else "remotely")
            file_contents = b''
            for chunk in self.volume.read_file(path=prepped_path):
                file_contents += chunk

        else: 
            # Reading from local filesystem, or reading (from mounted volume) while running remotely
            print(f"Reading {file_full_path=} with open()", "locally" if modal.is_local() else "remotely")
            with open(file_full_path, 'rb') as f:
                file_contents = f.read()
        return file_contents

    def remove_file_or_directory(self, file_or_dir_to_remove_full_path: str):
        '''Remove the given full path from the filesystem or modal volume'''
        # Remove the given file or directory
        if modal.is_local() and self.volume:
            # Remove the file/dir from the volume
            # Make sure there is a leading slash in the case of a bare filename passed
            
            prepped_path = self.path_without_volume_mount_dir(file_or_dir_to_remove_full_path)
            print(f"Removing",prepped_path,"from volume", self.volume_name)
            self.volume.remove_file(prepped_path, recursive=True)
        else:
            # Remove directly from the filesystem or mounted volume
            print(f"Removing from filesystem:",file_or_dir_to_remove_full_path)
            if os.path.isfile(file_or_dir_to_remove_full_path): os.remove(file_or_dir_to_remove_full_path)
            if os.path.isdir(file_or_dir_to_remove_full_path):
                from shutil import rmtree
                rmtree(file_or_dir_to_remove_full_path) 
                

    def file_or_dir_exists(self, full_path) -> bool:
        '''Returns true if the passed file or directory exists in the volume/local filesystem'''
        if modal.is_local() and self.volume:
            prepped_path = self.path_without_volume_mount_dir(full_path)
            filename_wanted = os.path.basename(prepped_path)
            volume_dir = os.path.normpath(os.path.join('/', os.path.dirname(prepped_path)))

            logger.debug(f"file_or_dir_exists: searching for '%s' in '%s' '%s'", filename_wanted, self.volume_name, volume_dir)
            # Look in the volume by iterating
            for f in self.volume.iterdir(volume_dir):
                filename = os.path.basename(f.path)
                logger.debug(f"    file_or_dir_exists: see filename = '%s'", filename)
                if filename == filename_wanted:
                    logger.debug(f"    file_or_dir_exists: found {filename} returning True") 
                    return True     
        else:
            # Look in the local filesystem or mounted volume
            logger.debug(f"file_or_dir_exists: checking for {full_path=}")
            if os.path.isfile(full_path) : return True
            if os.path.isdir(full_path) : return True

        logger.debug(f"    file_or_dir_exists: returning False")
        return False
    
    def path_without_volume_mount_dir(self, full_path: str) -> str:
        '''Return given path without the volume mount dir prepended'''
        # If the give path starts with the volume mount dir, remove the volume mount dir
        norm_full_path = str(os.path.normpath(os.path.join('/', full_path)))
        if norm_full_path.startswith(self.volume_mount_dir):
            path_without_volume_mount_dir = norm_full_path.removeprefix(self.volume_mount_dir)
            return path_without_volume_mount_dir
        return norm_full_path
    
    def listdir(self, dir_full_path : str = None, return_full_paths: bool = False) -> List[str]:
        '''Return a list of files/directories in the given path on either the filesystem or a modal volume'''
        list_to_return = []
        if modal.is_local() and self.volume:
            # Remove the volume mount dir if it was passed as part of the full path
            prepped_path = self.path_without_volume_mount_dir(dir_full_path)
            for f in self.volume.iterdir(prepped_path):
                if return_full_paths:
                    list_to_return.append(str(os.path.normpath(os.path.join('/', self.volume_mount_dir, f.path))))
                else:
                    filename = os.path.basename(f.path)
                    list_to_return.append(filename)
        else:
            # Get the list from the local filesystem
            for filename in sorted(os.listdir(dir_full_path)):
                if return_full_paths:
                    list_to_return.append(str(os.path.normpath(os.path.join('/', dir_full_path, filename))))
                else: 
                    list_to_return.append(filename)
        return list_to_return

    def create_directory(self, dir_full_path : str):
        '''Create a directory (and parent dirs as needed) on the local filesystem or on a volume'''

        if modal.is_local() and self.volume:
            # Create the notice dir on the volume
            # Remove the volume mount dir if it was passed as part of the full path
            prepped_path = self.path_without_volume_mount_dir(dir_full_path)

            # Create a temp directory locally to "put" up to the volume
            temp_dir = os.path.join("/tmp", "tmp_create_directory_" + str(os.getpid()))
            
            print(f"Creating {temp_dir=}")
            os.mkdir(temp_dir)
            temp_file = os.path.join(temp_dir, "tmp.txt")
            with open(temp_file, 'w') as f:
                f.write("This is a temp file for modal.batch_upload to create a dir - it can be safely removed\n")

            print("putting", temp_dir, prepped_path)
            with self.volume.batch_upload(force=True) as batch:
                batch.put_directory(temp_dir, prepped_path)

            print(f"Removing {temp_file=} and {temp_dir=}")
            os.remove(temp_file)
            os.rmdir(temp_dir)

            # Remove the temporary file (tmp.txt) from the volume
            self.volume.remove_file(os.path.join(dir_full_path, os.path.basename(temp_file)))
        else:
            # Creating a directory locally or on a volume while running remotely
            if not os.path.isdir(dir_full_path) : os.makedirs(dir_full_path)









