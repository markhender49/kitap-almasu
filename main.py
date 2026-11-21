from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import bcrypt
import jwt
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, or_, update
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from seed import ROOT, DB, init_db, connect

import base64
import io
import json
from PIL import Image, ImageOps, UnidentifiedImageError

init_db()
with connect() as migration:
    columns={r[1] for r in migration.execute("PRAGMA table_info(books)")}
    for field in ("photo","wanted"):
        if field not in columns:
            migration.execute(f"ALTER TABLE books ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")

def prepare_listing(data):
    values=data.model_dump()
    values["wanted"]=json.dumps(values["wanted"],ensure_ascii=False)
    encoded=values.pop("photo")
    if encoded:
        try:
            raw=base64.b64decode(encoded,validate=True)
            image=Image.open(io.BytesIO(raw))
            if image.format not in ("JPEG","PNG","WEBP") or image.width*image.height>24000000:
                raise ValueError()
            image.thumbnail((1200,1200))
            out=io.BytesIO()
            ImageOps.exif_transpose(image).convert("RGB").save(out,"JPEG",quality=82)
            values["photo"]=base64.b64encode(out.getvalue()).decode()
        except (ValueError,OSError,Image.DecompressionBombError):
            raise HTTPException(422,"JPEG / PNG / WebP")
    return values
with connect() as db:
    db.execute("CREATE TABLE IF NOT EXISTS accounts(name TEXT PRIMARY KEY, hash TEXT NOT NULL, role TEXT NOT NULL)")
engine = create_engine("sqlite:///" + str(DB))
base = automap_base()
base.prepare(autoload_with=engine)
Book, User, Offer, Account = [base.classes[k] for k in ("books","users","requests","accounts")]
keyfile = ROOT / ".jwt-key"
if not keyfile.exists():
    keyfile.write_text(secrets.token_hex(48))
key = keyfile.read_text()
app = FastAPI(title="Вавилонская библиотека")
app.mount("/static", StaticFiles(directory=ROOT/"static"), name="static")
bearer = OAuth2PasswordBearer(tokenUrl="/api/token")

def session():
    with Session(engine) as s:
        yield s

