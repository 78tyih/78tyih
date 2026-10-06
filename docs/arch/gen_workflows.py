#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 7 个项目的架构流程编译成 Archify workflow candidate（schema v2）。

facts 来自各仓库 showcase/project.json（单一事实源）。
"""
import json, os

SPECS = [
    {
        "slug": "sarah", "title": "sarah-motion · 动效组件库",
        "lanes": [{"id": "engine", "label": "引擎 Engine"}, {"id": "quality", "label": "质检 Quality"}],
        "nodes": [
            {"id": "t", "lane": "engine", "col": 0, "type": "external", "label": "时间 t", "sublabel": "seek(t) 可跳转"},
            {"id": "spring", "lane": "engine", "col": 1, "type": "backend", "label": "弹簧引擎", "sublabel": "纯时间函数"},
            {"id": "components", "lane": "engine", "col": 2, "type": "backend", "label": "组件族", "sublabel": "报价/杠杆/回放"},
            {"id": "bpm", "lane": "quality", "col": 2, "type": "backend", "label": "节拍网格", "sublabel": "120 BPM"},
            {"id": "blur", "lane": "quality", "col": 3, "type": "frontend", "label": "60fps 运动模糊", "sublabel": "一形十态"},
            {"id": "atlas", "lane": "quality", "col": 4, "type": "database", "label": "规格图谱", "sublabel": "数据×6 金融×6"},
        ],
        "edges": [["t", "spring"], ["spring", "components"], ["components", "bpm"], ["bpm", "blur"], ["blur", "atlas"]],
    },
    {
        "slug": "ssf", "title": "sera-subtitle-factory · 字幕工厂",
        "lanes": [{"id": "input", "label": "输入 Input"}, {"id": "render", "label": "渲染 Render"}],
        "nodes": [
            {"id": "audio", "lane": "input", "col": 0, "type": "external", "label": "音频/文本", "sublabel": "素材输入"},
            {"id": "align", "lane": "input", "col": 1, "type": "backend", "label": "词级对齐", "sublabel": "每词时间码"},
            {"id": "recipe", "lane": "render", "col": 1, "type": "database", "label": "Recipe (JSON)", "sublabel": "样式即数据"},
            {"id": "renderer", "lane": "render", "col": 2, "type": "frontend", "label": "渲染", "sublabel": "单行·逐词"},
            {"id": "studio", "lane": "render", "col": 3, "type": "cloud", "label": "在线工作台", "sublabel": "studio/"},
        ],
        "edges": [["audio", "align"], ["align", "recipe"], ["recipe", "renderer"], ["renderer", "studio"]],
    },
    {
        "slug": "dsc", "title": "deepseek-color · Agent 设计技能",
        "lanes": [{"id": "pipeline", "label": "色彩管线"}],
        "nodes": [
            {"id": "palettes", "lane": "pipeline", "col": 0, "type": "database", "label": "5 色卡", "sublabel": "克制配色"},
            {"id": "skeletons", "lane": "pipeline", "col": 1, "type": "backend", "label": "12 版式骨架", "sublabel": "零依赖"},
            {"id": "combos", "lane": "pipeline", "col": 2, "type": "frontend", "label": "8 换肤组合", "sublabel": "实时试穿"},
            {"id": "install", "lane": "pipeline", "col": 3, "type": "cloud", "label": "Agent 安装", "sublabel": "四大 Agent"},
        ],
        "edges": [["palettes", "skeletons"], ["skeletons", "combos"], ["combos", "install"]],
    },
    {
        "slug": "dsh", "title": "dsh-deepseek-color · DSH 皮肤包",
        "lanes": [{"id": "pipeline", "label": "皮肤管线"}],
        "nodes": [
            {"id": "tokens", "lane": "pipeline", "col": 0, "type": "database", "label": "纯 token 皮肤", "sublabel": "只 CSS 变量"},
            {"id": "vars", "lane": "pipeline", "col": 1, "type": "backend", "label": "CSS 变量映射", "sublabel": "不碰 DOM"},
            {"id": "center", "lane": "pipeline", "col": 2, "type": "cloud", "label": "DSH 皮肤中心", "sublabel": "更新不失效"},
        ],
        "edges": [["tokens", "vars"], ["vars", "center"]],
    },
    {
        "slug": "mojo", "title": "mojo-plate-design · 雕版图谱",
        "lanes": [{"id": "distill", "label": "逆向 Distill"}, {"id": "output", "label": "产出 Output"}],
        "nodes": [
            {"id": "reverse", "lane": "distill", "col": 0, "type": "backend", "label": "mojo 逆向", "sublabel": "学模式不搬"},
            {"id": "rules", "lane": "distill", "col": 1, "type": "database", "label": "8 非协商规则", "sublabel": "字体三件套"},
            {"id": "blueprints", "lane": "output", "col": 1, "type": "backend", "label": "4 段版式蓝图", "sublabel": "雕版分区"},
            {"id": "motion", "lane": "output", "col": 2, "type": "frontend", "label": "招牌动效", "sublabel": "steps() 印刷感"},
            {"id": "replica", "lane": "output", "col": 3, "type": "cloud", "label": "replica", "sublabel": "一比一复刻"},
        ],
        "edges": [["reverse", "rules"], ["rules", "blueprints"], ["blueprints", "motion"], ["motion", "replica"]],
    },
    {
        "slug": "trae", "title": "trae-skills · 四个管住 Agent 的技能",
        "lanes": [{"id": "pipeline", "label": "技能路由"}],
        "nodes": [
            {"id": "trigger", "lane": "pipeline", "col": 0, "type": "external", "label": "触发", "sublabel": "按情境进技能"},
            {"id": "tree", "lane": "pipeline", "col": 1, "type": "backend", "label": "决策树 5 轮", "sublabel": "追问到理解"},
            {"id": "route", "lane": "pipeline", "col": 2, "type": "backend", "label": "三分支路由", "sublabel": "做 / 查 / 画"},
            {"id": "land", "lane": "pipeline", "col": 3, "type": "frontend", "label": "落地", "sublabel": "核验/拆解/出图"},
        ],
        "edges": [["trigger", "tree"], ["tree", "route"], ["route", "land"]],
    },
    {
        "slug": "niuniu", "title": "牛牛AI · niuniuai.app",
        "lanes": [{"id": "product", "label": "产品 Product"}, {"id": "delivery", "label": "交付 Delivery"}],
        "nodes": [
            {"id": "mt5", "lane": "product", "col": 0, "type": "external", "label": "MT5 终端", "sublabel": "行情/持仓"},
            {"id": "sync", "lane": "product", "col": 1, "type": "backend", "label": "数据同步", "sublabel": "账户+历史"},
            {"id": "ai", "lane": "product", "col": 2, "type": "backend", "label": "AI 引擎", "sublabel": "分析/诊断/复盘"},
            {"id": "features", "lane": "product", "col": 3, "type": "frontend", "label": "四大功能", "sublabel": "助手·诊断·复盘"},
            {"id": "pay", "lane": "delivery", "col": 3, "type": "backend", "label": "订阅支付", "sublabel": "Stripe+双通道"},
            {"id": "deploy", "lane": "delivery", "col": 4, "type": "cloud", "label": "Zeabur 部署", "sublabel": "推送即部署"},
        ],
        "edges": [["mt5", "sync"], ["sync", "ai"], ["ai", "features"], ["features", "pay"], ["pay", "deploy"]],
    },
]


def build(spec):
    focus = [n["id"] for n in spec["nodes"]]
    return {
        "schema_version": 2,
        "diagram_type": "workflow",
        "meta": {
            "title": spec["title"],
            "animation": "trace",
            "visual_preset": "signal-flow",
            "quality_profile": "showcase",
            "views": [{"id": "happy-path", "label": "主路径", "focus": focus, "note": spec["title"] + " 的架构流程（事实源：showcase/project.json）。"}],
        },
        "lanes": spec["lanes"],
        "nodes": spec["nodes"],
        "edges": [{"from": a, "to": b} for a, b in spec["edges"]],
    }


out = "/tmp/arch"
os.makedirs(out, exist_ok=True)
for s in SPECS:
    p = f"{out}/{s['slug']}.workflow.json"
    json.dump(build(s), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", p)
