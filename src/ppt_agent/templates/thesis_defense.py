"""Thesis defense scene template."""

from ppt_agent.models import StyleConfig

THESIS_DEFENSE_GUIDE = """场景指南：学术答辩

=== 图文并重原则 ===
学术答辩PPT以图片、图表、实验结果图为核心内容载体。
每页内容幻灯片必须规划至少1张图片/图表/示意图。
文字仅作为简短注解和关键论断，不要写大段文字或长bullet列表。

可用布局类型及使用时机：
- title: 封面页（论文题目+答辩人+导师+日期）
- section: 章节分隔页（每个大章节前用一页分隔）
- image_focus: 核心展示页 — 1张大图 + 关键论断 + 1-3条简短注解
- dual_image: 双图对比 — 方法对比、实验前后对比、模型架构对比
- figure_caption: 图+分析 — 实验结果图+分析文字、模型结构图+说明
- chart: 数据图表页 — 实验数据、统计结果、性能对比曲线
- process_flow: 流程图 — 研究路线、实验流程、技术架构
- table: 数据表格 — 实验参数、方法对比、文献对比
- key_findings: 关键指标卡 — 核心数据、性能指标、创新点
- references: 参考文献页
- closing: 致谢页

推荐结构（15-20页）：
1. 封面页 (title)
2. 目录/研究框架图 (image_focus — 用研究框架示意图)
3. "研究背景" 分隔 (section)
4. 研究现状 (image_focus — 领域发展示意图)
5. 文献对比 (table)
6. 研究问题与动机 (image_focus — 问题示意图)
7. "研究方法" 分隔 (section)
8. 技术路线 (process_flow)
9. 模型/方法架构 (image_focus — 架构图)
10. 方法对比 (dual_image)
11. "实验结果" 分隔 (section)
12. 核心实验数据 (chart)
13. 实验结果图 (figure_caption)
14. 关键性能指标 (key_findings)
15. 结果对比 (dual_image)
16. "总结与展望" 分隔 (section)
17. 主要贡献 (key_findings)
18. 不足与展望 (image_focus — 未来规划图)
19. 参考文献 (references)
20. 致谢 (closing)

布局使用原则：
- 图片优先：每页优先考虑用图片/图表展示
- image_focus 是最常用布局：架构图、实验图、示意图、截图都用它
- 有数据对比 → chart（不要用文字描述数据）
- 有方法/结果对比 → dual_image
- 有步骤/流程 → process_flow
- 多维度对比 → table
- 纯文字content布局已废弃，不要使用"""

THESIS_DEFENSE_STYLE = StyleConfig(
    primary_color="1A1A1A",
    accent_color="444444",
    background_color="FFFFFF",
    text_color="1A1A1A",
    font_title="SimSun",
    font_body="Microsoft YaHei",
    font_size_title=30,
    font_size_body=18,
)
