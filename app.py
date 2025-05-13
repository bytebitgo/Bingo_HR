import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort, jsonify
from werkzeug.utils import secure_filename
from utils import allowed_file, get_file_list, call_openai_api
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import queue
import time
import mimetypes
import csv
from io import StringIO
import base64  # 新增
try:
    import docx
except ImportError:
    docx = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'md'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'resume_matcher_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume_matcher.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AI分析任务队列和并发控制
ai_task_queue = queue.Queue()
MAX_AI_WORKERS = 2

def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

def nl2br(value):
    if value:
        return value.replace('\n', '<br>')
    return ''

app.jinja_env.filters['datetimeformat'] = datetimeformat
app.jinja_env.filters['nl2br'] = nl2br

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    resumes = db.relationship('Resume', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    size = db.Column(db.Integer)
    mtime = db.Column(db.Float)
    analysis_status = db.Column(db.String(32), default='未分析')
    analysis_result = db.Column(db.Text)
    analysis_records = db.relationship('AnalysisRecord', backref='resume', lazy=True, cascade='all, delete-orphan')
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=True)
    job = db.relationship('Job', backref='resumes')

class Setting(db.Model):
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text)

class AnalysisRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    result = db.Column(db.Text)
    status = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    requirements = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='jobs')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # 获取可选的招聘需求
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.updated_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.updated_at.desc()).all()
    if request.method == 'POST':
        files = request.files.getlist('resumes')
        job_id = request.form.get('job_id')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                # 写入数据库
                resume = Resume(
                    filename=filename,
                    user_id=current_user.id,
                    size=os.path.getsize(save_path),
                    mtime=os.path.getmtime(save_path),
                    job_id=job_id if job_id else None
                )
                db.session.add(resume)
                db.session.commit()
            else:
                flash(f"文件类型不被允许: {file.filename}", 'danger')
        return redirect(url_for('index'))
    # 权限控制：超级管理员可见所有，普通用户仅见自己
    if current_user.is_admin:
        resumes = Resume.query.order_by(Resume.mtime.desc()).all()
    else:
        resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.mtime.desc()).all()
    return render_template('index.html', resumes=resumes, jobs=jobs)

