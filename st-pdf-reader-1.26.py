import streamlit as st
import fitz  # PyMuPDF
from googletrans import Translator
import base64
import io
from PIL import Image
import numpy as np

def main():
    st.set_page_config(page_title="雙語翻譯對照閱讀器", layout="wide")
    st.title("雙語翻譯對照閱讀器, 支持英,法,德,西,日,韓,簡七國語言")
    st.markdown("##### *V1.00, 設計人: Aries Yeh*")

    # 初始化 session state
    if 'pdf_doc' not in st.session_state:
        st.session_state.pdf_doc = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'auto_translate' not in st.session_state:
        st.session_state.auto_translate = True
    if 'source_lang' not in st.session_state:
        st.session_state.source_lang = 'auto'
    if 'font_size' not in st.session_state:
        st.session_state.font_size = 21
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

    # 添加自定義CSS樣式，為原稿區域和翻譯區域添加藍色邊框
    st.markdown("""
    <style>
        /* 為原稿區域和翻譯區域添加藍色邊框 */
        .border-box {
            border: 2px solid #1E90FF;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 15px;
        }
        
        /* 調整翻譯文字的樣式 */
        .translated-text {
            padding: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # 建立兩大區塊：主畫面（左側）和控制區（右側）
    col_main, col_ctrl = st.columns([10, 1])

    # 側邊控制項保留在 col_ctrl
    with col_ctrl:
        st.subheader("控制項")
        uploaded_file = st.file_uploader("上傳PDF", type=["pdf"])
        if uploaded_file:
            try:
                file_name = getattr(uploaded_file, "name", "未命名")
                if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != file_name:
                    pdf_bytes = uploaded_file.read()
                    st.session_state.pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    st.session_state.current_page = 0
                    st.session_state.last_uploaded_file = file_name
            except Exception as e:
                st.error(f"無法打開PDF文件: {str(e)}")

        if st.session_state.pdf_doc:
            total_pages = len(st.session_state.pdf_doc)
            st.write(f"第 {st.session_state.current_page + 1} / {total_pages} 頁")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("上頁"):
                    if st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        st.session_state.translate_trigger = True
            with col3:
                if st.button("下頁"):
                    if st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        st.session_state.translate_trigger = True

            page_input = st.number_input("跳至頁數", min_value=1, max_value=total_pages, value=st.session_state.current_page + 1, step=1)
            if st.button("跳轉"):
                new_page = int(page_input) - 1
                if new_page != st.session_state.current_page:
                    st.session_state.current_page = new_page
                    st.session_state.translate_trigger = True

            source_lang = st.selectbox("原語言", options=list(lang_options.values()), 
                                       index=list(lang_options.keys()).index(st.session_state.source_lang))
            source_lang_code = [k for k, v in lang_options.items() if v == source_lang][0]
            if source_lang_code != st.session_state.source_lang:
                st.session_state.source_lang = source_lang_code
                st.session_state.translate_trigger = True

            font_size = st.slider("翻譯文字大小", min_value=10, max_value=30, value=st.session_state.font_size, step=1)
            st.session_state.font_size = font_size

            auto_translate = st.checkbox("自動翻譯", value=st.session_state.auto_translate)
            if auto_translate != st.session_state.auto_translate:
                st.session_state.auto_translate = auto_translate
                st.session_state.translate_trigger = True

            if st.button("重新翻譯"):
                st.session_state.translate_trigger = True

    # 主內容顯示區
    if st.session_state.pdf_doc:
        page = st.session_state.pdf_doc[st.session_state.current_page]
        with col_main:
            col_left, col_right = st.columns([1, 1], gap="small")

            with col_left:
                # 使用HTML包裝原稿區域，添加藍色邊框
                st.markdown('<div class="border-box">', unsafe_allow_html=True)
                st.markdown("#### PDF 頁面")
                try:
                    pix = page.get_pixmap()

                    if pix.n < 3:
                        img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                        img = img.convert("RGB")
                    else:
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="PNG")
                    img_bytes = img_bytes.getvalue()

                    st.image(img_bytes, use_container_width=True)

                except Exception as e:
                    st.error(f"渲染頁面失敗: {str(e)}")

                st.markdown('</div>', unsafe_allow_html=True)  # 關閉邊框div

            with col_right:
                # 使用HTML包裝翻譯區域，添加藍色邊框
                st.markdown('<div class="border-box">', unsafe_allow_html=True)
                st.markdown("#### 翻譯結果")

                translation_key = f"translation_{st.session_state.current_page}_{st.session_state.source_lang}"
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

                    st.session_state[translation_key] = translation
                    st.session_state.translate_trigger = False
                else:
                    translation = st.session_state.get(translation_key, "翻譯未啟用或未觸發")

                st.markdown(f'<style>.translated-text {{ font-size: {st.session_state.font_size}px; }}</style>', unsafe_allow_html=True)
                st.markdown(f'<div class="translated-text">{translation}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)  # 關閉邊框div

if __name__ == "__main__":
    main()
