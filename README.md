# Codex Long-Task Continuity

通过 Codex `SessionStart` Hook，为长任务提供两段额外的 developer context：

1. 压缩连续性与 `Completion gate`，让压缩摘要明确保留任务为什么还不能结束。
2. 子 Agent 编排原则，让 root Agent 根据上下文成本、并行收益和独立判断价值进行委派。

默认只对以下模型生效：

| 模型 | 压缩连续性 | 子 Agent 编排 |
|---|---:|---:|
| `gpt-5.6-sol` | 是 | 是 |
| `gpt-5.6-terra` | 是 | 是 |
| `gpt-5.6-luna` | 否 | 否 |
| `gpt-5.5` | 否 | 否 |
| 其他模型 | 否 | 否 |

这套方案不替换 Codex 官方的模型、root、child-agent、工具或 multi-agent mode 提示词，也不修改静态模型目录。它只在官方上下文之外追加两段独立规则。

> [!IMPORTANT]
> Hook 是能够在本机执行命令的扩展。安装后必须在 Codex 中打开 `/hooks`，检查命令和文件路径，再亲自信任。不要使用 `--dangerously-bypass-hook-trust` 代替正常审查。

## 直接交给 Agent 安装

把本仓库链接发给 Agent：

```text
https://github.com/hututuo/codex-long-task-continuity
```

然后发送下面这段话：

```text
请安装这个仓库提供的 Codex Long-Task Continuity Hook。先完整读取 README.md，确认真实 CODEX_HOME 和现有 hooks.json；克隆仓库后运行测试，再执行 install.py install。保留所有无关 Hook 和配置，安装前创建备份；不要覆盖 config.toml 或模型目录。检查并迁移旧版 root_agent_usage_hint_text 和模型目录中的 Compaction continuity 遗留段，最后运行严格验证，并用新的 Sol、Terra 会话做正向验证，用 Luna、GPT-5.5 做负向验证。请保留回滚路径，不要强制结束承载当前任务的 Codex 进程。
```

Agent 应完成从检查、备份、安装、信任提示、验证到回滚记录的整个流程，而不是只把文件下载下来。

## 它解决什么

| 长任务问题 | 规则如何处理 |
|---|---|
| 读取大量文件后压缩，只保留了最终结论 | 摘要同时保留目标、工作状态、推理状态、探索地图、证据和准确下一步 |
| 尚未形成结论时，压缩后又要重新阅读 | 保存否定性证据、矛盾、失败路径、已排除假设和当前工作模型 |
| 摘要明明还有待办，接手 Agent 却直接 Final | `Completion gate` 明确记录提交最终回复前必须满足的条件，以及当前为什么不能结束 |
| 已确认结论掩盖仍需探索的部分 | 暂定结论、未解决线索、缺失环节和后续方向获得同等可见度 |
| Agent 完全不用子 Agent，或机械地大量委派 | 按任务边界、耦合度、上下文成本、并行收益、独立判断和验证成本综合决定 |
| 主 Agent 只剩分派与汇报 | 主 Agent 继续负责完整上下文、核心推理、跨模块取舍、整合、验证和最终交付 |
| 独立复核被主 Agent 的假设锚定 | 给子 Agent 的上下文明确区分事实、假设和开放问题 |
| 普通任务也使用最高思考强度 | 大多数任务使用 `medium`，再按重要性逐级提升到 `high`、`xhigh` 和极少数 `max` |

## 工作原理

