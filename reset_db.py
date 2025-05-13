from app import db, app

def reset_db():
    with app.app_context():
        db.drop_all()
        print("所有表已删除！")
        db.create_all()
        print("所有表已重建！")

if __name__ == '__main__':
    reset_db() 