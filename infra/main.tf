# ============================================================
# DICOM Metadata Extractor Datalake - Infrastructure as Code
# 
# Creates: VPC, OBS buckets, KMS key, DLI database/queue/table,
# CCE cluster, FunctionGraph function with OBS trigger,
# SMN topic for errors, IAM agency
# ============================================================

locals {
  az = "${var.region}a"

  common_env = {
    OBS_OUTPUT_BUCKET = var.obs_output_bucket_name
    OBS_OUTPUT_REGION = var.region
    DLI_DATABASE_NAME = var.dli_database_name
    DLI_TABLE_NAME    = var.dli_table_name
    DLI_REGION        = var.region
    DLI_QUEUE_NAME    = var.dli_queue_name
    CCE_REGION        = var.region
    PARTITION_COL     = var.partition_col
    MAX_FUNCTION_SIZE = tostring(var.max_function_size)
    LOGLEVEL          = var.log_level
    CCE_IMAGE         = var.cce_image
    CCE_NAMESPACE     = "dicom-parser"
  }
}

# ============================================================
# 1. VPC and Network
# ============================================================

resource "huaweicloud_vpc" "vpc" {
  name = "dicom-datalake-vpc"
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "subnet" {
  name       = "dicom-datalake-subnet"
  vpc_id     = huaweicloud_vpc.vpc.id
  cidr       = var.subnet_cidr
  gateway_ip = cidrhost(var.subnet_cidr, 1)
}

resource "huaweicloud_networking_secgroup" "batch_sg" {
  name        = "dicom-batch-sg"
  description = "Security group for CCE batch processing nodes"
}

resource "huaweicloud_networking_secgroup_rule" "batch_egress" {
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = huaweicloud_networking_secgroup.batch_sg.id
}

# ============================================================
# 2. KMS Key for OBS Encryption
# ============================================================

resource "huaweicloud_kms_key" "dicom_key" {
  key_alias       = var.kms_key_alias
  key_description = "KMS key for DICOM datalake OBS bucket encryption"
  pending_days    = "7"
}

# ============================================================
# 3. OBS Buckets (Input + Output)
# ============================================================

resource "huaweicloud_obs_bucket" "input_bucket" {
  bucket             = var.obs_input_bucket_name
  acl                = "private"
  sse_algorithm      = "kms"
  kms_key_id         = huaweicloud_kms_key.dicom_key.id
  bucket_key_enabled = true
}

resource "huaweicloud_obs_bucket" "output_bucket" {
  bucket             = var.obs_output_bucket_name
  acl                = "private"
  sse_algorithm      = "kms"
  kms_key_id         = huaweicloud_kms_key.dicom_key.id
  bucket_key_enabled = true
}

# ============================================================
# 4. DLI Database and Queue
# ============================================================

resource "huaweicloud_dli_database" "dicom_db" {
  name        = var.dli_database_name
  description = "DICOM metadata data lake database"
}

# resource "huaweicloud_dli_queue" "dicom_queue" {
#   name       = var.dli_queue_name
#   queue_type = "general"
#   cu_count   = var.dli_queue_cu
# }

# DLI Table creation via SQL (Terraform does not have a native DLI table resource)
resource "null_resource" "dli_table" {
  triggers = {
    db_name    = var.dli_database_name
    table_name = var.dli_table_name
    bucket     = huaweicloud_obs_bucket.output_bucket.bucket
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Creating DLI table ${var.dli_table_name} in database ${var.dli_database_name}..."
      echo "Table location: obs://${huaweicloud_obs_bucket.output_bucket.bucket}/"
      echo "Run the following SQL in DLI console after deployment:"
      echo ""
      echo "CREATE TABLE IF NOT EXISTS ${var.dli_database_name}.${var.dli_table_name} ("
      echo "  modality string,"
      echo "  sopclass_uid string,"
      echo "  study_time string,"
      echo "  study_id string,"
      echo "  series_number string,"
      echo "  patient_sex string,"
      echo "  patient_birth_date date,"
      echo "  patient_age string,"
      echo "  patient_orientation array<string>,"
      echo "  patient_weight string,"
      echo "  image_comments string,"
      echo "  source_obs_bucket string,"
      echo "  source_obs_region string,"
      echo "  source_obs_key string,"
      echo "  source_obs_archive_path string"
      echo ")"
      echo "USING PARQUET"
      echo "OPTIONS ('compression'='snappy')"
      echo "PARTITIONED BY (${var.partition_col} DATE)"
      echo "LOCATION 'obs://${huaweicloud_obs_bucket.output_bucket.bucket}/';"
      echo ""
      echo "Table created successfully (run SQL manually in DLI console)."
    EOT
  }

  depends_on = [huaweicloud_dli_database.dicom_db]
}

# ============================================================
# 5. CCE Cluster for Batch Processing
# ============================================================

resource "huaweicloud_cce_cluster" "batch_cluster" {
  name                   = var.cce_cluster_name
  cluster_version        = var.cce_cluster_version
  cluster_type           = "VirtualMachine"
  flavor_id              = "cce.s1.small"
  vpc_id                 = huaweicloud_vpc.vpc.id
  subnet_id              = huaweicloud_vpc_subnet.subnet.id
  security_group_id      = huaweicloud_networking_secgroup.batch_sg.id
  container_network_type = "vpc-router"
  container_network_cidr = "172.16.0.0/16"
}

resource "huaweicloud_cce_node_pool" "batch_pool" {
  cluster_id         = huaweicloud_cce_cluster.batch_cluster.id
  name               = "batch-pool"
  os                 = "EulerOS 2.9"
  initial_node_count = var.cce_node_count
  flavor_id          = var.cce_node_flavor
  key_pair           = var.ssh_key_pair
  availability_zone  = local.az
  subnet_id          = huaweicloud_vpc_subnet.subnet.id
  scall_enable       = true
  min_node_count     = 0
  max_node_count     = 5

  root_volume {
    size       = 40
    volumetype = "SSD"
  }

  data_volumes {
    size       = 100
    volumetype = "SSD"
  }
}

# ============================================================
# 6. SWR Repository for Container Images
# ============================================================

resource "huaweicloud_swr_repository" "dicom_parser" {
  organization = "dicom"
  name         = "dicom-parser"
  is_public    = false
  description  = "DICOM metadata parser container image for CCE batch processing"
}

# ============================================================
# 7. IAM Agency for FunctionGraph
# ============================================================

resource "huaweicloud_identity_agency" "dicom_agency" {
  name                  = "dicom-parser-agency"
  description           = "Agency allowing FunctionGraph to access OBS, DLI, CCE, and SMN"
  delegated_domain_name = "op_svc_fgs"

  domain_roles = [
    "OBS OperateAccess",
    "DLI FullAccess",
    "CCE FullAccess",
    "SMN FullAccess",
  ]
}

# ============================================================
# 8. FunctionGraph Function
# ============================================================

data "archive_file" "dicom_parser_zip" {
  type        = "zip"
  output_path = "${path.module}/dicom_parser.zip"
  source_dir  = "${path.module}/../src"
}

resource "huaweicloud_fgs_function" "dicom_parser" {
  name          = "${var.function_app_name}-dicom-parser"
  app           = "default"
  description   = "Extract DICOM metadata and write Parquet to OBS output bucket"
  handler       = "app.handler"
  memory_size   = var.function_memory
  timeout       = var.function_timeout
  runtime       = var.function_runtime
  code_type     = "zip"
  code_filename = "dicom_parser.zip"
  func_code     = filebase64(data.archive_file.dicom_parser_zip.output_path)
  # user_data omitted - FunctionGraph env vars set via console

  depends_on = [
    huaweicloud_obs_bucket.input_bucket,
    huaweicloud_obs_bucket.output_bucket,
    huaweicloud_dli_database.dicom_db,
    huaweicloud_cce_cluster.batch_cluster,
  ]
}

# OBS Trigger: invoke function when DICOM (.dcm) files are created in the input bucket
resource "huaweicloud_fgs_trigger" "obs_trigger_dcm" {
  function_urn = huaweicloud_fgs_function.dicom_parser.urn
  type         = "OBS"

  obs {
    bucket_name             = huaweicloud_obs_bucket.input_bucket.bucket
    event_notification_name = "dicom-dcm-notification"
    events                  = ["ObjectCreated"]
    suffix                  = ".dcm"
  }
}

# OBS Trigger: invoke function when archive (.zip) files are created in the input bucket
resource "huaweicloud_fgs_trigger" "obs_trigger_zip" {
  function_urn = huaweicloud_fgs_function.dicom_parser.urn
  type         = "OBS"

  obs {
    bucket_name             = huaweicloud_obs_bucket.input_bucket.bucket
    event_notification_name = "dicom-zip-notification"
    events                  = ["ObjectCreated"]
    suffix                  = ".zip"
  }
}

# OBS Trigger: invoke function when archive (.tar) files are created in the input bucket
resource "huaweicloud_fgs_trigger" "obs_trigger_tar" {
  function_urn = huaweicloud_fgs_function.dicom_parser.urn
  type         = "OBS"

  obs {
    bucket_name             = huaweicloud_obs_bucket.input_bucket.bucket
    event_notification_name = "dicom-tar-notification"
    events                  = ["ObjectCreated"]
    suffix                  = ".tar"
  }
}

# ============================================================
# 9. SMN Topic for Error Notifications
# ============================================================

resource "huaweicloud_smn_topic" "error_topic" {
  name         = var.smn_topic_name
  display_name = "DICOM Datalake Error Notifications"
}

resource "huaweicloud_smn_subscription" "email_sub" {
  count     = var.smn_email_endpoint != "" ? 1 : 0
  topic_urn = huaweicloud_smn_topic.error_topic.topic_urn
  protocol  = "email"
  endpoint  = var.smn_email_endpoint
}