安装器在用户级 `hooks.json` 中结构化合并一个 Hook：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|compact",
        "hooks": [
          {
            "type": "command",
            "command": "<python> <CODEX_HOME>/hooks/codex-long-task-continuity.py",
            "statusMessage": "Loading Codex long-task continuity rules"
          }
        ]
      }
    ]
  }
}
```

运行顺序如下：

1. 新任务触发 `SessionStart source=startup`。
2. Hook 脚本读取事件中的 `model` 和 `source`。
3. 只有 Sol 或 Terra 且来源为 `startup` 或 `compact` 时，脚本才把两段 Markdown 输出到 stdout。
4. Codex 把 stdout 作为额外 developer context 加入任务。
5. 新任务第一次压缩时，摘要模型已经能看到压缩连续性规则。
6. 压缩完成后，Codex 排队一次 `SessionStart source=compact`；下一轮开始时 Hook 再次注入两段规则，使后续任务和下一次压缩继续携带它们。

因此，`compact` 事件不是 compact prompt 本身，也不会替换 Codex 原生摘要提示。它负责在压缩完成后恢复额外规则；第一次压缩能否遵循 `Completion gate`，取决于该任务此前是否通过 `startup` 获得了规则。

## 安装内容

默认 `CODEX_HOME` 是环境变量 `$CODEX_HOME`；未设置时使用 `~/.codex`。

| 目标路径 | 用途 |
|---|---|
| `$CODEX_HOME/hooks.json` | 保留已有内容，只合并一个 `SessionStart` matcher group |
| `$CODEX_HOME/hooks/codex-long-task-continuity.py` | 模型和事件范围过滤、提示词输出 |
| `$CODEX_HOME/prompt-overlays/compaction-continuity.md` | 压缩连续性与 Completion gate |
| `$CODEX_HOME/prompt-overlays/subagent-orchestration.md` | 子 Agent 编排与思考强度规则 |
| `$CODEX_HOME/backups/codex-long-task-continuity-*` | 安装、升级或卸载前的精确备份和 manifest |

安装器不会修改：

- `$CODEX_HOME/config.toml`
- `model_catalog_json` 指向的模型目录
- Codex 官方 base instructions
- 官方 root / child-agent / tool / mode 提示词
- 与本项目无关的其他 Hook

## 自动安装

要求 Python 3.9 或更高版本，只使用 Python 标准库。

```sh
git clone https://github.com/hututuo/codex-long-task-continuity.git
cd codex-long-task-continuity
python3 -m unittest discover -s tests -v
python3 install.py install
```

使用非默认 Codex Home：

```sh
python3 install.py --codex-home /absolute/path/to/codex-home install
```

首次安装、文件升级和卸载都会先创建备份。重复运行相同版本是幂等操作，不会增加重复 Hook 或重复提示词。

安装器的写入门禁包括：

- `hooks.json` 不是合法 JSON 对象时立即停止，不覆盖原文件；
- 目标文件或其父目录是符号链接时立即停止，避免写出 `CODEX_HOME`；
- 现有目标不是普通文件时立即停止；
- Hook 命令使用 PATH 中稳定的 Python 绝对入口，不固化 Homebrew Cellar 版本目录；
- 恢复只接受当前 `CODEX_HOME/backups/` 下由本项目生成的 manifest；
- manifest 必须准确对应本项目管理的四个目标文件；
- 所有 payload 路径和 SHA-256 会在任何恢复写入开始前完成验证。

安装后在 Codex 中：

1. 输入 `/hooks`。
2. 检查命令确实指向 `$CODEX_HOME/hooks/codex-long-task-continuity.py`。
3. 信任该 Hook。
4. 运行验证：

```sh
python3 install.py verify --strict-legacy
```

预期输出：

```text
Verification passed: Sol/Terra receive both prompts; Luna/GPT-5.5 receive neither.
```

`verify` 会检查：

- 仓库源文件与安装文件逐字一致；
- `hooks.json` 中恰好存在一个本项目 Hook；
- matcher 是 `startup|compact`；
- Sol、Terra 在 `startup` 和 `compact` 都各输出两段提示词一次；
- Luna、GPT-5.5 不输出任何内容；
- `resume` 不输出内容；
- 是否仍存在旧版完整 root 覆盖或模型目录压缩段。

静态验证不能代替 Hook 信任，也不能证明真实模型调用已经收到 developer context。最终验收应创建新的 Sol、Terra 任务，并检查对应 rollout 中：

```text
official_root=1
compaction=1
completion_gate=1
subagent=1
reasoning_policy=1
```

同时用 Luna 和 GPT-5.5 做负向检查，四个自定义计数都应为零。

## 从旧版仓库配置升级

本仓库最初版本采用两项完整覆盖：

- 在静态模型目录的 `gpt-5.6-sol.base_instructions` 中加入 `## Compaction continuity`；
- 在 `config.toml` 中设置完整的 `root_agent_usage_hint_text`。

新版不再采用这两种方式。完整覆盖会冻结一份官方提示词副本，Codex 更新后容易漂移，也无法同时安全地按 Sol/Terra 路由。

安装器会报告旧版遗留，但不会自动改写 `config.toml` 或模型目录，因为这两个文件可能包含用户自己的 GPT-5.5 路由和其他模型配置。交给 Agent 升级时，应按以下顺序处理：

1. 记录 Codex 版本、`CODEX_HOME`、模型目录路径、文件权限和哈希。
2. 同时备份 `config.toml`、模型目录、`hooks.json` 和旧提示词文件。
3. 从 `[features.multi_agent_v2]` 中只移除 `root_agent_usage_hint_text`，保留当前仍需要的其他字段。
4. 以当前 Codex 版本和当前官方模型目录为基线，只移除 Sol `base_instructions` 中旧的 `## Compaction continuity` 附加段；保留 GPT-5.5 自定义路由和其他模型对象。
5. 使用 JSON/TOML 结构化解析和 `codex debug models` 验证候选，再安装 Hook。
6. 运行 `python3 install.py verify --strict-legacy`，直到没有旧版警告。
7. 通过 `/hooks` 信任并完成真实新任务验证。

不要为了升级而拿仓库中的静态快照覆盖整个模型目录。本仓库不再分发任何官方 base instructions 副本。

## 旧任务、重启与压缩边界

