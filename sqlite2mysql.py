import sqlite3
import re

SQLITE_DB = 'resume_matcher.db'
OUTPUT_FILE = 'sqlite_schema_mysql_ddl.sql'

# 类型映射
SQLITE_TO_MYSQL = {
    'INTEGER': 'INT',
    'TEXT': 'TEXT',
    'REAL': 'DOUBLE',
    'BLOB': 'BLOB',
    'BOOLEAN': 'BOOLEAN',
    'DATETIME': 'DATETIME',
    'FLOAT': 'DOUBLE',
}

def convert_type(sqlite_type):
    t = sqlite_type.upper()
    for k, v in SQLITE_TO_MYSQL.items():
        if t.startswith(k):
            return t.replace(k, v)
    return t

def main():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()
    mysql_ddls = []
    for name, ddl in tables:
        # 替换类型
        lines = ddl.split('\n')
        new_lines = []
        for line in lines:
            m = re.match(r'\s*([`\w]+)\s+([\w\(\)]+)', line)
            if m and not line.strip().upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CONSTRAINT', 'KEY')):
                col, typ = m.groups()
                new_typ = convert_type(typ)
                line = line.replace(typ, new_typ, 1)
            new_lines.append(line)
        # 替换AUTOINCREMENT
        ddl_mysql = '\n'.join(new_lines)
        ddl_mysql = ddl_mysql.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
        # 替换单引号为反引号
        ddl_mysql = re.sub(r'"(\w+)"', r'`\1`', ddl_mysql)
        ddl_mysql = re.sub(r'\"', '`', ddl_mysql)
        # 替换IF NOT EXISTS
        ddl_mysql = ddl_mysql.replace('IF NOT EXISTS', '')
        # 添加ENGINE和字符集
        ddl_mysql = ddl_mysql.strip().rstrip(';') + ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n'
        mysql_ddls.append(ddl_mysql)
    # 输出到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ddl in mysql_ddls:
            f.write(ddl + '\n')
    print(f'已导出所有表结构到 {OUTPUT_FILE}')

if __name__ == '__main__':
    main() 