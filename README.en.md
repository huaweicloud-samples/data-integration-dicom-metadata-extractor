# dicom-metadata-extractor-datalake — Huawei Cloud Practice

## Table of Contents
- Overview
- Architecture
- Highlights
- Cloud Services
- Prerequisites
- Quick Start
- Deployment
- Usage
- Cleanup
- FAQ
- License
- Contact

## 1. Overview

This project is a **DICOM medical image metadata auto-extraction and querying platform**.
It extracts structured metadata from medical imaging files (DICOM format),
converts them to columnar storage (Parquet), and loads them into a data lake
for downstream querying, analysis, and machine learning.
### Problem Statement
- Medical imaging data volumes are large and complex; manual metadata extraction is inefficient
- Traditional batch processing requires server management, increasing operational overhead
- Metadata is scattered across systems, making unified querying difficult
### Solution Highlights
- **Serverless trigger**: FunctionGraph listens to OBS upload events and auto-triggers processing
- **Elastic batch processing**: Large file batches are handled by CCE container clusters with auto-scaling
- **Data lake storage**: Metadata is written to DLI, supporting standard SQL queries
- **Infrastructure as Code**: All resources deployed via Terraform in one command
---

## 2. Architecture

```
    +-----------+       +-------------------+       +-------------------+
    |  Medical  |       |   FunctionGraph   |       |   OBS Input       |
    |  DICOM    |------>|   (Event-Driven)  |<------|   Bucket          |
    |  Upload   |       +-------------------+       |   (Trigger)       |
    +-----------+               |                   +-------------------+
                                |
                    +-----------+-----------+
                    |                       |
              Small  |                Large  |
                    v                       v
          +-------------------+   +-------------------+
          |   FunctionGraph   |   |    CCE Cluster    |
          |   Direct Process  |   |   (Batch Job)     |
          +-------------------+   +-------------------+
                    |                       |
                    v                       v
          +-------------------+   +-------------------+
          |   OBS Output      |   |   OBS Output      |
          |   (Parquet)       |   |   (Parquet)       |
          +-------------------+   +-------------------+
                    |                       |
                    +-----------+-----------+
                                |
                                v
                    +-------------------+       +-------------------+
                    |   DLI Database    |<------|   DLI Queue       |
                    |   (Metadata Table)|       |   (Flink Import)  |
                    +-------------------+       +-------------------+
                                |
                                v
                    +-------------------+
                    |   SQL Query /     |
                    |   Analytics       |
                    +-------------------+
```
### Data Flow
1. DICOM files uploaded to OBS input bucket
2. OBS event triggers FunctionGraph function
3. Small batches processed directly by FunctionGraph; large batches submitted to CCE
4. Metadata extracted as Parquet and written to OBS output bucket
5. DLI loads Parquet data from OBS into metadata table
6. Users query metadata via DLI SQL
---

## 3. Highlights

Highlights of this practice are described in the Chinese README (`README.md`).

## 4. Cloud Services

The practice uses Huawei Cloud services provisioned by the `infra/` Terraform configurations.

## 5. Prerequisites

See `docs/deployment-guide.md` for the prerequisite checklist.

## 6. Quick Start

