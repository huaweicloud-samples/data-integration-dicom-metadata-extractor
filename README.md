# DICOM 医疗影像元数据无服务器数据湖

# DICOM 医疗影像元数据无服务器数据湖
> 基于 华为云 FunctionGraph + OBS + CCE + DLI 构建的医疗影像元数据自动提取与查询平台
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Terraform](https://img.shields.io/badge/Terraform->=1.0-blue.svg)](https://developer.hashicorp.com/terraform)
[![Huawei Cloud](https://img.shields.io/badge/Huawei%20Cloud-FunctionGraph%20%7C%20OBS%20%7C%20CCE%20%7C%20DLI-red.svg)](https://www.huaweicloud.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
---

## 目录
- [1. 简介](#1-简介)
- [2. 架构说明](#2-架构说明)
- [3. 架构图](#3-架构图)
- [4. 方案亮点](#4-方案亮点)
- [5. 涉及云服务](#5-涉及云服务)
- [6. 前置条件](#6-前置条件)
- [7. 快速开始](#7-快速开始)
- [8. 分步部署](#8-分步部署)
- [9. 使用方法](#9-使用方法)
- [10. 清理资源](#10-清理资源)
- [11. 详细说明](#11-详细说明)
- [12. 依赖](#12-依赖)
- [13. FAQ](#13-faq)
- [14. 贡献指南](#14-贡献指南)
- [15. 许可证](#15-许可证)
- [16. 联系方式](#16-联系方式)

## 1. 简介

本项目是一个 **DICOM 医疗影像元数据自动提取与查询平台**，将医疗影像文件（DICOM 格式）
中的结构化元数据提取出来，转化为列式存储格式（Parquet），并加载到数据湖中，
便于后续的查询、分析和机器学习。
### 解决的问题
- 医疗影像数据量大、格式复杂，手动提取元数据效率低下
- 传统批处理方案需要管理服务器，运维成本高
- 元数据分散在不同系统中，难以统一查询和分析
### 方案特点
- **无服务器触发**: FunctionGraph 监听 OBS 上传事件，自动触发处理流程
- **弹性批处理**: 大批量文件通过 CCE 容器集群处理，按需弹性伸缩
- **数据湖存储**: 元数据写入 DLI，支持标准 SQL 查询
- **基础设施即代码**: 全部资源通过 Terraform 一键部署
---

## 2. 架构说明

```
    +-----------+       +-------------------+       +-------------------+
    |  医疗影像  |       |   FunctionGraph   |       |     OBS 输入桶     |
    |  DICOM    |------>|   (事件触发函数)   |<------|   (上传触发器)     |
    |  文件上传  |       +-------------------+       +-------------------+
    +-----------+               |
                                |
                    +-----------+-----------+
                    |                       |
           数量少    |          数量大        |
                    v                       v
          +-------------------+   +-------------------+
          |   FunctionGraph   |   |    CCE 集群       |
          |   直接处理         |   |   (容器批处理)     |
          +-------------------+   +-------------------+
                    |                       |
                    |                       |
                    v                       v
          +-------------------+   +-------------------+
          |    OBS 输出桶     |   |    OBS 输出桶     |
          |   (Parquet 文件)  |   |   (Parquet 文件)  |
          +-------------------+   +-------------------+
                    |                       |
                    +-----------+-----------+
                                |
                                v
                    +-------------------+       +-------------------+
                    |     DLI 数据库    |<------|   DLI 队列        |
                    |   (元数据表)      |       |   (Flink 导入)    |
                    +-------------------+       +-------------------+
                                |
                                v
                    +-------------------+
                    |   SQL 查询 / 分析  |
                    +-------------------+
```
### 数据流说明
1. DICOM 文件上传到 OBS 输入桶
2. OBS 事件触发 FunctionGraph 函数
3. 小批量文件由 FunctionGraph 直接处理；大批量文件提交到 CCE 批处理
4. 元数据提取为 Parquet 格式，写入 OBS 输出桶
5. DLI 从 OBS 加载 Parquet 数据到元数据表
6. 用户通过 DLI SQL 查询元数据
---

## 3. 架构图

（架构图见 `docs/architecture.md`）

## 4. 方案亮点

（见 `docs/` 目录）

## 5. 涉及云服务

本实践涉及 OBS、CCE、DLI、DWS、DDS、APIG、FunctionGraph、SMN 等华为云服务；具体清单以 `infra/` 中 Terraform 资源为准。

## 6. 前置条件

### 开发环境
- Python 3.9+
- Terraform >= 1.0
- Huawei Cloud CLI (hcloud) >= 7.0 (可选，用于手动操作)
- Docker (可选，用于构建 CCE 容器镜像)
### 华为云资源
- 已开通 FunctionGraph、OBS、CCE、DLI、SMN、VPC 服务
- 已获取 AK/SK (Access Key / Secret Key)
- 已知项目 ID (Project ID) 和区域 (Region)
### Python 依赖
```
esdk-obs-python==3.24.4    # OBS SDK
pydicom==2.4.3             # DICOM 解析
pyarrow==14.0.1            # Parquet 读写
structlog==23.2.0          # 结构化日志
requests==2.31.0           # HTTP 客户端
pandas==2.1.4              # 数据处理
```
---

## 7. 快速开始

### 7.1 配置凭证
```bash
export HW_ACCESS_KEY="your-access-key"
export HW_SECRET_KEY="your-secret-key"
export HW_PROJECT_ID="your-project-id"
export HW_REGION="cn-north-4"
```
> AK/SK 建议通过环境变量传入，不要写入 .tf 文件或提交到代码仓库。
### 7.2 部署基础设施
```bash
cd infra/
# 初始化 Terraform
terraform init
# 查看部署计划
terraform plan
# 执行部署
terraform apply
```
### 7.3 部署处理函数
将 `src/` 目录打包为 ZIP 上传到 FunctionGraph:
```bash
cd src/
zip -r ../dicom-extractor.zip . -x "Dockerfile" "requirements.txt"
```
通过控制台或 CLI 更新函数代码包。
### 7.4 构建并推送 CCE 镜像 (可选)
```bash
cd src/
docker build -t dicom-extractor:latest .
# 推送到 SWR (容器镜像服务)
docker tag dicom-extractor:latest swr.cn-north-4.myhuaweicloud.com/your-namespace/dicom-extractor:latest
docker push swr.cn-north-4.myhuaweicloud.com/your-namespace/dicom-extractor:latest
```
### 7.5 测试
```bash
# 上传一个 DICOM 文件到 OBS 输入桶
# FunctionGraph 将自动触发处理
# 检查 OBS 输出桶是否有 Parquet 文件
# 在 DLI 中查询元数据表
hcloud DLI RunSQL --cli-region=$HW_REGION --sql "SELECT * FROM dicom_metadata LIMIT 10"
```
---

## 8. 分步部署

（见 `docs/` 目录）

## 9. 使用方法

（见 `docs/` 目录）

## 10. 清理资源

运行 `cd infra && terraform destroy` 释放由 Terraform 创建的资源，避免资源残留。

## 11. 详细说明

### 3.1 FunctionGraph (事件触发)
- 监听 OBS 输入桶的 ObjectCreated 事件
- 判断文件数量，决定直接处理还是提交 CCE 批处理
- 提取 DICOM 元数据并转换为 Parquet 格式
- 将结果写入 OBS 输出桶并触发 DLI 导入
### 3.2 OBS (对象存储)
- **输入桶**: 存储原始 DICOM 文件，配置事件通知触发 FunctionGraph
- **输出桶**: 存储处理后的 Parquet 文件，供 DLI 读取
- **归档桶**: 存储处理完成后的原始文件归档（可选）
### 3.3 CCE (容器批处理)
- 当单次上传文件数量超过阈值时，FunctionGraph 通过 API 向 CCE 提交批处理任务
- CCE 集群运行容器化处理程序，批量提取 DICOM 元数据
- 处理完成后将 Parquet 文件写入 OBS 输出桶
### 3.4 DLI (数据湖探索)
- 创建元数据数据库和表，表 schema 对应 DICOM 标签字段
- 通过 Flink 作业从 OBS 加载 Parquet 文件到 DLI 表
- 支持标准 SQL 查询元数据
---

### 4. 工作流程

```
文件上传        事件触发         路由决策
  |               |                |
  v               v                v
OBS 输入桶 --> FunctionGraph --> 文件数 <= 阈值?
  |               |                |
  |               |        +-------+-------+
  |               |        |YES            |NO
  |               |        v               v
  |               |   直接处理         CCE 批处理
  |               |   (pydicom)        (容器化)
  |               |        |               |
  |               |        v               v
  |               |   写 Parquet      写 Parquet
  |               |   到 OBS 输出     到 OBS 输出
  |               |        |               |
  |               |        +-------+-------+
  |               |                |
  |               |                v
  |               |         DLI Flink 导入
  |               |                |
  |               |                v
  |               |         DLI 元数据表
  |               |                |
  |               |                v
  |               |         SQL 查询就绪
```
---

### 5. 目录结构

```
dicom-metadata-extractor-datalake/
|
|-- infra/                       Terraform 基础设施代码
|   |-- versions.tf             Provider 版本声明
|   |-- variables.tf            输入变量定义
|   |-- main.tf                 主资源编排 (VPC/OBS/CCE/DLI/FunctionGraph)
|   |-- outputs.tf              输出值
|
|-- src/                         Python 源代码
|   |-- app.py                  FunctionGraph 入口 + CCE 批处理入口
|   |-- dicom_wrapper.py        DICOM 元数据提取 (pydicom)
|   |-- obs_wrapper.py          OBS 文件操作 (esdk-obs-python)
|   |-- dli_client.py           DLI 表/分区管理 (SQL API)
|   |-- cce_client.py           CCE 任务提交 (REST API)
|   |-- logger.py               结构化日志
|   |-- utils/
|   |   |-- tags.py             DICOM VR (值表示) 处理
|   |   |-- utils.py            归档工具函数
|   |-- requirements.txt        Python 依赖
|   |-- Dockerfile              CCE 容器构建文件
|
|-- docs/                        文档
|   |-- architecture.md         架构设计文档
|   |-- deployment-guide.md     部署指南
|
|
|-- README.md                    中文文档 (本文件)
|-- README.en.md                 英文文档
|-- LICENSE                      MIT 许可证
```
---

## 12. 依赖

- Terraform >= 1.5 + huaweicloud Provider
- 部署所需运行时依赖见 `docs/deployment-guide.md`

## 13. FAQ

- 常见问题与排查方法请参照 `docs/deployment-guide.md` 各节。

## 14. 贡献指南

欢迎提交 Issue 与 Pull Request 改进本实践；提交前请先运行 `terraform fmt -check` 与文档自检。

## 15. 许可证

本项目采用 [MIT 许可证](LICENSE)。
---

## 16. 联系方式

| **创建者** | `Shangdongd` |
| **维护者** | `Shangdongd` |

**Shangdongd** - Project Maintainer
---

