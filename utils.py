import os
import requests
from azure.storage.blob import BlobServiceClient
import threading
import re

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'md'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_list(upload_folder):
    files = []
    for fname in os.listdir(upload_folder):
        fpath = os.path.join(upload_folder, fname)
        if os.path.isfile(fpath):
            files.append({
                'name': fname,
                'size': os.path.getsize(fpath),
                'mtime': os.path.getmtime(fpath)
            })
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return files

def generate_prompt(job_description, resume_text):
    prompt = f"""
    我们的目标是根据以下的岗位职责，评估这份简历的匹配度。请给出详细的评估意见，并指出简历中的亮点与改进建议。

    岗位职责：
    {job_description}

    简历内容：
    {resume_text}

    请评估简历与岗位职责的匹配度，并以1到5分的等级给出匹配度评分，其中1表示完全不匹配，5表示高度匹配。
    """
    return prompt

def call_openai_api(prompt, api_version, deployment_name, api_key, endpoint):
    url = f"{endpoint}/openai/deployments/{deployment_name}/completions?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.2
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['text']

def upload_to_azure_blob(local_path, blob_name, conn_str, container):
    print(f'[Azure Blob] 开始上传: {local_path} -> {blob_name}')
    print(f'[Azure Blob] 连接字符串: {conn_str}')
    print(f'[Azure Blob] 容器名: {container}')
    if not conn_str or not container:
        print('[Azure Blob] 未配置连接字符串或容器名')
        return False
    try:
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
        with open(local_path, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        print(f'[Azure Blob] 上传成功: {blob_name}')
        return True
    except Exception as e:
        import traceback
        print(f'[Azure Blob] 上传失败: {e}')
        traceback.print_exc()
        return False

def async_upload_to_blob(local_path, blob_name, conn_str, container):
    threading.Thread(target=upload_to_azure_blob, args=(local_path, blob_name, conn_str, container), daemon=True).start()

def secure_filename_keep_chinese(filename):
    # 只去除特殊符号，保留中日韩文字、英文、数字、下划线、点
    filename = re.sub(r'[^\w.\u4e00-\u9fa5\u3040-\u30ff\uac00-\ud7af-]', '', filename)
    return filename

# 其它工具函数略... 