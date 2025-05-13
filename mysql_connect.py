import pymysql

# Azure MySQL连接参数
HOST = 'mybingosql.mysql.database.azure.com'
PORT = 3306
USER = 'bingo'
PASSWORD = 'xxxxxx'  # 请替换为实际密码
DB = 'bingohr'  # 可选，若只测试连通性可不指定数据库

# 连接测试
try:
    connection = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        database=DB,
        ssl={'ssl': {}}
    )
    print('MySQL连接成功！')
    connection.close()
except Exception as e:
    print(f'MySQL连接失败: {e}') 