@app.route('/download/<int:resume_id>')
@login_required
def download_file(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    # 权限校验
    if not current_user.is_admin and resume.user_id != current_user.id:
        flash('无权限下载该简历', 'danger')
        return redirect(url_for('index'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], resume.filename, as_attachment=True)

@app.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete_file(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if not current_user.is_admin and resume.user_id != current_user.id:
        flash('无权限删除该简历', 'danger')
        return redirect(url_for('index'))
    
    # 先删除所有关联的分析记录
    AnalysisRecord.query.filter_by(resume_id=resume.id).delete()
    
    # 删除文件和数据库记录
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(resume)
    db.session.commit()
    flash(f"已删除: {resume.filename}", 'success')
    return redirect(url_for('index'))

@app.route('/delete_batch', methods=['POST'])
@login_required
def delete_batch():
    ids = request.form.getlist('resume_ids')
    deleted, not_found, no_perm = [], [], []
    for rid in ids:
        resume = Resume.query.get(rid)
        if not resume:
            not_found.append(rid)
            continue
        if not current_user.is_admin and resume.user_id != current_user.id:
            no_perm.append(resume.filename)
            continue
            
        # 先删除所有关联的分析记录
        AnalysisRecord.query.filter_by(resume_id=resume.id).delete()
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(resume)
        deleted.append(resume.filename)
    db.session.commit()
    if deleted:
        flash(f"已批量删除: {', '.join(deleted)}", 'success')
    if not_found:
        flash(f"未找到: {', '.join(not_found)}", 'danger')
    if no_perm:
        flash(f"无权限: {', '.join(no_perm)}", 'danger')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))
        is_admin = username.lower() in ['admin', 'betty']
        user = User(username=username, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('login'))

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)
    users = User.query.order_by(User.id).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    if not new_password:
        flash('新密码不能为空', 'danger')
    else:
        user.set_password(new_password)
        db.session.commit()
        flash(f'用户 {user.username} 密码已重置', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
def admin_toggle_admin(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能修改自己的管理员权限', 'danger')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'用户 {user.username} 管理员权限已变更', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能删除自己', 'danger')
        return redirect(url_for('admin_users'))
    # 删除用户简历文件和记录
    for resume in user.resumes:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(resume)
    db.session.delete(user)
    db.session.commit()
    flash(f'用户 {user.username} 及其简历已删除', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/add', methods=['POST'])
@login_required
def admin_add_user():
    if not current_user.is_admin:
        abort(403)
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = bool(request.form.get('is_admin'))
    if not username or not password:
        flash('用户名和密码不能为空', 'danger')
    elif User.query.filter_by(username=username).first():
        flash('用户名已存在', 'danger')
    else:
        user = User(username=username, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'用户 {username} 已添加', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/edit', methods=['POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    new_username = request.form.get('edit_username')
    new_password = request.form.get('edit_password')
    new_is_admin = bool(request.form.get('edit_is_admin'))
    if new_username:
        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash('新用户名已存在', 'danger')
            return redirect(url_for('admin_users'))
        user.username = new_username
    if new_password:
        user.set_password(new_password)
    user.is_admin = new_is_admin
    db.session.commit()
    flash(f'用户 {user.username} 信息已更新', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not current_user.is_admin:
        abort(403)
    default_settings = {
        'api_key': 'replace_with_your_api_key',
        'endpoint': 'https://myjycloud.openai.azure.com/',
        'deployment_name': 'gpt-4.5-preview',
        'api_version': '2025-01-01-preview'
    }
    keys = ['api_key', 'endpoint', 'deployment_name', 'api_version']
    settings = {}
    for k in keys:
        s = db.session.get(Setting, k)
        if s:
            settings[k] = s.value
        else:
            settings[k] = default_settings[k]
    if request.method == 'POST':
        for k in keys:
            v = request.form.get(k, '').strip()
            setting = db.session.get(Setting, k)
            if setting:
                setting.value = v
            else:
                db.session.add(Setting(key=k, value=v))
        db.session.commit()
        flash('设置已保存', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin_settings.html', settings=settings)

def extract_resume_text(resume):
    file_path = os.path.join(UPLOAD_FOLDER, resume.filename)
    ext = resume.filename.rsplit('.', 1)[-1].lower()
    if ext in ['txt', 'md']:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return '[无法读取文本文件内容]'
    elif ext in ['pdf']:
        if not PyPDF2:
            return '[未安装PyPDF2库，无法解析PDF内容]'
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                # 提取所有页面文本，拼接
                return '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception:
            return '[无法读取PDF内容]'
    elif ext in ['docx']:
        if not docx:
            return '[未安装python-docx库，无法解析Word内容]'
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs)
        except Exception:
            return '[无法读取Word内容]'
    elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return '[图片文件，暂不支持内容提取]'
    else:
        return '[暂不支持该文件类型内容提取]'

# 图片转base64函数
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ai_worker():
    print("ai_worker线程函数已进入", flush=True)
    while True:
        resume_id = ai_task_queue.get()
        print(f"worker线程收到任务，简历ID={resume_id}", flush=True)
        with app.app_context():
            resume = db.session.get(Resume, resume_id)
            print(f"[AI分析] 任务启动，简历ID={resume_id}", flush=True)
            if not resume:
                print(f"[AI分析] 未找到简历ID={resume_id}", flush=True)
                ai_task_queue.task_done()
                continue
            resume.analysis_status = '分析中'
            db.session.commit()
            try:
                settings = {k: (db.session.get(Setting, k).value if db.session.get(Setting, k) else '') for k in ['api_key', 'endpoint', 'deployment_name', 'api_version']}
                print(f"[AI分析] 读取API参数: {settings}", flush=True)
                ext = resume.filename.rsplit('.', 1)[-1].lower()
                file_path = os.path.join(UPLOAD_FOLDER, resume.filename)
                # 判断是否为图片简历
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                    # 构造多模态消息
                    base64_image = encode_image(file_path)
                    job_prompt = ''
                    if resume.job:
                        job_prompt = f"""
【招聘需求】\n岗位名称：{resume.job.title}\n岗位要求：{resume.job.requirements or ''}\n岗位描述：{resume.job.description or ''}\n"""
                    prompt_text = f"""请你作为一名专业的招聘顾问，基于以下招聘需求和候选人简历图片，进行匹配度分析：\n\n{job_prompt}\n【候选人简历为图片，请识别图片内容后分析】\n\n请完成以下任务：\n1. 结合招聘需求，分析该简历的优势与不足，指出与岗位要求高度匹配的部分，以及存在的差距或改进建议。\n2. 给出该简历与该岗位的匹配度评分（1-5分，1为完全不匹配，5为高度匹配），并简要说明评分理由。\n3. 输出格式建议：\n- 匹配度评分：X分\n- 评分理由：……\n- 优势亮点：……\n- 改进建议：……\n\n请用中文作答，内容尽量简明扼要、专业客观。"""
                    if AzureOpenAI:
                        print("[AI分析-图片] 调用Azure OpenAI...", flush=True)
                        client = AzureOpenAI(
                            api_version=settings['api_version'],
                            azure_endpoint=settings['endpoint'],
                            api_key=settings['api_key'],
                        )
                        response = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "你是一个专业的简历分析助手。"},
                                {"role": "user", "content": [
                                    {"type": "text", "text": prompt_text},
                                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{base64_image}"}}
                                ]}
                            ],
                            max_completion_tokens=800,
                            temperature=0.7,
                            top_p=1.0,
                            frequency_penalty=0.0,
                            presence_penalty=0.0,
                            model=settings['deployment_name']
                        )
                        result = response.choices[0].message.content
                        print(f"[AI分析-图片] Azure OpenAI返回结果，长度={len(result)}", flush=True)
                    else:
                        print("[AI分析-图片] openai库未安装，无法分析", flush=True)
                        result = '[未安装openai库，无法实际分析图片]'
                    resume.analysis_result = result
                    resume.analysis_status = '已完成'
                    record = AnalysisRecord(
                        resume_id=resume.id,
                        user_id=resume.user_id,
                        result=result,
                        status='已完成'
                    )
                    db.session.add(record)
                    db.session.commit()
                    ai_task_queue.task_done()
                    continue
                # 非图片简历，走原有文本流程
                resume_text = extract_resume_text(resume)
                print(f"[AI分析] 读取简历内容完成，长度={len(resume_text)}", flush=True)
                if resume_text == '[未安装python-docx库，无法解析Word内容]':
                    resume.analysis_status = '失败'
                    resume.analysis_result = '服务器未安装python-docx库，无法解析Word简历，请联系管理员安装依赖。'
                    db.session.commit()
                    ai_task_queue.task_done()
                    continue
                if resume_text == '[未安装PyPDF2库，无法解析PDF内容]':
                    resume.analysis_status = '失败'
                    resume.analysis_result = '服务器未安装PyPDF2库，无法解析PDF简历，请联系管理员安装依赖。'
                    db.session.commit()
                    ai_task_queue.task_done()
                    continue
                # 新版专业prompt
                job_prompt = ''
                if resume.job:
                    job_prompt = f"""
【招聘需求】\n岗位名称：{resume.job.title}\n岗位要求：{resume.job.requirements or ''}\n岗位描述：{resume.job.description or ''}\n"""
                prompt = f"""请你作为一名专业的招聘顾问，基于以下招聘需求和候选人简历，进行匹配度分析：\n\n{job_prompt}\n【候选人简历】\n{resume_text}\n\n请完成以下任务：\n1. 结合招聘需求，分析该简历的优势与不足，指出与岗位要求高度匹配的部分，以及存在的差距或改进建议。\n2. 给出该简历与该岗位的匹配度评分（1-5分，1为完全不匹配，5为高度匹配），并简要说明评分理由。\n3. 输出格式建议：\n- 匹配度评分：X分\n- 评分理由：……\n- 优势亮点：……\n- 改进建议：……\n\n请用中文作答，内容尽量简明扼要、专业客观。"""
                if AzureOpenAI:
                    print("[AI分析] 调用Azure OpenAI...", flush=True)
                    client = AzureOpenAI(
                        api_version=settings['api_version'],
                        azure_endpoint=settings['endpoint'],
                        api_key=settings['api_key'],
                    )
                    response = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "你是一个专业的简历分析助手。"},
                            {"role": "user", "content": prompt}
                        ],
                        max_completion_tokens=800,
                        temperature=0.7,
                        top_p=1.0,
                        frequency_penalty=0.0,
                        presence_penalty=0.0,
                        model=settings['deployment_name']
                    )
                    result = response.choices[0].message.content
                    print(f"[AI分析] Azure OpenAI返回结果，长度={len(result)}", flush=True)
                else:
                    print("[AI分析] openai库未安装，无法分析", flush=True)
                    result = '[未安装openai库，无法实际分析]'
                resume.analysis_result = result
                resume.analysis_status = '已完成'
                record = AnalysisRecord(
                    resume_id=resume.id,
                    user_id=resume.user_id,
                    result=result,
                    status='已完成'
                )
                db.session.add(record)
            except Exception as e:
                print(f"[AI分析] 分析失败: {e}", flush=True)
                resume.analysis_status = '失败'
                resume.analysis_result = f"分析失败: {e}"
                record = AnalysisRecord(
                    resume_id=resume.id,
                    user_id=resume.user_id,
                    result=f"分析失败: {e}",
                    status='失败'
                )
                db.session.add(record)
            db.session.commit()
            ai_task_queue.task_done()

