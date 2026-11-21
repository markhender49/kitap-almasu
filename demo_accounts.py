import secrets
from main import Account, User, Session, engine, bcrypt, ROOT
path=ROOT/"demo-access.txt"
with Session(engine) as session, path.open("a",encoding="utf-8") as out:
    for name, role in [("Айдана","reader"),("София","reader"),("Нұрлан","admin")]:
        if session.get(User,name) and not session.get(Account,name):
            password=secrets.token_urlsafe(12)
            session.add(Account(name=name,role=role,hash=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()))
            out.write(f"{name} | {role} | {password}\n")
    session.commit()
