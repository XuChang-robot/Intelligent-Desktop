import sqlite3
import json

db_path = "cache/cache.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询所有缓存记录
cursor.execute("SELECT id, intent_str, plan, plan_template, entities_template, timestamp FROM cache")
records = cursor.fetchall()

print("=" * 80)
print("缓存内容")
print("=" * 80)
print()

for record in records:
    id, intent_str, plan, plan_template, entities_template, timestamp = record
    
    print(f"ID: {id}")
    print(f"Timestamp: {timestamp}")
    print(f"Intent: {intent_str}")
    print()
    
    print("Plan:")
    print(json.dumps(json.loads(plan), ensure_ascii=False, indent=2))
    print()
    
    print("Plan Template:")
    print(json.dumps(json.loads(plan_template), ensure_ascii=False, indent=2))
    print()
    
    print("Entities Template:")
    print(json.dumps(json.loads(entities_template), ensure_ascii=False, indent=2))
    print()
    
    print("-" * 80)
    print()

conn.close()