@app.route('/ai_analyze/<int:resume_id>', methods=['POST'])
@login_required
def ai_analyze(resume_id):
    print(f"收到AI分析请求，简历ID={resume_id}", flush=True)
    resume = db.session.get(Resume, resume_id)
    if not current_user.is_admin and resume.user_id != current_user.id:
        flash('无权限分析该简历', 'danger')
        return redirect(url_for('index'))
    if resume.analysis_status in ['排队中', '分析中']:
        flash('该简历正在分析中，请稍后', 'info')
        return redirect(url_for('index'))
    resume.analysis_status = '排队中'
    db.session.commit()
    print(f"任务入队，简历ID={resume.id}", flush=True)
    ai_task_queue.put(resume.id)
    flash(f'AI分析任务已提交，稍后请刷新查看结果。<a href="{url_for("ai_analysis_records")}?resume_id={resume.id}" class="alert-link" target="_blank">查看分析历史</a>', 'success')
    return redirect(url_for('index'))

@app.route('/ai_status/<int:resume_id>')
@login_required
def ai_status(resume_id):
    resume = db.session.get(Resume, resume_id)
    if not current_user.is_admin and resume.user_id != current_user.id:
        return jsonify({'error': '无权限'}), 403
    return jsonify({
        'status': resume.analysis_status,
        'result': resume.analysis_result or ''
    })

