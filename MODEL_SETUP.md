# DeepseekChan 公开模型下载与组装

只想看角色表演，从第一节开始。想用手机和她聊天，接着做第二节。想让自己的角色出镜，再做第三节。动作在制作阶段生成一次，通话时浏览器播放已有的 MP4，因此搭电话可以省下整套 H3 权重。[鲸语独立仓库](https://github.com/InariNGT-Ofiicial/jingyu-digital-human) · [夸克项目素材，提取码 Up9Z](https://pan.quark.cn/s/fd7642532ef9)

## 一、在普通电脑预览九组动作

把分享目录里的 `01-鲸语源码与H3工作流.zip` 和 `02-DeepseekChan九组动作.zip` 解压到同一目录。已有 Git 仓库的读者只需把 02 解压到仓库根目录。检查 `preview.py` 和 `.local/` 同级，在这里用 Python 3.10+ 执行 `python preview.py`。打开 <http://127.0.0.1:18980/>，先点挥手，再点托腮思考，观察当前动作播完后怎样切换。此步骤下载的模型数为零。

## 二、接通实时对话

手机发送麦克风音频，Qwen3-ASR 转成文字。鲸语命中预设时可以直接播放缓存语音；遇到开放问题，中控结合前文生成回答，CosyVoice2 用你的参考音色逐段合成。回复音频可以先播放，当前动作在片段边界切换。下表路径均以鲸语仓库根目录为起点。

| 用途 | 上游下载或配置入口 | 默认放置位置 |
|---|---|---|
| 听懂用户 | [Qwen3-ASR-1.7B-hf 完整目录](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf/tree/main) | `.local/models/asr/` |
| 合成角色语音 | [CosyVoice2-0.5B 完整目录](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B/tree/main) 和 [配套代码版本](https://github.com/FunAudioLLM/CosyVoice/tree/074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc) | 权重放 `.local/models/cosyvoice/`，代码含子模块放 `.local/CosyVoice/`，自己的参考音放 `.local/reference.wav` |
| 离线文本规范化 | [WeText 规则文件](https://modelscope.cn/models/pengzhendong/wetext/files) | `.local/models/wetext/` 下保留 `zh/tn/` 和 `en/tn/`，各放 `tagger.fst` 与 `verbalizer.fst` |
| 云端中控 | [DeepSeek API](https://api-docs.deepseek.com/) | 两个进程设 `JINGYU_CONTROLLER=deepseek`，电话进程配置 `DEEPSEEK_API_KEY`，无需对话模型权重 |
| 本地中控（可选） | [Qwen2.5-1.5B-Instruct 完整目录](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/main) | `.local/models/decision/`，两个进程设 `JINGYU_CONTROLLER=local` |

1. 在 Linux 云实例的数据盘检出仓库，解压 02。按仓库的云部署命令创建电话环境和语音环境，分别使用 Transformers 5.16.1 和 4.51.3。下载表中的完整模型目录，保留配置、分词器和子目录。语音环境按指定 CosyVoice 提交安装，包括 Matcha-TTS 子模块。[可复制的安装和下载命令](https://github.com/InariNGT-Ofiicial/jingyu-digital-human#在云实例上部署)
2. 准备一段有权使用的人声 WAV。两个终端选同一个中控。终端一用语音环境运行 `python synthesis.py`，等到 `READY`（默认端口 18983）。终端二用电话环境运行 `python prepare_lines.py` 生成预设语音，再运行 `python server.py`（默认端口 18982）。换参考音后用 `python prepare_lines.py --refresh` 重建缓存。
3. 在实例本机打开 <http://127.0.0.1:18982/>。手机端使用自己的 HTTPS 域名，把通话入口反向代理到实例本机 6006，开启 WebSocket，并按仓库说明配置允许的源和邀请码。先问一个开放问题，再用“那第二种怎么做？”连续追问，播放中途插一次话。这样可分别检查识别、上下文、动态合成和打断。[手机接听配置](https://github.com/InariNGT-Ofiicial/jingyu-digital-human#手机接听和验收)

## 三、用 MiniMax H3 重做角色动作

以下是仓库挥手工作流实际引用的五个文件。下载链接固定到上游版本。目标路径相对**运行工作流的 ComfyUI 根目录**。前四项约 42.49 GB，加上二采放大器共约 43.18 GB（十进制，仅权重）。下载放大器后请按表中目标文件名保存，两者名字不同。

| 用途 | 固定版本下载 | 保存到 ComfyUI 下 |
|---|---|---|
| H3 Ref2VA 基座，从角色图生成动作 | [下载 INT8 基座](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/4b53a35191437de05370da548e59aeabe2a5a09a/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors) | `models/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` |
| Qwen3-VL-32B，编码参考画面和动作描述 | [下载 NVFP4 AWQ 编码器](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/4b53a35191437de05370da548e59aeabe2a5a09a/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) | `models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` |
| 视频 VAE，将潜变量解码为画面 | [下载 FP16 视频 VAE](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/4b53a35191437de05370da548e59aeabe2a5a09a/vae/minimax_h3_video_vae_fp16.safetensors) | `models/vae/minimax_h3_video_vae_fp16.safetensors` |
| Turbo v4 LoRA，供少步采样使用 | [下载 step600 EMA](https://huggingface.co/drbaph/MiniMax-H3-Turbo-Lora-ComfyUI/resolve/bb2bc497cbaca89dadd0bcf1856eed4f8275be20/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors) | `models/loras/minimax_h3_turbo_v4_step600_ema_pruned_comfyui.safetensors` |
| 二采用的三维潜空间放大器 | [下载 conv_v1 FP16](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/resolve/85a0187096046badc0a71ab6bd6be182ab06c0f4/minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_fp16.safetensors) | `models/latent_upscale_models/minimax_h3_latent_upscaler_3d_fp16.safetensors` |

**装节点。** 使用带 MiniMax H3 原生支持的 ComfyUI。按各节点仓库说明安装到该实例的 `custom_nodes/` 并用同一 Python 环境安装依赖。四组节点分别负责采样调度、缓存、两遍潜变量处理和放大。安装后重启 ComfyUI，默认监听本机 8188。[ComfyUI](https://github.com/Comfy-Org/ComfyUI) · [YCNodes](https://github.com/yichengup/ComfyUI-YCNodes-MiniMax-H3) · [ClipStream](https://github.com/AraneaQwQ/ComfyUI-H3-ClipStream) · [T8](https://github.com/T8mars/comfyui-minimax-h3-audio-T8) · [LBH 三维放大节点](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler)

**准备五张图。** 在 `ComfyUI/input/role/` 放入自己的正视图 `front.png`，复制一份作为回正图 `pose_end.png`。另外画三张同机位的动作引导图，命名为 `pose20.png`、`pose29.png`、`pose38.png`。让手势依次变化，保持脸、背景、景深和画幅一致。

**先看四步动作，再做十二步细化。** 在鲸语仓库的 `workflows/` 下执行 `python submit.py wave-first.json`。脚本先检查节点，再返回任务号。等队列完成，在 `ComfyUI/output/role/` 检查首采视频和本次的缓存名称。把 `wave-finish.json` 中的 `finish_load.inputs.latent_path` 对准该缓存（首次通常为 `role/cache_00001.safetensors`），再执行 `python submit.py wave-finish.json`。检查同目录中以 `finish` 开头的成片。[两份工作流与提交脚本](https://github.com/InariNGT-Ofiicial/jingyu-digital-human/tree/main/workflows)

**接回鲸语。** 把验过的挥手成片命名为 `wave.mp4`，放入备齐九段源视频的素材目录。安装 Pillow（`python -m pip install Pillow`），准备好 FFmpeg（带 libx264），在鲸语仓库根目录运行 `python avatar.py --clips "/path/to/my-clips" --poster "/path/to/front.png"`，再用 `python preview.py` 检查挥手、收手和回待机。只换一个动作时，其余八段沿用自己的原素材。手机通话和桌面预览都使用导入后的版本。[九段文件名和角色设置](https://github.com/InariNGT-Ofiicial/jingyu-digital-human#换成自己的形象)
