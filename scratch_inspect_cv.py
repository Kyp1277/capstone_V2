import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path("d:/capstone dicoding/backend")
sys.path.append(str(backend_path))

from modules.database import get_connection

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, target_role, cv_text FROM analyses ORDER BY created_at DESC LIMIT 5")
            rows = cur.fetchall()
            if not rows:
                print("Tidak ada riwayat analisis ditemukan di database.")
            else:
                for idx, row in enumerate(rows):
                    print(f"Row {idx}: ID={row[0]}, Target={row[1]}")
                    print(f"CV Text:\n{row[2]}")
                    print("=" * 60)
except Exception as e:
    print(f"Error: {e}")
