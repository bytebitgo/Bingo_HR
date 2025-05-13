import os
import requests

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

# 其它工具函数略... 