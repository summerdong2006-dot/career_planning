# 岗位数据导入、清洗与画像抽取模块

该模块负责把官方岗位原始表导入数据库、完成字段标准化与去重，并在清洗后的标准岗位数据上抽取结构化岗位画像，供岗位图谱、人岗匹配和职业规划报告直接消费。

## 官方数据入口

默认原始数据目录为仓库根目录下的 `data/raw/`，支持以下格式：

- `.csv`
- `.xls`
- `.xlsx`

当 `import_jobs.py` 未显式传入 `--input` 时，会自动选择 `data/raw/` 中最新的一个支持文件作为官方岗位表。

## 运行方式

### 1. 导入并清洗岗位数据

```bash
cd backend
python -m app.modules.job_profile.import_jobs --input ../data/raw/official_job_postings_sample.csv --batch-name official-jobs-20260322
python -m app.modules.job_profile.clean_jobs --batch-id 1
```

### 2. 单条岗位画像抽取

```bash
cd backend
python -m app.modules.job_profile.extract_profiles --source-clean-id 1
```

### 3. 批量岗位画像抽取（开发/测试阶段默认只跑前 50 条）

```bash
cd backend
python -m app.modules.job_profile.extract_profiles --batch-id 1 --limit 50
```

### 4. API 方式调用单条抽取

```bash
curl -X POST http://localhost:8000/api/v1/job-profiles/extract \
  -H "Content-Type: application/json" \
  -d '{
    "source_clean_id": 1,
    "persist": true
  }'
```

### 5. 评估脚本

```bash
cd backend
python scripts/evaluate_job_profiles.py --gold-file sample_data/job_profile_gold_sample.json
```

## 输出物

- 数据库原始表：`job_postings_raw`
- 数据库标准表：`job_postings_clean`
- 数据库画像表：`job_posting_profiles`
- 清洗日志表：`job_cleaning_logs`
- 画像抽取日志表：`job_profile_extraction_logs`
- 标准化 JSON 导出：`backend/output/normalized_jobs/job_postings_batch_<batch_id>.json`
- 清洗日志 JSON 导出：`backend/output/cleaning_logs/job_cleaning_batch_<batch_id>.json`

## 岗位画像稳定输出字段

岗位画像固定输出以下字段，不允许自由新增字段名：

- `job_title`
- `job_level`
- `education_requirement`
- `years_experience_requirement`
- `must_have_skills`
- `nice_to_have_skills`
- `certificates`
- `soft_skills`
- `internship_requirement`
- `industry_tags`
- `promotion_path`
- `summary`
- `extracted_evidence`
- `confidence_score`

其中 `extracted_evidence` 内部也使用固定键，便于追溯。

## 实现说明

- 抽取链路：`schema -> prompt -> llm wrapper -> parser -> persistence`
- 默认 provider 为 `heuristic`，无需外部模型即可开发和测试。
- 当配置 `JOB_PROFILE_LLM_PROVIDER=openai_compatible` 且提供 URL/API Key 时，会优先调用兼容接口；调用失败时自动回退到启发式抽取。
- 批处理入口强制限制为最多 50 条，避免开发阶段误跑全量 9431 条。
- 字段不稳定时会做类型归一化和默认值兜底，不会破坏 JSON 结构。
- 处理失败的记录会写入 `job_profile_extraction_logs` 并继续处理剩余记录。

## 验证方式

### 单元测试

```bash
cd backend
python -m pytest tests/test_job_profile_extraction.py tests/test_job_profile_api.py
```

### 全量后端测试

```bash
cd backend
python -m pytest
```
