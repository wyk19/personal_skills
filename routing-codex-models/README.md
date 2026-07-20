# routing-codex-models

该 Skill 让主 Agent 保持编排者角色，根据可观察的任务条件选择合适的执行 Agent。它不会更改当前主 Agent 的模型，也不会将普通对话或尚未进入实施阶段的设计讨论交给编程团队。

## 项目结构

```text
routing-codex-models/
├── README.md
├── .gitattributes                 # preserve reference Markdown hard breaks
├── skill/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   └── scripts/
│       └── audit-routing-session.py
├── agents/
│   ├── code-explorer.toml
│   ├── simple-coder.toml
│   ├── complex-coder.toml
│   └── code-reviewer.toml
├── tests (project-local)
├── docs/
└── references/
```

`skill/` 是可安装的 Skill 包，包含入口 `SKILL.md`、UI 元数据和审计脚本。`agents/` 保存需要单独安装到全局 Agent 目录的自定义 Agent 配置。`references/*.md` 是字节保持的源参考资料，其中的行尾空格用于 Markdown hard break；`.gitattributes` 禁止 Git 将这些有意空格报告为 whitespace 错误。

## 路由策略

| 场景 | Agent | 模型与推理强度 |
| --- | --- | --- |
| 不清楚代码归属、执行路径或验证命令 | `code_explorer` | `gpt-5.6-luna` / medium / 只读 |
| 文件、行为边界和验证命令都明确的小改动 | `simple_coder` | `gpt-5.6-luna` / medium |
| 跨模块、高风险、架构不清晰，或 Luna 实质性失败 | `complex_coder` | `gpt-5.6-sol` / high |
| 对实质性实现进行独立审查 | `code_reviewer` | `gpt-5.6-sol` / high / 只读 |

Terra 被有意排除。Luna 负责低成本、边界明确的探索与实现；Sol 用于推理深度会显著影响正确性的任务。

## 前置条件

- Codex 运行环境支持 Skills 和自定义 Subagents。
- 当前账号可使用 `gpt-5.6-luna` 与 `gpt-5.6-sol`。
- 默认 Codex 配置目录为 `~/.codex`。

## 安装

通过 SSH 克隆仓库：

```bash
git clone git@github.com:wyk19/personal_skills.git
cd personal_skills
```

安装 Skill 和配套 Agent：

```bash
mkdir -p ~/.codex/skills/routing-codex-models ~/.codex/agents
cp -R ./routing-codex-models/skill/. ~/.codex/skills/routing-codex-models/
cp ./routing-codex-models/agents/*.toml ~/.codex/agents/
```

安装必须同时包含完整的 `routing-codex-models/skill/` 包和 `routing-codex-models/agents/*.toml` 全局 Agent 配置。只复制 Skill 包或只复制 TOML 文件都不完整。安装完成后启动新的 Codex 会话，使 Skill 和 Agent 配置生效。

如果目标位置已经存在同名文件，请先比较或备份已有版本。

## 使用

可以显式调用：

```text
Use $routing-codex-models to implement and verify this change.
```

也可以直接提出代码探索、修改、调试、重构、测试或审查任务，由 Skill 描述自动触发路由。

路由时必须通过 `spawn_agent` 的 `agent_type` 选择自定义 Agent，并设置 `fork_turns="none"`。`task_name` 仅用于实例标签，不能代替 `agent_type` 选择角色或模型。

## Fail-closed dispatch

对于需要代码检查、修改、调试、测试、重构或审查的任务，必须先成功调用带有 `agent_type` 和 `fork_turns="none"` 的 `spawn_agent`。在首次成功类型化 spawn 之前，父会话不得检查实现细节；在任何时候都不得编辑实现或测试，也不得接管实现。小型、紧急或串行任务也不例外。父会话只负责任务拆分、协调执行、整合证据和最终验证。若运行时拒绝类型化路由，必须原样报告 `ROUTING_UNAVAILABLE: <exact runtime error>`，并在代码检查或修改前停止。仅有通用 Agent 或类似角色的 `task_name` 不构成路由证据。

## 审计

可用标准库审计 CLI 检查会话 JSONL：

```bash
python routing-codex-models/skill/scripts/audit-routing-session.py SESSION_ID \
  --sessions-dir ~/.codex/sessions \
  --latest-turn \
  --expect simple_coder:gpt-5.6-luna:medium \
  --expect code_reviewer:gpt-5.6-sol:high
```

CLI 同样接受根 JSONL 路径；`--sessions-dir` 始终必填且必须指向包含所有日期目录的 Codex sessions 根目录。每次审计必须在互斥的 `--latest-turn` 与 `--turn-id TURN_ID` 中选择一个。

审计器使用根会话的 `turn_context` 和 spawn call 自带的 turn ID，仅核验所选 turn；started 事件和工具输出即使没有 turn ID，也会通过所选 call ID 关联到精确的子会话 UUID。

所选 turn 中的每个 `spawn_agent` 都必须是类型化调用并完成有序的 call、started、成功输出和唯一子会话链。`--expect` 必须完整列出该 turn 的全部类型化调用：每个值消耗不同的 call ID 和子会话 UUID，同一角色出现多次时必须重复传入；未声明角色、额外调用、不完整调用或重放子会话都会失败。随后审计器核验 `fork_turns`、角色、模型和推理强度。证据无法读取或 JSONL 损坏时会失败关闭；诊断写入 stderr 并返回非零状态。

该 CLI 证明的是可观察的路由生命周期、子会话身份以及模型配置证据。它不解析不可靠的 shell 命令来推断父会话是否修改代码；父会话禁止编辑和实现仍由 Skill 的 fail-closed 行为契约约束。

## 行为边界

- 主 Agent 负责任务拆分、证据整合和最终验证。
- 独立探索可以并行；存在重叠写入的实现必须串行。
- Luna 遇到范围扩张、实质性验证失败或关键不确定性时，只升级一次到 `complex_coder`，不重复低成本重试。
- `code_reviewer` 保持只读，不修改实现。
- 父会话的实时沙箱与权限策略优先于 TOML 中的默认设置。
- 如果运行时不支持指定的 `agent_type`、Agent 或模型，Skill 会报告 `ROUTING_UNAVAILABLE: <exact runtime error>` 并立即停止，不会重试、替换模型或由父会话接手实现。
- `code_explorer` 或 `code_reviewer` 成功启动也不会授权父会话编辑或实现；所有实现、测试编写和审查修正仍必须交给 `simple_coder` 或 `complex_coder`。

## 设计与计划

- [路由强制设计](./docs/superpowers/specs/2026-07-20-routing-enforcement-design.md)
- [路由强制计划](./docs/superpowers/plans/2026-07-20-routing-enforcement.md)
- [项目结构设计](./docs/superpowers/specs/2026-07-20-project-structure-design.md)
- [项目结构计划](./docs/superpowers/plans/2026-07-20-project-structure.md)

## 添加新的 Skill

1. 在仓库根目录新建以 Skill 名称命名的目录。
2. 将入口说明写入该目录的 `skill/SKILL.md`，并保留有效的 YAML frontmatter。
3. 可选的 UI 元数据放在该 Skill 的 `skill/agents/openai.yaml`。
4. 如果 Skill 依赖全局 Agent 配置，将 TOML 放入该 Skill 的 `agents/`。
5. 在根 README 的 Skill 索引中增加一行，并补充该项目的独立安装说明。
