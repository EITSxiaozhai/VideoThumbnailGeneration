#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频缩略图生成脚本
支持从网络路径读取视频文件并批量生成缩略图
"""

import os
import sys
import ffmpeg
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import argparse
import subprocess
from tqdm import tqdm

def has_nvidia_gpu():
    try:
        result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception:
        return False

def get_video_info(video_path):
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = float(video_stream['duration'])
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        nb_frames = int(video_stream.get('nb_frames', 0))
        r_frame_rate = video_stream['r_frame_rate']
        fps = eval(r_frame_rate)
        size = os.path.getsize(video_path)
        codec = video_stream['codec_name']
        return {
            'duration': duration,
            'width': width,
            'height': height,
            'fps': fps,
            'nb_frames': nb_frames,
            'size': size,
            'filename': os.path.basename(video_path),
            'codec': codec
        }
    except Exception as e:
        print(f"获取视频信息失败: {e}")
        return None

def extract_frames_ffmpeg_gpu(video_path, num_frames):
    info = get_video_info(video_path)
    if not info:
        return []
    duration = info['duration']
    codec = info['codec']
    if codec not in ['h264', 'hevc']:
        print(f"[警告] {video_path} 编码为{codec}，不支持GPU解码，自动跳过。")
        return []
    cuvid_codec = codec + '_cuvid'
    timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
    frames = []
    for t in timestamps:
        try:
            input_kwargs = {'ss': t}
            out, _ = (
                ffmpeg
                .input(video_path, **input_kwargs, hwaccel='cuda', vcodec=cuvid_codec)
                .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
            )
            img = np.asarray(bytearray(out), dtype=np.uint8)
            frame = cv2.imdecode(img, cv2.IMREAD_COLOR)
            frames.append((frame, t))
        except Exception as e:
            print(f"提取帧失败: {e}")
    return frames

def make_grid(frames, grid_size=(4,4), thumb_size=(320,180), info=None):
    grid_w, grid_h = grid_size
    thumb_w, thumb_h = thumb_size
    margin = 10
    font = None
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    out_w = grid_w * thumb_w + margin * 2
    out_h = grid_h * thumb_h + margin * 2 + 120
    out_img = Image.new('RGB', (out_w, out_h), (245,245,245))
    draw = ImageDraw.Draw(out_img)
    if info:
        info_lines = [
            f"文件名: {info['filename']}",
            f"大小: {info['size']/1024/1024:.2f}MB", 
            f"分辨率: {info['width']}x{info['height']}",
            f"时长: {int(info['duration']//60):02d}:{int(info['duration']%60):02d}",
            f"FPS: {info['fps']:.2f}",
            f"编码: {info['codec']}"
        ]
        for i, line in enumerate(info_lines):
            draw.text((margin, margin + i*24), line, fill=(50,50,50), font=font)
    for idx, (frame, t) in enumerate(frames):
        if frame is None:
            continue
        row = idx // grid_w
        col = idx % grid_w
        x = margin + col * thumb_w
        y = margin + 120 + row * thumb_h
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        frame_pil = frame_pil.resize((thumb_w, thumb_h), Image.LANCZOS)
        out_img.paste(frame_pil, (x, y))
        ts = f"{int(t//3600):02d}:{int((t%3600)//60):02d}:{int(t%60):02d}"
        bbox = draw.textbbox((0, 0), ts, font=font)
        ts_w = bbox[2] - bbox[0]
        ts_h = bbox[3] - bbox[1]
        draw.rectangle([x+5, y+thumb_h-ts_h-8, x+5+ts_w+8, y+thumb_h-5], fill=(0,0,0,180))
        draw.text((x+9, y+thumb_h-ts_h-6), ts, fill=(255,255,255), font=font)
    return out_img

def process_video(video_path, output_dir):
    info = get_video_info(video_path)
    if not info:
        print(f"无法获取视频信息: {video_path}")
        return False
    print(f"正在处理: {video_path}")
    frames = extract_frames_ffmpeg_gpu(video_path, 16)
    if not frames or len(frames) < 1:
        print(f"帧提取失败: {video_path}")
        return False
    grid_img = make_grid(frames, grid_size=(4,4), thumb_size=(320,180), info=info)
    out_name = Path(video_path).stem + ".jpg"
    out_path = Path(output_dir) / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grid_img.save(str(out_path), quality=95)
    print(f"已保存: {out_path}")
    return True

def process_directory(input_dir, output_dir):
    input_path = Path(input_dir)
    video_files = []
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if Path(file).suffix.lower() in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']:
                video_files.append(str(Path(root) / file))
    print(f"找到 {len(video_files)} 个视频文件")
    for video_file in tqdm(video_files, desc="生成拼图"):
        try:
            process_video(video_file, output_dir)
        except KeyboardInterrupt:
            print("用户中断，已停止。")
            sys.exit(1)
        except Exception as e:
            print(f"处理失败: {video_file}, 错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PotPlayer风格视频缩略图拼图生成器（强制GPU解码，仅合并大图）')
    parser.add_argument('input_path', help='输入路径 (本地目录或单个视频)')
    parser.add_argument('-o', '--output', help='输出目录', default='thumbnails_grid')
    args = parser.parse_args()

    input_path = args.input_path
    output_dir = args.output

    if not has_nvidia_gpu():
        print('未检测到NVIDIA显卡或nvidia-smi不可用，无法使用GPU解码！')
        sys.exit(1)

    if os.path.isdir(input_path):
        process_directory(input_path, output_dir)
    else:
        process_video(input_path, output_dir)