@app.route('/admin/ai_queue')
@login_required
def admin_ai_queue():
    if not current_user.is_admin:
        abort(403)
    # 获取队列中所有待分析任务ID
    queue_ids = list(ai_task_queue.queue)
    # 获取数据库中分析中/排队中的任务
    in_progress = Resume.query.filter(Resume.analysis_status.in_(['排队中', '分析中'])).all()
    # 统计信息
    total_waiting = len(queue_ids)
    total_processing = Resume.query.filter_by(analysis_status='分析中').count()
    total_completed = Resume.query.filter_by(analysis_status='已完成').count()
    total_failed = Resume.query.filter_by(analysis_status='失败').count()
    return render_template('admin_ai_queue.html',
        queue_ids=queue_ids,
        in_progress=in_progress,
        total_waiting=total_waiting,
        total_processing=total_processing,
        total_completed=total_completed,
        total_failed=total_failed
    )

@app.route('/admin/ai_queue_data')
@login_required
def admin_ai_queue_data():
    if not current_user.is_admin:
        abort(403)
    queue_ids = list(ai_task_queue.queue)
    in_progress = Resume.query.filter(Resume.analysis_status.in_(['排队中', '分析中'])).all()
    total_waiting = len(queue_ids)
    total_processing = Resume.query.filter_by(analysis_status='分析中').count()
    total_completed = Resume.query.filter_by(analysis_status='已完成').count()
    total_failed = Resume.query.filter_by(analysis_status='失败').count()
    queue_data = []
    for rid in queue_ids:
        resume = db.session.get(Resume, rid)
        queue_data.append({
            'queue_order': queue_ids.index(rid) + 1,
            'id': rid,
            'filename': resume.filename if resume else '-',
            'user_id': resume.user_id if resume else '-',
            'username': resume.user.username if resume and resume.user else '-',
            'status': resume.analysis_status if resume else '-'
        })
    in_progress_data = []
    for resume in in_progress:
        in_progress_data.append({
            'id': resume.id,
            'filename': resume.filename,
            'user_id': resume.user_id,
            'username': resume.user.username if resume.user else '-',
            'status': resume.analysis_status
        })
    return jsonify({
        'queue': queue_data,
        'in_progress': in_progress_data,
        'total_waiting': total_waiting,
        'total_processing': total_processing,
        'total_completed': total_completed,
        'total_failed': total_failed
    })

