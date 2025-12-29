"""Script to update table references from 'trends' to 'youtube'"""
import os

file_path = 'src/supabase_storage.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace table references
content = content.replace('table("trends")', 'table("youtube")')
content = content.replace("table('trends')", "table('youtube')")

# Replace timestamp column references (only in order clauses)
content = content.replace('order("created_at"', 'order("scraped_at"')
content = content.replace("order('created_at'", "order('scraped_at'")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated all table references from 'trends' to 'youtube'")
print("✅ Updated timestamp column from 'created_at' to 'scraped_at'")
