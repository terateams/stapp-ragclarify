import json
import os
import jwt
import requests
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredExcelLoader

from langchain_community.document_loaders import MHTMLLoader
from langchain_community.document_loaders import UnstructuredODTLoader
from langchain_community.document_loaders import UnstructuredXMLLoader
from langchain_community.document_loaders import NotebookLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.document_loaders import JSONLoader
from langchain_community.document_loaders.chatgpt import ChatGPTLoader
from langchain_community.document_loaders import UnstructuredEmailLoader
from langchain_community.document_loaders import EverNoteLoader
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    UnstructuredEPubLoader,
)



def check_apptoken_from_apikey(apikey: str):
    if not apikey:
        return None
    apisecret = os.environ.get('APP_SECRET')
    if apikey:
        try:
            payload = jwt.decode(apikey, apisecret, algorithms=['HS256'])
            uid = payload.get('uid')
            if uid :
                return uid
        except Exception as e:
            return None
    return None

def get_global_datadir(subpath: str = None):
    """
    获取全局数据目录。

    Args:
        subpath (str, optional): 子路径。默认为None。

    Returns:
        str: 数据目录路径。
    """
    datadir = os.environ.get("DATA_DIR", "/tmp/teamsgpt")
    if subpath:
        datadir = os.path.join(datadir, subpath)
    if not os.path.exists(datadir):
        os.makedirs(datadir)
    return datadir


def openai_text_generate(sysmsg: str, prompt: str, apikey: str):
    url = os.getenv("TEAMSGPT_APISITE", "https://api.teamsgpt.net") + "/api/generate"
    # Prepare headers and data
    headers = {'Content-Type': 'application/json', "Authorization": f"Bearer {apikey}"}
    data = json.dumps({
        "sysmsg": sysmsg,
        "prompt": prompt,
        "temperature": 0.7,  # Adjust this as needed
    })
    
    with requests.post(url, data=data, headers=headers, stream=True) as response:
        if response.status_code == 200:
            for line in response.iter_lines():
                decoded_line = line.decode('utf-8')               
                if decoded_line.startswith('data:'):
                    try:
                        json_str = decoded_line[len('data: '):]
                        if json_str:  
                            yield json.loads(json_str)
                        else:
                            pass
                    except json.JSONDecodeError as e:
                        print(f"JSON decoding failed: {e}")
                elif "data: [DONE]" in decoded_line:
                    break
        else:
            raise Exception(f"Error: {response.status_code} {response.reason}")

def write_stream_text(placeholder, response):
    """写入流式响应。"""
    full_response = ""
    for tobj in response:
        text = tobj.get("content")
        if text is not None:
            full_response += text
            placeholder.markdown(full_response)
        placeholder.markdown(full_response)
    return full_response




def get_loader_from_file(filepath: str):
    filetype = os.path.splitext(filepath)[1][1:].lower()
    if filetype in ["pdf"]:
        loader = PyMuPDFLoader(filepath)
    elif filetype in ["ppt", "pptx"]:
        loader = UnstructuredPowerPointLoader(filepath)
    elif filetype in ["xls", "xlsx"]:
        loader = UnstructuredExcelLoader(filepath)
    elif filetype in ["doc", "docx"]:
        loader = UnstructuredWordDocumentLoader(filepath)
    elif filetype in ["txt"]:
        loader = TextLoader(filepath)
    elif filetype in ["ipynb"]:
        loader = NotebookLoader(filepath)
    elif filetype in ["md"]:
        loader = UnstructuredMarkdownLoader(filepath)
        # loader = UnstructuredFileLoader(filepath)
    elif filetype in ["epub"]:
        loader = UnstructuredEPubLoader(filepath)
    elif filetype in ["csv"]:
        loader = CSVLoader(filepath)
    elif filetype in ["html", "htm"]:
        loader = UnstructuredHTMLLoader(filepath)
    elif os.path.basename(filepath).endswith("fake_conversations.json"):
        loader = ChatGPTLoader(filepath)
    elif os.path.basename(filepath).endswith("text_array.json"):
        loader = JSONLoader(filepath, jq_schema=".[]", text_content=True)
    elif filetype in ["json"]:
        loader = JSONLoader(
            filepath, jq_schema=".messages[].content", text_content=False
        )
    elif filetype in ["eml"]:
        loader = UnstructuredEmailLoader(filepath)
    elif filetype in ["enex"]:
        loader = EverNoteLoader(filepath)
    elif filetype in ["mht"]:
        loader = MHTMLLoader(filepath)
    elif filetype in ["xml"]:
        loader = UnstructuredXMLLoader(filepath)
    elif filetype in ["odt"]:
        loader = UnstructuredODTLoader(filepath)
    else:
        loader = UnstructuredFileLoader(filepath)
    print("-"*100)
    print(filetype)
    print(type(loader))
    return loader


def fetch_page(surl: str):
    response = requests.get(f"https://r.jina.ai/{surl}")
    if response.status_code != 200:
        raise Exception(f"Request failed with status {response.status_code}")
    return response.text


def get_title(text, slen=32):
    if slen > len(text):
        return text
    return text[:slen] + "..."