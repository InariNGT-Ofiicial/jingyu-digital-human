# 用 MiniMax H3 制作角色的挥手动作

MiniMax H3 是 MiniMax 发布的音视频生成模型。本工程采用 **MiniMax H3 Base Ref2VA** 参考素材生成路径。角色正视图固定人物与构图，姿势图规定挥手的中间位置，结束引导让手收回。这里的二采由下面的 ComfyUI 图完成，手机通话里的新台词另由 CosyVoice2 现场合成。[MiniMax H3 官方项目](https://github.com/MiniMax-AI/MiniMax-H3) · [官方模型页与许可](https://huggingface.co/MiniMaxAI/MiniMax-H3)

`wave-first.json` 与 `wave-finish.json` 是 ComfyUI API 格式。来自一次实际挥手制作的首采与二采。首遍使用四步采样并保存潜变量，第二遍读取缓存，用 H3 三维潜空间放大模型和十二步细化生成成片。Qwen3-VL-32B 对参考画面与提示词编码，H3 Ref2VA 与 Turbo v4 LoRA 生成动作，视频 VAE 解码画面。

准备兼容 MiniMax H3 参考视频、引导帧、潜变量片段缓存及 3D 放大节点的 ComfyUI 环境。基座、编码器和视频 VAE 分别使用 `minimax_h3_ref2va_pruned_int8_convrot.safetensors`、`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`、`minimax_h3_video_vae_fp16.safetensors`。Turbo 与放大模型的精确文件名见图中的 `lora_name`、`model_name`。仓库分发工作流和提交工具。MiniMax H3 权重适用上游 Community License，量化、LoRA、节点和个人引导素材分别依其来源获取。[MiniMax 官方集成索引](https://github.com/MiniMax-AI/awesome-minimax-h3-integration)

把自己的正面角色图放入 `ComfyUI/input/role/front.png`。另存相同回正图为 `pose_end.png`，把三个手势引导图放为 `pose20.png`、`pose29.png`、`pose38.png`。从仓库根目录进入 `workflows/`，先提交 `wave-first.json`，在输出目录确认 `role/cache_00001.safetensors` 已生成，再提交 `wave-finish.json`。同目录再次运行时，检查二采的 `finish_load.inputs.latent_path` 确实指向本次缓存。

```sh
python submit.py wave-first.json
# 在 ComfyUI 完成首采、确认缓存后
python submit.py wave-finish.json
```

可以 SSH 登录云实例，在同机执行以上命令。提交脚本默认连接 `127.0.0.1:8188`，先读 `GET /object_info` 检查节点，再向 `POST /prompt` 发送工作流。返回的 `prompt_id` 是队列任务号，可在 ComfyUI 队列或 `GET /history/<prompt_id>` 确认输出。若采用 SSH 端口转发，可用 `--url http://127.0.0.1:<本地转发端口>` 指定入口。

将最终单机位竖屏 MP4 命名为 `wave.mp4`。其他动作复用这两个工作流，分别修改动作描述、中间姿势、种子和输出前缀。眼睛、肩膀、窗框和光照均应在首尾连续。动作验完后按[主指南](../README.md)导入。
