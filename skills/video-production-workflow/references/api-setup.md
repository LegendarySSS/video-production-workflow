# 视频 API 安装、配置与使用

本说明随技能安装，脚本位于本技能 scripts/video.py，示例位于 assets/。需要 Python 3.10+ 和访问供应商 API、素材地址的网络；脚本只使用标准库，无需 pip 安装依赖。此技能没有内置 API Key、额度、图像生成器或完整剪辑程序。

## Agent 先检查的事项

1. 确认能执行本地 Python、读写项目和访问网络。只有网页浏览或文字输出能力的聊天会话无法运行此脚本；此时提供给使用者在终端执行的命令，不能假装工具已连接。
2. 定位已安装技能的真实 scripts/video.py；安装工具可能采用不同目录或符号链接，不硬编码 ~/.codex/skills。运行脚本时用绝对路径；环境文件、镜头 JSON、任务目录放在用户项目或配置目录，不放入技能安装目录。
3. 只检查 doctor 的状态，不读取或显示密钥文件正文。让使用者在本机终端输入密钥；不要求在聊天、截图或项目 JSON 中提交密钥。
4. 先离线 preview，再依照明确的付费授权 submit 一次。--confirm-spend 是本次创建的授权开关，不估算费用、不限制实际扣费。金额上限需使用供应商控制台的账户/额度控制；没有核定预算不批量提交。
5. 先做动态试镜，完整播放检查后再继续。API succeeded 只表示生成完成，quality_review 仍为 pending，不自动批准角色、动作或口型。

## 供应商与密钥

