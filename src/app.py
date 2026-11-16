"""
DICOM Metadata Extractor - Main Application Entry Point

This module serves as the entry point for both:
1. FunctionGraph handler - triggered by OBS event notifications for small DICOM files
2. CCE batch job - processes large DICOM archive files (ZIP, TAR, etc.)

The application:
- Reads DICOM files from an OBS input bucket
- Extracts metadata using pydicom (stop_before_pixels=True for efficiency)
- Converts metadata to Parquet format using pyarrow
- Writes Parquet files to an OBS output bucket, partitioned by study_date
- Refreshes DLI table partitions for query availability
"""

import logging
import json
import os
import re
import pydicom
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from urllib import parse
from utils.utils import getname
from logger import get_logger
from obs_wrapper import ObsFile
from dicom_wrapper import DcmFile
import dli_client
import cce_client

# Environment variables (set by FunctionGraph or CCE job)
OBS_BUCKET = os.environ.get('OBS_BUCKET', None)
OBS_KEY = os.environ.get('OBS_KEY', None)
OBS_REGION = os.environ.get('OBS_REGION', None)
OBJ_SIZE = os.environ.get('OBJ_SIZE', None)
LOCAL_LOCATION = os.environ.get('LOCAL_LOCATION', '/tmp')
OBS_OUTPUT_BUCKET = os.environ.get('OBS_OUTPUT_BUCKET', None)
OBS_OUTPUT_REGION = os.environ.get('OBS_OUTPUT_REGION', 'cn-north-4')
DLI_DATABASE_NAME = os.environ.get('DLI_DATABASE_NAME', 'dicom_db')
DLI_TABLE_NAME = os.environ.get('DLI_TABLE_NAME', 'dicom_metadata')
MAX_FUNCTION_SIZE = int(os.environ.get('MAX_FUNCTION_SIZE', '500'))
PARTITION_COL = os.environ.get('PARTITION_COL', 'study_date')

log = get_logger(__name__)


def transform(name, img, dcm):
    """Append a flattened DICOM dataset to the collection."""
    log.info(f'Flatten {name} structure')
    dcm.append(name, img)


def write_parquet_to_obs(dcm, obs_client):
    """
    Convert the extracted DICOM metadata to a Parquet file and upload to OBS.
    Converts extracted DICOM metadata to Parquet using pyarrow.
    """
    log.debug('Convert data structure to dataframe')
    df = pd.DataFrame.from_dict(dcm.img_list)
    # Drop columns with all None values
    df.dropna(axis=1, how='all', inplace=True)

    # Convert partition column to string for path partitioning
    if PARTITION_COL in df.columns:
        df[PARTITION_COL] = df[PARTITION_COL].astype(str)

    # Write Parquet to local temp file
    temp_file = f'{LOCAL_LOCATION}/dicom_output_{os.getpid()}.parquet'
    table = pa.Table.from_pandas(df, preserve_index=False)

    # Get the study_date partition value (use first row's value)
    if PARTITION_COL in df.columns and len(df) > 0:
        partition_value = str(df[PARTITION_COL].iloc[0])
    else:
        partition_value = '1900-01-01'

    # Write with snappy compression
    pq.write_table(table, temp_file, compression='snappy')
    log.debug(f'Parquet file written locally: {temp_file}')

    # Upload to OBS with partition path
    obs_key = f'{PARTITION_COL}={partition_value}/{os.getpid()}_{hash(dcm.source_obs_key)}.parquet'
    log.info(f'Uploading Parquet to obs://{OBS_OUTPUT_BUCKET}/{obs_key}')

    # Set object tagging with source info (truncated for OBS tag limits)
    tags = parse.urlencode({
        "OBS_BUCKET": dcm.source_obs_bucket[-128:] if dcm.source_obs_bucket else "",
        "OBS_KEY": dcm.source_obs_key[-256:] if dcm.source_obs_key else ""
    })

    resp = obs_client.putFile(
        OBS_OUTPUT_BUCKET,
        obs_key,
        temp_file,
        headers={'x-obs-tagging': tags}
    )

    if resp.status >= 300:
        raise Exception(f'OBS upload failed: {resp.errorMessage}')

    # Clean up local temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)

    log.info(f'Completed output, obs://{OBS_OUTPUT_BUCKET}/{obs_key}')
    return {'paths': f'obs://{OBS_OUTPUT_BUCKET}/{obs_key}'}


def get_obs_client(region=None):
    """Create an OBS client for the output bucket."""
    from obs import ObsClient
    access_key = os.environ.get('ACCESS_KEY', '')
    secret_key = os.environ.get('SECRET_KEY', '')
    server = f'https://obs.{region or OBS_OUTPUT_REGION}.myhuaweicloud.com'
    return ObsClient(access_key_id=access_key, secret_access_key=secret_key, server=server)


def inspect(dcm, ds, obs_client):
    """
    Process a DICOM source file: extract metadata and write Parquet output.
    """
    ds.get()
    if len(ds.file_list) > 0:
        try:
            for img in ds.file_list:
                name = getname(img)
                log.info(f'Processing {ds} - {name}')
                image = pydicom.dcmread(fp=img, stop_before_pixels=True)
                image.remove_private_tags()
                if hasattr(img, 'close'):
                    img.close()
                transform(name, image, dcm)
            log.info(f'Completed DICOM Parsing {dcm}, found {dcm.size} files')
            return write_parquet_to_obs(dcm, obs_client)
        except pydicom.errors.InvalidDicomError as i:
            log.error('Invalid DICOM file')
            log.error(i)
            raise
        except Exception as e:
            log.error(e)
            raise
    else:
        return {"paths": f'No file found, file ext: {ds.file_ext}'}


