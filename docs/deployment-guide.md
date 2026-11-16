# 部署指南

## 1. 部署前准备

### 1.1 检查账号权限

确保您的华为云账号已开通以下服务:

| 服务 | 用途 | 控制台入口 |
|------|------|------------|
| FunctionGraph | 无服务器函数 | 函数工作流控制台 |
| OBS | 对象存储 | 对象存储服务控制台 |
| CCE | 容器引擎 | 云容器引擎控制台 |
| DLI | 数据湖探索 | 数据湖探索控制台 |
| SMN | 消息通知 | 消息通知服务控制台 |
| IAM | 身份管理 | 统一身份认证控制台 |
| VPC | 虚拟私有云 | 虚拟私有云控制台 |

### 1.2 准备 AK/SK

1. 登录华为云控制台
2. 进入"统一身份认证" > "用户" > 您的用户
3. 创建访问密钥 (AK/SK)
4. 安全保存密钥信息

> 安全提示: 请勿将 AK/SK 硬编码到代码或提交到代码仓库。推荐使用环境变量或 IAM 委托。

### 1.3 安装 Terraform

```bash
# 使用华为云镜像下载 (国内加速)
curl -o terraform.zip \
  https://mirrors.huaweicloud.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip

unzip terraform.zip
sudo mv terraform /usr/local/bin/

# 验证安装
terraform version
```

### 1.4 安装 obsutil (可选，用于测试上传)

```bash
# 下载 obsutil
wget https://obs-community.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
tar -xzf obsutil_linux_arm64.tar.gz
cd obsutil_linux_arm64_*
./obsutil version
```

## 2. 部署步骤

### 2.1 获取项目代码

```bash
git clone <repo-url>
cd dicom-metadata-extractor-datalake
```

### 2.2 配置环境变量

```bash
export HW_ACCESS_KEY="您的AccessKey"
export HW_SECRET_KEY="您的SecretKey"
export HW_REGION="cn-north-4"
```

### 2.3 创建变量文件

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars  # 如有示例文件
# 或手动创建
```

编辑 `terraform.tfvars`:

```hcl
region              = "cn-north-4"
input_bucket_name   = "my-org-dicom-input-001"
output_bucket_name  = "my-org-dicom-output-001"
dli_database_name   = "dicom_metadata_db"
dli_queue_name      = "dicom_processing_queue"
cce_cluster_name    = "dicom-batch-cluster"
function_name       = "dicom-metadata-extractor"
function_memory     = 1024
function_timeout    = 600
max_file_size_mb    = 200
smn_topic_name      = "dicom-error-alerts"
```

> 注意: OBS 桶名需全局唯一，建议添加组织前缀或随机后缀。

### 2.4 初始化 Terraform

```bash
terraform init
```

此步骤会下载华为云 Provider 插件。如遇网络问题，可配置华为云镜像源:

```bash
# 在 ~/.terraformrc 中配置
provider "huaweicloud" {
  mirror = "https://mirrors.huaweicloud.com/terraform/"
}
```

### 2.5 预览执行计划

```bash
terraform plan -var-file="terraform.tfvars"
```

仔细检查输出，确认将要创建的资源列表:

- 1 个 VPC + 2 个子网 (公有/私有)
- 2 个安全组
- 2 个 OBS 桶 (输入/输出)
- 1 个 KMS 密钥 (可选)
- 1 个 DLI 数据库 + 表（DLI 队列需在控制台预创建，名称与变量 `dli_queue_name` 一致，默认 `dicom_queue`）
- 1 个 CCE 集群 + 节点池
- 1 个 FunctionGraph 函数 + OBS 触发器
- 1 个 SMN 主题
- 1 个 IAM 委托

### 2.6 执行部署

```bash
terraform apply -var-file="terraform.tfvars"
```

输入 `yes` 确认执行。部署过程约 10-15 分钟 (CCE 集群创建耗时较长)。

### 2.7 记录输出

部署完成后，Terraform 会输出关键信息:

```bash
terraform output
```

记录以下输出值:
- `input_bucket_name`: 输入桶名 (用于上传测试文件)
- `output_bucket_name`: 输出桶名
- `function_urn`: 函数 URN
- `dli_database_name`: DLI 数据库名
- `cce_cluster_id`: CCE 集群 ID
- `smn_topic_urn`: SMN 主题 URN

## 3. 部署后验证

### 3.1 配置 SMN 订阅

1. 进入 SMN 控制台
2. 找到部署创建的主题 (名称为 `terraform.tfvars` 中配置的值)
3. 添加订阅: 邮件 / 短信 / HTTP

### 3.2 上传测试文件

```bash
# 配置 obsutil
./obsutil config -i=$HW_ACCESS_KEY -k=$HW_SECRET_KEY -e=obs.cn-north-4.myhuaweicloud.com

# 上传测试 DICOM 文件
./obsutil cp ./sample.dcm obs://<input_bucket_name>/

# 或使用 OBS 控制台上传
```

### 3.3 检查处理结果

1. **FunctionGraph 控制台**: 查看函数执行日志
2. **DLI 控制台**: 执行 SQL 查询验证元数据写入

```sql
SELECT * FROM dicom_metadata LIMIT 10;
```

3. **OBS 控制台**: 检查输出桶中的处理结果文件

### 3.4 测试错误通知

上传一个非 DICOM 文件 (如 .txt)，验证 SMN 错误通知是否正常推送。

## 4. 更新与维护

### 4.1 更新函数代码

修改 `src/` 目录下的 Python 代码后，重新部署:

```bash
cd infra
terraform apply -var-file="terraform.tfvars"
```

Terraform 会检测代码变更并自动更新函数。

### 4.2 更新 CCE 容器镜像

如修改了 Dockerfile:

```bash
# 在 CCE 集群中重新构建镜像
docker build -t dicom-processor:latest .
# 推送到 SWR 或更新 CCE 工作负载
```

### 4.3 调整资源配置

修改 `terraform.tfvars` 中的参数后执行 `terraform apply`:

- `function_memory`: 调整函数内存
- `function_timeout`: 调整超时时间
- `max_file_size_mb`: 调整 CCE 路由阈值
- CCE 节点规格: 修改 `main.tf` 中节点池配置

## 5. 销毁资源

> 警告: 此操作不可逆! 会删除所有资源及 OBS 桶中的数据。

```bash
# 1. 先清空 OBS 桶 (Terraform 无法删除非空桶)
./obsutil rm -r -f obs://<input_bucket_name>/
./obsutil rm -r -f obs://<output_bucket_name>/

# 2. 执行销毁
cd infra
terraform destroy -var-file="terraform.tfvars"
```

## 6. 常见部署问题

### 6.1 OBS 桶名冲突

```
Error: BucketAlreadyExists
```

**解决**: OBS 桶名全局唯一。修改 `terraform.tfvars` 中的桶名，添加唯一后缀。

### 6.2 CCE 集群创建失败

```
Error: insufficient quota for cce
```

**解决**: 检查账号 CCE 配额，在控制台申请扩容或减小节点规格。

### 6.3 DLI 队列启动失败

```
Error: DLI queue creation timeout
```

**解决**: DLI 队列首次创建需要几分钟启动。检查队列状态，确认可用后重试。

### 6.4 IAM 委托创建失败

```
Error: AccessDenied
```

**解决**: 确认您的 AK/SK 对应用户具备 IAM 管理员权限，或联系主账号管理员代为创建委托。

### 6.5 Terraform Provider 下载失败

```
Error: Failed to download provider
```

**解决**: 配置华为云镜像源 (见 2.4 步骤) 或手动下载 Provider 插件。