### 7.1 Configure Credentials
```bash
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"
export HW_PROJECT_ID="your-project-id"
export HW_REGION="cn-north-4"
```
> AK/SK should be passed via environment variables, not written into .tf files or committed to git.
### 7.2 Deploy Infrastructure
```bash
cd infra/

## 7. Deployment

terraform plan

terraform apply
```
### 7.3 Deploy Function Code
Package `src/` as ZIP and upload to FunctionGraph:
```bash
cd src/
zip -r ../dicom-extractor.zip . -x "Dockerfile" "requirements.txt"
```
Update function code package via console or CLI.
### 7.4 Build and Push CCE Image (Optional)
```bash
cd src/
docker build -t dicom-extractor:latest .

## 8. Usage

Follow the usage/verification steps described in the deployment guide.

## 9. Cleanup

Run `cd infra && terraform destroy` to release resources created by Terraform and avoid residue.

## 10. FAQ

Frequently asked questions are maintained in the deployment guide.

## 11. License

This project is licensed under the [MIT License](LICENSE).
---

## 12. Contact

| **Creator** | `Shangdongd` |
| **Maintainer** | `Shangdongd` |

## Appendix

### DICOM Medical Image Metadata Extractor - Serverless Datalake
> Automated DICOM metadata extraction and querying powered by FunctionGraph + OBS + DLI + CCE
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-%3E%3D1.3-blue.svg)](https://www.terraform.io/)
[![Huawei Cloud](https://img.shields.io/badge/Huawei%20Cloud-Provider-red.svg)](https://www.huaweicloud.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
---

### Table of Contents
---

### 3. Core Components
### 3.1 FunctionGraph (Event Trigger)
- Listens for ObjectCreated events on OBS input bucket
- Determines whether to process directly or submit to CCE based on file count
- Extracts DICOM metadata and converts to Parquet format
- Writes results to OBS output bucket and triggers DLI import
### 3.2 OBS (Object Storage)
- **Input bucket**: Stores raw DICOM files, configured with event notification to trigger FunctionGraph
- **Output bucket**: Stores processed Parquet files for DLI to read
- **Archive bucket**: Stores original files after processing (optional)
### 3.3 CCE (Container Batch Processing)
- When file count exceeds threshold, FunctionGraph submits a batch job to CCE via API
- CCE cluster runs containerized processing code to batch-extract DICOM metadata
- Processed Parquet files are written to OBS output bucket
### 3.4 DLI (Data Lake Insight)
- Creates metadata database and table; table schema maps to DICOM tag fields
- Loads Parquet files from OBS into DLI table via Flink job
- Supports standard SQL queries on metadata
---

### 4. Workflow
```
File Upload     Event Trigger      Routing Decision
  |               |                  |
  v               v                  v
OBS Input   --> FunctionGraph --> File count <= threshold?
  |               |                  |
  |               |        +---------+---------+
  |               |        |YES                |NO
  |               |        v                   v
  |               |   Direct Process      CCE Batch Job
  |               |   (pydicom)           (Containerized)
  |               |        |                   |
  |               |        v                   v
  |               |   Write Parquet        Write Parquet
  |               |   to OBS Output        to OBS Output
  |               |        |                   |
  |               |        +---------+---------+
  |               |                  |
  |               |                  v
  |               |           DLI Flink Import
  |               |                  |
  |               |                  v
  |               |           DLI Metadata Table
  |               |                  |
  |               |                  v
  |               |           SQL Query Ready