def handler(event, context):
    """
    FunctionGraph entry point.
    Triggered by OBS event notification when a DICOM file is uploaded.

    Args:
        event: OBS event data containing bucket, key, and size information
        context: FunctionGraph execution context

    Returns:
        dict with code and message indicating processing result
    """
    log.debug('Running in FunctionGraph')
    log.debug(json.dumps(event))

    # Parse OBS event data (FunctionGraph OBS trigger format)
    # The event format from OBS notification contains Records array
    if isinstance(event, dict) and 'Records' in event:
        records = event['Records']
        if isinstance(records, list) and len(records) > 0:
            record = records[0]
            obs_bucket = record.get('obs', {}).get('bucket', {}).get('name', '')
            obs_key = record.get('obs', {}, ).get('object', {}).get('key', '')
            obs_region = record.get('obs', {}).get('bucket', {}).get('region', OBS_REGION or 'cn-north-4')
            obj_size = int(record.get('obs', {}).get('object', {}).get('size', 0))
        else:
            raise ValueError('No records in OBS event')
    elif isinstance(event, dict) and 'obs_bucket' in event:
        # Direct invocation format
        obs_bucket = event['obs_bucket']
        obs_key = event['obs_key']
        obs_region = event.get('obs_region', OBS_REGION or 'cn-north-4')
        obj_size = int(event.get('obj_size', 0))
    else:
        raise ValueError(f'Unrecognized event format: {type(event)}')

    if not obs_bucket or not obs_key:
        raise ValueError(f'Empty OBS input values: bucket={obs_bucket}, key={obs_key}')

    log.info(f'OBS input: obs://{obs_bucket}/{obs_key}, size={obj_size}')

    dcm = DcmFile(
        source_obs_bucket=obs_bucket,
        source_obs_region=obs_region,
        source_obs_key=obs_key,
        source_obs_size=obj_size
    )
    ds = ObsFile(
        obs_bucket=obs_bucket,
        obs_key=obs_key,
        obs_region=obs_region,
        size=obj_size
    )
    ds.eval_ext()

    # Large files: forward to CCE batch processing
    if obj_size > (MAX_FUNCTION_SIZE * 1024 * 1024) and ds.file_ext != '.dcm':
        log.info(f'Filesize greater than {MAX_FUNCTION_SIZE}MB, '
                 f'submit to CCE batch job')
        try:
            env_vars = {
                'OBS_OUTPUT_BUCKET': OBS_OUTPUT_BUCKET or '',
                'OBS_OUTPUT_REGION': OBS_OUTPUT_REGION,
                'DLI_DATABASE_NAME': DLI_DATABASE_NAME,
                'DLI_TABLE_NAME': DLI_TABLE_NAME,
                'LOGLEVEL': logging.getLevelName(log.level),
                'PARTITION_COL': PARTITION_COL,
            }
            result = cce_client.submit_job(
                obs_bucket=obs_bucket,
                obs_key=obs_key,
                obs_region=obs_region,
                obj_size=obj_size,
                env_vars=env_vars
            )
            log.info(f'Forwarded request to CCE: {result}')
            return result
        except Exception as e:
            log.error(e)
            raise

    # Small files: process directly in FunctionGraph
    obs_client = get_obs_client(OBS_OUTPUT_REGION)
    output_location = inspect(dcm, ds, obs_client)

    # Refresh DLI partitions to make new data queryable
    try:
        dli_client.repair_partitions()
    except Exception as e:
        log.warning(f'DLI partition refresh failed (non-fatal): {e}')

    return {
        'code': 200,
        'message': f'Completed job INPUT {dcm}, OUTPUT {output_location["paths"]}'
    }


# CCE Batch Job entry point
if __name__ == '__main__':
    log.debug('Start print ENV variables')
    for item, value in os.environ.items():
        log.debug(f'{item}={value}')
    log.debug('End print ENV variables')

    if (OBS_BUCKET is None or OBS_KEY is None or OBS_REGION is None or OBJ_SIZE is None):
        raise ValueError(
            f'Empty OBS input values: bucket={OBS_BUCKET}, key={OBS_KEY}, '
            f'region={OBS_REGION}, size={OBJ_SIZE}'
        )

    log.info(f'OBS input: obs://{OBS_BUCKET}/{OBS_KEY}, size={OBJ_SIZE}')

    dcm = DcmFile(
        source_obs_bucket=OBS_BUCKET,
        source_obs_region=OBS_REGION,
        source_obs_key=OBS_KEY,
        source_obs_size=OBJ_SIZE
    )
    ds = ObsFile(
        obs_bucket=OBS_BUCKET,
        obs_key=OBS_KEY,
        obs_region=OBS_REGION,
        size=OBJ_SIZE
    )
    ds.eval_ext()

    obs_client = get_obs_client(OBS_OUTPUT_REGION)
    output_location = inspect(dcm, ds, obs_client)

    # Refresh DLI partitions after batch processing
    try:
        dli_client.repair_partitions()
    except Exception as e:
        log.warning(f'DLI partition refresh failed (non-fatal): {e}')

    log.info(
        f'Completed batch job INPUT obs://{OBS_BUCKET}/{OBS_KEY}, '
        f'OUTPUT {output_location["paths"]}'
    )
