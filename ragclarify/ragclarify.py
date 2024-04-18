import json
import tempfile
import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
import streamlit as st
from .common import check_apptoken_from_apikey, get_global_datadir, get_loader_from_file, fetch_page, get_title
import os
import time
from streamlit_ace import st_ace
from dotenv import load_dotenv
from .session import PageSessionState

load_dotenv()

def split_docs(filename, bytes, keep_separator=False, chunk_size=4096):
    # Read documents
    docs = []
    temp_dir = tempfile.TemporaryDirectory()
    temp_filepath = os.path.join(temp_dir.name, filename)
    with open(temp_filepath, "wb") as f:
        f.write(bytes)
    loader = get_loader_from_file(temp_filepath)
    docs.extend(loader.load())

    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        keep_separator=keep_separator,
        chunk_size=chunk_size,
        chunk_overlap=200,
    )
    splits = text_splitter.split_documents(docs)
    return splits


def main():
    st.set_page_config(page_title="RAG 数据清洗", page_icon="🗃", layout="wide")
    page_state = PageSessionState("ragclarify")
    page_state.initn_attr("latest_content", None)
    page_state.initn_attr("latest_content_name", None)
    page_state.initn_attr("latest_content_json", None)
    with st.sidebar:
        st.title("🗃 RAG 数据清洗")
        tab1, tab2 = st.tabs(["参数设置", "关于"])
        with tab1:
            apikey_box = st.empty()
            if not page_state.app_uid:
                apikey = st.query_params.get("apikey")
                if not apikey:
                    apikey = apikey_box.text_input("请输入 API Key", type="password")

                if apikey:
                    appuid = check_apptoken_from_apikey(apikey)
                    if appuid:
                        page_state.app_uid = appuid
                        page_state.apikey = apikey
                        # apikey_box.empty()

            if not page_state.app_uid:
                st.error("Auth is invalid")
                st.stop()
            param_box = st.container()

        with tab2:
            st.image(
                os.path.join(os.path.dirname(__file__), "ragclarify.png"),
                use_column_width=True,
            )

    uploaded_file = param_box.file_uploader(
        "上传文档", type=["srt", "txt", "html", "md", "pdf", "pptx", "xlsx", "docx"]
    )
    neturl = param_box.text_input("网址抓取")
    fetch_action = None
    if neturl:
        fetch_action = param_box.button("抓取")
    keep_separator = param_box.radio("是否保留分隔符", [True, False])
    chunk_size = param_box.number_input("分块大小", min_value=512, value=4096)
    
    def process_content(name, bytes):
        spdocs = split_docs(
            name, bytes, keep_separator, chunk_size
        )
        json_data = []
        for spdoc in spdocs:
            json_data.append(spdoc.to_json())
        page_state.latest_content_json = json_data
        page_state.latest_content = "\n\n".join(
            [spdoc.page_content for spdoc in spdocs]
        )

    
    if fetch_action:
        with st.spinner("正在抓取网页"):
            text = fetch_page(neturl)
            process_content("httpdata.md", text.encode("utf-8"))

    elif uploaded_file:
        process_content(uploaded_file.name, uploaded_file.getvalue())


    tab1, tab2 = st.tabs(["文本", "json"])

    with tab1:
        if page_state.latest_content:
            page_state.latest_content = st_ace(
                page_state.latest_content,
                language="markdown",
                height=420,
                wrap=True,
            )
            if st.button("重新处理"):
                process_content(
                    page_state.latest_content_name,
                    page_state.latest_content.encode("utf-8")
                )
        else:
            st.info("请上传文档")

    with tab2:
        if page_state.latest_content_json:
            st.write(page_state.latest_content_json)
        else:
            st.info("请上传文档")

    st.divider()
    
    c1, c2 = st.columns(2)
    
    if page_state.latest_content:
        c1.download_button(
            label=f"文本下载",
            data=page_state.latest_content,
            file_name=f"ragclarify_{uuid.uuid4().hex}.txt",
            key="ragclarify_download_latest_file",
        )

    if page_state.latest_content_json:
        c2.download_button(
            label=f"JSON 下载",
            data=json.dumps(page_state.latest_content_json, indent=2),
            file_name=f"ragclarify_json_{uuid.uuid4().hex}.txt",
            key="ragclarify_json_download_latest_file",
        )

