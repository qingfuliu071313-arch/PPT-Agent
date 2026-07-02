# Claude Code 全局配置备份

这里是 PPT-Agent 对 Claude Code 的两个全局入口文件的版本化副本。
**生效位置在 `~/.claude/`，这里只是备份**——改动请先改全局文件，再同步回来提交。

| 仓库内副本 | 生效位置 | 作用 |
|---|---|---|
| `agents/ppt-agent.md` | `~/.claude/agents/ppt-agent.md` | 全局 agent：让任何会话可通过 `Agent(subagent_type="ppt-agent")` 委派做/改 PPT |
| `skills/academic-pptx/SKILL.md` | `~/.claude/skills/academic-pptx/SKILL.md` | 深度规格书：JSON schema、版式规则、工作流（ppt-agent 的内部说明书） |

## 恢复（新机器 / 误删后）

```bash
mkdir -p ~/.claude/agents ~/.claude/skills/academic-pptx
cp claude-config/agents/ppt-agent.md          ~/.claude/agents/
cp claude-config/skills/academic-pptx/SKILL.md ~/.claude/skills/academic-pptx/
```

## 备份（改了全局文件之后）

```bash
cp ~/.claude/agents/ppt-agent.md               claude-config/agents/
cp ~/.claude/skills/academic-pptx/SKILL.md     claude-config/skills/academic-pptx/
```

## 路由设计（为什么两个文件都要）

同一能力同时暴露为 skill 和 agent 时，skill 会在主会话被优先触发（内联执行），
把 agent 截胡。因此 SKILL.md 顶部有 Routing 声明：主会话遇到做/改 PPT 的请求
应 spawn `ppt-agent` 子代理，仅当自己就是该子代理或用户明确要求就地做时才内联
执行。改这两个文件时不要删掉这段声明。
