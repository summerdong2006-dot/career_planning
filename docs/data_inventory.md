# Data Inventory

说明：本清单基于当前仓库静态扫描结果整理，仅记录现状与建议归类；本次未移动、未删除任何文件。

| 名称 | 当前路径 | 文件类型 | 推测来源 | 当前用途 | 建议归类 |
| --- | --- | --- | --- | --- | --- |
| 20260226105856_457.xls | `E:\Codex\data\raw\20260226105856_457.xls` | xls | 官方岗位原始 Excel 全量导出文件 | 作为岗位导入与清洗链路的原始数据源 | raw |
| official_job_postings_sample.csv | `E:\Codex\data\raw\official_job_postings_sample.csv` | csv | 官方岗位样本 CSV，供开发演示使用 | README 中用于演示导入、清洗和小样本验证 | seeds |
| job_postings_sample.csv | `E:\Codex\backend\sample_data\job_postings_sample.csv` | csv | 开发样本数据；与 `data/raw/official_job_postings_sample.csv` 哈希一致，属于副本 | 岗位画像评估和样本链路输入 | seeds |
| job_profile_gold_sample.json | `E:\Codex\backend\sample_data\job_profile_gold_sample.json` | json | 人工整理的岗位画像 gold 标注样本 | `backend/scripts/evaluate_job_profiles.py` 的评估基准数据 | seeds |
| job_postings_batch_1.json | `E:\Codex\backend\output\normalized_jobs\job_postings_batch_1.json` | json | `demo-jobs` 批次 1 清洗后导出的标准化样本结果 | 演示/小样本标准化输出，非正式全量结果 | seeds |
| job_cleaning_batch_1.json | `E:\Codex\backend\output\cleaning_logs\job_cleaning_batch_1.json` | json | `demo-jobs` 批次 1 清洗时生成的日志 | 查看样本清洗过程、去重与补全情况 | seeds |
| job_postings_batch_2.json | `E:\Codex\backend\output\normalized_jobs\job_postings_batch_2.json` | json | `official-jobs` 批次 2 从官方 Excel 清洗后生成的标准化全量结果 | 当前最接近正式消费的数据文件，Card6 真数据脚本直接读取它 | processed |
| job_cleaning_batch_2.json | `E:\Codex\backend\output\cleaning_logs\job_cleaning_batch_2.json` | json | `official-jobs` 批次 2 清洗过程日志 | 记录全量数据去重、标准化、异常提示与统计信息 | interim |
| card6_stats_first50.json | `E:\Codex\backend\output\card6_validation\card6_stats_first50.json` | json | `backend/scripts/run_card6_on_db_first50.py` 生成的校验快照 | 保存数据库前 50 条岗位运行 Card6 图谱后的统计结果 | archive |
| card6_paths_first50.json | `E:\Codex\backend\output\card6_validation\card6_paths_first50.json` | json | `backend/scripts/run_card6_on_db_first50.py` 生成的校验样例 | 保存数据库前 50 条岗位中部分职位的职业路径样例 | archive |
| student_build.json | `E:\Codex\student_build.json` | json | 手工构造的学生画像/简历测试请求体 | 用于生成 `test_001` 相关学生或报告演示数据 | seeds |
| test-001-1.json | `E:\Codex\test-001-1.json` | json | 针对 `test_001` 的报告导出结果 | 报告 JSON 导出演示样例，可用于前端/联调验收 | seeds |
| test-001-1.html | `E:\Codex\test-001-1.html` | html | 针对 `test_001` 的报告 HTML 导出结果 | 报告 HTML 导出演示样例 | archive |
| report_1.html | `E:\Codex\report_1.html` | html | 对 `report_id=1` 执行导出后生成的历史文件 | 报告 HTML 导出产物，偏人工验证留档 | archive |
| report_1.pdf | `E:\Codex\report_1.pdf` | pdf | 对 `report_id=1` 执行导出后生成的历史文件 | 报告 PDF 导出产物，偏人工验证留档 | archive |

## Unclear

当前扫描范围内没有必须归为 `unclear` 的文件。

说明：
- `backend/app` 目录本次未发现 `.csv/.xls/.xlsx/.json/.jsonl` 数据文件本体，主要是代码与 README 对数据路径的引用。
- 项目根目录下发现的 `html/pdf` 文件不是原始数据，但属于重要导出产物，因此保留在清单中。
- 当前未对任何旧文件做迁移或改名。