```
---

### 5. Directory Structure
```
dicom-metadata-extractor-datalake/
|
|-- infra/                       Terraform infrastructure code
|   |-- versions.tf             Provider version declarations
|   |-- variables.tf            Input variable definitions
|   |-- main.tf                 Main resource orchestration (VPC/OBS/CCE/DLI/FunctionGraph)
|   |-- outputs.tf              Output values
|
|-- src/                         Python source code
|   |-- app.py                  FunctionGraph entry + CCE batch entry
|   |-- dicom_wrapper.py        DICOM metadata extraction (pydicom)
|   |-- obs_wrapper.py          OBS file operations (esdk-obs-python)
|   |-- dli_client.py           DLI table/partition management (SQL API)
|   |-- cce_client.py           CCE job submission (REST API)
|   |-- logger.py               Structured logging
|   |-- utils/
|   |   |-- tags.py             DICOM VR (Value Representation) processing
|   |   |-- utils.py            Archive utility functions
|   |-- requirements.txt        Python dependencies
|   |-- Dockerfile              CCE container build file
|
|-- docs/                        Documentation
|   |-- architecture.md         Architecture design document
|   |-- deployment-guide.md     Deployment guide
|
|
|-- README.md                    Chinese documentation
|-- README.en.md                 English documentation (this file)
|-- LICENSE                      MIT License
```
---

### 6. Requirements
### Development Environment
- Python 3.9+
- Terraform >= 1.0
- Huawei Cloud CLI (hcloud) >= 7.0 (optional, for manual operations)
- Docker (optional, for building CCE container images)
### Huawei Cloud Resources
- FunctionGraph, OBS, CCE, DLI, SMN, VPC services enabled
- AK/SK (Access Key / Secret Key) obtained
- Project ID and Region known
### Python Dependencies
```
esdk-obs-python==3.24.4    # OBS SDK
pydicom==2.4.3             # DICOM parsing
pyarrow==14.0.1            # Parquet read/write
structlog==23.2.0          # Structured logging
requests==2.31.0           # HTTP client
pandas==2.1.4              # Data processing
```
---

### Initialize Terraform
terraform init

### Push to SWR (Software Repository for Containers)
docker tag dicom-extractor:latest swr.cn-north-4.myhuaweicloud.com/your-namespace/dicom-extractor:latest
docker push swr.cn-north-4.myhuaweicloud.com/your-namespace/dicom-extractor:latest
```
### 7.5 Test
```bash

### Upload a DICOM file to OBS input bucket

### FunctionGraph will auto-trigger processing

### Check OBS output bucket for Parquet files

### Query metadata table in DLI
hcloud DLI RunSQL --cli-region=$HW_REGION --sql "SELECT * FROM dicom_metadata LIMIT 10"
```
---

### 8. Configuration
### Terraform Variables
| Variable | Description | Default |
|----------|-------------|---------|
| region | Huawei Cloud region | cn-north-4 |
| hw_access_key | Huawei Cloud AK | (required) |
| hw_secret_key | Huawei Cloud SK | (required) |
| hw_project_id | Project ID | (required) |
| obs_input_bucket | Input bucket name | dicom-input-{random} |
| obs_output_bucket | Output bucket name | dicom-output-{random} |
| obs_archive_bucket | Archive bucket name | dicom-archive-{random} |
| dli_database_name | DLI database name | dicom_db |
| dli_table_name | DLI table name | dicom_metadata |
| dli_queue_name | DLI queue name | dicom_queue |
| cce_cluster_name | CCE cluster name | dicom-processor |
| cce_node_flavor | CCE node flavor | s6.large.2 |
| function_name | FunctionGraph function name | dicom-extractor |
| function_memory | Function memory (MB) | 2048 |
| function_timeout | Function timeout (seconds) | 300 |
| batch_threshold | CCE batch trigger threshold | 50 |
### Runtime Environment Variables
| Variable | Description |
|----------|-------------|
| ACCESS_KEY | Huawei Cloud AK |
| SECRET_KEY | Huawei Cloud SK |
| PROJECT_ID | Project ID |
| REGION | Region |
| OBS_INPUT_BUCKET | Input bucket name |
| OBS_OUTPUT_BUCKET | Output bucket name |
| DLI_DATABASE | DLI database name |
| DLI_TABLE | DLI table name |
| DLI_QUEUE | DLI queue name |
| CCE_CLUSTER_ID | CCE cluster ID |
| BATCH_THRESHOLD | Batch processing threshold |
---

### 9. FunctionGraph
### Entry Function
`app.py` contains `handler(event, context)` as the FunctionGraph entry:
1. Extract file info from OBS event (bucket name, object key)
2. Check if file count exceeds `BATCH_THRESHOLD`
3. If not: directly call `dicom_wrapper` to extract metadata
4. If yes: call `cce_client` to submit CCE batch job
5. Write results to OBS output bucket
6. Trigger DLI data import
### Event Format
FunctionGraph receives OBS events in this format:
```json
{
  "records": [{
    "eventVersion": "1.0",
    "eventSource": "OBS",
    "eventTime": "2026-01-01T00:00:00.000Z",
    "eventName": "ObjectCreated:Put",
    "userIdentity": {"ID": "user-id"},
    "requestParameters": {"sourceIPAddress": "x.x.x.x"},
    "obs": {
      "bucket": {"name": "dicom-input-bucket"},
      "object": {"key": "patient/scan.dcm", "size": 524288}
    }
  }]
}
```
### Timeout & Memory
- Default memory: 2048 MB (pydicom + pyarrow require significant memory)
- Default timeout: 300 seconds (5 minutes)
- Single file processing typically completes in 10-30 seconds
- Large batches handled by CCE, not subject to function timeout
---