- 新 Codex 进程或新任务会在 `startup` 时加载 Hook；不需要为每个新任务重启整个应用。
- 已经在安装前加载的旧任务，不会因为磁盘文件改变就自动获得过去的 `startup` 输出。
- Codex 支持宿主热刷新 Hook，但外部脚本写入文件不等于所有已加载任务一定完成了热刷新。
- `SessionStart source=compact` 在本次压缩完成后排队，并在下一轮开始时运行。因此它不能补救同一次压缩已经生成的摘要。
- 对旧任务，最可靠的做法是先在新的 Codex 进程中恢复任务，或开始一个新任务；不要假设“等它压缩一次”就能让第一次摘要遵循 Completion gate。
- matcher 故意没有默认加入 `resume`，因为每次恢复都重复注入完整提示词会增加上下文。需要覆盖旧任务时，应由 Agent 根据当前 Codex 的恢复和去重机制单独设计，而不是机械追加 `resume`。
- Hook 按事件发生时的活动模型路由。任务中途切换模型不会撤回已经进入历史的旧 developer context，也不会自动补发一次 `startup`；需要严格模型隔离时，应新建任务。

## 两段提示词

仓库中的英文文件是安装时的唯一权威来源：

- [压缩连续性提示词](prompts/compaction-continuity.md)
- [子 Agent 编排提示词](prompts/subagent-orchestration.md)

### 压缩连续性

压缩段要求摘要在相关时保留十项状态：

1. Current objective
2. Work state
3. Reasoning state
4. Exploration map
5. Conclusion state
6. Unresolved leads
7. Open-conclusion state
8. Remaining work
9. Communication and delivery state
10. Completion gate

其中 `Completion gate` 是结束判定：必须写明最终回复前尚需满足的条件，以及当前任务为什么不能结束。只要还有必要条件未满足，任务状态就必须保持为进行中或受阻，并与剩余工作一致。

### 子 Agent 编排

子 Agent 段只约束“已经获得当前 multi-agent mode 授权后如何委派”。是否允许主动委派仍由 Codex 官方 mode 消息决定。

主要原则包括：

- 委派收益必须高于协调与验证成本；
- 边界明确、可独立执行和审查的工作更适合委派；
- 关键路径任务只要能独立处理且隔离收益足够，也可以委派；
- 依赖完整上下文、持续全局判断和跨模块取舍的核心工作由 root Agent 保留；
- 确定性任务给足事实和约束，独立复核任务区分事实、假设和开放问题；
- root Agent 必须复核证据、整合冲突并对最终交付负责；
- 大多数子任务使用 `medium`，再按必要性逐级提升到 `high`、`xhigh` 和极少数 `max`。

## 手动安装

自动安装器是推荐方式。需要人工审计时，可以按以下步骤重现：

1. 把 `hooks/session_start_overlay.py` 安装到：

   ```text
   $CODEX_HOME/hooks/codex-long-task-continuity.py
   ```

2. 把 `prompts/` 下两个 Markdown 文件安装到：

   ```text
   $CODEX_HOME/prompt-overlays/
   ```

3. 结构化读取现有 `$CODEX_HOME/hooks.json`，保留所有其他事件和 matcher group，只向 `hooks.SessionStart` 数组加入本项目 group。
4. Hook 命令使用安装时 Python 解释器的绝对路径，以及 Hook 脚本的绝对路径。
5. 将 Hook 脚本权限设为 `0700`，提示词和 `hooks.json` 设为 `0600`（Windows 忽略 POSIX mode）。
6. 打开 `/hooks` 审查并信任。

不要用字符串拼接修改 JSON，也不要用本文示例覆盖已有 `hooks.json`。

## 卸载与回滚

只移除本项目管理的 Hook 和三个安装文件，保留其他 Hook：

```sh
python3 install.py uninstall
```

卸载前同样会创建备份。恢复任意一次安装或卸载前状态：

```sh
python3 install.py restore "$CODEX_HOME/backups/codex-long-task-continuity-<timestamp>-<action>"
```

每个备份目录包含 `manifest.json`，记录原路径、是否存在、权限和 SHA-256。恢复时会校验备份哈希，并拒绝写入 manifest 所记录的 Codex Home 之外。

回滚后再次打开 `/hooks` 检查当前信任状态；Hook 定义发生变化时，Codex 会要求重新审查。

## 开发与验证

仓库测试不访问真实 `~/.codex`：

```sh
python3 -m py_compile install.py hooks/session_start_overlay.py tests/test_install.py
python3 -m unittest discover -s tests -v
```

测试覆盖：

- 保留无关 Hook；
- 首次安装与幂等重装；
- 已知旧 Hook group 升级；
- Sol/Terra 正向与 Luna/GPT-5.5 负向范围；
- 卸载后保留无关配置；
- 安装和卸载备份恢复；
- 旧版覆盖检测；
- 无效 `hooks.json` 阻断且不覆盖原文件。

## 来源与许可

- [Codex Hooks 官方文档](https://learn.chatgpt.com/docs/hooks)
- [OpenAI Codex 开源仓库](https://github.com/openai/codex)
- [`SessionStart` Hook 运行逻辑](https://github.com/openai/codex/blob/main/codex-rs/core/src/hook_runtime.rs)
- [压缩完成后排队 `SessionStartSource::Compact`](https://github.com/openai/codex/blob/main/codex-rs/core/src/session/mod.rs)

本仓库使用 Apache License 2.0。它是独立项目，不是 OpenAI 官方组件；OpenAI 和 Codex 商标归其各自权利人所有。
