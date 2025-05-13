import os
from app import db, app

def reset_db():
    print("[reset_db] 当前工作目录:", os.getcwd(), flush=True)
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    print(f"[reset_db] 数据库URI: {db_uri}", flush=True)
    with app.app_context():
        print("[reset_db] 开始删除所有表...", flush=True)
        db.drop_all()
        print("[reset_db] 所有表已删除！", flush=True)
        print("[reset_db] 开始重建所有表...", flush=True)
        db.create_all()
        print("[reset_db] 所有表已重建！", flush=True)

if __name__ == '__main__':
    print("[reset_db] 脚本启动，准备重置数据库...", flush=True)
    reset_db()
    print("[reset_db] 数据库重置流程已完成。", flush=True) 