### 10. CCE Batch Processing
### Trigger Condition
When the number of files in an OBS upload event exceeds `BATCH_THRESHOLD` (default 50),
FunctionGraph submits a Kubernetes Job to CCE via REST API:
```python
from cce_client import submit_batch_job
job_name = submit_batch_job(
    cluster_id=CCE_CLUSTER_ID,
    image="swr.cn-north-4.myhuaweicloud.com/ns/dicom-extractor:latest",
    file_list=file_keys,
    obs_input=OBS_INPUT_BUCKET,
    obs_output=OBS_OUTPUT_BUCKET,
)
```
### CCE Job Spec
- Uses Kubernetes Job resource (one-shot task)
- Each file processed by a parallel Pod
- `completions` and `parallelism` control concurrency
- Pods auto-exit after processing
### Container Image
Dockerfile based on `python:3.9-slim`, installing:
- pydicom: DICOM file parsing
- esdk-obs-python: OBS SDK
- pyarrow: Parquet read/write
- structlog: Logging
```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
WORKDIR /app
ENTRYPOINT ["python", "app.py", "--batch"]
```
---

### 11. DLI Data Lake
### Database & Table
Terraform creates the following DLI resources:
- **Database**: `dicom_db`
- **Table**: `dicom_metadata` (Parquet format, mapping to OBS output bucket)
- **Queue**: `dicom_queue` (Flink job execution queue)
### Table Schema
```sql
CREATE TABLE dicom_metadata (
    patient_id        STRING,
    patient_name      STRING,
    study_id          STRING,
    study_date        STRING,
    modality          STRING,
    series_number     INT,
    instance_number   INT,
    rows              INT,
    columns           INT,
    bits_allocated    INT,
    pixel_spacing     STRING,
    -- ... more DICOM fields
    source_file       STRING,
    processed_at      TIMESTAMP
) USING PARQUET
LOCATION 'obs://dicom-output-bucket/parquet/';
```
### Data Import
DLI Flink job loads Parquet files from OBS output bucket:
```sql
LOAD DLI TABLE dicom_metadata
FROM OBS 'dicom-output-bucket/parquet/'
WITH FORMAT PARQUET;
```
### Query Examples
```sql
-- Count images by modality
SELECT modality, COUNT(*) AS count
FROM dicom_metadata
GROUP BY modality
ORDER BY count DESC;
-- Query by date range
SELECT * FROM dicom_metadata
WHERE study_date BETWEEN '20260101' AND '20260331';
-- Query all images for a patient
SELECT * FROM dicom_metadata
WHERE patient_id = 'PAT001';
```
---

### 12. OBS Storage Design
### Bucket Structure
```
dicom-input-bucket/             (Input)
  |-- patient-001/
  |   |-- scan-001.dcm
  |   |-- scan-002.dcm
  |-- patient-002/
      |-- scan-001.dcm
dicom-output-bucket/            (Output)
  |-- parquet/
  |   |-- 2026-09-20/
  |   |   |-- batch-001.parquet
  |   |   |-- batch-002.parquet
  |   |-- 2026-09-21/
  |       |-- batch-003.parquet
dicom-archive-bucket/           (Archive, optional)
  |-- processed/
      |-- patient-001/
          |-- scan-001.dcm
          |-- scan-002.dcm
```
### Event Notification
Input bucket configured with OBS event notification to trigger FunctionGraph on new object upload:
- Event type: `ObjectCreated:Put`
- Prefix filter: configurable to process only specific paths
- Suffix filter: configurable to process only `.dcm` files
### Storage Classes
| Bucket | Storage Class | Reason |
|--------|---------------|--------|
| Input | Standard | Frequent access |
| Output | Standard | DLI requires Standard storage |
| Archive | Archive | Low-cost long-term retention |
---

