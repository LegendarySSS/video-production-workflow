# 视频制作工作流

面向短剧、短片和 MV 的 Agent Skill：剧本、角色一致性、分镜预演、动态镜头制作、验收及项目恢复。

**V0.2.0 已内置可灵 Kling 4.0、Seedance 2.0/2.5、Runway Gen-4.5 的官方视频 API 调用脚本。** 使用者配置自己选用供应商的 API Key 即可提交、查询、等待和下载镜头；不需要同时购买三家服务。API 账户仍需具备模型权限与额度。

几张静帧加配音只能算预演，不能替代要求人物动作与表演的短剧。脚本生成成功后仍须播放验收。

## 运行条件

- 能执行本地命令、读取文件并访问外网的 Agent，或由本人终端运行。
- Python 3.10+；脚本仅用标准库，无需 pip 安装依赖。
- 所选供应商的 API Key、相应模型权限与 API 额度。

**只有网页浏览或文字能力的 ChatGPT 会话不能仅凭 GitHub 链接自动执行脚本。** 此时让 Agent 提供命令，由本人在终端执行，或在具备命令执行能力的环境使用。技能不内置密钥、付费额度、图像生成器或完整剪辑软件。

## 安装 Skill

在支持 skill-installer 的 Codex 中发送：

> 请安装 https://github.com/LegendarySSS/video-production-workflow/tree/main/skills/video-production-workflow 的完整技能，包括 scripts、references 和 assets；保留已有同名技能，更新前先检查差异。

也可以用 Vercel Labs 的 skills 安装器（需 Node.js 22.20+、npm 与 Git）：

```bash
npx skills add LegendarySSS/video-production-workflow --skill video-production-workflow -a codex -g
```

不加 `-g` 为项目级安装。安装后在下一轮调用 `$video-production-workflow`。可手动下载 ZIP，将 skills/video-production-workflow 整个文件夹放入本机 Agent 使用的技能目录，保留所有附件。

已安装旧版时使用安装器更新或比对后替换技能目录，再新开会话；不要覆盖自己的密钥与作品目录。安装器选项见 [官方说明](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)。

## 最快运行：克隆后使用

```bash
git clone https://github.com/LegendarySSS/video-production-workflow.git
cd video-production-workflow
python3 --version
```

以下先以可灵为例；Seedance 和 Runway 只需替换 provider 与示例文件。

### 1. 配置本人的 API Key

```bash
python3 skills/video-production-workflow/scripts/video.py configure --provider kling
python3 skills/video-production-workflow/scripts/video.py doctor --provider kling
```

configure 在本机提示输入，密钥不回显，保存到当前目录 .env；不会覆盖已有文件。doctor 只检查是否配置，不验证权限和余额。不要把真实密钥发给 Agent、提交 Git 或放入镜头 JSON。

| provider | 环境变量 | 获取密钥 | 示例 |
|---|---|---|---|
| kling | KLING_API_KEY | [可灵控制台](https://kling.ai/dev/api-key) | [kling-shot.json](skills/video-production-workflow/assets/kling-shot.json) |
| seedance | ARK_API_KEY | [火山方舟](https://ark.volcengine.com/region:cn-beijing/apikey) | [seedance-shot.json](skills/video-production-workflow/assets/seedance-shot.json) |
| runway | RUNWAYML_API_SECRET | [Runway Dev](https://dev.runwayml.com/) | [runway-shot.json](skills/video-production-workflow/assets/runway-shot.json) |

也可在本机环境中配置同名变量，优先于 .env；多家配置参考 [环境文件模板](skills/video-production-workflow/assets/api-keys.env.example)。已安装技能的 Agent 应定位脚本的真实绝对路径，密钥和任务记录放在独立项目内，详见 [完整配置说明](skills/video-production-workflow/references/api-setup.md)。

### 2. 离线检查输入

```bash
python3 skills/video-production-workflow/scripts/video.py preview --spec skills/video-production-workflow/assets/kling-shot.json
```

这个步骤不联网、不扣费。修改镜头 JSON 可以调整 prompt、duration、aspect_ratio、resolution 和参考素材。三家参数能力不完全一致，脚本会拒绝不支持的输入。

### 3. 创建一次实际生成任务

确认供应商价格及本人授权后执行；此命令会消耗本人的 API 额度：

```bash
python3 skills/video-production-workflow/scripts/video.py submit --spec skills/video-production-workflow/assets/kling-shot.json --job-dir renders/S001-v001 --confirm-spend
python3 skills/video-production-workflow/scripts/video.py wait --job-dir renders/S001-v001 --timeout 600
python3 skills/video-production-workflow/scripts/video.py download --job-dir renders/S001-v001 --output renders/S001-v001.mp4
```

--confirm-spend 表示一次创建授权，不是金额封顶。任务目录已存在时拒绝重复创建；等待超时后继续查询同一任务，不再 submit。素材 URL 需是供应商可读取的 HTTPS 地址，脚本不自动上传本地图片或公开私人素材。

### 4. 继续制作与恢复

```text
按 video-production-workflow 创建短剧项目，使用我已在本机配置的可灵 API。
先定位脚本和环境文件，不读取或显示密钥正文。
完成角色与分镜方案后，先给我看一个动态试镜的请求预览。
根据我明确授权的次数与预算生成，播放验收后再继续，不接受静帧配音替代。
```

只有看到真实视频动作、表演和必要的口型检查结果才能批准镜头。API succeeded 不是质量验收通过。完整影片还需角色资产、镜头制作、声音与剪辑。

## 模型范围与注意事项

- **可灵**：新版 Kling 4.0 API，新加坡接口、API Key Bearer 认证；支持文生与 Omni 多参考/关键帧生成。旧版 Access Key/Secret Key 对不适用本入口。
- **Seedance**：北京方舟 API，支持 2.0、Fast、Mini 和 2.5 的指定 Model ID。含写实人脸参考需按方舟可信素材/肖像规则准备，不能默认任意跨平台角色图都能用。
- **Runway**：Gen-4.5 文生与单首帧图生，当前适配范围为 720p、2–10 秒；此入口不提供原生音频与口型保证。不能只贴配音就将对白镜头判为完成。

详见 [完整安装、配置、素材输入、恢复与排错说明](skills/video-production-workflow/references/api-setup.md)。

## 文件与测试

- [技能入口](skills/video-production-workflow/SKILL.md)
- [API 命令入口](skills/video-production-workflow/scripts/video.py)
- [项目模板](skills/video-production-workflow/assets/project-template.json)
- [动态短剧要求](skills/video-production-workflow/references/dynamic-drama.md)
- [角色与镜头验收](skills/video-production-workflow/references/continuity-and-review.md)
- [使用与交接](docs/usage.md)

```bash
python3 -m unittest discover -s tests -v
```

测试使用模拟 API 和网络响应，覆盖三家协议、任务恢复、防止重复创建、错误处理、下载及密钥保护；**没有使用真实 API Key 进行三家付费生成实测**。请先用自己的账号完成一个短镜头，再扩大生产规模。
