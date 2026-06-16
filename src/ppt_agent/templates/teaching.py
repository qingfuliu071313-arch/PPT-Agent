"""Teaching courseware scene template."""

from ppt_agent.models import StyleConfig

TEACHING_GUIDE = """场景指南：教学课件

=== 图文并重原则 ===
学术教学课件以图片、图表、示意图为核心内容载体。
每页内容幻灯片必须规划至少1张图片/图表/示意图。
文字仅作为简短注解和关键定义，不要写大段文字。

可用布局类型及使用时机：
- title: 封面页（课程名+教师+院系+日期）
- section: 章节分隔页（每个知识模块前用一页分隔）
- image_focus: 核心展示页 — 1张大图/示意图 + 关键论断 + 1-3条简短注解
- dual_image: 双图对比 — 适合对比实验、前后对比、不同方法对比
- figure_caption: 图+分析 — 适合带解释的实验结果图、公式推导示意
- chart: 数据图表页 — 统计数据、实验数据对比
- process_flow: 流程图 — 算法步骤、实验流程、推导过程
- table: 数据表格 — 参数对比、方法特性对比
- key_findings: 关键概念卡 — 核心定义、公式、定理
- references: 参考文献页
- closing: 课程总结/思考题

推荐结构（15-25页）：
1. 封面页 (title)
2. 课程大纲 (image_focus — 用思维导图)
3. "基础概念" 分隔 (section)
4. 核心概念定义 (key_findings)
5. 概念示意图 (image_focus)
6. 概念对比 (dual_image)
7. "理论推导" 分隔 (section)
8. 推导过程 (process_flow)
9. 公式图解 (figure_caption)
10. "实验/案例" 分隔 (section)
11. 实验设计示意 (image_focus)
12. 实验数据 (chart)
13. 结果对比 (dual_image)
14. 参数对比 (table)
15. "总结与练习" 分隔 (section)
16. 核心知识点 (key_findings)
17. 参考文献 (references)
18. 课程总结/思考题 (closing)

布局使用原则：
- 图片优先：每页优先考虑用图片/图表展示，文字仅做简短注解
- image_focus 是最常用布局：概念图、示意图、实验图、截图都用它
- 有对比 → dual_image（不要用文字列两列对比）
- 有数据 → chart 或 table
- 有步骤/过程 → process_flow
- 核心定义/公式 → key_findings
- 纯文字content布局已废弃，不要使用"""

TEACHING_STYLE = StyleConfig(
    primary_color="1B3A5C",
    accent_color="2B6CB0",
    background_color="FFFFFF",
    text_color="1A202C",
    font_title="Microsoft YaHei",
    font_body="Microsoft YaHei",
    font_size_title=28,
    font_size_body=18,
)
