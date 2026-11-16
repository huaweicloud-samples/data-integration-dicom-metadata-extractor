"""
CCE (Cloud Container Engine) client for batch job submission.
Submits Kubernetes Jobs to a CCE cluster for processing large DICOM archives
that exceed the FunctionGraph size limit.
Submits Kubernetes Jobs to a CCE cluster.
"""

import os
import json
import requests
import hashlib
import hmac
import datetime
from logger import get_logger

log = get_logger(__name__)

CCE_REGION = os.environ.get('CCE_REGION', 'cn-north-4')
CCE_CLUSTER_ID = os.environ.get('CCE_CLUSTER_ID', '')
CCE_NAMESPACE = os.environ.get('CCE_NAMESPACE', 'dicom-parser')
CCE_IMAGE = os.environ.get('CCE_IMAGE', '')
MAX_FUNCTION_SIZE = int(os.environ.get('MAX_FUNCTION_SIZE', '500'))


def _sign_request(method, uri, headers, body=''):
    """Sign a request using HMAC-SHA256 with AK/SK credentials."""
    access_key = os.environ.get('ACCESS_KEY', '')
    secret_key = os.environ.get('SECRET_KEY', '')

    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_headers = '\n'.join(
        f'{k.lower()}:{v.strip()}' for k, v in sorted(headers.items())
    )
    signed_headers = ';'.join(k.lower() for k in sorted(headers.keys()))

    canonical_request = f'{method}\n{uri}\n\n{canonical_headers}\n{signed_headers}\n{content_hash}'

    date_str = datetime.datetime.utcnow().strftime('%Y%m%d')
    service = 'cce'
    region = CCE_REGION

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


def submit_job(obs_bucket, obs_key, obs_region, obj_size, env_vars):
    """
    Submit a Kubernetes Job to the CCE cluster for batch processing.
    The job runs the DICOM parser container with the same code as the
    FunctionGraph function but with extended resources.
    """
    if not CCE_CLUSTER_ID:
        raise ValueError('CCE_CLUSTER_ID environment variable is not set')

    job_name = ''.join(c if c.isalnum() else '-' for c in obs_key[:63]).strip('-')
    if not job_name:
        job_name = 'dicom-batch-job'

    # Build environment variables for the container
    container_env = [
        {'name': 'OBS_BUCKET', 'value': obs_bucket},
        {'name': 'OBS_KEY', 'value': obs_key},
        {'name': 'OBS_REGION', 'value': obs_region},
        {'name': 'OBJ_SIZE', 'value': str(obj_size)},
    ]
    for k, v in env_vars.items():
        container_env.append({'name': k, 'value': str(v)})

    # Kubernetes Job manifest
    job_manifest = {
        'apiVersion': 'batch/v1',
        'kind': 'Job',
        'metadata': {
            'name': job_name,
            'namespace': CCE_NAMESPACE,
        },
        'spec': {
            'ttlSecondsAfterFinished': 3600,
            'backoffLimit': 2,
            'template': {
                'spec': {
                    'restartPolicy': 'OnFailure',
                    'containers': [{
                        'name': 'dicom-parser',
                        'image': CCE_IMAGE,
                        'env': container_env,
                        'resources': {
                            'requests': {
                                'cpu': '500m',
                                'memory': '1024Mi',
                            },
                            'limits': {
                                'cpu': '1000m',
                                'memory': '2048Mi',
                            },
                        },
                    }],
                },
            },
        },
    }

    # Submit via CCE Kubernetes API
    api_version = 'v1'
    uri = f'/apis/batch/{api_version}/namespaces/{CCE_NAMESPACE}/jobs'
    endpoint = f'https://{CCE_CLUSTER_ID}.cce.{CCE_REGION}.myhuaweicloud.com{uri}'

    headers = {
        'Content-Type': 'application/json',
        'X-Cluster-ID': CCE_CLUSTER_ID,
    }
    body = json.dumps(job_manifest)
    headers = _sign_request('POST', uri, headers, body)

    try:
        resp = requests.post(endpoint, headers=headers, data=body, timeout=30, verify=False)
        result = resp.json()
        if resp.status_code in (200, 201):
            job_name_result = result.get('metadata', {}).get('name', job_name)
            log.info(f'Submitted CCE batch job: {job_name_result}')
            return {
                'code': 200,
                'job_name': job_name_result,
                'message': f'Forwarded request to CCE batch job: {job_name_result}'
            }
        else:
            log.error(f'CCE job submission failed: {result}')
            raise Exception(f'CCE API error: {result}')
    except Exception as e:
        log.error(f'CCE job submission error: {e}')
        raise