def member(token=Depends(bearer), s=Depends(session)):
    try:
        name = jwt.decode(token,key,algorithms=["HS256"])["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(401,"Войдите повторно")
    account = s.get(Account,name)
    if not account:
        raise HTTPException(401)
    return account

def admin(a=Depends(member)):
    if a.role != "admin":
        raise HTTPException(403,"Требуются права администратора")
    return a

class Registration(BaseModel):
    name: str = Field(min_length=2,max_length=60,pattern=r"^\S(?:.*\S)$")
    city: str = Field(min_length=1,max_length=80)
    password: str = Field(min_length=8,max_length=72)

CITIES="Алматы Астана Шымкент Қарағанды Ақтөбе Тараз Павлодар Өскемен Семей Атырау Ақтау Қостанай Қызылорда Орал Түркістан Петропавл Көкшетау Талдықорған".split()
from pydantic import field_validator

class Listing(BaseModel):
    @field_validator("city")
    @classmethod
    def supported_city(cls,value):
        if value not in CITIES:
            raise ValueError("Выберите город из списка")
        return value
    photo: str = Field(default='',max_length=7000000)
    wanted: list[str] = Field(default_factory=list,max_length=20)
    title: str = Field(min_length=1,max_length=160)
    author: str = Field(min_length=1,max_length=120)
    genre: str = Field(min_length=1,max_length=50)
    city: str = Field(min_length=1,max_length=80)
    language: str = Field(min_length=1,max_length=40)
    condition: str = Field(min_length=1,max_length=40)
    description: str = Field(default="",max_length=700)

class Proposal(BaseModel):
    offered_id: int | None = None
    offer: str = Field(min_length=1,max_length=180)
    message: str = Field(default="",max_length=500)

@app.get("/",include_in_schema=False)
def home():
    return FileResponse(ROOT/"static/index.html")

@app.post("/api/register",status_code=201)
def register(data:Registration,s=Depends(session)):
    password=data.password.encode()
    if len(password)>72:
        raise HTTPException(422,"Пароль должен занимать до 72 байт")
    if s.get(User,data.name) or s.scalar(select(Offer.id).where(Offer.requester==data.name)):
        raise HTTPException(409,"Имя занято")
    s.add(Account(name=data.name,hash=bcrypt.hashpw(password,bcrypt.gensalt()).decode(),role="reader"))
    s.add(User(name=data.name,city=data.city,rating=0,reviews=0,swaps=0,joined=str(datetime.now().year)))
    try:
        s.commit()
    except IntegrityError:
        raise HTTPException(409,"Имя занято")
    return {"name":data.name}

@app.post("/api/token")
def login(form=Depends(OAuth2PasswordRequestForm),s=Depends(session)):
    a=s.get(Account,form.username)
    raw=form.password.encode()
    if not a or len(raw)>72 or not bcrypt.checkpw(raw,a.hash.encode()):
        raise HTTPException(401,"Неверное имя или пароль")
    return {"access_token":jwt.encode({"sub":a.name,"exp":datetime.now(timezone.utc)+timedelta(hours=8)},key,algorithm="HS256"),"token_type":"bearer"}

@app.get("/api/me")
def me(a=Depends(member)):
    return {"name":a.name,"role":a.role}

def card(b,s):
    u=s.get(User,b.owner)
    return {**{c.name:getattr(b,c.name) for c in Book.__table__.columns if c.name not in ("photo","wanted")}, "wanted":json.loads(b.wanted or "[]"), "photo":f"/api/books/{b.id}/photo" if b.photo else "",
            "owner_rating":u.rating if u else None,"owner_reviews":u.reviews if u else 0}

@app.get("/api/books")
def catalog(page:int=Query(1,ge=1),limit:int=Query(12,ge=1,le=100),q:str="",city:str="",genre:str="",language:str="",s=Depends(session)):
    stmt=select(Book).where(Book.status=="available")
    if q:
        stmt=stmt.where(or_(Book.title.contains(q),Book.author.contains(q)))
    for field,value in [(Book.city,city),(Book.genre,genre),(Book.language,language)]:
        if value:
            stmt=stmt.where(field==value)
    return [card(b,s) for b in s.scalars(stmt.order_by(Book.id.desc()).offset((page-1)*limit).limit(limit))]

def find_book(i,s):
    b=s.get(Book,i)
    if not b or b.status=="deleted":
        raise HTTPException(404,"Книга не найдена")
    return b

@app.get("/api/books/{i}")
def detail(i:int,s=Depends(session)):
    return card(find_book(i,s),s)

@app.post("/api/books",status_code=201)
def publish(data:Listing,a=Depends(member),s=Depends(session)):
    if not s.get(Genre,data.genre):
        raise HTTPException(422,'Выберите жанр из каталога')
    b=Book(**prepare_listing(data),owner=a.name,status="available",cover="")
    s.add(b)
    s.commit()
    return card(b,s)

@app.put("/api/books/{i}")
def edit(i:int,data:Listing,a=Depends(admin),s=Depends(session)):
    b=find_book(i,s)
    if b.status!="available":
        raise HTTPException(409,"Книга участвует в обмене")
    if not s.get(Genre,data.genre):
        raise HTTPException(422,'Выберите жанр из каталога')
    for k,v in prepare_listing(data).items():
        setattr(b,k,v)
    s.commit()
    return card(b,s)

@app.delete("/api/books/{i}")
def remove(i:int,a=Depends(admin),s=Depends(session)):
    b=find_book(i,s)
    if b.status!="available":
        raise HTTPException(409,"Книга участвует в обмене")
    b.status="deleted"
    s.commit()
    return {"id":i}

@app.post("/api/books/{i}/requests",status_code=201)
def propose(i:int,data:Proposal,a=Depends(member),s=Depends(session)):
    result=s.execute(update(Book).where(Book.id==i,Book.status=="available",Book.owner!=a.name).values(status="pending"))
    if not result.rowcount:
        raise HTTPException(409,"Выберите доступную книгу другого участника")
    if data.offered_id is not None:
        offered=s.get(Book,data.offered_id)
        if not offered or not mutual(offered,s.get(Book,i),a.name):
            raise HTTPException(409,"Совпадение больше недоступно")
        if not s.execute(update(Book).where(Book.id==offered.id,Book.status=="available").values(status="pending")).rowcount:
            raise HTTPException(409,"Книга уже зарезервирована")
        data.offer=offered.title
    item=Offer(book_id=i,requester=a.name,status="pending",offer=data.offer,message=data.message)
    s.add(item)
    s.flush()
    s.add(Transfer(id=item.id,other=data.offered_id,receiver=s.get(Book,i).owner))
    s.add(item)
    s.commit()
    return {"id":item.id}

@app.get("/api/requests")
def history(a=Depends(member),s=Depends(session)):
    stmt=select(Offer,Book).join(Book,Offer.book_id==Book.id).where(or_(Offer.id.in_(select(Transfer.id).where(Transfer.receiver==a.name)),Offer.requester==a.name, (Book.owner==a.name) & ~Offer.id.in_(select(Transfer.id)))).order_by(Offer.id.desc())
    return [dict(owner_ok=bool(s.get(Transfer,o.id) and s.get(Transfer,o.id).owner_ok),sender_ok=bool(s.get(Transfer,o.id) and s.get(Transfer,o.id).sender_ok),id=o.id,offer=o.offer,message=o.message,status=o.status,requester=o.requester,owner=(s.get(Transfer,o.id).receiver if s.get(Transfer,o.id) else b.owner),book_title=b.title) for o,b in s.execute(stmt)]

@app.patch("/api/requests/{i}")
def decide(i:int,status:str=Query(pattern="^(accepted|rejected)$"),a=Depends(member),s=Depends(session)):
    o=s.get(Offer,i)
    if not o or s.get(Book,o.book_id).owner!=a.name:
        raise HTTPException(403,"Только владелец может ответить")
    if not s.execute(update(Offer).where(Offer.id==i,Offer.status=="pending").values(status=status)).rowcount:
        raise HTTPException(409,"Решение уже принято")
    transfer=s.get(Transfer,i)
    if not transfer:
        transfer=Transfer(id=i,receiver=a.name)
        s.add(transfer)
    for book_id in filter(None,[o.book_id,transfer.other]):
        s.get(Book,book_id).status="pending" if status=="accepted" else "available"
    s.commit()
    return {"status":status}
class GenreName(BaseModel):
    name: str = Field(min_length=1,max_length=50)

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class CatalogBase(DeclarativeBase):
    pass

class Genre(CatalogBase):
    __tablename__="genres"
    name: Mapped[str]=mapped_column(primary_key=True)

CatalogBase.metadata.create_all(engine)
with Session(engine) as s:
    for name in s.scalars(select(Book.genre).distinct()):
        if not s.get(Genre,name):
            s.add(Genre(name=name))
    s.commit()

@app.get("/api/categories")
def categories(s=Depends(session)):
    return list(s.scalars(select(Genre.name).order_by(Genre.name)))

@app.post("/api/categories",status_code=201)
def add_category(data:GenreName,a=Depends(admin),s=Depends(session)):
    if s.get(Genre,data.name):
        raise HTTPException(409,"Жанр существует")
    s.add(Genre(name=data.name))
    s.commit()
    return data

@app.put("/api/categories/{name}")
def rename_category(name:str,data:GenreName,a=Depends(admin),s=Depends(session)):
    genre=s.get(Genre,name)
    if not genre:
        raise HTTPException(404,"Жанр не найден")
    if data.name!=name and s.get(Genre,data.name):
        raise HTTPException(409,"Жанр существует")
    genre.name=data.name
    s.execute(update(Book).where(Book.genre==name).values(genre=data.name))
    s.commit()
    return data

@app.delete("/api/categories/{name}")
def delete_category(name:str,a=Depends(admin),s=Depends(session)):
    genre=s.get(Genre,name)
    if not genre:
        raise HTTPException(404,"Жанр не найден")
    if s.scalar(select(Book.id).where(Book.genre==name)):
        raise HTTPException(409,"Жанр используется книгами")
    s.delete(genre)
    s.commit()
    return {"name":name}


from fastapi.responses import Response

@app.get("/api/books/{i}/photo")
def photograph(i:int,s=Depends(session)):
    photo=find_book(i,s).photo
    if not photo:
        raise HTTPException(404)
    return Response(base64.b64decode(photo),media_type="image/jpeg")

for route in ("/catalog","/favorites","/exchanges","/community","/guide","/account","/publish","/books/{book_id}"):
    app.add_api_route(route,home,methods=["GET"],include_in_schema=False)

from sqlalchemy import func
from fastapi import Request
import qrcode

class Transfer(CatalogBase):
    __tablename__="transfers"
    id: Mapped[int]=mapped_column(primary_key=True)
    other: Mapped[int | None]
    receiver: Mapped[str]
    owner_ok: Mapped[bool]=mapped_column(default=False)
    sender_ok: Mapped[bool]=mapped_column(default=False)

class Journey(CatalogBase):
    __tablename__="journeys"
    id: Mapped[int]=mapped_column(primary_key=True)
    book_id: Mapped[int]
    city: Mapped[str]
    origin: Mapped[str]
    date: Mapped[str]

CatalogBase.metadata.create_all(engine)

def normalized(value):
    return " ".join(value.casefold().split())

def wants(book,title):
    return normalized(title) in {normalized(v) for v in json.loads(book.wanted or "[]")}

def mutual(mine,theirs,name):
    return (mine.owner==name and theirs.owner!=name and mine.status=="available"
            and normalized(mine.city)==normalized(theirs.city)
            and wants(mine,theirs.title) and wants(theirs,mine.title))

@app.get("/api/matches")
def matches(a=Depends(member),s=Depends(session)):
    books=s.scalars(select(Book).where(Book.status=="available")).all()
    return [{"give":card(m,s),"get":card(b,s)} for m in books if m.owner==a.name
            for b in books if mutual(m,b,a.name)]

@app.post("/api/requests/{i}/confirm")
def confirm(i:int,a=Depends(member),s=Depends(session)):
    # Serialize confirmations so the second signature records each movement once.
    from sqlalchemy import text
    s.execute(text("UPDATE transfers SET id=id WHERE id=:id"),{"id":i})
    transfer=s.get(Transfer,i)
    offer=s.get(Offer,i)
    if not offer or not transfer or a.name not in (transfer.receiver,offer.requester):
        raise HTTPException(403)
    if offer.status!="accepted":
        raise HTTPException(409)
    if a.name==transfer.receiver:
        transfer.owner_ok=True
    else:
        transfer.sender_ok=True
    if transfer.owner_ok and transfer.sender_ok:
        for book_id,name in [(offer.book_id,offer.requester),(transfer.other,transfer.receiver)]:
            if book_id:
                book=s.get(Book,book_id)
                profile=s.get(User,name)
                city=profile.city if profile else book.city
                s.add(Journey(book_id=book_id,origin=book.city,city=city,date=datetime.now(timezone.utc).date().isoformat()))
                book.owner,book.city,book.status,book.wanted=name,city,"traded","[]"
        offer.status="completed"
    s.commit()
    return {"status":offer.status}

@app.post("/api/books/{i}/relist")
def relist(i:int,a=Depends(member),s=Depends(session)):
    b=find_book(i,s)
    if b.owner!=a.name or b.status!="traded" or not s.scalar(select(Journey.id).where(Journey.book_id==i)):
        raise HTTPException(403)
    b.status="available"
    s.commit()
    return {"id":i}

@app.get("/api/books/{i}/journey")
def journey(i:int,s=Depends(session)):
    find_book(i,s)
    return [{"from":e.origin,"to":e.city,"date":e.date} for e in s.scalars(select(Journey).where(Journey.book_id==i).order_by(Journey.id))]

@app.get("/api/books/{i}/qr")
def qr(i:int,request:Request,s=Depends(session)):
    find_book(i,s)
    buffer=io.BytesIO()
    qrcode.make(str(request.base_url)+f"books/{i}#passport").save(buffer,format="PNG")
    return Response(buffer.getvalue(),media_type="image/png")

@app.get("/api/community")
def stats(s=Depends(session)):
    cities=s.execute(select(User.city,func.count()).group_by(User.city).order_by(func.count().desc())).all()
    return {"readers":sum(n for _,n in cities),"cities":dict(cities),"books":s.scalar(select(func.count()).select_from(Book).where(Book.status=="available"))}
# Older releases stored the recipient only on the listing.
with Session(engine) as session_:
    for previous in session_.scalars(select(Offer).where(~Offer.id.in_(select(Transfer.id)))):
        listing=session_.get(Book,previous.book_id)
        if listing:
            session_.add(Transfer(id=previous.id,receiver=listing.owner))
    session_.commit()

class ReaderProfile(CatalogBase):
    __tablename__="reader_profiles"
    name: Mapped[str]=mapped_column(primary_key=True)
    display: Mapped[str]
    avatar: Mapped[str]

class Feedback(CatalogBase):
    __tablename__="feedback"
    exchange: Mapped[int]=mapped_column(primary_key=True)
    author: Mapped[str]=mapped_column(primary_key=True)
    recipient: Mapped[str]
    stars: Mapped[int]
    comment: Mapped[str]

CatalogBase.metadata.create_all(engine)

class ProfileInput(BaseModel):
    display: str=Field(min_length=1,max_length=60)
    photo: str=Field(default="",max_length=7000000)

@app.get("/api/profile/{name}")
def profile(name:str,s=Depends(session)):
    p=s.get(ReaderProfile,name)
    return {"display":p.display if p else name,"avatar":("/api/avatar/"+name) if p and p.avatar else ""}

@app.get("/api/avatar/{name}")
def avatar(name:str,s=Depends(session)):
    p=s.get(ReaderProfile,name)
    if not p or not p.avatar:
        raise HTTPException(404)
    return Response(base64.b64decode(p.avatar),media_type="image/jpeg")

@app.put("/api/profile")
def save_profile(data:ProfileInput,a=Depends(member),s=Depends(session)):
    p=s.get(ReaderProfile,a.name) or ReaderProfile(name=a.name,avatar="")
    p.display=data.display.strip()
    if not p.display:
        raise HTTPException(422)
    if data.photo:
        p.avatar=prepare_listing(Listing(title="avatar",author=a.name,genre="avatar",city=CITIES[0],language="-",condition="-",photo=data.photo))["photo"]
    s.add(p)
    s.commit()
    return {"display":p.display}

@app.get("/api/my-listings")
def own_books(a=Depends(member),s=Depends(session)):
    return [card(b,s) for b in s.scalars(select(Book).where(Book.owner==a.name,Book.status!="deleted").order_by(Book.id.desc()))]

class ReviewInput(BaseModel):
    stars:int=Field(ge=1,le=5)
    comment:str=Field(min_length=2,max_length=600)

@app.get("/api/reviews/{name}")
def reviews(name:str,s=Depends(session)):
    return [dict(author=r.author,stars=r.stars,comment=r.comment) for r in s.scalars(select(Feedback).where(Feedback.recipient==name).order_by(Feedback.exchange.desc()))]

@app.put("/api/requests/{i}/review")
def review(i:int,data:ReviewInput,a=Depends(member),s=Depends(session)):
    o=s.get(Offer,i)
    tr=s.get(Transfer,i)
    if not tr or not o or o.status!="completed" or a.name not in (tr.receiver,o.requester):
        raise HTTPException(403)
    recipient=tr.receiver if a.name==o.requester else o.requester
    old=s.get(Feedback,(i,a.name))
    previous=old.stars if old else None
    reader=s.get(User,recipient)
    if reader:
        total=reader.rating*reader.reviews
        reader.reviews+=int(previous is None)
        reader.rating=(total+data.stars-(previous or 0))/reader.reviews
    s.merge(Feedback(exchange=i,author=a.name,recipient=recipient,**data.model_dump()))
    s.commit()
    return {"saved":True}