| provider | 默认模型 | 环境变量 | 账户入口 |
|---|---|---|---|
| kling | Kling 4.0，kling-4.0 | KLING_API_KEY | [可灵开发者控制台](https://kling.ai/dev/api-key) |
| seedance | Seedance 2.0，doubao-seedance-2-0-260128 | ARK_API_KEY | [火山方舟 API Key](https://ark.volcengine.com/region:cn-beijing/apikey) |
| runway | Runway Gen-4.5，gen4.5 | RUNWAYML_API_SECRET | [Runway Dev](https://dev.runwayml.com/) |

只配置一家即可。网页会员与 API 账户权限、额度需要分别核对。此版本可灵使用新加坡官方 API、新版 API Key Bearer 认证；旧版 Access Key/Secret Key 对不能直接填入 KLING_API_KEY。Seedance 使用北京方舟 API。账户需具有对应地区、模型权限与额度；doctor 不会替你开通账户、充值或验证余额。

## 本机安全配置

在本人终端运行，密钥输入不回显。以下命令中的 /absolute/path 表示使用者本机的真实路径，Agent 应填入已定位的实际位置。

```bash
python3 /absolute/path/to/skill/scripts/video.py --env-file /absolute/path/to/project/.env configure --provider kling
```

seedance 或 runway 用户替换 --provider 的值。Windows 可以把 python3 替换为 py -3。环境文件只在本机保存；新建时在 POSIX 系统使用 0600 权限，Windows 另由账户目录权限保护。

多家密钥可在本机编辑器中参照 [密钥格式模板](../assets/api-keys.env.example) 写入同一文件；configure 不覆盖已有文件。脚本只解析上述三个键，不执行 shell 代码；进程中已有同名环境变量优先。不得把模板中的 YOUR_... 原样当成密钥。

离线检查配置：

```bash
python3 /absolute/path/to/skill/scripts/video.py --env-file /absolute/path/to/project/.env doctor --provider kling
```

configured_not_verified 表示存在非空密钥，不代表鉴权、模型权限或额度已验证。环境变量在一个终端设置后，已经运行的 Agent 不一定继承；显式指定同一份 --env-file 可避免这个问题。

## 第一个视频任务

先把对应 assets/*-shot.json 复制到项目中，修改 prompt 及所需画幅。下例在项目目录运行，VIDEO_CLI 是已定位的脚本绝对路径。

```bash
VIDEO_CLI=/absolute/path/to/skill/scripts/video.py
python3 "$VIDEO_CLI" --env-file .env preview --spec shot.json
```

preview 不联网、不花额度；它会显示镜头内容和输入素材地址，含私人参考时不要把输出公开分享。校验通过后，本人确认一次实际生成：

```bash
python3 "$VIDEO_CLI" --env-file .env submit --spec shot.json --job-dir renders/S001-v001 --confirm-spend
python3 "$VIDEO_CLI" --env-file .env status --job-dir renders/S001-v001
python3 "$VIDEO_CLI" --env-file .env wait --job-dir renders/S001-v001 --timeout 600 --poll-interval 60
python3 "$VIDEO_CLI" --env-file .env download --job-dir renders/S001-v001 --output renders/S001-v001.mp4
```

三个供应商共用这组命令，只需更换镜头 JSON 的 provider 和参数。任务目录必须不存在，防止重复提交；每次新候选使用新版本目录。wait 超时不会取消远端任务，可继续 status/wait。download 会先重新查询短期有效的视频地址，再下载；不向素材 CDN 发送 API Key，不覆盖已有输出。

在 PowerShell 中可设置 `$VideoCli = "C:\path\to\skill\scripts\video.py"`，然后使用 `py -3 $VideoCli --env-file .env ...` 运行相同子命令；或直接让具备终端能力的 Agent 执行命令。

## 素材输入与范围

JSON 中 image 是起始画面，last_image 是结尾画面；reference_images 是人物/场景参考，reference_videos 是动作或运镜参考，reference_audio 是声音参考。它们全部使用供应商可访问的 HTTPS 地址。脚本不会把本地路径自动上传，也不会把私人素材自动设为公开；请使用获授权的存储、足够有效期的签名链接或平台允许的素材方式。不支持用户名密码嵌入 URL、非默认端口、data URI 或 asset URI 的此入口输入；这些高级素材类型需要后续专门适配。

### Kling 4.0

- 无素材走 /text-to-video/kling-4.0；有 image、last_image 或 reference_* 走 /omni-video/kling-4.0。
- 素材引用名为 @start、@end、@image_1、@image_2、@video_1 等。提示词明确每张图控制哪个角色、每段视频参考什么。
- 3–30 秒；此入口只开放 720p/1080p，以及 16:9、9:16、1:1、21:9、adaptive。
- 原生音画默认开启。不暴露未核实的关闭开关；静音在后期处理。不接入旧版 JWT 或原始音频 URL；音色 profile 管理、视频编辑和延长不在此版本范围。

### Seedance

- 默认 2.0；还可选择 doubao-seedance-2-0-fast-260128、doubao-seedance-2-0-mini-260615、doubao-seedance-2-5-260628。实际账户需开通所选模型。
- 2.0 系列此入口为 4–15 秒；2.5 为 4–30 秒。分辨率开放 480p/720p/1080p，Fast/Mini 限 720p 及以下。
- audio 对应 generate_audio。首尾帧模式与多模态参考模式分开提交；reference_audio 需要同时有图片或视频。
- 本入口保守限制参考图 9 张、视频 3 段、音频 3 段；文件大小、参考时长、像素等由供应商继续校验，不保证覆盖模型所有功能。
- 含写实人脸素材需按方舟可信模型产物、虚拟人像或授权肖像规则准备。不能默认把其他平台生成的脸直接作为可用参考。

### Runway Gen-4.5

- 无 image 调用 /v1/text_to_video；有 image 调用 /v1/image_to_video，后者为单张首帧。
- 2–10 秒、720p；图生提供 16:9、9:16、1:1、4:3、3:4、21:9，文生仅暴露已核实的 16:9。
- 不接受额外人物多图参考、尾帧、参考视频或原生音频请求，避免静默丢弃。入口将 prompt 限为 1000 个 UTF-16 单元。
- 此视频入口不提供原生配音及口型保证。对白镜头若需要这些能力，另选具备能力的制作路径，不能只补配音就批准。

## 记录、恢复与错误

每个任务目录生成 task.json：保存供应商、模型、输入规格、请求摘要、task_id、状态、输出链接和下载记录；密钥不写入。文件含私人提示词和短期签名地址，按项目素材保护，不提交 Git。下载成功只说明拿到媒体文件，不证明人物动起来了。

- 401/403：核对本机密钥、账户 API 权限及额度，不能通过切换别人的账号解决。
- 429/5xx：查询请求最多有限重试；所有创建请求都不自动重试。
- submission_unknown 或 submitting：连接中断或响应不完整，平台仍可能已受理。先到对应控制台核对，找到真实 ID 后关联原目录：

```bash
python3 "$VIDEO_CLI" --env-file .env attach --job-dir renders/S001-v001 --task-id REAL_TASK_ID
```

关联不会创建新任务或扣费，然后继续 status。没有找到任务时由本人决定下一次尝试，不能自动切换模型/供应商再次扣费。

- rejected：创建被明确拒绝，修改原因后使用新目录再提交，仍需要本次付费授权。
- failed/cancelled/expired：任务终止，查看记录原因；不自动重提或自动退款承诺。
- 网络限制：Agent 的沙箱必须允许出站 HTTPS。没有权限时申请所需网络权限或让本人终端执行；不关闭 TLS 验证。
- 下载失败或链接过期：重跑 download，它会重新查询；支持 --max-bytes 调整单文件限制，默认 2 GiB。只保存识别为 MP4/MOV 的内容；不覆盖现有文件。

退出码：0 命令成功或状态查询成功，2 参数/本机/网络错误，3 等待超时（远端继续），4 查询到终止失败，130 用户中断。submit 的 0 不是动态成片验收通过。

Agent 应在 project.json.generations 中关联任务目录、模型、输入资产和下载文件，保持 quality_review 为 pending，实际播放验收后再更新原制作台账。本脚本不直接改写 project.json，避免覆盖人工决定或同时编辑内容。

## 核对来源与测试边界

接口按 2026-11-02 读取的供应商官方说明实现。API 会变更，升级前先核对来源；拒绝未知模型和不支持参数，避免猜测接口。

- [Kling 4.0 官方 API 手册](https://kling.ai/document-api/api/usage-guide/kling-4-0)
- [Kling API 认证](https://kling.ai/document-api/api/get-started/authentication)
- [Seedance 调用教程](https://docs.volcengine.com/docs/ark/video-generation-tutorial?lang=zh)
- [Seedance 肖像素材规则](https://docs.volcengine.com/docs/ark/seedance-portrait-asset-guide?lang=zh)
- [Runway API 入门](https://docs.dev.runwayml.com/guides/using-the-api/)
- [Runway 输出与下载](https://docs.dev.runwayml.com/assets/outputs/)

自动测试使用模拟响应，覆盖请求、状态、异常恢复与密钥处理；未使用真实密钥进行三家付费生成实测。首次由使用者用本人账户完成一个短镜头验收，不要在此之前宣称端到端效果已经验证。
