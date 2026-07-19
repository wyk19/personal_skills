# Personal Codex Skills

这个仓库用于集中维护个人创建的 Codex Skills。每个 Skill 使用独立目录，仓库根目录提供索引、安装说明和共享配置，便于后续继续增加新的 Skill。

## Skill 索引

| Skill | 用途 | 状态 |
| --- | --- | --- |
| [`routing-codex-models`](./routing-codex-models/) | 按代码任务的范围、风险和不确定性，将工作路由给 Luna 或 Sol 自定义 Agent | 可用 |

## 仓库结构

```text
personal_skills/
├── README.md
├── routing-codex-models/
│   ├── SKILL.md
│   └── agents/
│       └── openai.yaml
└── codex-agents/
    └── routing-codex-models/
        ├── code-explorer.toml
        ├── simple-coder.toml
        ├── complex-coder.toml
        └── code-reviewer.toml
```

`routing-codex-models/` 是标准 Skill 包。`codex-agents/` 保存 Skill 依赖的全局自定义 Agent 配置；安装时需要将这些 TOML 文件单独放入 Codex 的 Agent 目录。

## routing-codex-models

该 Skill 让主 Agent 保持编排者角色，根据可观察的任务条件选择合适的执行 Agent。它不会更改当前主 Agent 的模型，也不会将普通对话或尚未进入实施阶段的设计讨论交给编程团队。

### 路由策略

| 场景 | Agent | 模型与推理强度 |
| --- | --- | --- |
| 不清楚代码归属、执行路径或验证命令 | `code_explorer` | `gpt-5.6-luna` / medium / 只读 |
| 文件、行为边界和验证命令都明确的小改动 | `simple_coder` | `gpt-5.6-luna` / medium |
| 跨模块、高风险、架构不清晰，或 Luna 实质性失败 | `complex_coder` | `gpt-5.6-sol` / high |
| 对实质性实现进行独立审查 | `code_reviewer` | `gpt-5.6-sol` / high / 只读 |

Terra 被有意排除。Luna 负责低成本、边界明确的探索与实现；Sol 用于推理深度会显著影响正确性的任务。

### 前置条件

- Codex 运行环境支持 Skills 和自定义 Subagents。
- 当前账号可使用 `gpt-5.6-luna` 与 `gpt-5.6-sol`。
- 默认 Codex 配置目录为 `~/.codex`。

### 安装

通过 SSH 克隆仓库：

```bash
git clone git@github.com:wyk19/personal_skills.git
cd personal_skills
```

安装 Skill 和配套 Agent：

```bash
mkdir -p ~/.codex/skills ~/.codex/agents
cp -R ./routing-codex-models ~/.codex/skills/
cp ./codex-agents/routing-codex-models/*.toml ~/.codex/agents/
```

如果目标位置已经存在同名文件，请先比较或备份已有版本。安装完成后启动新的 Codex 会话，使 Skill 和 Agent 配置生效。

### 使用

可以显式调用：

```text
Use $routing-codex-models to implement and verify this change.
```

也可以直接提出代码探索、修改、调试、重构、测试或审查任务，由 Skill 描述自动触发路由。

路由时必须通过 `spawn_agent` 的 `agent_type` 选择自定义 Agent，并设置 `fork_turns="none"`。`task_name` 仅用于实例标签，不能代替 `agent_type` 选择角色或模型。

### 行为边界

- 主 Agent 负责任务拆分、证据整合和最终验证。
- 独立探索可以并行；存在重叠写入的实现必须串行。
- Luna 遇到范围扩张、实质性验证失败或关键不确定性时，只升级一次到 `complex_coder`，不重复低成本重试。
- `code_reviewer` 保持只读，不修改实现。
- 父会话的实时沙箱与权限策略优先于 TOML 中的默认设置。
- 如果运行时不支持指定的 `agent_type` 或模型，Skill 会明确报告降级，不会声称已完成模型路由。

## 添加新的 Skill

1. 在仓库根目录新建以 Skill 名称命名的目录。
2. 将入口说明写入该目录的 `SKILL.md`，并保留有效的 YAML frontmatter。
3. 可选的 UI 元数据放在该 Skill 的 `agents/openai.yaml`。
4. 如果 Skill 依赖全局 Agent 配置，将 TOML 放入 `codex-agents/<skill-name>/`。
5. 在本 README 的 Skill 索引中增加一行，并补充独立安装说明。
