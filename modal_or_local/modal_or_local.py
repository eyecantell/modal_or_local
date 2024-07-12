import json
import os
import modal
from pathlib import Path
from typing import Any, List, Generator, Tuple
from modal.volume import FileEntry, FileEntryType
from io import BytesIO
from grpclib import Status, GRPCError

import logging
import modal_or_local.logging_config
logger = logging.getLogger("modal_or_local." + __name__)

# Class can use either local directory or a modal volume to store/retrieve files, create directories, etc.
class ModalOrLocal:
    '''Class to allow directory/file calls to be made to a modal volume or a local filesystem'''

    def __init__(self, volume_name : str = None, volume_mount_dir : str = None):
        # If volume name is not set, all methods will pull from the local filesystem
        self.volume_name = volume_name # Name of the volume to be used. If None the local filesystem will be used
        self.volume_mount_dir = volume_mount_dir  # Directory used to mount this volume
        self.volume = None
        if volume_name:
            self.volume = modal.Volume.from_name(volume_name, create_if_missing=True)

        #print(f"ModalOrLocal init setting {volume_name=}, {volume_mount_dir=}")

    def __str__(self):
        props = []
        if self.volume_name: props.append(f"volume_name={self.volume_name}")
        if self.volume_mount_dir: props.append(f"volume_mount_dir={self.volume_mount_dir}")
        return __class__.__name__ + "(" + ", ".join(props) + ")"

    
    def read_json_file(self, json_file_full_path : str) -> Any:
        '''Load json from the given file - works on filesystem or on volume'''
        if modal.is_local() and self.volume:
            # Read using the modal volume tools - volume.read_file() apparently expects a "relative" path from / and does not use the volume mount dir in path

            prepped_path = self.path_without_volume_mount_dir(json_file_full_path, volume_mount_dir_required=True)
            if prepped_path.startswith('/'): prepped_path=prepped_path.replace("/","",1)
            #print(f"Reading {prepped_path=} with read_file() from {self.volume_name=}", "locally" if modal.is_local() else "remotely")
            file_contents = b''
            for chunk in self.volume.read_file(path=prepped_path):
                file_contents += chunk

            metadata = json.loads(file_contents)
        else: 
            # Reading from local filesystem, or reading (from mounted volume) while running remotely
            #print(f"Reading {json_file_full_path=} with open()", "locally" if modal.is_local() else "remotely")
            with open(json_file_full_path, 'r') as f:
                metadata = json.load(f)
        return metadata
        
    def write_json_file(self, new_json_file_full_path: str, metadata : Any, force: bool = True):
        '''Write a json file to either the local filesystem or to a volume. This will create any needed parent directories automatically.'''

        if modal.is_local() and self.volume:
            # Reading locally from volume
            
            prepped_path = self.path_without_volume_mount_dir(new_json_file_full_path, volume_mount_dir_required=True)
            prepped_path = os.path.normpath(os.path.join('/', prepped_path))
            #logger.debug("write_json_file: prepped path is '%s'", prepped_path)

            json_encoded = json.dumps(metadata, indent=4).encode()
            
            with self.volume.batch_upload(force=force) as batch:
                batch.put_file(BytesIO(json_encoded), prepped_path)
            #print("Put json metadata file to", prepped_path)

        else: # Writing to local filesystem or writing to mounted volume while running remotely

            with open(new_json_file_full_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            #print("Wrote metadata to", new_json_file_full_path)

    def write_file(self, new_file_full_path: str, encoded_content : Any, force: bool = True):
        '''Write the encoded content to a file in either the local filesystem or to a volume. This will create any needed parent directories automatically.'''

        if modal.is_local() and self.volume:
            # Reading locally from volume
            
            prepped_path = self.path_without_volume_mount_dir(new_file_full_path, volume_mount_dir_required=True)
            prepped_path = os.path.normpath(os.path.join('/', prepped_path))
            #logger.debug("write_file: prepped path is '%s'", prepped_path)
            
            with self.volume.batch_upload(force=force) as batch:
                batch.put_file(BytesIO(encoded_content), prepped_path)
            #print("Put encoded_content to file at", prepped_path)

        else: # Writing to local filesystem or writing to mounted volume while running remotely

            with open(new_file_full_path, 'wb') as f:
                f.write(encoded_content)
            #print("Wrote encoded_content to", new_file_full_path)

    def read_file(self, file_full_path : str) -> Any:
        '''Load content from the given file - works on filesystem or on volume'''
        if modal.is_local() and self.volume:
            # Read using the modal volume tools - volume.read_file() apparently expects a "relative" path from / and does not use the volume mount dir in path
            prepped_path = self.path_without_volume_mount_dir(file_full_path, volume_mount_dir_required=True)
            if prepped_path.startswith('/'): prepped_path=prepped_path.replace("/","",1)
            #print(f"Reading {prepped_path=} with read_file() from {self.volume_name=}", "locally" if modal.is_local() else "remotely")
            file_contents = b''
            for chunk in self.volume.read_file(path=prepped_path):
                file_contents += chunk

        else: 
            # Reading from local filesystem, or reading (from mounted volume) while running remotely
            #print(f"Reading {file_full_path=} with open()", "locally" if modal.is_local() else "remotely")
            with open(file_full_path, 'rb') as f:
                file_contents = f.read()
        return file_contents

    def remove_file_or_directory(self, file_or_dir_to_remove_full_path: str):
        '''Remove the given full path from the filesystem or modal volume'''

        if not self.file_or_dir_exists(file_or_dir_to_remove_full_path):
            raise RuntimeError(f"Cannot remove file that does not exist: '{file_or_dir_to_remove_full_path}'")
        
        # Remove the given file or directory
        if modal.is_local() and self.volume:
            # Remove the file/dir from the volume
            # Make sure there is a leading slash in the case of a bare filename passed
            
            prepped_path = self.path_without_volume_mount_dir(file_or_dir_to_remove_full_path, volume_mount_dir_required=True)
            print(f"Removing {prepped_path} ({file_or_dir_to_remove_full_path}) from volume", self.volume_name)
            self.volume.remove_file(prepped_path, recursive=True)
        else:
            # Remove directly from the filesystem or mounted volume
            #print(f"Removing from filesystem:",file_or_dir_to_remove_full_path)
            if os.path.isfile(file_or_dir_to_remove_full_path): os.remove(file_or_dir_to_remove_full_path)
            if os.path.isdir(file_or_dir_to_remove_full_path):
                from shutil import rmtree
                rmtree(file_or_dir_to_remove_full_path) 
                

    def file_or_dir_exists(self, full_path) -> bool:
        '''Returns true if the passed file or directory exists in the volume/local filesystem'''
        fe = self.get_FileEntry(full_path)
        #print("file_or_dir_exists:", f"{fe=}")
        if fe: return True
        return False
    
    def path_without_volume_mount_dir(self, full_path: str, volume_mount_dir_required: bool = True) -> str:
        '''Return given path without the volume mount dir prepended. Typically needed for the modal.volume utils.'''

        if not full_path:
            raise RuntimeError(f"path_without_volume_mount_dir got blank {full_path=}")
        
        # If the volume mount dir was not the start of the path, path is not legit
        if volume_mount_dir_required and not self.path_starts_with_volume_mount_dir(full_path): 
            raise RuntimeError(f"Expected path to have volume mount dir prepended: {full_path=}, {self.volume_mount_dir=}")
        
        # If the give path starts with the volume mount dir, remove the volume mount dir
        norm_full_path = str(os.path.normpath(os.path.join('/', full_path)))
        #print(f"path_without_volume_mount_dir: {full_path=}, {norm_full_path=}")
        if norm_full_path.startswith(self.volume_mount_dir):
            path_without_volume_mount_dir = norm_full_path.removeprefix(self.volume_mount_dir)
            if path_without_volume_mount_dir == "": return "/"
            return path_without_volume_mount_dir
        return norm_full_path
    
    def path_starts_with_volume_mount_dir(self, full_path: str) -> bool:
        '''Return true if given path has the volume mount dir prepended'''

        norm_full_path = str(os.path.normpath(os.path.join('/', full_path)))
        if norm_full_path.startswith(self.volume_mount_dir): return True
        return False
    
    def listdir(self, dir_full_path : str = None, return_full_paths: bool = False) -> List[str]:
        '''Return a (non-recursive) list of files/directories in the given path on either the filesystem or a modal volume'''
        list_to_return = []
        if modal.is_local() and self.volume:
            # Remove the volume mount dir if it was passed as part of the full path
            prepped_path = self.path_without_volume_mount_dir(dir_full_path, volume_mount_dir_required=True)
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
    
    import os

    def walk(self, dir_full_path: str = None) -> Generator[Tuple[str, list[str], list[str]], None, None]:
        """
        Return a generator of (dirpath, dirs, files) tuples similar to os.walk(). Uses os.walk() if not using a volume and running locally.
        Note dirpath will include the volume_mount_dir if applicable.

        Yields:
            Tuple[str, list[str], list[str]]: A tuple containing the current directory path,
            a list of subdirectory names, and a list of filenames.
        """
        if modal.is_local() and self.volume:
            # Remove the volume mount dir if it was passed as part of the full path
            prepped_path = self.path_without_volume_mount_dir(dir_full_path, volume_mount_dir_required=True)

            # Add the entries from the given directory
            dirpath = dir_full_path
            dirnames = []
            filenames = []

            for entry in self.volume.iterdir(prepped_path, recursive=False):
                print(f"walk {entry=}, {prepped_path=}")
                if entry.type == FileEntryType.DIRECTORY:
                    dirnames.append(os.path.basename(entry.path))
                else:
                    filenames.append(os.path.basename(entry.path))

            print("yielding", (os.path.join(self.volume_mount_dir, dirpath), dirnames, filenames))
            yield (os.path.join(self.volume_mount_dir, dirpath), dirnames, filenames)

            # Walk the other directories found
            for dir_to_walk in sorted(dirnames):
                yield from self.walk(os.path.join(dir_full_path, dir_to_walk))
        else:
            # Get the list from the local filesystem
            yield from os.walk(dir_full_path)

    def create_directory(self, dir_full_path : str):
        '''Create a directory (and parent dirs as needed) on the local filesystem or on a volume'''

        if modal.is_local() and self.volume:
            # Create the notice dir on the volume
            # Remove the volume mount dir if it was passed as part of the full path
            prepped_path = self.path_without_volume_mount_dir(dir_full_path, volume_mount_dir_required=True)

            # Create a temp directory (with a temp file) locally to "directory_put" up to the volume
            temp_dir = os.path.join("/tmp", "tmp_create_directory_" + str(os.getpid()))
            
            #print(f"create_directory: Creating {temp_dir=}")
            os.mkdir(temp_dir)
            temp_file = os.path.join(temp_dir, "tmp.txt")
            with open(temp_file, 'w') as f:
                f.write("This is a temp file for modal.batch_upload to create a directory - it can be safely removed\n")

            #print("putting", temp_dir, prepped_path)
            with self.volume.batch_upload(force=True) as batch:
                #print(f"create_directory: Putting {temp_dir=}, {prepped_path=}")
                batch.put_directory(temp_dir, prepped_path)

            #print(f"Removing local {temp_file=} and {temp_dir=}")
            os.remove(temp_file)
            os.rmdir(temp_dir)

            # Remove the temporary file (tmp.txt) from the volume
            temp_file_in_volume = os.path.join(dir_full_path, os.path.basename(temp_file))
            #print(f"Removing from volume {temp_file_in_volume=}")
            self.remove_file_or_directory(temp_file_in_volume)
        else:
            # Creating a directory locally or on a volume while running remotely
            if not os.path.isdir(dir_full_path) : os.makedirs(dir_full_path)

    
    def get_mtime(self, full_path) -> int:
        '''Returns most recent modified time (in seconds) of the given file/dir'''
        fe = self.get_FileEntry(full_path)
        if fe is None: return None
        return fe.mtime
        
    def get_FileEntry(self, full_path) -> FileEntry:
        '''Return a modal.volume.FileEntry for the given path if it exists.'''

        if not full_path:
            raise RuntimeError(f"get_FileEntry was passed a blank full_path {full_path=}")

        if modal.is_local() and self.volume:
            # Get the file info from the volume

            prepped_path = self.path_without_volume_mount_dir(full_path, volume_mount_dir_required=True)
            # volume.iterdir expects paths to be relative from "/", so remove any leading slash
            if prepped_path != "/" and prepped_path.startswith('/'): prepped_path=prepped_path.replace("/","",1)
            #print(f"{prepped_path=}")

            # Modal does not make getting a FileEntry for '/' available, so return a placeholder
            if prepped_path == "/": 
                return FileEntry(path=self.volume_mount_dir.replace("/","",1),type=FileEntryType.DIRECTORY, mtime=0, size=0)

            # If the full path is a file, volume.listdir() will return a single FileEntry
            # Its also possible that there is a single file in the full_path directory, so we double check the path
            
            try:
                entries = self.volume.listdir(prepped_path)
            except GRPCError as e:
                if e.status == Status.NOT_FOUND:
                    # The path does not exist on the volume
                    return None
                else:
                    raise
            
            #print(f"get_FileEntry: Checking for file '{prepped_path}' got ", f"{entries=}")
            volume_mount_dir_no_lead_slash = self.volume_mount_dir.replace("/","",1)
            if len(entries) == 1 and entries[0].path == prepped_path: 
                entry = entries[0]
                # Add the volume mount directory back onto the start of path and return (note the entry itself is immutable)
                return FileEntry(path=os.path.join(volume_mount_dir_no_lead_slash, entry.path), type=entry.type, mtime=entry.mtime, size=entry.size)

            # Presuming full_path is a directory, list its parent to get the FileEntry
            parent_dir = str(Path(prepped_path).parent)
            if parent_dir == ".": parent_dir = "/"
            if parent_dir != "/" and parent_dir.startswith('/'): parent_dir=parent_dir.replace("/","",1)
            #print(f"{parent_dir=}")
            
            #print("get_FileEntry: Checking for dir got ", self.volume.listdir(parent_dir))
            for entry in self.volume.listdir(parent_dir):
                if entry.path == prepped_path: 
                    # Add the volume mount directory back onto the start of path and return (note the entry itself is immutable)
                    return FileEntry(path=os.path.join(volume_mount_dir_no_lead_slash, entry.path), type=entry.type, mtime=entry.mtime, size=entry.size)

            # Did not find a file or directory for the given path
            return None

        else:
            # Get the file info from the local filesystem
            print(f"Getting FileEntry for {full_path=} from filesystem")
            path = Path(full_path)
            if not path.exists(): return False
            entry_type = FileEntryType.FILE if path.is_file() else FileEntryType.DIRECTORY if path.is_dir() else None
            path_to_return = str(path)
            if path_to_return.startswith("/"): path_to_return=path_to_return.replace("/","",1)
            return FileEntry(path=path_to_return, type=entry_type, mtime=path.stat().st_mtime, size=path.stat().st_size)

    def isdir(self, full_path) -> bool:
        fe = self.get_FileEntry(full_path)
        #print("file_or_dir_exists:", f"{fe=}")
        if fe.type == FileEntryType.DIRECTORY: return True
        return False
    
    def isfile(self, full_path) -> bool:
        fe = self.get_FileEntry(full_path)
        #print("file_or_dir_exists:", f"{fe=}")
        if fe.type == FileEntryType.FILE: return True
        return False




