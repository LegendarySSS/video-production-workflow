# 视频制作工作流

面向短剧、短片和 MV 的 Agent Skill：把创作、角色资产、分镜、生成记录与验收保存为可交接、可恢复的项目。

它提供制作方法与项目模板，视频生成、配音和剪辑按使用者实际接入的工具执行；不附带模型、付费额度或素材，不承诺人物绝对一致或一键成片。

## 快速安装

### 方式一：让 Codex 安装

将下面这段话发送给支持 skill-installer 的 Codex：

> 请使用 skill-installer 安装 https://github.com/LegendarySSS/video-production-workflow/tree/main/skills/video-production-workflow 的技能，保留已有同名技能；遇到冲突先告诉我。

### 方式二：一条命令安装

安装了 Node.js 22.20 或更新版本、npm 和 Git 的用户可执行：

```bash
npx skills add LegendarySSS/video-production-workflow --skill video-production-workflow -a codex -g
```

按提示检查安装目标并确认。去掉 `-g` 可安装到当前项目。`skills` 是 Vercel Labs 维护的第三方安装工具，命令参数见其 [官方说明](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)。

### 方式三：手动安装

下载本仓库的 ZIP，将 `skills/video-production-workflow` 整个文件夹放入 Codex 使用的 skills 目录。不要只复制 SKILL.md，参考文档和模板也必须保留。避免覆盖已有同名技能；自定义安装目录按本机配置处理。

在下一轮对话调用 `$video-production-workflow`；若未发现，检查目录层级并新开聊天或重启应用。

## 第一次使用

```text
使用 $video-production-workflow 帮我建立一个视频项目。
我还没确定短片还是 MV，也没有生成工具。
先帮我确定一个小规模试作方向，保存简报和项目进度，不调用付费服务。
```

已有创意时：

```text
使用 $video-production-workflow 制作一个 45 秒悬疑短片项目。
竖屏，一个主角、两个场景，无对白，项目放在当前工作区。
先完成创作简报、角色设定和试镜方案，角色确认后再进入完整分镜。
```

## 制作过程

```mermaid
flowchart LR
    A[创作简报] --> B[剧本或音乐结构]
    B --> C[角色与场景资产]
    C --> D[关键帧与预演]
    D --> E[逐镜头制作与验收]
    E --> F[剪辑与交付]
    F --> G[项目归档与复盘]
```

- 角色控制：建立身份标准图，区分固定特征与场次状态，先试镜再批量制作。
- 连续性：检查单镜头运动，以及相邻镜头的持物、视线、动作与空间关系。
- 可恢复：把阶段、决定、选中素材和下一步保存在 project.json。
- 可追溯：每次候选保留输入、版本和检查结果，达到次数或费用上限后停止调用。
- 无生成工具也可用：先输出文案、分镜和外部执行清单，回传素材后继续。

## 后续操作

```text
继续指定目录下的项目，先读取 project.json，完成下一项任务。
只改 S006 的动作，保留其他要求，检查与前后镜头的衔接。
为我指定的视频生成工具整理输入包，未执行项目记录为 awaiting_external。
整理项目交接：当前进度、选中素材、缺失文件、访问依赖和下一步。
```

## 文件结构

- [技能入口](skills/video-production-workflow/SKILL.md)
- [项目模板](skills/video-production-workflow/assets/project-template.json)
- [短剧、短片、MV 分支](skills/video-production-workflow/references/production-modes.md)
- [角色与镜头验收](skills/video-production-workflow/references/continuity-and-review.md)
- [项目数据约定](skills/video-production-workflow/references/project-data.md)
- [详细使用说明](docs/usage.md)

技能目录保存规则；各作品另建项目目录，不将客户素材、私人偏好、密钥或成片写入通用技能。

当前版本：0.1.0。已完成文件结构与引用检查；实际视频质量、跨工具表现和端到端制作需要使用者以真实样片验证。
