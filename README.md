# 视频批量缩略图拼图生成器（PotPlayer风格，GPU加速）

## 功能简介

- 批量处理本地或网络路径下的所有视频文件
- 每个视频只生成一张4x4（16帧）拼图大图，风格类似PotPlayer
- 左上角自动显示视频信息（文件名、分辨率、时长、编码等）
- 每个小图左下角带时间戳
- 强制使用NVIDIA显卡（CUDA）进行GPU解码（仅支持h264/hevc编码）
- 支持.mp4、.avi、.mkv、.mov、.wmv、.flv、.webm等常见格式
- 输出目录默认为 `thumbnails_grid`

---

## 环境依赖

- Python 3.7+
- ffmpeg-python
- opencv-python
- numpy
- pillow
- tqdm
- 你的ffmpeg需支持cuvid（CUDA），可用 `ffmpeg -codecs | findstr cuvid` 检查
- 需有NVIDIA显卡和驱动

安装依赖：
```bash
pip install -r requirements.txt
```

---

## 使用方法

### 1. 批量处理整个文件夹
```bash
python main.py "\\192.168.0.110\USB-raidz2\porn"
```

### 2. 处理单个视频
```bash
python main.py "你的文件.mp4"
```

### 3. 指定输出目录
```bash
python main.py "你的文件夹" -o my_thumbnails
```

---

## 输出示例

- 所有拼图大图保存在 `thumbnails_grid` 目录下
- 每个视频只生成一张大图，命名为 `原视频名.jpg`

```
thumbnails_grid/
├── hhd800.com@RCTD-667.jpg
├── MUKC-104ch.jpg
├── ...
```

---

## 注意事项

- 只支持h264/hevc编码的视频，其他编码自动跳过
- 需本地ffmpeg支持cuvid（CUDA），否则无法GPU加速
- 只输出合并大图，不会生成单帧缩略图
- 运行前建议清空旧的 `thumbnails` 目录，避免混淆
- 网络路径需有访问权限

---

## 故障排查

- Pillow 10+ 兼容性已修复，如遇 `textsize` 报错请升级代码
- 如遇"未检测到NVIDIA显卡"，请检查驱动和nvidia-smi
- 如遇"编码不支持"，请确认视频为h264/hevc
- 如需支持更多格式或自定义拼图样式，请联系开发者

---

## 许可证

MIT License 