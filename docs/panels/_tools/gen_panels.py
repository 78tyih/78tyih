#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_panels.py — 把「一份紧凑项目 spec」编译成 live-panel 的 config JSON。

为什么要有这一层：live-panel 的坐标是画布像素，手写一张 1500 行；
我们的项目有 N 个。所以：spec（几十行事实）→ 生成器 → config → mp4/GIF → README。
事实来自各仓库的 showcase/project.json（单一事实源），动效计数一律标注「示意」。
"""
import json, math, os, sys

W = H = 1080
M = 48
CW = W - 2 * M          # 984 content width
GAP = 24

CREDIT = "事实源：各仓库 showcase/project.json · 动效引擎 live-panel (ythx-101/live-panel-skill) · 计数为示意"


LH = 24          # light-pastel lineHeight: every line is exactly 24 px tall
PADT = 16        # box padding-top (padding-bottom is 0 in the template)


def rows_for(n):
    if n <= 4:
        return 1
    if n <= 8:
        return 2
    return 3


def layout(n):
    """Return list of (x, y, w, h) for n stage boxes, serpentine.

    Each row is centred on its own item count, and the column index is row-local —
    a short last row must not reuse the full row's column pitch (that pushes boxes
    off the canvas).
    """
    R = rows_for(n)
    per = math.ceil(n / R)
    bw = (CW - (per - 1) * GAP) / per
    bh = {1: 204, 2: 190, 3: 140}[R]
    pitch = {1: 0, 2: bh + 34, 3: bh + 26}[R]
    y0 = 156
    out = []
    for i in range(n):
        r = i // per
        local = i - r * per
        cnt = min(per, n - r * per)
        row_w = cnt * bw + (cnt - 1) * GAP
        # even rows: centred; odd rows: right-aligned so the carriage-return wire
        # from the previous row's last box drops straight down instead of diagonally
        x0 = M + (CW - row_w) / 2 if r % 2 == 0 else M + CW - row_w
        c = local if r % 2 == 0 else cnt - 1 - local   # serpentine, row-local
        out.append((x0 + c * (bw + GAP), y0 + r * pitch, bw, bh))
    return out, bw, bh


def connectors(boxes, bw):
    """Polylines between consecutive boxes (right→left on even rows, left→right on odd, drop between rows)."""
    paths = []
    for i in range(len(boxes) - 1):
        x1, y1, w1, h1 = boxes[i]
        x2, y2, w2, h2 = boxes[i + 1]
        same_row = abs(y1 - y2) < 1
        if same_row:
            if x2 > x1:                     # going right
                pts = [[x1 + w1, y1 + h1 / 2], [x2 - 14, y1 + h1 / 2], [x2, y2 + h2 / 2]]
            else:                           # going left
                pts = [[x1, y1 + h1 / 2], [x2 + w2 + 14, y1 + h1 / 2], [x2 + w2, y2 + h2 / 2]]
        else:                               # carriage return: drop straight down
            cx = x1 + w1 / 2
            pts = [[cx, y1 + h1], [cx, y2 - 12], [x2 + w2 / 2, y2], [x2 + w2 / 2, y2 + 6]]
        paths.append(pts)
    return paths


def box_stage(b, i, stage, color, fill, max_sub=2):
    x, y, w, h = b
    lines = [
        {"t": "%02d" % (i + 1), "c": color, "b": 1, "size": 15},
        {"t": stage["name"], "c": "ink", "b": 1, "size": 20},
        "",
    ]
    for sub in stage.get("lines", [])[:max_sub]:
        lines.append({"t": sub, "c": "fg", "size": 15, "align": "left"})
    return {"type": "box", "x": x, "y": y, "w": w, "h": h, "color": color, "fill": fill,
            "pad": [PADT, 16, 16], "align": "center", "lines": lines}


def build(spec):
    stages = spec["stages"]
    n = len(stages)
    boxes, bw, bh = layout(n)
    stage_bottom = max(b[1] + b[3] for b in boxes)

    machines = {}
    elements = []

    # ---- header ----
    elements.append({"type": "text", "x": M, "y": 62, "w": CW, "align": "left",
                     "t": spec["title"], "size": 30, "b": 1, "c": "ink"})
    elements.append({"type": "text", "x": M, "y": 100, "w": CW, "align": "left",
                     "t": spec["sub"], "size": 16, "c": "dim"})
    elements.append({"type": "rule", "x": M, "y": 126, "w": CW})

    # ---- lanes (work units: running → done) + log rows ----
    lane_ids = []
    for k, ln in enumerate(spec.get("lanes", [])):
        lid = "u%d" % k
        lane_ids.append(lid)
        machines[lid] = {"type": "lane", "period": ln.get("period", 9),
                         "run": ln.get("run", 6), "off": ln.get("off", 3),
                         "busy": ln["busy"], "done": ln["done"], "phase": k,
                         "log": {"who": ln["who"], "c": ln.get("c", "bl"),
                                 "msgs": [[m, t] for m, t in ln["msgs"]]}}

    # ---- stage boxes ----
    palette = ["bl", "gn", "yl", "pu", "tl", "or", "mc", "rd"]
    fills = {"bl": "blf", "gn": "gnf", "yl": "ylf", "pu": "puf", "tl": "tlf",
             "or": "orf", "mc": "mcf", "rd": "rdf"}
    R = rows_for(n)
    for i, (st, b) in enumerate(zip(stages, boxes)):
        col = st.get("c") or palette[i % len(palette)]
        elements.append(box_stage(b, i, st, col, fills[col], max_sub=1 if R == 3 else 2))

    # ---- wires with packets ----
    for i, pts in enumerate(connectors(boxes, bw)):
        elements.append({"type": "path", "points": pts, "color": "gy", "width": 2.2, "r": 10,
                         "arrow": True,
                         "flow": {"period": 1.3 + 0.17 * (i % 3), "offsets": [0, 0.55],
                                  "color": "pk", "tail": True}})

    # ---- facts panel (static, real numbers only) ----
    fy = stage_bottom + 28
    fh = PADT + LH * (len(spec["facts"]) + 1) + 12
    elements.append({"type": "box", "x": M, "y": fy, "w": CW, "h": fh, "color": "gy", "fill": "gyf",
                     "pad": [14, 18, 18], "align": "left",
                     "lines": [{"t": "实测 · 纪律（静态事实，非动效生成）", "c": "dim", "b": 1, "size": 15}] +
                              [{"runs": [{"t": k, "c": "fg", "b": 1, "size": 16},
                                         {"t": "  " + v, "c": "dim", "size": 15}]}
                               for k, v in spec["facts"]]})

    # ---- log ----
    ly = fy + fh + 22
    elements.append({"type": "log", "x": M, "y": ly, "w": CW, "rows": 4,
                     "padTop": 16, "padBottom": 26, "padLeft": 18,
                     "title": "run log", "titleX": 30, "titleW": 150,
                     "cols": [{"key": "time", "x": 0}, {"key": "who", "x": 110},
                              {"key": "m", "x": 240}, {"key": "g", "x": 700}]})

    # ---- status bar: lane states + delivered packets (illustrative) ----
    sy = ly + 4 * 24 + 16 + 26 + 34
    row = []
    for k, ln in enumerate(spec.get("lanes", [])):
        lid = lane_ids[k]
        row.append({"w": 130, "align": "left", "runs": [{"t": ln["who"], "c": "dim", "size": 15}]})
        row.append({"w": 210, "align": "left", "runs": [{"v": lid, "c": ln.get("c", "bl"), "b": 1, "size": 15}]})
    elements.append({"type": "box", "x": M, "y": sy, "w": CW, "h": 54, "color": "gy", "fill": "wh",
                     "pad": [0, 18, 18], "align": "left",
                     "lines": [{"items": row + [
                         {"grow": 1},
                         {"w": 250, "align": "right", "runs": [
                             {"t": "packets ", "c": "dim", "size": 15},
                             {"v": "packets", "c": "pk", "b": 1, "size": 15},
                             {"t": " (示意)", "c": "dim", "size": 13}]}]}]})

    return {
        "meta": {"title": spec["title"], "lang": "zh-CN"},
        "canvas": {"width": W, "height": H, "duration": spec.get("duration", 20), "fps": 25, "preroll": 0},
        "theme": {"preset": "light-pastel", "colors": spec.get("colors", {})},
        "clock": {"start": "09:30:00", "rate": 1},
        "credit": {"text": spec.get("credit", CREDIT), "y": H - 26, "size": 13},
        "machines": machines,
        "elements": elements,
    }


SPECS = [
    # ---------- 0. 全景：Repo Showcase OS ----------
    {
        "slug": "overview",
        "title": "Repo Showcase OS · 八步流水线",
        "sub": "每个仓库走同一套流水线：事实先于文案，展示页中英 × 日夜，最后落到 Pages 与记忆",
        "stages": [
            {"name": "事实盘点", "lines": ["读仓库真实代码/文档", "不靠猜"]},
            {"name": "事实包", "lines": ["project.json 单一事实源", "evidence.md 证据分级"]},
            {"name": "四问 README", "lines": ["解决什么 / 什么场景结果", "什么结构 / 能复用什么"]},
            {"name": "展示页", "lines": ["单文件 ZH/EN × 日夜", "?lang=&theme= 深链"]},
            {"name": "独立目录推送", "lines": ["/tmp 浅克隆", "不碰共享工作区 .git"]},
            {"name": "GitHub Pages", "lines": ["main /docs", "curl 验收非 404"]},
            {"name": "About 设置", "lines": ["一句话 + homepage"]},
            {"name": "记忆沉淀", "lines": ["坑表进 SKILL.md"]},
        ],
        "facts": [
            ("组件与设计系统", "sarah-motion · deepseek-color · dsh-deepseek-color · sera-subtitle-factory"),
            ("技能与工具", "mojo-plate-design · trae-skills · CC-statusline-kit · niuniu-ai-official"),
            ("证据分级", "Observed 已实见 / Inferred 待复验 / Unknown 未验证"),
            ("已踩坑", "README 的 <video> 被剥离（上限 GIF）· jsDelivr 对 .html 返回纯文本"),
        ],
        "lanes": [
            {"who": "流水线", "c": "bl", "busy": "生成展示包中", "done": ["已上线"],
             "msgs": [["事实包写完才动笔写文案", "顺序"], ["展示页单文件自包含", "零依赖"], ["独立目录推送，不碰共享 .git", "纪律"]], "period": 11, "run": 7, "off": 4},
            {"who": "验收", "c": "gn", "busy": "curl 验收中", "done": ["200 OK"],
             "msgs": [["Pages 上线后必须 curl 验非 404", "纪律"], ["截图前先确认不是自建 404 页", "踩过"], ["证据分 Observed / Inferred / Unknown", "分级"]], "period": 13, "run": 8, "off": 5},
        ],
        "duration": 22,
    },

    # ---------- 1. 牛牛AI ----------
    {
        "slug": "niuniu",
        "title": "牛牛AI · niuniuai.app",
        "sub": "连接 MT5 的 AI 交易助手：订阅制产品，同时是一套可抄走的订阅制全栈参考实现",
        "stages": [
            {"name": "MT5 终端", "lines": ["行情 / 持仓 / 成交", "账户数据"]},
            {"name": "数据同步", "lines": ["账户 + 历史", "Supabase 存"]},
            {"name": "AI 引擎", "lines": ["分析 / 诊断 / 复盘"]},
            {"name": "四大功能", "lines": ["AI 助手 · 行情分析", "持仓诊断 · 交易复盘"]},
            {"name": "订阅与支付", "lines": ["Stripe Checkout", "微信 / 支付宝 demo"]},
            {"name": "Zeabur 部署", "lines": ["Docker node:22", "main 推送即部署"]},
        ],
        "facts": [
            ("前端", "React + Vite + Tailwind"),
            ("后端", "双同源：api/ (Vercel) + cloud-functions/api/ (EdgeOne)"),
            ("价格", "¥19.9 试用 3 天 / ¥980 月 / ¥2,018 季 / ¥6,980 年"),
            ("认证", "Supabase：邮箱 / 手机 / 重置密码"),
        ],
        "lanes": [
            {"who": "诊断", "c": "bl", "busy": "读持仓中", "done": ["已出诊断"],
             "msgs": [["持仓诊断只描述风险，不做收益承诺", "合规"], ["结算走 mark_order_paid RPC", "幂等"], ["前端 React + Vite + Tailwind", "栈"]], "period": 11, "run": 7, "off": 4},
            {"who": "订单", "c": "gn", "busy": "轮询支付中", "done": ["已到账"],
             "msgs": [["Stripe 为测试模式，微信/支付宝为 demo", "现状"], ["订阅到期自动降级为试用态", "状态机"]], "period": 15, "run": 9, "off": 6},
        ],
    },

    # ---------- 2. sarah-motion ----------
    {
        "slug": "sarah",
        "title": "sarah-motion · 动效组件库",
        "sub": "每个组件都是时间的纯函数：可跳转、可逐帧、循环闭合零像素差，含金融 UI 组件族",
        "stages": [
            {"name": "时间 t", "lines": ["seek(t) 任意跳转", "逐帧可控"]},
            {"name": "弹簧引擎", "lines": ["纯函数，无状态累积"]},
            {"name": "组件族", "lines": ["报价 / 杠杆 / 回放", "金融 UI 补齐"]},
            {"name": "节拍网格", "lines": ["120 BPM"]},
            {"name": "60fps 运动模糊", "lines": ["一个形状十种状态"]},
            {"name": "规格图谱", "lines": ["spec-atlas 数据 × 6", "金融 × 6"]},
        ],
        "facts": [
            ("核心不变量", "循环闭合 0 px 差 · 任意 t 可跳转 · 逐帧可复现"),
            ("补齐的空白", "通用组件库长期缺金融/交易展示组件"),
            ("规格图谱", "Drawdown meter 为新提案，待批准才进引擎"),
        ],
        "lanes": [
            {"who": "渲染", "c": "pu", "busy": "逐帧渲染中", "done": ["闭包校验通过"],
             "msgs": [["首帧与末帧逐像素比对", "验收"], ["组件是时间的纯函数，不是表演", "设计"], ["循环闭合 0 px 差", "指标"]], "period": 10, "run": 6, "off": 4},
            {"who": "节拍", "c": "yl", "busy": "对齐 120 BPM", "done": ["已对齐"],
             "msgs": [["节拍网格让多组件同步不靠手调", "方法"], ["运动模糊只在快速段出现", "克制"]], "period": 14, "run": 8, "off": 6},
        ],
    },

    # ---------- 3. sera-subtitle-factory ----------
    {
        "slug": "ssf",
        "title": "Sera Subtitle Factory",
        "sub": "像设计 UI 组件一样设计字幕：永远单行、逐词跟着声音走、active 词不推挤邻词",
        "stages": [
            {"name": "音频 / 文本", "lines": ["素材输入"]},
            {"name": "词级对齐", "lines": ["每个词有时间码"]},
            {"name": "Recipe (JSON)", "lines": ["样式即数据", "复制即复刻"]},
            {"name": "渲染", "lines": ["单行 · 逐词跟随", "active 不推挤邻词"]},
            {"name": "在线工作台", "lines": ["studio/ 直接在浏览器改"]},
        ],
        "facts": [
            ("技术栈", "TypeScript · Next.js · zustand · framer-motion"),
            ("三条铁律", "永远单行 · 逐词跟随语音 · active 词不推挤邻词"),
            ("样式资产", "Recipe = JSON，跨项目可复制"),
        ],
        "lanes": [
            {"who": "对齐", "c": "tl", "busy": "词级对齐中", "done": ["已对齐"],
             "msgs": [["对齐精度决定逐词动效的观感", "关键"], ["单行铁律：永不换行", "铁律"]], "period": 12, "run": 7, "off": 5},
            {"who": "渲染", "c": "bl", "busy": "套 Recipe 中", "done": ["已导出"],
             "msgs": [["Recipe 改一次，全片同步", "单一事实源"], ["active 词不推挤邻词", "铁律"]], "period": 16, "run": 9, "off": 7},
        ],
    },

    # ---------- 4. deepseek-color ----------
    {
        "slug": "dsc",
        "title": "deepseek-color · Agent 设计技能",
        "sub": "给 AI Agent 装上审美：5 套克制色卡 × 12 个零依赖 HTML 骨架 × 8 换肤组合",
        "stages": [
            {"name": "5 色卡", "lines": ["莫兰迪式克制配色"]},
            {"name": "12 版式骨架", "lines": ["零依赖 HTML"]},
            {"name": "8 换肤组合", "lines": ["色卡 × 骨架实时试穿"]},
            {"name": "Agent 安装", "lines": ["Kimi Work · Codex", "Claude Code · WorkBuddy"]},
        ],
        "facts": [
            ("运行时依赖", "0"),
            ("配色纪律", "base 70–85% / muted 10–25% / accent <5%"),
            ("在线化", "25 个自包含 HTML 全部可直接打开"),
        ],
        "lanes": [
            {"who": "试穿", "c": "pu", "busy": "换肤试穿中", "done": ["已定色"],
             "msgs": [["accent 永远 <5%，克制是纪律不是风格", "规则"], ["色彩三档：base / muted / accent", "结构"]], "period": 12, "run": 7, "off": 5},
            {"who": "骨架", "c": "bl", "busy": "套版式中", "done": ["已生成"],
             "msgs": [["零依赖：不引 CDN、不引框架", "约束"], ["12 个骨架都能直接双击打开", "验收"]], "period": 15, "run": 8, "off": 7},
        ],
    },

    # ---------- 5. dsh-deepseek-color ----------
    {
        "slug": "dsh",
        "title": "dsh-deepseek-color · DSH 皮肤包",
        "sub": "五套纯 token 皮肤，把 DeepSeek Color 色卡带进 DeepSeek Harness",
        "stages": [
            {"name": "5 纯 token 皮肤", "lines": ["只有 CSS 变量"]},
            {"name": "CSS 变量映射", "lines": ["不碰 DOM 结构"]},
            {"name": "DSH 皮肤中心", "lines": ["官方更新不失效"]},
        ],
        "facts": [
            ("安全等级", "零补丁 · 零脚本 · 零背景媒体 —— 最安全的一类皮肤"),
            ("为什么", "多数皮肤靠补丁 DOM / 注入 JS / 换背景，随官方更新失效"),
            ("来源", "色卡体系复用 deepseek-color"),
        ],
        "lanes": [
            {"who": "皮肤", "c": "tl", "busy": "映射 token 中", "done": ["已生效"],
             "msgs": [["只改变量，不改结构 → 官方更新不破", "设计"], ["五套皮肤互相切换零位移", "验收"]], "period": 13, "run": 7, "off": 5},
            {"who": "校验", "c": "gn", "busy": "比对渲染中", "done": ["无差异"],
             "msgs": [["渲染前后逐像素比对", "验收"], ["不注入脚本 = 最安全的一类皮肤", "安全"]], "period": 17, "run": 9, "off": 8},
        ],
    },

    # ---------- 6. mojo-plate-design ----------
    {
        "slug": "mojo",
        "title": "mojo-plate-design · 雕版图谱设计技能",
        "sub": "近黑暖纸 + 骨白墨 + 唯一酸绿：steps() 印刷动效，含完整 replica",
        "stages": [
            {"name": "mojo.trade 逆向", "lines": ["只学模式，不搬资产"]},
            {"name": "8 条非协商规则", "lines": ["字体三件套固定"]},
            {"name": "4 段版式蓝图", "lines": ["雕版式分区"]},
            {"name": "招牌动效", "lines": ["steps(2-4,end)", "胶片颗粒 · boil 扰动"]},
            {"name": "replica", "lines": ["可打开的一比一复刻页"]},
        ],
        "facts": [
            ("色板", "paper #0b0b09 · ink #e9e5d4 · accent #cdf546"),
            ("字体三件套", "Instrument Serif 斜体 · Inter 300 · JetBrains Mono"),
            ("动效", "steps(2-4,end) 印刷感 · 70–90s 天体自转 · 硬偏移阴影"),
            ("合规", "学习用途逆向，字标与标本插图归原作者，商用需替换"),
        ],
        "lanes": [
            {"who": "排版", "c": "yl", "busy": "按蓝图排版中", "done": ["已出片"],
             "msgs": [["酸绿只出现一次：唯一强调色", "规则"], ["标本插图为内容层，不是装饰层", "全感官"]], "period": 10, "run": 6, "off": 4},
            {"who": "动效", "c": "gn", "busy": "steps() 定格中", "done": ["已定格"],
             "msgs": [["印刷感来自 steps() 的阶梯，不是平滑曲线", "方法"],
                      ["胶片颗粒与 boil 扰动叠在版面上", "质感"]], "period": 16, "run": 9, "off": 7},
        ],
    },

    # ---------- 7. trae-skills ----------
    {
        "slug": "trae",
        "title": "trae-skills · 四个管住 Agent 的技能",
        "sub": "想法澄清决策树 · 反诈骗查链核验 · 博主知识拆解 · 可视化路由",
        "stages": [
            {"name": "触发", "lines": ["按情境进对应技能"]},
            {"name": "决策树 5 轮", "lines": ["追问到共享理解"]},
            {"name": "三分支路由", "lines": ["做 / 查 / 画"]},
            {"name": "落地", "lines": ["核验链上 / 拆解知识 / 出图"]},
        ],
        "facts": [
            ("技能数", "4（其中 grill 决策树、链上核验在此完整实现）"),
            ("决策树", "5 轮提问 → 共享理解 → 3 分支路由"),
            ("链上核验字段", "TxHash · From · To · Block Height · Timestamp"),
            ("知识评分权重", "insight 20 · evergreen 20 · evidence/novelty/argument/density 各 15"),
        ],
        "lanes": [
            {"who": "grill", "c": "or", "busy": "追问中", "done": ["共享理解"],
             "msgs": [["先问清再动手，管住 Agent 的冲动", "目的"], ["5 轮提问 → 共享理解 → 3 分支", "流程"]], "period": 12, "run": 7, "off": 5},
            {"who": "核验", "c": "rd", "busy": "查链中", "done": ["已核验"],
             "msgs": [["只认链上五字段，不认截图", "铁律"], ["核验结论必须可复查", "留档"], ["查不到就说不确定", "诚实"]], "period": 15, "run": 9, "off": 6},
        ],
    },
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/panels"
    os.makedirs(out, exist_ok=True)
    for spec in SPECS:
        cfg = build(spec)
        d = os.path.join(out, spec["slug"])
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "config.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
        print("wrote", p, len(cfg["elements"]), "elements,", len(cfg["machines"]), "machines")


if __name__ == "__main__":
    main()
