import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import io
import time  # 引入时间模块，用于防报错

# --- 1. 页面配置 ---
# 修改点：网页标题改为“个性化海报分析”
st.set_page_config(page_title="个性化海报分析", layout="wide")
st.title("🚀 个性化海报分析")

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("输入 Google Gemini API Key", type="password")
    
    st.markdown("### 🧠 模型选择")
    # 默认使用 Gemini 1.5 Flash (速度快，免费额度高)
    model_name = st.text_input(
        "模型名称", 
        value="models/gemini-1.5-flash" 
    )
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"API Key 配置出错: {e}")

# --- 3. 核心逻辑区 ---

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📤 素材上传")
    st.info("💡 提示：系统会自动忽略海报底部的固定信息栏，聚焦分析主视觉设计。")
    uploaded_images = st.file_uploader("1. 上传海报图片", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    uploaded_data = st.file_uploader("2. 上传业务数据表 (Excel/CSV)", type=['xlsx', 'csv'])
    
    df_metrics = None
    if uploaded_data:
        try:
            df_metrics = pd.read_excel(uploaded_data) if uploaded_data.name.endswith('.xlsx') else pd.read_csv(uploaded_data)
            st.success(f"✅ 数据表加载成功: {len(df_metrics)} 条记录")
        except Exception as e:
            st.error(f"❌ 数据读取失败: {e}")

# --- 核心函数：定制化分析 ---
def analyze_image_with_gemini(image, filename, model_target):
    model = genai.GenerativeModel(model_target)
    
    # --- 定制化 Prompt：提取特征 ---
    prompt = """
    你是一位资深的视觉设计师和数据分析师。请分析这张转介绍/裂变海报。
    
    ⚠️ **重要指令**：
    1. **排除干扰**：完全忽略底部的固定信息栏（二维码、个人头像、昵称、固定Logo等）。只分析海报的**主视觉区域**。
    2. **专业提取**：请严格按照以下维度进行特征提取。
    
    请提取以下维度，并返回**纯 JSON 格式**数据：
    {
        "filename": "文件名",
        "main_color": "主色调 (如: 红色系, 暖黄系, 冷白系)",
        "subject_type": "主体类型 (如: 单人全身, 半身特写, 人物+场景)",
        "model_gender": "模特性别 (男/女/多人)",
        "model_expression": "模特表情 (如: 大笑, 专注, 搞怪, 惊讶)",
        "shot_scale": "景别 (如: 远景, 中景, 近景特写)",
        "key_visual_elements": "关键前景元素 (如: 手绘线条, 3D图标, 涂鸦, 气泡)",
        "scene_atmosphere": "场景氛围 (如: 春节喜庆, 冬日户外, 书房学习)",
        "copy_type": "文案类型 (如: 学习干货, 节日祝福, 名人名言)",
        "copy_layout": "文案排版 (如: 上下结构, 标题居中, 杂志风)",
        "font_style": "字体风格 (如: 手写感, 宋体, 圆体)",
        "emotion_vibe": "情感氛围 (如: 喜庆, 温馨, 焦虑, 活泼)"
    }
    """
    
    try:
        response = model.generate_content([prompt, image])
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        data['filename'] = filename
        return data
    except Exception as e:
        st.error(f"分析 {filename} 失败: {e}")
        return None

with col2:
    st.subheader("🤖 智能分析中心")
    start_btn = st.button("🚀 开始 AI 视觉拆解", type="primary", disabled=not (uploaded_images and api_key))

    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []

    if start_btn:
        st.session_state.analysis_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total = len(uploaded_images)
        for idx, img_file in enumerate(uploaded_images):
            status_text.text(f"正在分析 ({idx+1}/{total}): {img_file.name} ...")
            
            # --- 核心分析过程 ---
            image = Image.open(img_file)
            result = analyze_image_with_gemini(image, img_file.name, model_name)
            
            if result:
                st.session_state.analysis_results.append(result)
            
            # --- 🔥 关键修改：强制休息 2 秒，防止报错 ---
            time.sleep(2)
            # ---------------------------------------

            progress_bar.progress((idx + 1) / total)
        
        status_text.text("✅ 所有海报分析完成！")
        progress_bar.empty()

    if st.session_state.analysis_results:
        st.markdown("### 📊 视觉特征矩阵")
        df_vision = pd.DataFrame(st.session_state.analysis_results)
        
        # 尝试自动合并数据
        final_df = df_vision
        if df_metrics is not None:
            metric_key = None
            for col in df_metrics.columns:
                if any(x in str(col) for x in ['名', 'name', 'Name', '文件']):
                    metric_key = col
                    break
            
            if metric_key:
                df_vision['filename'] = df_vision['filename'].astype(str)
                df_metrics[metric_key] = df_metrics[metric_key].astype(str)
                final_df = pd.merge(df_vision, df_metrics, left_on='filename', right_on=metric_key, how='left')
                st.info(f"成功关联业务数据表，匹配列：{metric_key}")
            else:
                st.warning("未在Excel中找到‘文件名/名称’列，仅展示视觉数据。")

        st.dataframe(final_df, use_container_width=True)

        st.markdown("---")
        if st.button("💡 生成全维度策略报告 (含执行Brief)"):
            with st.spinner("AI 正在策划下一期海报方案..."):
                report_model = genai.GenerativeModel(model_name)
                data_csv = final_df.to_csv(index=False)
                
                # --- 关键修改：报告生成的 Prompt ---
                # 增加了【人物设定固定为8岁】的强约束
                report_prompt = f"""
                你是一席首席增长官 (CGO) 兼 创意总监。请根据这份【海报视觉特征-转化数据表】撰写执行报告。
                
                数据表如下：
                {data_csv}
                
                请输出以下两部分内容：

                ### 第一部分：📊 数据归因洞察
                * 简要分析哪些视觉元素（颜色、模特表情、场景）带来了高转化。

                ### 第二部分：🚀 下一步行动指令 (Actionable Design Briefs)
                请策划 **3个** 具体的裂变海报主题方案。
                
                ⚠️ **人物设定强制约束**：
                **所有方案中的【人物设定】必须固定为：8岁左右的小学生（具体的性别、发型、服饰可变，但年龄感必须一致）。**

                #### 方案 A (稳健型 - 复刻高转化特征)
                * **📸 背景图拍摄/生图提示词**：
                    * **人物设定**：(必须是8岁左右孩子，描述其具体的穿着、发型)
                    * **场景与光影**：(描述具体的环境、光线方向)
                    * **动作与神态**：(描述具体的动作，如拿书、大笑、奔跑)
                * **✨ 装饰元素建议**：(例如：涂鸦风格的星星、手绘线条、特定的图标)
                * **✍️ 推荐文案 (20字内)**：(一句符合该场景和情绪的短文案，例如：“2026，让成长的每一步都算数！”)

                #### 方案 B (创新型 - 尝试新风格)
                * **📸 背景图拍摄/生图提示词**：(请提供一套全新的、与方案A截然不同的人物、场景、动作描述，人物仍为8岁)
                * **✨ 装饰元素建议**：(匹配该新风格的元素)
                * **✍️ 推荐文案 (20字内)**：(一句配合该新风格的文案)

                #### 方案 C (特定场景/节日型)
                * **📸 背景图拍摄/生图提示词**：(针对即将到来的节日或特定学习场景的详细画面描述，人物为8岁)
                * **✨ 装饰元素建议**：(匹配的氛围元素)
                * **✍️ 推荐文案 (20字内)**：(强相关文案)
                """
                
                try:
                    res = report_model.generate_content(report_prompt)
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"报告生成失败: {e}")
