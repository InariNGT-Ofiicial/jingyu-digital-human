# 鲸语 · 二次元数字人

> DeepseekChan 还托着腮，你已经问了下一句。她可以直接接话，让眼前这段动作自然播完。

鲸语让你用自己的角色图、动作和音色搭一个能听、能说、能回应的二次元数字人。H3 提前拍好角色表演，交互时浏览器连续播放这些动作，鲸语根据对话选择下一段。这样，角色可以保持原有画风，开口也无需等视频模型生成下一帧。

**第一个已验证场景是手机浏览器视频电话。** 接通后可以围绕同一件事连续追问，也可以在角色说到一半时插话。一个实例同时服务一个通话席位。默认角色是 DeepseekChan。公开仓库提供可自行生成的示例机器人、动作工作流和通话代码，搭建自己的角色时需要准备角色素材、参考音色和模型权重。

## 角色由哪些部分组成

| 积木 | 使用的模型或代码 | 交给下一步的内容 |
|---|---|---|
| 表演 | Qwen3-VL 编码参考图和动作描述，H3 Ref2VA 生成动作 | 固定机位、首尾能衔接的动作片段，导入浏览器播放器 |
| 听觉 | 浏览器检测说话和停顿，Qwen3-ASR 转写 | 当前轮的文字送入鲸语路由 |
| 应答 | 鲸语匹配台词和动作意图，Qwen2.5 处理开放问题 | 预设语音键，或结合近期对话生成的回答文字 |
| 声音 | 预设台词读取缓存，现答由 CosyVoice2 分段合成 | 可以连续播放的音频和逐句字幕所需的文本位置 |
| 动作与打断 | 浏览器动作调度器、音频播放器和轮次控制 | 新一轮可以立即停止旧回答，当前动作仍能在片段边界自然切换 |