### 13. DICOM Metadata
### Extracted Fields
The following metadata is extracted from DICOM files via pydicom:
| DICOM Tag | Name | VR | Description |
|-----------|------|----|-------------|
| (0010,0020) | PatientID | LO | Patient ID |
| (0010,0010) | PatientName | PN | Patient name |
| (0020,000D) | StudyInstanceUID | UI | Study instance UID |
| (0008,0020) | StudyDate | DA | Study date |
| (0008,0060) | Modality | CS | Modality (CT/MR/XR etc.) |
| (0020,0011) | SeriesNumber | IS | Series number |
| (0020,0013) | InstanceNumber | IS | Instance number |
| (0028,0010) | Rows | US | Image rows |
| (0028,0011) | Columns | US | Image columns |
| (0028,0100) | BitsAllocated | US | Bit depth |
| (0028,0030) | PixelSpacing | DS | Pixel spacing |
### VR (Value Representation) Processing
`utils/tags.py` handles DICOM standard VR types:
- Numeric (US/IS/DS/FL/FD): convert to INT/FLOAT
- String (LO/PN/CS/DA/UI/SH): keep as STRING
- Sequence (SQ): expand to JSON string
- Binary (OB/OW): skip or extract summary
### Parquet Output
Metadata stored in Parquet format for these advantages:
- Columnar storage, high query efficiency
- Built-in compression, saves storage space
- Natively supported by DLI, no extra conversion
- Self-describing schema, easy to extend fields
---

### 14. Monitoring & Alerts
### FunctionGraph Monitoring
- Invocation count, execution duration, error rate
- View function metrics via CES (Cloud Eye Service)
- Alert rule: trigger SMN notification when error rate > 5%
### CCE Monitoring
- Pod status, CPU/memory utilization
- Job completion rate, failure rate
- View via CCE console or CES
### DLI Monitoring
- Query latency, queue resource usage
- Flink job status
- Data import success rate
### Alert Notification
Alerts sent via SMN topic:
```
Trigger --> CES Alert Rule --> SMN Topic --> Email/SMS
```
---

### 15. Security
### Data Security
- DICOM files contain PHI (Protected Health Information); transport uses HTTPS
- OBS buckets default to private access
- Patient names in metadata can be masked before writing to DLI
### Access Control
- Use least-privilege AK/SK (grant only necessary OBS/DLI/CCE/FunctionGraph permissions)
- Use IAM agency instead of plaintext AK/SK for production
- CCE cluster uses RBAC for in-cluster service accounts
### Network Security
- CCE cluster runs inside VPC
- OBS accessed via internal endpoint (reduces latency and traffic cost)
- FunctionGraph accesses internal resources via VPC
### Compliance
> Medical imaging data involves patient privacy. Consult a compliance team
> before production deployment to ensure PHI handling meets HIPAA, GDPR,
> or local regulatory requirements.
---

### 16. Extensibility
### 16.1 Adding New DICOM Fields
1. Edit `src/dli_client.py`, add corresponding column in table schema
2. Update DLI table schema (via Terraform or manual ALTER TABLE)
### Building Container Image
```bash
cd src
docker build -t dicom-extractor:latest .
```
### Contributing
1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add your feature'`
4. Push branch: `git push origin feature/your-feature`
5. Submit a Pull Request
---

### 18. Maintainer
**`Shangdongd`** - Project Maintainer
---
> This project is for learning and reference only. Medical imaging systems involve patient privacy. Consult a compliance team before production deployment.
