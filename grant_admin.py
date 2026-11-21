import sys
from main import Account, Session, engine
with Session(engine) as session:
    account=session.get(Account,sys.argv[1])
    if not account:
        raise SystemExit("Сначала зарегистрируйте пользователя")
    account.role="admin"
    session.commit()