想先看到效果，从下面的本地挥手示例开始。准备自己的形象可以直接看动作素材表，接模型前可先顺着一轮对话读懂接口。[换成自己的形象](#换成自己的形象) · [一通电话里的积木怎样拼起来](#一通电话里的积木怎样拼起来) · [在云实例上部署](#在云实例上部署)

## 先在电脑上看见角色挥手

```sh
git clone https://github.com/InariNGT-Ofiicial/jingyu-digital-human.git
cd jingyu-digital-human
python -m pip install Pillow
python avatar.py --demo
python preview.py
```

需要 Python 3.10+ 和带 libx264 编码器的 FFmpeg。把 `ffmpeg` 加入 PATH，或将 `FFMPEG` 环境变量设为可执行文件路径。打开 <http://127.0.0.1:18980/>，点「轻挥手」，等当前动作自然播完。示例机器人由代码在本机生成。这一步可以在普通电脑上运行。

## 一通电话里的积木怎样拼起来

拿“我想在窗边拍猫，站哪边好？……那我该拉一点窗帘吗？”举例。手机只传入声音；第二句话的“那”依靠前一轮对话才能理解。

```mermaid
flowchart LR
  mic["手机麦克风"] --> vad["浏览器检测说话与停顿"]
  vad -->|"WebSocket · 16 kHz PCM"| asr["Qwen3-ASR 识别"]
  asr --> route["鲸语路由"]
  route -->|"命中合适台词"| bank["缓存语音与动作意图"]
  route -->|"开放问题"| llm["近期对话 + Qwen2.5"]
  llm -->|"按语义分段"| voice["CosyVoice2 合成"]
  bank --> phone["手机声音与字幕"]
  voice -->|"分段音频"| phone
  h3["H3 离线制作"] -->|"九段竖屏 H.264"| player["手机动作播放器"]
  route -->|"状态与动作意图"| player
```

1. **听到一句完整的话。** 浏览器请求回声消除，用播放参考信号辅助判断外放回声。麦克风重采样成 16 kHz 单声道 PCM。一次短暂停顿可以先触发识别草稿，说话继续就放弃相应的预答。最终提交时，Qwen3-ASR-1.7B-hf 把整句转成文字。输入键盘文字时从路由开始。[麦克风与判停](web/call.js) · [回声参考](web/duplex.js) · [服务端](server.py)
2. **决定用预设还是现答。** “挥挥手”这类明确意图命中台词库时，服务端发回录音键和动作意图。问怎么拍猫、再追问窗帘时，鲸语将当轮文字、近期对话和纠正过的条件交给 Qwen2.5-1.5B-Instruct。挂断会结束这次会话的记忆。可选的 JEV 路由仅在显式启用后调用外部服务，默认路径在本机运行。[台词库](dialogue-bank.json) · [路由](router.py) · [上下文](phone_context.py)
3. **把回答说出来。** 预设走缓存 WAV。现答按语义切成可连续朗读的短句，电话进程逐段请求合成服务的 `POST /speak`。CosyVoice2-0.5B 结合文字与参考音色生成语音符号，Flow 生成声学特征，HiFT 声码器输出 24 kHz 波形。服务端用 `voice_part` 把音频和对应的累计字符位置送回浏览器，手机一边播放前段，一边接收后段。字幕根据音频播放时钟在底部逐句显示。[合成服务](synthesis.py) · [播放与字幕](client.js)
4. **让动作接得上。** 准备素材时，Qwen3-VL-32B 编码参考图和动作描述。H3 Ref2VA 配合 Turbo v4 LoRA 先用四步看动作，二采读回缓存、做三维潜空间放大和十二步细化，再由视频 VAE 解码。当电话接通，浏览器根据倾听、思考、说话等状态和重复间隔选择现有片段。角色还在前倾时声音就能接入，画面在片段边界转场。当前路线使用动作片中的面部表情，逐字口型未同步。[H3 工作流](workflows/README.md) · [动作策略](web/motion-policy.json) · [调度器](web/motion-director.js)
5. **插话之后接着聊。** 确认来电者开始说话时，浏览器停止旧音频并清空字幕，通知服务器切换轮次；旧轮迟到的结果会被丢弃。已经开始播放的分段用于估算已听到的文字范围，下一轮根据这段上下文接话。复盘里的“末音到首声”是浏览器估算，受判停、模型、网络和播放设备影响。[通话协议处理](server.py) · [打断测试](tests/test_interrupted_dialogue.py)

## 换成自己的形象

1. 在 `character.json` 填角色呼号。准备一张正视来电图和九段相同机位、相同画幅的动作。首尾使用同一个回正姿势，前后片段才能自然衔接。
2. 素材目录中按下表命名 MP4，执行 `python avatar.py --clips "/path/to/my-clips" --poster "/path/to/front.png"`。命令会在本地数据目录生成桌面、手机和首播版本。再次打开预览，分别点选每个动作。
3. 在 `dialogue-bank.json` 修改台词、别名和关联动作。`web/motion-policy.json` 控制状态可选动作和最短重复间隔。更换呼号或改词后重新生成预设语音。更换参考音色时执行 `python prepare_lines.py --refresh`。

| 动作 | MP4 文件名 | 动作 | MP4 文件名 |
|---|---|---|---|
| 正视呼吸 | front-breathe.mp4 | 舒展肩膀 | h3-shoulders.mp4 |
| 整理领结 | h3-ribbon.mp4 | 点头 | acknowledge.mp4 |
| 看消息 | read-request.mp4 | 挥手 | wave.mp4 |
| 倾听 | listen.mp4 | 托腮思考 | think.mp4 |
| 浅笑 | smile.mp4 | | |

已有视频可以直接导入。需要自己生成动作时，看 [H3 挥手工作流](workflows/README.md)。

## 接入语音和对话

原项目实测的参考部署为 Linux、NVIDIA 48 GB vGPU、CUDA 12.8 和 PyTorch 2.8.0。动作预生成与电话服务可以分时运行，通话阶段直接解码 H.264。模型、参考声音和角色素材由搭建者自行准备。

| 模型 | 实际职责 | 默认目录 |
|---|---|---|
| [Qwen3-ASR-1.7B-hf](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf) | 将浏览器的 16 kHz 单声道语音转成文字 | .local/models/asr |
| [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | 判断短句是否适合预设，为连续追问生成带上下文的回答 | .local/models/decision |
| [CosyVoice2-0.5B](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B) | 从文字、参考音色生成 24 kHz 语音，整句按语义分段衔接播放 | .local/models/cosyvoice |

### 在云实例上部署

从云平台控制台开机，复制该实例的 SSH 登录命令。登录后运行 `nvidia-smi` 查看显存和驱动，运行 `df -h` 确认数据盘挂载。在 AutoDL 上，常见数据盘是 `/root/autodl-tmp`。在挂载的数据盘中检出本仓库，再执行下面的安装命令。已有九段动作可以直接导入；同卡制作 H3 动作时，先让生成任务结束并释放模型，再启动电话模型。

```sh
# AutoDL 示例，其他平台替换为实际数据盘挂载点
cd /root/autodl-tmp
git clone https://github.com/InariNGT-Ofiicial/jingyu-digital-human.git
cd jingyu-digital-human
```

在 Linux 上单独准备两个 Python 环境。电话环境使用 Transformers 5.16.1，语音环境使用 Transformers 4.51.3。以下命令从仓库根目录执行，`python3.10` 也可换成兼容的解释器。

```sh
python3.10 -m venv .local/call-env
.local/call-env/bin/pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
.local/call-env/bin/pip install -r requirements-call.txt
.local/call-env/bin/hf download Qwen/Qwen3-ASR-1.7B-hf --local-dir .local/models/asr
.local/call-env/bin/hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir .local/models/decision
.local/call-env/bin/hf download FunAudioLLM/CosyVoice2-0.5B --local-dir .local/models/cosyvoice
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git .local/CosyVoice
git -C .local/CosyVoice checkout 074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc
git -C .local/CosyVoice submodule update --init --recursive
```

按 [CosyVoice 安装说明](https://github.com/FunAudioLLM/CosyVoice/tree/074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc) 配好独立语音环境，包括 Matcha-TTS、语音前端与 CUDA 版 PyTorch。确认该环境能用 `CosyVoice2-0.5B` 生成一段声音，然后安装 `aiohttp==3.12.15`、`transformers==4.51.3`。把一段有权使用的人声 WAV 放到 `.local/reference.wav`。

离线运行时，从 [WeText 规则库](https://modelscope.cn/models/pengzhendong/wetext) 取得 `zh/tn` 和 `en/tn` 下的 `tagger.fst`、`verbalizer.fst`，保留相对目录放入 `.local/models/wetext`。已有规则可设置 `JINGYU_WETEXT`。这样首次启动就能直接加载中英文规范化规则。

按顺序启动。下表中的 Python 分别指相应环境里的解释器。第一个和第三个进程保持运行。

| 顺序 | 环境和命令 | 成功时看到 |
|---|---|---|
| 1 | 语音环境：`python synthesis.py` | 预热后输出 READY，语音与快速回答服务监听本机 18983 |
| 2 | 电话环境：`python prepare_lines.py` | 本地生成台词 WAV 和校验清单 |
| 3 | 电话环境：`python server.py` | 输出 READY，在电脑打开 <http://127.0.0.1:18982/> |

语音合成采用与演示相同的 CosyVoice 2 链路，实际音色取决于参考录音和 `JINGYU_VOICE_STYLE`。已有权重可设置 `JINGYU_ASR`、`JINGYU_DECISION`、`JINGYU_COSY_MODEL`、`JINGYU_COSY_SOURCE`、`JINGYU_VOICE_REFERENCE` 指向本机路径。自定义数据目录用 `JINGYU_DATA`。设置和默认值见 [settings.py](settings.py)。运行前请完成动作导入或生成示例。

## 手机接听和验收

1. 在本机数据目录 `.local/mobile-origin.txt` 中写一行自己的 HTTPS 源地址，例如 `https://call.example.org`，结尾不带斜杠。重启 `server.py`，它会生成 `.local/mobile-invite`。
2. 将该 HTTPS 源反向代理到 `127.0.0.1:6006`，启用 WebSocket 升级，保留原浏览器 Origin。18982 和 18983 只供本机使用。手机访问 `https://call.example.org/#你的邀请码`，允许麦克风后接听。
   使用云平台自定义服务时，填写控制台分配的完整 HTTPS 源（含非标准端口）。自管域名且 Caddy 与电话服务位于同一台机器时，可使用下面的 Caddyfile 配置。域名要指向这台服务器，入口应能正常提供 HTTPS。

   ```caddyfile
   call.example.org {
       reverse_proxy 127.0.0.1:6006
   }
   ```

3. 围绕同一主题连续追问，在角色回答时开口插话。挂断后进入「通话复盘」查看识别文本、末音到首声的逐轮估算和打断次数。录音、实际网络、浏览器和 GPU 都影响延迟。

只开动作预览和运行文本逻辑测试均无需 GPU。运行测试可执行 `python -m unittest discover -s tests`。

## 项目来源与许可

鲸语数字人的代码从鲸语 Live2D 仓库的数字人分支独立出来。VoxEMW 是早期研究实时数字人时参考的项目，本仓库采用 H3 预生成二次元表演与鲸语实时对话编排。[鲸语原始源码快照](https://github.com/InariNGT-Ofiicial/jingyu-live2d-agent/tree/09ec496a341757b15d04c21d407af5fcbc50ba32/digital-human) · [VoxEMW](https://github.com/emwstudio/VoxEMW)

代码使用 MIT 许可证，模型及自行导入的角色素材遵循各自许可。[MIT 许可证](LICENSE.txt)
