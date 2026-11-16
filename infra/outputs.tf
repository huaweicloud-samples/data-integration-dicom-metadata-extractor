# ============================================================
# Outputs for DICOM Metadata Extractor Datalake
# ============================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = huaweicloud_vpc.vpc.id
}

output "obs_input_bucket" {
  description = "Name of the OBS input bucket for DICOM file uploads"
  value       = huaweicloud_obs_bucket.input_bucket.bucket
}

output "obs_output_bucket" {
  description = "Name of the OBS output bucket for Parquet metadata"
  value       = huaweicloud_obs_bucket.output_bucket.bucket
}

output "dli_database_name" {
  description = "DLI database name for querying DICOM metadata"
  value       = huaweicloud_dli_database.dicom_db.name
}

output "dli_queue_name" {
  description = "DLI queue name for SQL execution"
  value       = var.dli_queue_name
}

output "dli_table_name" {
  description = "DLI table name for DICOM metadata"
  value       = var.dli_table_name
}

output "cce_cluster_id" {
  description = "CCE cluster ID for batch processing"
  value       = huaweicloud_cce_cluster.batch_cluster.id
}

output "cce_cluster_name" {
  description = "CCE cluster name"
  value       = huaweicloud_cce_cluster.batch_cluster.name
}

output "function_urn" {
  description = "FunctionGraph function URN"
  value       = huaweicloud_fgs_function.dicom_parser.urn
}

output "function_name" {
  description = "FunctionGraph function name"
  value       = huaweicloud_fgs_function.dicom_parser.name
}

output "obs_trigger_ids" {
  description = "OBS trigger IDs for DICOM file events"
  value = {
    dcm = huaweicloud_fgs_trigger.obs_trigger_dcm.id
    zip = huaweicloud_fgs_trigger.obs_trigger_zip.id
    tar = huaweicloud_fgs_trigger.obs_trigger_tar.id
  }
}

output "smn_topic_urn" {
  description = "SMN topic URN for error notifications"
  value       = huaweicloud_smn_topic.error_topic.topic_urn
}

output "swr_repository" {
  description = "SWR repository path for the DICOM parser container image"
  value       = "${huaweicloud_swr_repository.dicom_parser.organization}/${huaweicloud_swr_repository.dicom_parser.name}"
}

output "kms_key_id" {
  description = "KMS key ID for OBS bucket encryption"
  value       = huaweicloud_kms_key.dicom_key.id
}

output "iam_agency_name" {
  description = "IAM agency name for FunctionGraph delegation"
  value       = huaweicloud_identity_agency.dicom_agency.name
}