@app.route('/admin/ai_queue_export')
@login_required
def admin_ai_queue_export():
    if not current_user.is_admin:
        abort(403)
    # 获取队列中的任务
    queue_ids = list(ai_task_queue.queue)
    # 获取所有状态的任务
    all_resumes = Resume.query.filter(Resume.analysis_status.in_(['排队中', '分析中', '已完成', '失败'])).order_by(Resume.id.desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['队列顺序', '简历ID', '文件名', '用户ID', '用户名', '当前状态', '分析时间'])
    
    # 写入队列中的任务
    for idx, rid in enumerate(queue_ids):
        resume = db.session.get(Resume, rid)
        if resume:
            latest_record = AnalysisRecord.query.filter_by(resume_id=resume.id).order_by(AnalysisRecord.created_at.desc()).first()
            analysis_time = latest_record.created_at.strftime('%Y-%m-%d %H:%M:%S') if latest_record else '-'
            cw.writerow([
                idx+1,
                resume.id,
                resume.filename,
                resume.user_id,
                resume.user.username if resume.user else '-',
                resume.analysis_status,
                analysis_time
            ])
    
    # 写入其他状态的任务（已完成、失败、处理中）
    for resume in all_resumes:
        if resume.id not in queue_ids:  # 避免重复写入队列中的任务
            latest_record = AnalysisRecord.query.filter_by(resume_id=resume.id).order_by(AnalysisRecord.created_at.desc()).first()
            analysis_time = latest_record.created_at.strftime('%Y-%m-%d %H:%M:%S') if latest_record else '-'
            cw.writerow([
                '-',  # 非队列中的任务没有队列顺序
                resume.id,
                resume.filename,
                resume.user_id,
                resume.user.username if resume.user else '-',
                resume.analysis_status,
                analysis_time
            ])
    
    output = si.getvalue()
    return (output, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=ai_queue_all.csv'
    })

@app.route('/ai_analysis_records')
@login_required
def ai_analysis_records():
    resume_id = request.args.get('resume_id', type=int)
    if current_user.is_admin:
        q = AnalysisRecord.query
    else:
        q = AnalysisRecord.query.filter_by(user_id=current_user.id)
    if resume_id:
        q = q.filter_by(resume_id=resume_id)
    records = q.order_by(AnalysisRecord.created_at.desc()).all()
    return render_template('ai_analysis_records.html', records=records)

@app.route('/ai_analysis_record/<int:record_id>')
@login_required
def ai_analysis_record_detail(record_id):
    record = AnalysisRecord.query.get_or_404(record_id)
    if not current_user.is_admin and record.user_id != current_user.id:
        abort(403)
    return render_template('ai_analysis_record_detail.html', record=record)

