import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips
import os
import tempfile
import random

# ===========================
# 1. 核心工具函数：智能裁切
# ===========================
def resize_and_crop(clip, target_ratio_type):
    """
    根据目标比例，自动对视频进行中心裁切 (Center Crop)，保证填满画面不留黑边
    """
    w, h = clip.size
    current_ratio = w / h
    
    # 定义目标分辨率 (基于720p基准，兼顾速度与画质)
    target_resolution = (1280, 720) # 默认 16:9
    
    if target_ratio_type == "9:16 (抖音/Shorts)":
        target_resolution = (720, 1280)
        target_ratio = 9 / 16
    elif target_ratio_type == "1:1 (Instagram/朋友圈)":
        target_resolution = (720, 720)
        target_ratio = 1
    else: # 16:9
        target_resolution = (1280, 720)
        target_ratio = 16 / 9

    # 逻辑：如果当前更宽，就切掉两边；如果当前更高，就切掉上下
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        crop_x1 = (w - new_w) // 2
        crop_x2 = crop_x1 + new_w
        clip = clip.crop(x1=crop_x1, y1=0, x2=crop_x2, y2=h)
    else:
        new_h = int(w / target_ratio)
        crop_y1 = (h - new_h) // 2
        crop_y2 = crop_y1 + new_h
        clip = clip.crop(x1=0, y1=crop_y1, x2=w, y2=crop_y2)
        
    return clip.resize(newsize=target_resolution)

# ===========================
# 2. 页面配置
# ===========================
st.set_page_config(page_title="智能视频混剪 Pro", page_icon="🎬", layout="wide")

st.title("🎬 智能视频混剪 Pro")
st.markdown("### 现在的你，是导演。")

# ===========================
# 3. 侧边栏：控制面板
# ===========================
with st.sidebar:
    st.header("⚙️ 导演设置")
    
    # --- 功能 1: 画幅尺寸 ---
    aspect_ratio = st.radio(
        "1. 画幅比例 (Output Size)",
        ["9:16 (抖音/Shorts)", "16:9 (横屏/YouTube)", "1:1 (Instagram/朋友圈)"]
    )
    
    st.divider()
    
    # --- 功能 2: 时长控制 (包含随机裁剪) ---
    st.markdown("**2. 时长控制**")
    duration_mode = st.radio("模式", ["智能分配 (指定总时长)", "保持原长 (全部拼接)"])
    
    target_total_duration = 0
    enable_random_cut = False # 默认关闭

    if duration_mode == "智能分配 (指定总时长)":
        col1, col2 = st.columns([2, 1])
        with col1:
            target_total_duration = st.number_input("期望成品总秒数", value=30, step=5, min_value=5)
        with col2:
            st.write("秒")
        
        # [随机裁剪开关]
        enable_random_cut = st.checkbox("🎲 随机截取片段 (Random Cut)", value=False, help="勾选后，系统将从素材中间随机选取一段，而不是只取开头。让视频更具动感！")
        if enable_random_cut:
            st.caption("💡 已启用随机：系统会自动在素材中寻找最精彩的片段（随机位置）。")
        else:
            st.caption("💡 默认模式：系统将截取每个素材的开头部分。")

    st.divider()

    # --- 功能 3: 智能剪辑 ---
    st.markdown("**3. 智能增强**")
    enable_shuffle = st.checkbox("随机打乱顺序 (Shuffle)", value=False, help="打乱素材的播放先后顺序")
    enable_crossfade = st.checkbox("启用电影级转场 (Crossfade)", value=True, help="添加 0.5秒 叠化转场")

# ===========================
# 4. 主区域：上传与处理
# ===========================
uploaded_files = st.file_uploader("拖入素材 (支持多选 MP4)", type=["mp4"], accept_multiple_files=True)

