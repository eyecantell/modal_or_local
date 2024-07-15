import os
from typing import Any, Dict, List, Optional

import logging
from datetime import datetime

import modal_or_local.logging_config
logger = logging.getLogger("modal_or_local." + __name__)
from warnings import warn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modal_or_local import ModalOrLocal

class ModalOrLocalDir:
    '''Class to do directory things and sync between modal volumes and/or local filesystems'''

    def __init__(self,  dir_full_path : str, modal_or_local : Optional['ModalOrLocal'] = None, volume_name : Optional[str] = None, volume_mount_dir : Optional[str] = None):
        '''Expects dir_full_path and either modal_or_local or (volume_name and volume_mount_dir) to be passed'''
        self.dir_full_path = os.path.normpath(dir_full_path)
        '''Full path of the directory - should include volume mount if on a volume'''

        from modal_or_local import ModalOrLocal

        # Set self.modal_or_local
        if modal_or_local: 
            self.modal_or_local = modal_or_local 
            '''The ModalOrLocal instance designating the modal volume or local filesystem on which our directory lives'''
            if volume_name:
                warn(volume_name + " is ignored when a ModalOrLocal instance (modal_or_local) is passed")
            if volume_mount_dir:
                warn(volume_mount_dir + " is ignored when a ModalOrLocal instance (modal_or_local) is passed")

        elif volume_name and volume_mount_dir:
            self.modal_or_local = ModalOrLocal(volume_name=volume_name, volume_mount_dir=volume_mount_dir)
        elif volume_name or volume_mount_dir:
            raise ValueError(f"Expected both volume_name and volume_mount_dir to be set if either is passed. Got {volume_name=}, {volume_mount_dir=}")
        else:
            # Will be using the local filesystem
            self.modal_or_local = ModalOrLocal()

        # If the directory is on a modal volume, make sure the path includes the volume mount dir
        if self.modal_or_local.volume and not self.modal_or_local.path_starts_with_volume_mount_dir(self.dir_full_path):
            raise RuntimeError(f"ModalOrLocalDir in volume full path expected to start with volume mount dir {self.modal_or_local.volume_name=}, {self.dir_full_path=}")

    def get_full_path(self, filename : str) -> str:
        '''Prepend the directory path to the given filename. File may or may not exist'''
        return os.path.join(self.dir_full_path, filename)
    
    def __str__(self):
        return __class__.__name__ + f"(dir_full_path={self.dir_full_path}, modal_or_local={self.modal_or_local})"
    
    def listdir(self)->List:
        '''Return a (non-recursive) list of files/directories in the given path'''
        self.modal_or_local.listdir(self.dir_full_path)

    def write_json_file(self, json_filename: str, metadata : Any, force: bool = True):
        '''Write a json file to the directory. This will overwrite existing and create any needed parent/sub directories automatically.'''
        return self.modal_or_local.write_json_file(new_json_file_full_path=self.get_full_path(json_filename), metadata=metadata, force=force)
    
    def read_json_file(self, json_filename: str) -> Any:
        '''Load json from the given file'''
        return self.modal_or_local.read_json_file(json_file_full_path=self.get_full_path(json_filename))
    
    def file_or_dir_exists(self, filename: str) -> bool:
        '''Returns true if the passed file or directory exists in our directory'''
        return self.modal_or_local.file_or_dir_exists(full_path=self.get_full_path(filename))
    
    def get_mtime(self, filename: str) -> float:
        '''Returns modified time (in seconds since epoch) of the given file/dir in our directory'''
        return self.modal_or_local.get_mtime(full_path=self.get_full_path(filename))

    def get_FileEntry(self, filename: str) -> float:
        '''Return a modal.volume.FileEntry for the given path (relative to our directory) if it exists.'''
        return self.modal_or_local.get_FileEntry(full_path=self.get_full_path(filename))

    def get_changes(self, since_datetime : Optional[datetime] = None) -> Dict:
        '''Return a list of files that changed in this directory since the given datetime (inclusive)
           Note this tries to give changed directories as well, but the mtimes on the modal volume directories are unreliable (maybe caching?). 
           It will catch new directories but may or may not catch changed ones (ones with new/modified entries)'''

        report = {
            "new_or_modified_files": [],
            "new_or_modified_directories": [],
        }

        if since_datetime is None:
            # Everything is considered new
            #print(f"Walking without since_datetime {self.dir_full_path=}")
            for path, dirs, files in self.modal_or_local.walk(self.dir_full_path):
                #print(f"Walking {path=}, {dirs=}, {files=}")
                for file in files:
                    report["new_or_modified_files"].append(os.path.join(path, file))
                for dir in dirs:
                    report["new_or_modified_directories"].append(os.path.join(path, dir))
        else:
            # Check for changes since the since_datetime
            #print(f"Walking {since_datetime.timestamp()=} {self.dir_full_path=}")
            for path, dirs, files in self.modal_or_local.walk(self.dir_full_path):
                #print(f"Walking {path=}, {dirs=}, {files=}")
                for file in files:
                    full_path = os.path.join(path, file)
                    mtime = self.modal_or_local.get_mtime(full_path)
                    #print(f"  mtime of file {full_path} is {mtime}")
                    if mtime >= since_datetime.timestamp():
                        #print("  adding file", full_path, mtime-since_datetime.timestamp())
                        report["new_or_modified_files"].append(full_path)

                for dir in dirs:
                    full_path = os.path.join(path, dir)
                    mtime = self.modal_or_local.get_mtime(full_path)
                    if mtime >= since_datetime.timestamp():
                        report["new_or_modified_directories"].append(full_path)

        return report