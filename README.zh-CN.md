# Imagen GPT 生图工具

这是一个本地运行的 GPT 生图工具，包含：

- Python 生图封装脚本 `gpt_image_client.py`
- FastAPI 后端服务
- Vue 3 + Vite WebUI
- 本地图片保存、历史记录与删除
- 生成任务状态持久化，刷新后仍可看到进行中或失败任务
- 可选 FRP 端口穿透

当前版本聚焦文本生图、图片编辑、结果预览、下载、历史记录和本地开发穿透。

## 目录结构

```text
imagen/
  gpt_image_client.py          # OpenAI-compatible 图片 API 封装
  auth.json                    # 本地密钥配置，不要提交
  requirements.txt             # Python 依赖
  backend/                     # FastAPI 后端
  scripts/                     # Windows 生命周期管理脚本
  webui/                       # Vue WebUI
  outputs/                     # 生成图片、manifest.json 和 jobs.json
  docs/                        # 设计与验收文档
  frpc.example.toml            # FRP 示例配置
```

## 配置密钥

推荐使用 `auth.json`：

```json
{
  "API_KEY": "你的 API Key",
  "BASE_URL": "http://你的-openai-compatible-base-url"
}
```

也支持这些字段名：

```json
{
  "OPENAI_API_KEY": "你的 API Key",
  "OPENAI_BASE_URL": "http://你的-openai-compatible-base-url",
  "OPENAI_IMAGE_MODEL": "gpt-image-2"
}
```

注意：

- `auth.json` 已加入 `.gitignore`。
- API Key 只在后端读取，不会返回给前端。
- 如果不写 `BASE_URL`，脚本会使用代码中的默认 base url。

## 安装依赖

Python 后端依赖：

```powershell
pip install -r requirements.txt
```

前端依赖：

```powershell
cd webui
npm install
```

## 启动 WebUI

终端 1：启动后端。

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

终端 2：启动前端。

```powershell
cd webui
npm run dev
```

浏览器打开：

```text
http://localhost:5173
```

也可以直接在一个命令行窗口里集合启动后端、前端和 FRP：

```powershell
.\start-frp-webui.bat
```

停止由一键脚本管理的后端、前端和 FRP：

```powershell
.\stop-frp-webui.bat
```

一键脚本默认使用后端端口 `18000`，用于避开 Windows 上 `8000` 端口可能出现的套接字权限错误。脚本会在 `.run/` 下写入日志和进程元数据，并在启动前检查 `18000`、`5173` 端口占用。

WebUI 会通过 Vite 代理访问后端接口：

- `/api/health`
- `/api/config`
- `/api/generate`
- `/api/edit`
- `/api/jobs`
- `/api/images`
- `/outputs/{filename}`

## 命令行生图

直接使用 Python 脚本生成图片：

```powershell
python .\gpt_image_client.py generate "A clean product render of a white ceramic mug"
```

指定输出目录和参数：

```powershell
python .\gpt_image_client.py generate `
  -o .\outputs\test `
  --prefix demo `
  --size 1024x1024 `
  --quality low `
  --format png `
  "A simple red apple on a white background"
```

常用参数：

- `--model`：图片模型，默认 `gpt-image-2`
- `--size`：图片尺寸，例如 `1024x1024`
- `--quality`：质量，支持 `auto`、`low`、`medium`、`high`
- `--format`：输出格式，支持 `png`、`jpeg`、`webp`
- `--n`：生成数量
- `-o/--out-dir`：输出目录

## 后端接口

V1 后端接口：

```text
GET  /api/health
GET  /api/config
POST /api/generate
POST /api/edit
POST /api/jobs
GET  /api/jobs
GET  /api/jobs/active
GET  /api/jobs/{job_id}
GET  /api/images
DELETE /api/images/{image_id}
GET  /outputs/{filename}
```

生成请求示例：

```json
{
  "prompt": "A simple red apple on a white background",
  "options": {
    "model": "gpt-image-2",
    "size": "1024x1024",
    "quality": "low",
    "output_format": "png",
    "moderation": "none",
    "n": 1
  }
}
```

历史记录保存在：

```text
outputs/manifest.json
```

任务记录保存在：

```text
outputs/jobs.json
```

生成图片保存在：

```text
outputs/
```

## FRP 穿透

当前 WebUI 通过 Vite dev server 代理 `/api` 和 `/outputs`，所以 FRP 只需要暴露前端端口 `5173`。

复制示例配置：

```powershell
Copy-Item .\frpc.example.toml .\frpc.toml
```

编辑 `frpc.toml`，填写你的 FRPS 地址和 token：

```toml
serverAddr = "YOUR_FRPS_SERVER_IP_OR_DOMAIN"
serverPort = 7000

auth.method = "token"
auth.token = "YOUR_FRPS_TOKEN"

[[proxies]]
name = "imagen-webui"
type = "tcp"
localIP = "127.0.0.1"
localPort = 5173
remotePort = 15173
```

启动顺序：

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

```powershell
cd webui
npm run dev
```

```powershell
.\frpc.exe -c .\frpc.toml
```

一键启动：

```powershell
.\start-frp-webui.bat
```

一键停止：

```powershell
.\stop-frp-webui.bat
```

远程访问：

```text
http://<frps-server>:15173
```

## 验证

后端语法检查：

```powershell
python -m py_compile backend\app.py backend\config.py backend\schemas.py backend\image_service.py backend\image_store.py backend\job_store.py gpt_image_client.py
```

前端构建：

```powershell
cd webui
npm run build
```

健康检查：

```powershell
Invoke-RestMethod -Uri http://localhost:18000/api/health -Method Get
```

V1 已完成一次真实链路验证，记录见：

- [V1 集成验证报告](docs/v1-integration-verification.md)

## 文档

- [文档索引](docs/README.md)
- [接口与数据契约](docs/api-and-data-contract.md)
- [后端模块设计](docs/backend-modules.md)
- [前端模块设计](docs/frontend-modules.md)
- [实施计划](docs/implementation-plan.md)
- [V1 集成验证报告](docs/v1-integration-verification.md)

## 注意事项

- 不要提交 `auth.json`。
- 不要提交 `outputs/` 中的生成图片，除非明确需要样例图。
- `webui/node_modules/`、`webui/dist/`、`.run/` 和运行日志已加入 `.gitignore`。
