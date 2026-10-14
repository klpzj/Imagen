# Imagen（历史仓库）

[English](README.md)

2026-10-14 起，Imagen 的日常使用、开发、测试与发布统一在 [PersonalStation](https://github.com/klpzj/PersonalStation) 维护。本仓库保存旧 Vue/FastAPI 实现、独立 Python 客户端和设计历史。

正式入口：[Imagen 工房](https://bunnykloud.site/index/workshop/imagen)。使用说明见[原生参数编辑](https://github.com/klpzj/PersonalStation/blob/main/docs/imagen-parameters.md)，功能、运行依赖与旧数据核对见[原库整理记录](https://github.com/klpzj/PersonalStation/blob/main/docs/architecture/imagen-consolidation-20261014.md)。

## 当前维护入口

工作台、Rust API、任务与图片历史、站点媒体发布、Node CLI 和迁移工具均在 PersonalStation。正式服务的凭据位于仓库外，输出位于其 `DATA_DIR/imagen`，无需启动本仓库的 FastAPI/Vue 或 FRP。

在 PersonalStation 根目录使用 CLI：

```sh
node scripts/imagen.mjs --help
node scripts/imagen.mjs generate --quality low -o ./outputs "A simple red apple on a white background"
node scripts/imagen.mjs edit --image ./input.png "Replace the background with a studio backdrop"
```

CLI 默认调用本机 Rust API；访问正式站点时增加 `--api-url https://bunnykloud.site/index`。密钥与上游地址由 Rust 服务配置。

## 保留材料

- [完整旧中文教程](docs/legacy/README.zh-CN.md)与[英文教程](docs/legacy/README.md)：仅供复现旧版，命令从本仓库根目录执行。
- [历史文档索引](docs/README.md)：原始模块、契约、设计与验证资料。
- `gpt_image_client.py`：保留可直接访问上游的 Python 模块/CLI；PersonalStation 的 Node CLI 调用站点 API，两者不是同名 Python 导入接口。本次未发现其他项目或技能依赖旧客户端。
- `LICENSE` 和 Git 历史：保留原 MIT 许可与实现来源。

旧库 8 条任务已全部进入主站。检查中新发现的 1 张子目录图片、原始元数据及可验证 Git bundle 已保存于 PersonalStation 本机的 `data/archives/imagen-20261014`；旧密钥配置另存仓库外。浏览器草稿/预设的存储键与导出格式不同，不自动迁入原生版，转换说明见整理记录。

本轮只整理维护入口与可恢复档案，原目录、源码和 GitHub 仓库继续保留。后续功能和修复只提交 PersonalStation。
