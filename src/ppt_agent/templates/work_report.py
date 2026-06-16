"""Work report scene template."""

from ppt_agent.models import StyleConfig

WORK_REPORT_GUIDE = """场景指南：学术工作汇报

=== 图文并重原则 ===
学术工作汇报以图片、图表、实验结果图为核心内容载体。
每页内容幻灯片必须规划至少1张图片/图表/示意图。
文字仅作为简短注解和关键论断，不要写大段文字。

可用布局类型及使用时机：
- title: 封面页（标题+汇报人+课题组+日期）
- section: 章节分隔页
- image_focus: 核心展示页 — 1张大图/示意图 + 关键论断 + 1-3条简短注解
- dual_image: 双图对比 — 进展对比、方法对比、结果对比
- figure_caption: 图+分析 — 实验结果图+分析、数据可视化+解读
- chart: 数据图表页 — 实验数据、统计对比
- process_flow: 流程图 — 实验流程、工作计划、技术路线
- table: 数据表格 — 实验结果、参数对比
- key_findings: 关键指标卡 — 阶段成果量化
- references: 参考文献页
- closing: 总结/致谢页

推荐结构（10-15页）：
1. 封面页 (title)
2. 汇报框架 (image_focus — 用思维导图/框架图)
3. "研究进展" 分隔 (section)
4. 已完成工作概览 (image_focus — 进展示意图)
5. 关键实验数据 (chart)
6. 实验结果展示 (figure_caption)
7. 阶段性成果指标 (key_findings)
8. "问题与讨论" 分隔 (section)
9. 问题分析 (dual_image — 问题现象vs期望结果)
10. "下阶段计划" 分隔 (section)
11. 后续工作流程 (process_flow)
12. 参考文献 (references)
13. 总结致谢 (closing)

布局使用原则：
- 图片优先：每页优先考虑用图片/图表展示
- image_focus 是最常用布局
- 有数据 → chart 或 table
- 有对比 → dual_image
- 有步骤 → process_flow
- 纯文字content布局已废弃，不要使用"""

WORK_REPORT_STYLE = StyleConfig(
    primary_color="222222",
    accent_color="555555",
    background_color="FFFFFF",
    text_color="1A1A1A",
    font_title="Microsoft YaHei",
    font_body="Microsoft YaHei",
    font_size_title=28,
    font_size_body=18,
)
