import sqlite3
import json

def check():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    res = {}
    
    try:
        cursor.execute("SELECT id, subdominio, nombre FROM tenants_tenant")
        res['tenants'] = cursor.fetchall()
    except Exception as e:
        res['tenants_error'] = str(e)
        
    try:
        cursor.execute("SELECT id, email, tenant_id, rol FROM usuarios")
        res['usuarios'] = cursor.fetchall()
    except Exception as e:
        res['usuarios_error'] = str(e)
        
    with open('db_dump.json', 'w') as f:
        json.dump(res, f, indent=4)

if __name__ == '__main__':
    check()
