# ESP32 AI Dashboard — 界面设计

为 ESP32 + 三色墨水屏（400×300，横向）开发板设计的仪表盘界面。像素 / 终端复古风格，配色克制素雅，参考 Claude 的极简观感，并严格贴合墨水屏 **黑 / 白 / 红** 三色物理限制。

> 本仓库这一部分是**界面设计稿**（HTML 原型），用于确定视觉与布局，之后再落到固件里绘制。

---

## 预览

设计以 **Design Component**（`.dc.html`）形式交付，可直接用浏览器打开：

```
AI Dashboard v2.dc.html   ← 当前版本（像素 / 终端风）
AI Dashboard.dc.html      ← v1（极简素雅版，留档）
support.js                ← DC 运行时（请勿手改）
```

双击 `AI Dashboard v2.dc.html` 即可在浏览器查看。界面每秒跳动的倒计时、自动刷新闪屏、终端光标均为实时渲染。

---

## 界面内容

**用量监控**
- **Claude** / **Codex** 两张卡片：Daily / Weekly 用量百分比 + 进度条、重置倒计时
- 每张卡片底部：`MODEL`（最常用模型）、`TOTAL USED`（累计用量）、`REQUESTS`（请求数）及同比变化

**系统与环境**
- **Server Status**：CPU / RAM / DISK 占用条、负载、在线时长、ONLINE 状态灯
- **Weather**：温度、体感、湿度、风向 + 24h 趋势像素折线
- **自动刷新**：底部状态条显示刷新率与 `NEXT mm:ss` 倒计时，到点触发墨水屏刷新闪屏

**日程**
- **To-do**：紧凑单行列表，完成 / 未完成状态
- **Calendar**：月历网格，今日实心高亮、待办到期日描边标注

---

## 设计规格

| 项目 | 值 |
|---|---|
| 画布 | 400×300，横向（对应固件 `SCREEN_W=400, SCREEN_H=300`, rotation 1）|
| 配色 | 纸底 `#EFE9DD` / 墨黑 `#23201B` / 强调珊瑚红 `#B5573A` |
| 拉丁字体 | [Pixelify Sans](https://fonts.google.com/specimen/Pixelify+Sans)（宽体游戏像素）|
| 中文字体 | [方舟像素 Ark Pixel 12px](https://github.com/TakWolf/ark-pixel-font)（OFL，方正像素）|
| 风格 | 像素 / 终端，扫描线、方块进度条、闪烁光标、像素小螃蟹 logo |

可调项（Tweaks）：刷新间隔、扫描线开关、天气趋势开关。

---

## 版本记录

- **v2** — 像素 / 终端风；新增 Calendar；缩小 To-do；删除 Notes；修复 footer 与 Server Status 重叠；拉丁换 Pixelify Sans、中文换方舟像素；左上角改为像素小螃蟹。
- **v1** — 极简素雅版（Newsreader + IBM Plex Mono），留作对照。

---

## 字体授权

- Pixelify Sans — OFL-1.1
- 方舟像素 / Ark Pixel — OFL-1.1，保留字体保留名称「方舟像素 / Ark Pixel」

界面内数据均为占位示例，接固件时替换为设备实际读数。
