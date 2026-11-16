# ============================================================
# Variables for DICOM Metadata Extractor Datalake
# ============================================================

variable "region" {
  description = "Huawei Cloud region for all resources"
  type        = string
  default     = "cn-north-4"
}

variable "access_key" {
  description = "Huawei Cloud access key (AK)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Huawei Cloud secret key (SK)"
  type        = string
  sensitive   = true
}

variable "project_id" {
  description = "Huawei Cloud project ID"
  type        = string
  default     = ""
}

# --- OBS Buckets ---

variable "obs_input_bucket_name" {
  description = "Name of the OBS bucket where DICOM files are uploaded"
  type        = string
}

variable "obs_output_bucket_name" {
  description = "Name of the OBS bucket where extracted Parquet metadata is stored"
  type        = string
}

# --- VPC / Network ---

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "192.168.1.0/24"
}

# --- CCE Cluster ---

variable "cce_cluster_name" {
  description = "Name of the CCE cluster for batch processing"
  type        = string
  default     = "dicom-batch-cluster"
}

variable "cce_cluster_version" {
  description = "CCE cluster Kubernetes version"
  type        = string
  default     = "v1.28"
}

variable "cce_node_flavor" {
  description = "ECS flavor for CCE worker nodes"
  type        = string
  default     = "s6.large.2"
}

variable "cce_node_count" {
  description = "Initial number of CCE worker nodes"
  type        = number
  default     = 1
}

variable "ssh_key_pair" {
  description = "SSH key pair name for CCE nodes"
  type        = string
  default     = ""
}

# --- FunctionGraph ---

variable "function_app_name" {
  description = "FunctionGraph application name"
  type        = string
  default     = "dicom-parser"
}

variable "function_memory" {
  description = "Memory allocated to the FunctionGraph function (MB)"
  type        = number
  default     = 512
}

variable "function_timeout" {
  description = "Timeout for the FunctionGraph function (seconds)"
  type        = number
  default     = 600
}

variable "function_runtime" {
  description = "Runtime for the FunctionGraph function"
  type        = string
  default     = "Python3.9"
}

variable "max_function_size" {
  description = "Maximum file size (MB) to process in FunctionGraph before forwarding to CCE"
  type        = number
  default     = 500
}

# --- DLI ---

variable "dli_database_name" {
  description = "DLI database name for DICOM metadata"
  type        = string
  default     = "dicom_db"
}

variable "dli_queue_name" {
  description = "DLI queue name for SQL execution"
  type        = string
  default     = "dicom_queue"
}

variable "dli_queue_cu" {
  description = "DLI queue compute units"
  type        = number
  default     = 16
}

variable "dli_table_name" {
  description = "DLI table name for DICOM metadata"
  type        = string
  default     = "dicom_metadata"
}

variable "partition_col" {
  description = "Partition column for the DLI table"
  type        = string
  default     = "study_date"
}

# --- SMN ---

variable "smn_topic_name" {
  description = "SMN topic name for error notifications"
  type        = string
  default     = "dicom-error-notifications"
}

variable "smn_email_endpoint" {
  description = "Email endpoint for SMN error notifications (empty to skip)"
  type        = string
  default     = ""
}

# --- KMS ---

variable "kms_key_alias" {
  description = "KMS key alias for OBS bucket encryption"
  type        = string
  default     = "dicom-datalake-key"
}

# --- Logging ---

variable "log_level" {
  description = "Application log level (INFO or DEBUG)"
  type        = string
  default     = "INFO"
}

# --- Container Image ---

variable "cce_image" {
  description = "Container image for CCE batch processing (SWR URL)"
  type        = string
  default     = ""
}

variable "cce_node_password" {
  description = "Password for CCE nodes (used when no key pair specified). 必填：部署前在运行环境设置 TF_VAR_cce_node_password"
  type        = string
  sensitive   = true
}
