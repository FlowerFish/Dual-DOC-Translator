import streamlit as st
import fitz  # PyMuPDF
from googletrans import Translator
import base64
import io
from PIL import Image
import numpy as np

def main():
    st.set_page_config(page_title="PDF閱讀器與翻譯器", layout="wide")
    st.title("PDF閱讀器與翻譯器")

    # 初始化 session state
    if 'pdf_doc' not in st.session_state:
        st.session_state.pdf_doc = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'zoom_factor' not in st.session_state:
        st.session_state.zoom_factor = 2.0
    if 'auto_translate' not in st.session_state:
        st.session_state.auto_translate = True
    if 'source_lang' not in st.session_state:
        st.session_state.source_lang = 'auto'
    if 'font_size' not in st.session_state:
        st.session_state.font_size = 16
    if 'display_mode' not in st.session_state:
        st.session_state.display_mode = 'default'
    if 'translate_trigger' not in st.session_state:
        st.session_state.translate_trigger = False

    # 初始化翻譯器
    translator = Translator()

    # 語言選項
    lang_options = {
        'auto': '自動檢測',
        'en': '英文',
        'fr': '法文',
        'de': '德文',
        'es': '西班牙文',
        'ja': '日文',
        'ko': '韓文',
        'zh-cn': '簡體中文'
    }

    # 側邊欄控制項
    with st.sidebar:
        st.subheader("控制項")
        uploaded_file = st.file_uploader("上傳PDF", type=["pdf"])
        if uploaded_file:
            try:
                # 只有當新文件上傳時才重新加載PDF
                file_name = getattr(uploaded_file, "name", "未命名")
                if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_name:
                    pdf_bytes = uploaded_file.read()
                    st.session_state.pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    st.session_state.current_page = 0
                    st.session_state.zoom_factor = 2.0
                    st.session_state.display_mode = 'default'
                    st.session_state.last_uploaded_file = file_name
            except Exception as e:
                st.error(f"無法打開PDF文件: {str(e)}")

        if st.session_state.pdf_doc:
            total_pages = len(st.session_state.pdf_doc)
            st.write(f"第 {st.session_state.current_page + 1} / {total_pages} 頁")

            # 頁面導航
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("上一頁"):
                    if st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        # 不再重置顯示模式
                        st.session_state.translate_trigger = True
            with col3:
                if st.button("下一頁"):
                    if st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        # 不再重置顯示模式
                        st.session_state.translate_trigger = True

            # 跳頁
            page_input = st.number_input("跳至頁數", min_value=1, max_value=total_pages, value=st.session_state.current_page + 1, step=1)
            if st.button("跳轉"):
                new_page = int(page_input) - 1
                if new_page != st.session_state.current_page:
                    st.session_state.current_page = new_page
                    st.session_state.translate_trigger = True

            # 縮放控制
            zoom_factor = st.slider("縮放", min_value=0.5, max_value=4.0, value=st.session_state.zoom_factor, step=0.5)
            if zoom_factor != st.session_state.zoom_factor:
                st.session_state.zoom_factor = zoom_factor
                # 不再重置顯示模式

            # 顯示模式
            display_options = ["預設", "自由適配", "比例適配"]
            display_values = ["default", "fit_free", "fit_proportional"]
            current_index = display_values.index(st.session_state.display_mode)
            display_mode = st.selectbox("顯示模式", display_options, index=current_index)
            selected_mode = display_values[display_options.index(display_mode)]
            if selected_mode != st.session_state.display_mode:
                st.session_state.display_mode = selected_mode

            # 源語言
            source_lang = st.selectbox("源語言", options=list(lang_options.values()), 
                                       index=list(lang_options.keys()).index(st.session_state.source_lang))
            source_lang_code = [k for k, v in lang_options.items() if v == source_lang][0]
            if source_lang_code != st.session_state.source_lang:
                st.session_state.source_lang = source_lang_code
                st.session_state.translate_trigger = True

            # 字體大小
            font_size = st.slider("翻譯文字大小", min_value=10, max_value=30, value=st.session_state.font_size, step=1)
            st.session_state.font_size = font_size

            # 自動翻譯切換
            auto_translate = st.checkbox("自動翻譯", value=st.session_state.auto_translate)
            if auto_translate != st.session_state.auto_translate:
                st.session_state.auto_translate = auto_translate
                st.session_state.translate_trigger = True

            # 手動翻譯按鈕
            if st.button("重新翻譯"):
                st.session_state.translate_trigger = True

    # 主內容
    if st.session_state.pdf_doc:
        page = st.session_state.pdf_doc[st.session_state.current_page]
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("PDF頁面")
            try:
                # 渲染 PDF 頁面
                if st.session_state.display_mode == 'fit_free':
                    rect = page.rect
                    container_width = st.session_state.container_width if 'container_width' in st.session_state else 600
                    container_height = st.session_state.container_height if 'container_height' in st.session_state else 800
                    zoom_x = container_width / rect.width
                    zoom_y = container_height / rect.height
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom_x * 0.95, zoom_y * 0.95))
                    effective_zoom = zoom_x * 0.95
                elif st.session_state.display_mode == 'fit_proportional':
                    rect = page.rect
                    container_width = st.session_state.container_width if 'container_width' in st.session_state else 600
                    container_height = st.session_state.container_height if 'container_height' in st.session_state else 800
                    zoom_x = container_width / rect.width
                    zoom_y = container_height / rect.height
                    zoom = min(zoom_x, zoom_y) * 0.95
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                    effective_zoom = zoom
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(st.session_state.zoom_factor, st.session_state.zoom_factor))
                    effective_zoom = st.session_state.zoom_factor

                # 確保 pixmap 格式
                if pix.n < 3:  # 如果不是RGB圖像，轉換為RGB
                    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    img = img.convert("RGB")
                else:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # 將 pixmap 轉換為圖像
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes = img_bytes.getvalue()

                # 顯示圖像
                st.image(img_bytes, use_column_width=False, width=int(pix.width))

                # 儲存容器大小
                st.session_state.container_width = pix.width / effective_zoom
                st.session_state.container_height = pix.height / effective_zoom

            except Exception as e:
                st.error(f"渲染頁面失敗: {str(e)}")
                st.error(f"詳細錯誤: {type(e).__name__}: {str(e)}")

        with col2:
            st.subheader("提取的文字與翻譯")
            # 提取文字
            text = page.get_text("text") or "本頁無文字"
            st.text_area("提取的文字", value=text, height=200, key=f"extracted_text_{st.session_state.current_page}")

            # 翻譯文字
            translation_key = f"translation_{st.session_state.current_page}_{st.session_state.source_lang}"
            
            # 檢查是否需要重新翻譯
            need_translate = (st.session_state.auto_translate and translation_key not in st.session_state) or st.session_state.translate_trigger
            
            if need_translate:
                blocks = page.get_text("blocks")
                if blocks:
                    try:
                        translated_texts = []
                        detected_langs = set()
                        for block in blocks:
                            text_block = block[4].strip()
                            if text_block:
                                translated = translator.translate(text_block, src=st.session_state.source_lang, dest='zh-tw')
                                translated_texts.append(translated.text)
                                detected_langs.add(translated.src)
                        translated_text = "\n\n".join(translated_texts)
                        if detected_langs:
                            primary_lang = max(detected_langs, key=lambda x: sum(1 for t in translated_texts if t))
                            lang_name = lang_options.get(primary_lang, primary_lang)
                            if len(detected_langs) > 1:
                                lang_name += "（含多語言）"
                        else:
                            lang_name = "未知"
                        translation = f"檢測到語言：{lang_name}\n\n{translated_text}"
                    except Exception as e:
                        translation = f"翻譯錯誤: {str(e)}"
                else:
                    translation = "本頁無文字可翻譯"
                
                # 儲存翻譯結果以便重用
                st.session_state[translation_key] = translation
                st.session_state.translate_trigger = False
            else:
                # 使用緩存的翻譯結果
                translation = st.session_state.get(translation_key, "翻譯未啟用或未觸發")

            # 應用字體大小
            st.markdown(f'<style>.translated-text {{ font-size: {st.session_state.font_size}px; }}</style>', unsafe_allow_html=True)
            st.markdown(f'<div class="translated-text">{translation}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()