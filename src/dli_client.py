"""
DLI (Data Lake Insight) client for table and partition management.
Provides SQL-based table creation and partition refresh functionality,
for DLI table creation and partition refresh.
"""

import os
import requests
import json
import hashlib
import hmac
import datetime
from logger import get_logger

log = get_logger(__name__)

DLI_DATABASE_NAME = os.environ.get('DLI_DATABASE_NAME', 'dicom_db')
DLI_TABLE_NAME = os.environ.get('DLI_TABLE_NAME', 'dicom_metadata')
DLI_REGION = os.environ.get('DLI_REGION', 'cn-north-4')
DLI_QUEUE_NAME = os.environ.get('DLI_QUEUE_NAME', 'dicom_queue')

# DLI table schema columns for flattened DICOM metadata
TABLE_COLUMNS = [
    ('modality', 'string'),
    ('sopclass_uid', 'string'),
    ('study_time', 'string'),
    ('study_id', 'string'),
    ('series_number', 'string'),
    ('patient_sex', 'string'),
    ('patient_birth_date', 'date'),
    ('patient_age', 'string'),
    ('patient_orientation', 'array<string>'),
    ('patient_weight', 'string'),
    ('image_comments', 'string'),
    ('source_obs_bucket', 'string'),
    ('source_obs_region', 'string'),
    ('source_obs_key', 'string'),
    ('source_obs_archive_path', 'string'),
]

PARTITION_COL = os.environ.get('PARTITION_COL', 'study_date')


def _sign_request(method, url, headers, body=''):
    """Sign a request using HMAC-SHA256 with AK/SK credentials."""
    access_key = os.environ.get('ACCESS_KEY', '')
    secret_key = os.environ.get('SECRET_KEY', '')

    # Build canonical request
    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_headers = '\n'.join(
        f'{k.lower()}:{v.strip()}' for k, v in sorted(headers.items())
    )
    signed_headers = ';'.join(k.lower() for k in sorted(headers.keys()))

    canonical_request = f'{method}\n{url}\n\n{canonical_headers}\n{signed_headers}\n{content_hash}'

    # Create signing key
    date_str = datetime.datetime.utcnow().strftime('%Y%m%d')
    service = 'dli'
    region = DLI_REGION

    k_date = hmac.new(('SDK-HMAC-SHA256-' + date_str).encode(), secret_key.encode(), hashlib.sha256).hexdigest()
    k_region = hmac.new(('SDK-HMAC-SHA256-' + region).encode(), k_date.encode(), hashlib.sha256).hexdigest()
    k_service = hmac.new(('SDK-HMAC-SHA256-' + service).encode(), k_region.encode(), hashlib.sha256).hexdigest()
    k_signing = hmac.new(b'SDK-HMAC-SHA256', k_service.encode(), hashlib.sha256).hexdigest()

    string_to_sign = f'SDK-HMAC-SHA256\n{date_str}T{datetime.datetime.utcnow().strftime("%H%M%S")}Z\n{k_signing}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}'
    signature = hmac.new(k_signing.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

    headers['Authorization'] = (
        f'SDK-HMAC-SHA256 Access={access_key}, '
        f'SignedHeaders={signed_headers}, Signature={signature}'
    )
    return headers


def _execute_sql(sql):
    """Execute a DLI SQL statement via the DLI REST API."""
    endpoint = f'https://dli.{DLI_REGION}.myhuaweicloud.com/v1.0/{os.environ.get("PROJECT_ID", "")}/jobs/submit-job'
    headers = {
        'Content-Type': 'application/json',
        'X-Project-Id': os.environ.get('PROJECT_ID', ''),
    }
    body = json.dumps({
        'sql': sql,
        'queue_name': DLI_QUEUE_NAME,
        'currentdb': DLI_DATABASE_NAME,
    })
    headers = _sign_request('POST', endpoint, headers, body)

    try:
        resp = requests.post(endpoint, headers=headers, data=body, timeout=60)
        result = resp.json()
        log.info(f'DLI SQL executed: {sql[:80]}...')
        return result
    except Exception as e:
        log.error(f'DLI SQL execution failed: {e}')
        raise


def create_table(obs_output_bucket):
    """Create the DLI table if it does not exist."""
    columns_sql = ',\n    '.join(f'{name} {dtype}' for name, dtype in TABLE_COLUMNS)
    sql = f"""
CREATE TABLE IF NOT EXISTS {DLI_DATABASE_NAME}.{DLI_TABLE_NAME} (
    {columns_sql}
)
USING PARQUET
OPTIONS ('compression'='snappy')
PARTITIONED BY ({PARTITION_COL} DATE)
LOCATION 'obs://{obs_output_bucket}/'
"""
    log.info(f'Creating DLI table {DLI_DATABASE_NAME}.{DLI_TABLE_NAME}')
    return _execute_sql(sql)


def repair_partitions():
    """Refresh partitions to discover new Parquet files in OBS."""
    sql = f'MSCK REPAIR TABLE {DLI_DATABASE_NAME}.{DLI_TABLE_NAME}'
    log.info('Refreshing DLI table partitions')
    return _execute_sql(sql)
