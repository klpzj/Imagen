# PersonalStation 工房集成（历史方案）

2026-10-13：正式入口 [Imagen 工房](https://bunnykloud.site/index/workshop/imagen)已经采用 PersonalStation 原生 Svelte/Rust 实现，使用共用站点 API。本文件保留旧 iframe/BFF 方案，供维护相应历史版本时参考。当前站点的运行与参数说明以 [PersonalStation 文档](https://github.com/klpzj/PersonalStation/blob/main/docs/imagen-parameters.md)为准；不需要按下文启动独立 Vue/FastAPI 服务或配置旧代理变量。

历史方案通过同源 BFF 把 Imagen 作为独立工具挂在 `/workshop/imagen`。Imagen 拥有自己的 Python API、Vue 状态和 `outputs/`；主站负责入口、路径转发和运行状态提示。以下命令与边界均属于该历史方案。

## 本地运行

终端 1，启动 Imagen API：

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 18000
```

终端 2，构建并提供 Imagen 前端：

```powershell
cd webui
npm run build
npm run preview -- --host 127.0.0.1 --port 5175
```

终端 3，在 PersonalStation `.env` 中保留默认值，或明确写出：

```text
IMAGEN_WEB_URL=http://127.0.0.1:5175
IMAGEN_API_URL=http://127.0.0.1:18000
```

然后启动 PersonalStation，打开 `/workshop/imagen`。Vue 构建使用相对资源路径；主站 iframe 使用 `tool/index.html`，这样脚本和样式会从 `/workshop/imagen/tool/assets/` 加载。运行在主站路径下时，前端会自动把 `/api` 与 `/outputs` 解析成 `/workshop/imagen/api` 和 `/workshop/imagen/outputs`。

嵌入主站时，预览和历史列表会显示“发布到站点媒体库”按钮。按钮只提交 Imagen 图片 ID，PersonalStation 服务端从 Imagen 读取输出，再调用自己的 `/api/v1/admin/media` 保存到 `DATA_DIR/media`；独立打开 Imagen 时该按钮隐藏。

## FRP 运行

如果 Imagen 前端在 PC 上由 FRP 暴露到 VPS 的 `15173` 端口，并且 Vite 继续代理 PC 上的 `18000` 后端，VPS 上的 PersonalStation 可以配置：

```text
IMAGEN_WEB_URL=http://127.0.0.1:15173
IMAGEN_API_URL=http://127.0.0.1:15173
```

`IMAGEN_API_URL` 指向同一个前端端口时，主站 BFF 请求 `/api/*` 与 `/outputs/*`，再由 Imagen Vite 代理转给本机 FastAPI。生产环境也可以把前端静态服务和 FastAPI 分开，此时两个变量分别指向各自的回环地址。

## 验证

```powershell
Invoke-RestMethod http://127.0.0.1:5300/workshop/imagen/api/health
Invoke-WebRequest http://127.0.0.1:5300/workshop/imagen/tool/index.html
```

第一条应返回 `{"ok":true}`；第二条应返回 Imagen HTML，HTML 中的脚本和样式路径应能通过同一主站前缀访问。真实生成仍需要在 Imagen 后端配置 `auth.json` 或 `OPENAI_API_KEY`；凭据不会经过浏览器或 PersonalStation。

## 运行边界

- `auth.json`、`OPENAI_BASE_URL` 和 `outputs/` 只属于 Imagen 后端。
- 工房代理对 API 使用较长的请求超时，静态资源和输出使用短超时；上游不可用时返回统一的 503 JSON。
- 任务状态、历史清理和图片文件删除继续由 Imagen 的 `jobs.json` 与 `manifest.json` 负责。
- 发布到站点媒体通过 `/workshop/imagen/publish` BFF 完成，限制为 8 MB 的 PNG、JPEG 或 WebP；不要让两个项目共同读写对方的目录。
