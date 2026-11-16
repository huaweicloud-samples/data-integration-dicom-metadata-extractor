"""
Archive extraction utilities.
Handles ZIP and TAR archive extraction, filtering for valid DICOM files.
Shared utility helpers for the DICOM pipeline.
"""

import os
from logger import get_logger

log = get_logger(__name__)


def unzip(zip_archive):
    """Extract files from a ZIP archive, returning valid DICOM file objects."""
    log.debug(f'Prep to unzip {zip_archive.filename}')
    list_files = []
    for file in zip_archive.infolist():
        if not file.is_dir() and (file.filename.upper().find('DICOMDIR') == -1):
            f = zip_archive.open(file)
            if check_dcm(f):
                list_files.append(zip_archive.open(file))
                log.debug(f'Added "{file.filename}" to process queue')
            else:
                log.info(f'Ignore File in ZipFile, Not Valid DCM file "{file.filename}"')
            f.close()
        else:
            log.info(f'Ignore File in ZipFile, "{file.filename}"')
    return list_files


def tar(tar_archive):
    """Extract files from a TAR archive, returning valid DICOM file objects."""
    log.debug(f'Prep to tar/bz2 {tar_archive.name}')
    list_files = []
    for file in tar_archive.getmembers():
        if file.isfile() and (file.name.upper().find('DICOMDIR') == -1):
            f = tar_archive.extractfile(file)
            if f and check_dcm(f):
                tarfile_obj = tar_archive.extractfile(file)
                tarfile_obj.tarname = file.name
                list_files.append(tarfile_obj)
                log.debug(f'Added {file.name} to process queue')
            else:
                log.info(f'Ignore File in TarFile, Not Valid DCM files "{file.name}"')
            if f:
                f.close()
        else:
            log.info(f'Ignore file-path in TarFile "{file.name}"')
    return list_files


def check_dcm(file):
    """Check if a file has a valid DICOM header (preamble + DICM magic)."""
    file.read(128)
    header = file.read(4)
    return header == b'DICM'


def getname(name):
    """Get a human-readable name from various file-like objects."""
    if hasattr(name, 'tarname'):
        return name.tarname
    elif hasattr(name, 'name'):
        return name.name
    else:
        return os.path.split(name)[1]
