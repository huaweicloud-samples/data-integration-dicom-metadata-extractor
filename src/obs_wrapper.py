"""
OBS (Object Storage Service) file wrapper.
Handles downloading files from OBS, detecting file extensions, and extracting
archive contents (.zip, .tar, .tar.gz, .tar.bz2, .tar.xz).
Wraps OBS object download/extraction using the Huawei Cloud OBS SDK.
"""

import os
import tarfile
import zipfile
from logger import get_logger
import utils.utils as utils

# File extensions to skip (not DICOM data)
IGNORE_FILE_EXT = ['.json', '.txt', '.csv']

log = get_logger(__name__)


class ObsFile:
    """Wraps an OBS object for download and archive extraction."""

    def __init__(self, obs_bucket, obs_key, obs_region, size=0):
        self.obs_bucket = obs_bucket
        self.obs_key = obs_key
        self.obs_region = obs_region
        self.size = self.set_size(size)
        self.local_dir = '/tmp'
        self.obs_client = self.generate_obs_client()
        self.file_ext = '.dcm'
        self.file_location = ''
        self.file_list = []

    def __repr__(self):
        return f'{self.obs_region} - obs://{self.obs_bucket}/{self.obs_key}'

    def set_size(self, size):
        try:
            return int(size)
        except Exception as e:
            log.error(e)
            raise

    def generate_obs_client(self):
        """Create an OBS client using the Huawei Cloud OBS SDK."""
        from obs import ObsClient

        access_key = os.environ.get('ACCESS_KEY', '')
        secret_key = os.environ.get('SECRET_KEY', '')
        server = f'https://obs.{self.obs_region}.myhuaweicloud.com'

        client = ObsClient(
            access_key_id=access_key,
            secret_access_key=secret_key,
            server=server
        )
        return client

    def eval_ext(self):
        """Evaluate the file extension from the OBS key."""
        _, ext = os.path.splitext(self.obs_key)
        if ext in IGNORE_FILE_EXT:
            log.info(f'File ext {ext} in IGNORE list, skip process {self}')
        self.set_file_ext(ext)

    def download_file(self):
        """Download the file from OBS to local /tmp directory."""
        try:
            folderpath, _ = os.path.split(self.obs_key)
            os.makedirs(f'{self.local_dir}/{folderpath}', exist_ok=True)
            log.debug(f'Created folder {self.local_dir}/{folderpath}')
            _, ext = os.path.splitext(f'{self.local_dir}/{self.obs_key}')
            log.info(f'Downloading file {self}')

            if self.file_ext == '.dcm':
                # DCM files: download only first 10 MB (metadata header)
                log.debug('Found DCM file type, downloading first 10 MB')
                start = 0
                end = 10000000
                resp = self.obs_client.getObject(
                    self.obs_bucket, self.obs_key,
                    downloadPath=f'{self.local_dir}/{self.obs_key}',
                    rangeStart=start, rangeEnd=end
                )
                if resp.status < 300:
                    log.debug(f'Completed download, partial bytes written')
                else:
                    raise Exception(f'OBS download failed: {resp.errorMessage}')
            else:
                # Full download for archive files
                resp = self.obs_client.downloadFile(
                    self.obs_bucket, self.obs_key,
                    downloadPath=f'{self.local_dir}/{self.obs_key}'
                )
                if resp.status >= 300:
                    raise Exception(f'OBS download failed: {resp.errorMessage}')

            log.info(f'Completed download {self}')
            self.file_location = f'{self.local_dir}/{self.obs_key}'

        except Exception as e:
            log.error(f'Unable to download file obs://{self.obs_bucket}/{self.obs_key} '
                      f'in region {self.obs_region}')
            log.error(e)
            raise

    def set_file_ext(self, ext):
        if ext != '' and len(ext) < 10:
            self.file_ext = ext.lower()
            log.debug(f'Set file extension to be {ext}')
        else:
            default_ext = os.environ.get('DEFAULT_OBS_FILE_EXT', '.dcm')
            log.info(f'Unable to evaluate file ext:{ext}, continue assuming {default_ext}')
            self.file_ext = default_ext

    def get(self):
        """Download and extract the file based on its extension."""
        log.debug(f'Selected file ext {self.file_ext}')
        if self.file_ext in IGNORE_FILE_EXT:
            log.info(f'File ext: {self.file_ext} is IGNORED')
        elif self.file_ext == '.dcm':
            log.debug(f'Select .dcm file type, return file location: {self.file_location}')
            self.download_file()
            self.file_list.append(self.file_location)
        elif self.file_ext == '.zip':
            self.download_file()
            if zipfile.is_zipfile(self.file_location):
                archive = zipfile.ZipFile(self.file_location, 'r')
                self.file_list = utils.unzip(archive)
            else:
                log.error(f'Invalid ZipFile {self} downloaded to {self.file_location}')
                raise
        elif self.file_ext == '.bz2':
            log.info('Select .bz2 file extension, assuming tar.bz2')
            self.download_file()
            archive = tarfile.open(self.file_location, 'r')
            self.file_list = utils.tar(archive)
        elif self.file_ext == '.tar':
            log.info(f'Select .tar file type for processing {self.file_location}')
            self.download_file()
            archive = tarfile.open(self.file_location, 'r')
            self.file_list = utils.tar(archive)
        elif self.file_ext == '.gz':
            log.info('Select .gz file extension, assuming tar.gz')
            self.download_file()
            archive = tarfile.open(self.file_location, 'r')
            self.file_list = utils.tar(archive)
        elif self.file_ext == '.xz':
            log.info('Select .xz file extension, assuming tar.xz')
            self.download_file()
            archive = tarfile.open(self.file_location, 'r')
            self.file_list = utils.tar(archive)
        else:
            log.error(f'Unexpected file extension {self.file_ext}')
            raise Exception(f'{self.file_ext} file extension not supported')
