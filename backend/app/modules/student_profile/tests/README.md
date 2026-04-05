学生画像模块测试统一放在 backend/tests/ 下，避免与全局 pytest 收集规则冲突。

当前对应测试文件：
- backend/tests/test_student_profile_service.py
- backend/tests/test_student_profile_api.py

从仓库根目录或 backend 目录执行以下命令都应被发现：
- pytest -q
