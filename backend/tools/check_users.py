from app.db import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).all()
print("users:", [(u.id, u.username, u.is_active) for u in users])
db.close()