@app.route('/ai_analysis_record/<int:record_id>/reanalyze', methods=['POST'])
@login_required
def ai_analysis_record_reanalyze(record_id):
    record = AnalysisRecord.query.get_or_404(record_id)
    resume = db.session.get(Resume, record.resume_id)
    if not current_user.is_admin and resume.user_id != current_user.id:
        abort(403)
    if resume.analysis_status in ['排队中', '分析中']:
        flash('该简历正在分析中，请稍后', 'info')
        return redirect(url_for('ai_analysis_record_detail', record_id=record_id))
    resume.analysis_status = '排队中'
    db.session.commit()
    ai_task_queue.put(resume.id)
    flash('已提交再次分析任务，请稍后刷新查看结果', 'success')
    return redirect(url_for('ai_analysis_record_detail', record_id=record_id))

# 招聘需求管理路由
@app.route('/jobs')
@login_required
def jobs_list():
    """显示招聘需求列表"""
    # 管理员可以看到所有需求，普通用户只能看到自己创建的
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.updated_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.updated_at.desc()).all()
    return render_template('jobs_list.html', jobs=jobs)

@app.route('/jobs/add', methods=['GET', 'POST'])
@login_required
def job_add():
    """添加招聘需求"""
    if request.method == 'POST':
        title = request.form.get('title')
        requirements = request.form.get('requirements')
        description = request.form.get('description')
        
        if not title:
            flash('职位名称不能为空', 'danger')
            return redirect(url_for('job_add'))
        
        job = Job(
            title=title,
            requirements=requirements,
            description=description,
            user_id=current_user.id
        )
        db.session.add(job)
        db.session.commit()
        flash('招聘需求已添加', 'success')
        return redirect(url_for('jobs_list'))
    
    return render_template('job_form.html', job=None, action='add')

@app.route('/jobs/<int:job_id>')
@login_required
def job_detail(job_id):
    """查看招聘需求详情"""
    job = Job.query.get_or_404(job_id)
    # 权限检查: 管理员或创建者可查看
    if not current_user.is_admin and job.user_id != current_user.id:
        abort(403)
    return render_template('job_detail.html', job=job)

@app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def job_edit(job_id):
    """编辑招聘需求"""
    job = Job.query.get_or_404(job_id)
    # 权限检查: 管理员或创建者可编辑
    if not current_user.is_admin and job.user_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('职位名称不能为空', 'danger')
            return redirect(url_for('job_edit', job_id=job_id))
        
        job.title = title
        job.requirements = request.form.get('requirements')
        job.description = request.form.get('description')
        job.updated_at = datetime.utcnow()
        db.session.commit()
        flash('招聘需求已更新', 'success')
        return redirect(url_for('job_detail', job_id=job_id))
    
    return render_template('job_form.html', job=job, action='edit')

@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def job_delete(job_id):
    """删除招聘需求"""
    job = Job.query.get_or_404(job_id)
    # 权限检查: 管理员或创建者可删除
    if not current_user.is_admin and job.user_id != current_user.id:
        abort(403)
    
    db.session.delete(job)
    db.session.commit()
    flash('招聘需求已删除', 'success')
    return redirect(url_for('jobs_list'))

@app.route('/resume/<int:resume_id>/edit', methods=['GET', 'POST'])
@login_required
def resume_edit(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    # 权限校验
    if not current_user.is_admin and resume.user_id != current_user.id:
        abort(403)
    # 获取可选的招聘需求
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.updated_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.updated_at.desc()).all()
    if request.method == 'POST':
        job_id = request.form.get('job_id')
        resume.job_id = job_id if job_id else None
        db.session.commit()
        flash('简历信息已更新', 'success')
        return redirect(url_for('index'))
    return render_template('resume_edit.html', resume=resume, jobs=jobs)

if __name__ == '__main__':
    print("主进程已进入main", flush=True)
    for _ in range(MAX_AI_WORKERS):
        print("准备启动worker线程", flush=True)
        t = threading.Thread(target=ai_worker, daemon=True)
        t.start()
    app.run(debug=False, use_reloader=False) 





