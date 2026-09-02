# VibeCoding-skills

个人维护的 Codex Skills 集合。仓库保存自建 Skill 的源码，以及经过版本锁定的第三方
Skill/Plugin 源码快照；不会保存 Codex 配置、会话记录、凭据或第三方缓存。

## 包含内容

| Skill | 用途 |
| --- | --- |
| `initialize-repository-context` | 初始化、修复或审计仓库的 `AGENTS.md`、代码地图、测试说明和语言规范。 |
| `summarize-codex-week` | 按时间范围汇总本地 Codex 会话中有证据支持的工作。 |
| `structure-technical-documents` | 按知识逻辑整理论文笔记、代码流程、持续记录和通用技术文档。 |
| `coding-workflow` | 按任务风险选择工作流，包含修改授权、调试和完成前验证。 |

第三方组件记录在 [`third-party.lock.yaml`](third-party.lock.yaml) 中。当前仓库内保存了
`Superpowers 6.3.0` 的完整源码快照，位置为 `third-party/superpowers/6.3.0/`。

该快照是后续定制的原始基线，保持官方目录结构、许可证、插件元数据、全部 skills、脚本、
参考文档和资源。它不会因为本仓库的自建 Skill 安装流程而自动启用；定制版本应放在
`skills/` 下，并且不得依赖 `~/.codex/plugins/cache/` 中的官方缓存。

## 安装

将仓库克隆到一个长期保留的目录，然后运行：

```bash
./bootstrap.sh check
./bootstrap.sh install
./bootstrap.sh status
```

`install` 只会把本仓库的四份 Skill 链接到 `${HOME}/.agents/skills/`。它具有以下安全边界：

- 不安装或升级第三方组件；
- 不联网；
- 不覆盖已有文件、目录或不同目标的符号链接；
- 只删除安装目录中指向本项目 `skills/`、且当前源目录已不存在的旧符号链接；
- 不删除其他来源的 Skill、普通文件或目录。

如需使用其他安装位置，可仅对当前命令设置 `AGENTS_SKILLS_HOME`：

```bash
AGENTS_SKILLS_HOME=/path/to/skills ./bootstrap.sh install
```

安装后重启 Codex，使其重新发现 Skill。

`coding-workflow` 默认选择最轻量的处理方式：简单任务不生成 plan 文档；只有跨模块、
跨会话、架构型任务或用户明确要求时，才创建可复用的设计或实施计划。官方
`Superpowers` 快照仅作为本地参考基线，不会被这套安装流程自动启用。

## 调用

直接在请求中写出稳定的 Skill 名称和任务，例如：

```text
使用 initialize-repository-context 初始化 /path/to/project 的 AI 编码上下文。
使用 summarize-codex-week 总结我本周的 Codex 工作。
使用 structure-technical-documents 整理这份论文、代码流程或持续工作记录，并先说明选择的文档类型。
```

支持 Skill 选择器的客户端也可以从选择器中选择对应名称。不同客户端的 `@`、`$`
等快捷语法可能不同，仓库不依赖某一种界面语法。

## 同步和更新

本仓库中的 `skills/` 是受版本控制的来源。其他机器首次安装后，后续更新流程为：

```bash
git pull --ff-only
./bootstrap.sh check
./bootstrap.sh status
```

符号链接无需重复创建。需要更新第三方组件时，先确认来源和版本，再更新
`third-party/superpowers/<version>/` 与 `third-party.lock.yaml`；不要提交
`~/.codex/plugins/cache/`，也不要让定制 Skill 直接引用该缓存路径。

## 仓库结构

```text
.
├── skills/
│   ├── coding-workflow/
│   ├── initialize-repository-context/
│   ├── summarize-codex-week/
│   └── structure-technical-documents/
├── third-party/
│   └── superpowers/
│       └── 6.3.0/          # 官方完整源码快照
├── bootstrap.sh
├── third-party.lock.yaml
└── README.md
```
