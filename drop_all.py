from app import db, app

def drop_all_tables():
    with app.app_context():
        db.drop_all()
        print("所有表已删除！")

if __name__ == '__main__':
    drop_all_tables() 