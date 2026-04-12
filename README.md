# Career Planning

AI 职业规划网站，包含学生画像生成、岗位推荐、岗位展览馆、职业报告、简历生成和“小涯”对话助手等功能。

## Project Structure

- `backend/`: FastAPI 后端、业务模块、测试用例
- `frontend/`: React + Vite 前端源码
- `docs/`: 项目文档
- `data/processed/`: 项目运行需要的处理后岗位数据
- `data/interim/`: 岗位数据清洗中间结果
- `data/seeds/`: 演示数据和种子数据
- `.env.example`: 环境变量模板
- `docker-compose.yml`: Docker 本地启动配置

## Quick Start

1. 克隆仓库

```bash
git clone https://github.com/summerdong2006-dot/career_planning.git
cd career_planning
```

2. 复制环境变量

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

3. 启动项目

```bash
docker compose up --build
```

4. 打开页面

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

默认配置使用启发式逻辑，不填写真实 API Key 也可以跑通基础演示流程。如果需要使用真实大模型能力，请在 `.env` 中配置对应的 `JOB_PROFILE_LLM_*`、`REPORTING_LLM_*` 或 `ASSISTANT_LLM_*` 变量。

## Local Frontend Development

如果只想本地开发前端：

```bash
cd frontend
npm install
npm run dev
```

前端默认读取 `VITE_API_BASE_URL`，Docker 默认配置为 `http://localhost:8000`。

## Tests

后端测试可以在容器启动后运行：

```bash
docker compose exec backend python -m pytest tests -q
```

前端测试：

```bash
cd frontend
npm install
npm test
```

## Manual Test Flow

1. 打开前端并确认页面正常加载。
2. 注册或登录账号。
3. 粘贴简历文本，生成学生画像。
4. 运行岗位推荐，确认推荐岗位正常出现。
5. 打开岗位展览馆，确认卡牌、背景图、成长路线正常展示。
6. 生成职业报告，编辑报告内容后刷新确认保存正常。
7. 生成定制简历。
8. 与“小涯”对话，确认回复区域显示为“小涯”。

## Collaboration Notes

- 不要提交 `.env`、真实 API Key、密码或个人 Token。
- 不要提交 `frontend/node_modules/`、`frontend/dist/`、`__pycache__/`、`.pytest_cache/` 等生成目录。
- 新增可共享数据优先放在 `data/seeds/` 或 `data/processed/`。
- 推荐通过功能分支和 Pull Request 协作。
