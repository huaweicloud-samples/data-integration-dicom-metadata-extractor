"""
DICOM metadata extraction wrapper.
Flattens DICOM tag elements into a dictionary suitable for DataFrame conversion.
This module relies only on pydicom for DICOM parsing.
"""

import os
import datetime
import utils.utils as utils
import utils.tags as tags
from logger import get_logger

PARTITION_COL = os.environ.get('PARTITION_COL', 'study_date')

log = get_logger(__name__)


class DcmFile:
    """Wraps a DICOM source file and collects flattened metadata elements."""

    def __init__(self, source_obs_bucket=None, source_obs_region=None,
                 source_obs_key=None, source_obs_size=0):
        self.img_list = []
        self.source_obs_bucket = source_obs_bucket
        self.source_obs_region = source_obs_region
        self.source_obs_key = source_obs_key
        self.source_obs_size = source_obs_size

    @property
    def size(self):
        return len(self.img_list)

    def __repr__(self):
        return f'obs://{self.source_obs_bucket}/{self.source_obs_key}'

    def update_obs_all(self, source_obs_bucket=None, source_obs_region=None,
                       source_obs_key=None):
        self.source_obs_bucket = source_obs_bucket
        self.source_obs_region = source_obs_region
        self.source_obs_key = source_obs_key

    def append(self, name, img):
        flat = self.transform(name, img)
        self.img_list.append(flat)

    def transform(self, name, img):
        """
        Flatten a pydicom Dataset into a plain dictionary.
        Each DICOM tag keyword becomes a key with its converted value.
        """
        log.debug(f'Flattening {name} to dataset')
        element = {}
        for elem in img:
            try:
                if elem.keyword and not elem.is_empty:
                    elem_val = self.eval_vr_value(elem)
                    element[elem.keyword] = elem_val
                    log.debug(f'Adding tag {elem.keyword}: "{elem_val}" VR: {elem.VR}')
                else:
                    log.info(f'Ignore Tag: {elem.tag} VR: {elem.VR}')
            except Exception as e:
                log.error(f'Unable to process {name}, invalid tag keyword')
                log.error(f'Dump Invalid Elem tag: "{elem.tag}" VR: "{elem.VR}" '
                          f'name: "{elem.name}" keyword: "{elem.keyword}" '
                          f'value: {elem.repval}')
                log.error(e)
                raise
        element['SOURCE_OBS_BUCKET'] = self.source_obs_bucket
        element['SOURCE_OBS_REGION'] = self.source_obs_region
        element['SOURCE_OBS_KEY'] = self.source_obs_key
        element['SOURCE_OBS_ARCHIVE_PATH'] = name

        # Convert snake_case partition column to CamelCase for DICOM keyword match
        cc_partition_col = self.convert_cc(PARTITION_COL)
        if cc_partition_col not in element:
            log.info(f'Missing {PARTITION_COL} adding default value')
            element[cc_partition_col] = datetime.datetime.fromisoformat('1979-01-01').date()

        return element

    def eval_vr_value(self, elem):
        return tags.vr_select(elem)(elem)

    @staticmethod
    def convert_cc(name):
        """Convert snake_case to CamelCase."""
        return ''.join(x.capitalize() for x in name.split('_'))
