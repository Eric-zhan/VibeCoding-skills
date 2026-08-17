# VibeCoding-skills

个人维护的 Codex Skills 集合。仓库只保存自建 Skill 的源码，以及第三方 Skill/Plugin
的来源和版本信息；不会保存 Codex 配置、会话记录、凭据或第三方缓存。

## 包含内容

| Skill | 用途 |
| --- | --- |
| `initialize-repository-context` | 初始化、修复或审计仓库的 `AGENTS.md`、代码地图、测试说明和语言规范。 |
| `summarize-codex-week` | 按时间范围汇总本地 Codex 会话中有证据支持的工作。 |

第三方组件记录在 [`third-party.lock.yaml`](third-party.lock.yaml) 中，不会复制到本仓库。

## 安装

将仓库克隆到一个长期保留的目录，然后运行：

```bash
./bootstrap.sh check
./bootstrap.sh install
./bootstrap.sh status
```

`install` 只会把本仓库的两份 Skill 链接到 `${HOME}/.agents/skills/`。它具有以下安全边界：

- 不安装或升级第三方组件；
- 不联网；
- 不覆盖已有文件、目录或不同目标的符号链接；
- 不删除任何内容。

如需使用其他安装位置，可仅对当前命令设置 `AGENTS_SKILLS_HOME`：

```bash
AGENTS_SKILLS_HOME=/path/to/skills ./bootstrap.sh install
```

安装后重启 Codex，使其重新发现 Skill。

## 调用

直接在请求中写出稳定的 Skill 名称和任务，例如：

```text
使用 initialize-repository-context 初始化 /path/to/project 的 AI 编码上下文。
使用 summarize-codex-week 总结我本周的 Codex 工作。
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

符号链接无需重复创建。需要更新第三方组件时，使用 Codex 对应的插件/Skill 管理器，
确认版本后再更新 `third-party.lock.yaml`，不要提交 `~/.codex/plugins/cache/`。

## 仓库结构

```text
.
├── skills/
│   ├── initialize-repository-context/
│   └── summarize-codex-week/
├── bootstrap.sh
├── third-party.lock.yaml
└── README.md
```