if uploaded_files:
    file_count = len(uploaded_files)
    st.info(f"🎞️ 已加载 {file_count} 个片段。")
    
    # 动态显示计算结果
    allocated_duration = 0
    if duration_mode == "智能分配 (指定总时长)" and file_count > 0:
        allocated_duration = target_total_duration / file_count
        st.success(f"⚡ 计算结果：为了凑够 {target_total_duration} 秒，每个视频将截取约 {allocated_duration:.1f} 秒。")

    if st.button("🚀 开始智能渲染", type="primary"):
        progress_bar = st.progress(0)
        status_box = st.empty()
        
        try:
            clips = []
            temp_files = [] 
            
            # --- 步骤 1: 准备与计算 ---
            status_box.text("正在分析视频队列...")
            
            file_list = list(uploaded_files)
            if enable_shuffle:
                random.shuffle(file_list)

            # --- 步骤 2: 逐个处理 ---
            for idx, uploaded_file in enumerate(file_list):
                # 保存临时文件
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tfile.write(uploaded_file.read())
                temp_files.append(tfile.name)
                
                # 加载视频
                clip = VideoFileClip(tfile.name)
                
                # [核心逻辑] 时长截取 (支持随机)
                if duration_mode == "智能分配 (指定总时长)":
                    # 只有当视频本身比需要分配的时间长，才需要截取
                    if clip.duration > allocated_duration:
                        if enable_random_cut:
                            # === 随机截取 ===
                            max_start_time = clip.duration - allocated_duration
                            random_start = random.uniform(0, max_start_time)
                            clip = clip.subclip(random_start, random_start + allocated_duration)
                            st.toast(f"片段 {idx+1}: 随机选取了 {random_start:.1f}s - {random_start + allocated_duration:.1f}s 位置")
                        else:
                            # === 固定开头 ===
                            clip = clip.subclip(0, allocated_duration)
                
                # [核心逻辑] 尺寸裁切
                clip = resize_and_crop(clip, aspect_ratio)
                
                # [核心逻辑] 智能转场
                if enable_crossfade:
                    if clip.duration > 0.6:
                        clip = clip.crossfadein(0.5)
                
                clips.append(clip)
                
                status_box.text(f"正在智能处理第 {idx+1}/{file_count} 个片段...")
                progress_bar.progress(int((idx + 1) / file_count * 40))

            # --- 步骤 3: 渲染输出 ---
            status_box.text("正在进行蒙太奇合成...")
            
            if clips:
                padding = -0.5 if enable_crossfade else 0
                final_clip = concatenate_videoclips(clips, method="compose", padding=padding)
                
                # 最终时长兜底修正
                if duration_mode == "智能分配 (指定总时长)":
                   if final_clip.duration > target_total_duration + 3:
                       final_clip = final_clip.subclip(0, target_total_duration)

                output_path = "output.mp4"
                final_clip.write_videofile(
                    output_path, 
                    codec="libx264", 
                    audio_codec="aac", 
                    preset="ultrafast",
                    threads=4,
                    fps=24
                )
                
                progress_bar.progress(100)
                status_box.success("✅ 智能混剪完成！")

                # --- 步骤 4: 预览与交付 ---
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.video(output_path)
                with col2:
                    st.write("### 导出中心")
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="📥 下载成品视频",
                            data=file,
                            file_name="smart_cut_video.mp4",
                            mime="video/mp4"
                        )
                    
                    # [新增] 针对手机用户的温馨提示
                    st.info("📱 **手机用户请注意：**\n\n1. **安卓**：下载后通常直接出现在相册的'下载'分类中。\n2. **iPhone**：视频会保存在'文件'APP的'下载'文件夹中，需手动点击'分享' -> '保存视频'才能存入相册。")
                    
            else:
                st.error("没有有效的视频片段可供处理。")

            # 清理资源
            for clip in clips:
                clip.close()
                del clip
            if 'final_clip' in locals():
                final_clip.close()
            for tf in temp_files:
                try: os.unlink(tf)
                except: pass

        except Exception as e:
            st.error(f"发生错误: {str(e)}")
            st.caption("提示: 建议上传的视频时长不要太短。")