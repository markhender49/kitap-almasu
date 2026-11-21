const kk=localStorage.locale==='kk', t=(ru,kz)=>kk?kz:ru
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
const $=s=>document.querySelector(s), main=$('main')
const labels={'/catalog':t('Каталог','Каталог'),'/exchanges':t('Мои обмены','Айырбастарым'),'/favorites':t('Избранное','Таңдаулылар'),'/publish':t('Добавить книгу','Кітап қосу'),'/guide':t('Как обменяться','Айырбас тәртібі'),'/account':t('Кабинет','Жеке кабинет')}
const link=(url,label)=>'<a href="'+url+'">'+esc(label)+'</a>'
const library=t('Вавилонская библиотека','Вавилон кітапханасы')
$('.brand').textContent=document.title=library
document.querySelector('nav a[href="'+location.pathname+'"]')?.setAttribute('aria-current','page')
document.documentElement.lang=kk?'kk':'ru'
$('nav').innerHTML=Object.entries(labels).map(([url,l])=>link(url,l)).join('')
$('#lang').textContent=kk?'Русский':'Қазақша'
$('#lang').onclick=()=>{localStorage.locale=kk?'ru':'kk';location.reload()}
const old={'#offers':'/exchanges','#catalog':'/catalog','#how':'/guide','#community':'/community'}
if(old[location.hash])location.replace(old[location.hash])
let me=null, fav=new Set(JSON.parse(localStorage.kitapWishes||'[]'))
async function api(url,method='GET',body){
 const headers={},opts={method,headers}
 if(sessionStorage.token)headers.Authorization='Bearer '+sessionStorage.token
 if(body instanceof URLSearchParams)opts.body=body
 else if(body){headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}
 const r=await fetch(url,opts)
 if(!r.ok)throw Error(({401:t('Проверьте имя и пароль или войдите повторно','Аты-жөніңіз бен құпиясөзді тексеріңіз'),403:t('Недостаточно прав','Рұқсат жоқ'),409:t('Действие недоступно. Проверьте имя или статус книги','Әрекет қолжетімсіз. Атын немесе кітап күйін тексеріңіз'),422:t('Проверьте поля формы и формат фото','Өрістер мен сурет пішімін тексеріңіз')})[r.status]||t('Страница недоступна','Бет қолжетімсіз'))
 return r.json()
}
function notice(e){$('#notice').textContent=e.message;setTimeout(()=>$('#notice').textContent='',5000)}
window.addEventListener('unhandledrejection',e=>notice(e.reason))
const title=s=>'<h1>'+esc(s)+'</h1>'
const mapValues={'Қазақша':['Казахский','Қазақша'],'Русский':['Русский','Орысша'],'English':['Английский','Ағылшынша'],'Өте жақсы':['Отличное','Өте жақсы'],'Жақсы':['Хорошее','Жақсы'],'Қанағаттанарлық':['Удовлетворительное','Қанағаттанарлық'],'Классика':['Классика','Классика'],'Роман':['Роман','Роман'],'Повесть':['Повесть','Хикаят'],'Фэнтези':['Фэнтези','Фэнтези'],'Антиутопия':['Антиутопия','Антиутопия'],'Фантастика':['Фантастика','Фантастика'],'Қазақ әдебиеті':['Казахская литература','Қазақ әдебиеті'],'Тарихи роман':['Исторический роман','Тарихи роман'],'Естелік':['Мемуары','Естелік'],'Novel':['Роман','Роман'],'Classic':['Классика','Классика'],'Romance':['Любовный роман','Махаббат романы'],'Dystopia':['Антиутопия','Антиутопия']}
const local=v=>mapValues[v]?t(...mapValues[v]):v
const options=(values,selected)=>values.map(v=>'<option value="'+esc(v)+'" '+(v===selected?'selected':'')+'>'+esc(local(v))+'</option>').join('')
const cover=b=>'<div class="cover">'+(b.photo?'<img alt="'+esc(b.title)+'" src="'+esc(b.photo)+'">':'<span class="jacket hue-'+(b.id%4)+'"><small>'+esc(b.author)+'</small><b>'+esc(b.title)+'</b><i>❖</i></span>')+'</div>'
const cards=rows=>'<div class="grid">'+rows.map(b=>'<section class="card"><a href="/books/'+b.id+'">'+cover(b)+'<h3>'+esc(b.title)+'</h3></a><p>'+esc(b.author)+'</p><small>'+esc(b.city)+' · '+esc(local(b.condition))+'</small></section>').join('')+'</div>'
const loginLink=()=>link('/account',t('Войти в аккаунт','Аккаунтқа кіру'))
function field(label,input){return '<label>'+esc(label)+input+'</label>'}
function form(html,submit){return '<form>'+html+'<button class="primary">'+esc(submit)+'</button></form>'}
function onForm(fn){$('form').onsubmit=async e=>{e.preventDefault();const btn=e.submitter;btn.disabled=true;try{await fn(Object.fromEntries(new FormData(e.target)))}catch(err){notice(err)}finally{btn.disabled=false}}}
async function account(){
 if(me)return editProfile()
 const reg=location.search==='?register'
 main.innerHTML=title(reg?t('Регистрация','Тіркелу'):t('Вход','Кіру'))+form(field(t('Имя','Аты'),'<input name="name" required>')+field(t('Пароль','Құпиясөз'),'<input type="password" name="password" required>')+(reg?field(t('Город','Қала'),citySelect()):''),reg?t('Зарегистрироваться','Тіркелу'):t('Войти','Кіру'))+link(reg?'/account':'/account?register',reg?t('У меня есть аккаунт','Аккаунтым бар'):t('Создать аккаунт','Аккаунт ашу'))
 onForm(async d=>{if(reg)await api('/api/register','POST',d);sessionStorage.token=(await api('/api/token','POST',new URLSearchParams({username:d.name,password:d.password}))).access_token;location.href='/catalog'})
}
const cities='Алматы Астана Шымкент Қарағанды Ақтөбе Тараз Павлодар Өскемен Семей Атырау Ақтау Қостанай Қызылорда Орал Түркістан Петропавл Көкшетау Талдықорған'.split(' ')
function citySelect(value){return '<select required name="city"><option value="">'+t('Выберите город','Қаланы таңдаңыз')+'</option>'+options(cities,value)+'</select>'}
async function publish(){
 if(!me){main.innerHTML=title(labels['/publish'])+loginLink();return}
 const id=new URLSearchParams(location.search).get('edit'),b=id?await api('/api/books/'+Number(id)):{},genres=await api('/api/categories')
 const names={title:t('Название','Атауы'),author:t('Автор','Авторы'),city:t('Город','Қала')}
 main.innerHTML=title(id?t('Редактировать книгу','Кітапты өңдеу'):labels['/publish'])+form(Object.entries(names).map(([k,l])=>field(l,k==='city'?citySelect(b.city):'<input required name="'+k+'" value="'+esc(b[k])+'">')).join('')+
 [['genre',t('Жанр','Жанр'),genres],['condition',t('Состояние','Күйі'),['Жақсы','Өте жақсы','Қанағаттанарлық']],['language',t('Язык книги','Кітап тілі'),['Қазақша','Русский','English']]].map(([k,l,vs])=>field(l,'<select name="'+k+'">'+options(vs,b[k])+'</select>')).join('')+
 field(t('Описание экземпляра','Дананың сипаттамасы'),'<textarea name="description">'+esc(b.description)+'</textarea>')+field(t('Какие книги хотите взамен? По одному названию в строке','Қандай кітаптарға айырбастайсыз? Әр атауды жеке жолға жазыңыз'),'<textarea name="wanted">'+esc((b.wanted||[]).join('\n'))+'</textarea>')+field(t('Фото вашего экземпляра · до 5 МБ','Кітаптың фотосы · 5 МБ дейін'),'<input type="file" accept="image/jpeg,image/png,image/webp" id="photo">'),t('Сохранить','Сақтау'))
 onForm(async d=>{d.wanted=[...new Set(d.wanted.split('\n').map(v=>v.trim()).filter(Boolean))];const f=$('#photo').files[0];if(f){if(f.size>5*1000*1000)throw Error(t('Фото больше 5 МБ','Фото 5 МБ-тан үлкен'));d.photo=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(f)})}const saved=await api('/api/books'+(id?'/'+Number(id):''),id?'PUT':'POST',d);location.href='/books/'+saved.id})
}
async function detail(){
 const b=await api('/api/books/'+Number(location.pathname.split('/')[2]))
 main.innerHTML=link('/catalog',labels['/catalog'])+'<div class="detail">'+cover(b)+'<section>'+title(b.title)+'<h2>'+esc(b.author)+'</h2><p>'+[b.genre,b.language,b.condition].map(x=>esc(local(x))).join(' · ')+'</p><p>'+esc(b.description)+'</p><p>'+esc(b.owner)+' · '+esc(b.city)+' · '+(b.owner_reviews?'★ '+Number(b.owner_rating).toFixed(1)+' ('+b.owner_reviews+')':t('Без оценок','Бағасы жоқ'))+'</p><h3>'+t('Владелец ищет','Иесі іздейтін кітаптар')+'</h3><p>'+esc(b.wanted.join(', ')||t('Рассмотрит ваши предложения','Ұсыныстарды қарастырады'))+'</p><button id="fav"></button></section></div>'
 function favLabel(){$('#fav').textContent=fav.has(b.id)?t('Удалить из избранного','Таңдаулылардан алып тастау'):labels['/favorites']+' +'}
 favLabel();$('#fav').onclick=()=>{fav.has(b.id)?fav.delete(b.id):fav.add(b.id);localStorage.kitapWishes=JSON.stringify([...fav]);favLabel()}
 if(me?.role==='admin')main.insertAdjacentHTML('beforeend','<p>'+link('/publish?edit='+b.id,t('Редактировать','Өңдеу'))+' <button id="del">'+t('Удалить','Жою')+'</button></p>')
 if($('#del'))$('#del').onclick=async()=>{if(confirm(t('Удалить книгу?','Кітапты жою керек пе?'))){await api('/api/books/'+b.id,'DELETE');location.href='/catalog'}}
 if(!me){main.insertAdjacentHTML('beforeend',loginLink());return}
 if(b.owner===me.name||b.status!=='available')return
 main.insertAdjacentHTML('beforeend',form(field(t('Что предложите взамен? Можно несколько названий','Орнына қандай кітаптар ұсынасыз? Бірнеше атау жазуға болады'),'<textarea name="offer" maxlength="180" required>'+esc(b.wanted[0]||'')+'</textarea>')+field(t('Сообщение','Хабарлама'),'<textarea name="message" maxlength="500"></textarea>'),t('Предложить обмен','Айырбас ұсыну')))
 onForm(async d=>{await api('/api/books/'+b.id+'/requests','POST',d);location.href='/exchanges'})
}
async function exchanges(){
 main.innerHTML=title(labels['/exchanges'])
 if(!me){main.insertAdjacentHTML('beforeend',loginLink());return}
 const rows=await api('/api/requests')
 const books=await api('/api/my-listings')
 main.insertAdjacentHTML('beforeend','<section class="mybooks"><h2>'+t('Мои объявления','Менің хабарландыруларым')+'</h2>'+ (books.length?books.map(b=>'<p>'+link('/books/'+b.id,b.title)+' <small>'+({available:t('В каталоге','Каталогта'),pending:t('В обмене','Айырбас жүріп жатыр'),traded:t('Получена','Алынды')})[b.status]+'</small></p>').join(''):link('/publish',labels['/publish']))+'</section><h2>'+t('Заявки','Өтінімдер')+'</h2>')
 for(const o of rows){
 const owner=o.owner===me.name
 const status={pending:t('Ожидает ответа','Жауап күтілуде'),accepted:t('Передача книг','Кітапты табыстау'),completed:t('Завершён','Аяқталды'),rejected:t('Отклонено','Қабылданбады')}[o.status]
 const receipt=(name,ok)=>'<li>'+esc(name)+' · '+(ok?t('получение подтверждено','алғанын растады'):t('ожидается подтверждение','растау күтілуде'))+'</li>'
 main.insertAdjacentHTML('beforeend','<article class="deal"><header><strong>'+ (owner?t('Входящая заявка','Кіріс өтінім'):t('Исходящая заявка','Шығыс өтінім'))+'</strong><span>'+status+'</span></header><div class="pair"><div><small>'+esc(o.requester)+'</small><h3>'+esc(o.offer)+'</h3></div><b>⇄</b><div><small>'+esc(o.owner)+'</small><h3>'+esc(o.book_title)+'</h3></div></div>'+(o.message?'<blockquote>'+esc(o.message)+'</blockquote>':'')+(['accepted','completed'].includes(o.status)?'<ul>'+receipt(o.owner,o.owner_ok)+receipt(o.requester,o.sender_ok)+'</ul>':'')+(o.status==='accepted'&&!(owner?o.owner_ok:o.sender_ok)?'<button class="primary" data-confirm="'+o.id+'">'+t('Я получил(а) книгу','Кітапты алдым')+'</button>':'')+(owner&&o.status==='pending'?['accepted','rejected'].map((s,i)=>'<button data-id="'+o.id+'" data-state="'+s+'">'+[t('Принять','Қабылдау'),t('Отклонить','Бас тарту')][i]+'</button>').join(' '):'')+(o.status==='completed'?reviewForm(o.id):'')+'</article>')
 }
 if(!rows.length)main.insertAdjacentHTML('beforeend','<p>'+t('Пока нет заявок','Әзірге өтінім жоқ')+'</p>')
 main.onclick=async e=>{if(e.target.dataset.confirm){await api('/api/requests/'+e.target.dataset.confirm+'/confirm','POST');notice(new Error(t('Подтверждение сохранено','Растау сақталды')));await exchanges();await showMatches()}if(e.target.dataset.state){await api('/api/requests/'+e.target.dataset.id+'?status='+e.target.dataset.state,'PATCH');await exchanges();await showMatches()}}
}
async function catalog(){
 const p=new URLSearchParams(location.search),page=Math.max(1,Number(p.get('page'))||1),genres=await api('/api/categories')
 main.innerHTML=title(labels['/catalog'])+'<form class="bar" action="/catalog"><input name="q" aria-label="'+t('Поиск','Іздеу')+'" placeholder="'+t('Название или автор','Атауы немесе авторы')+'" value="'+esc(p.get('q'))+'">'+[['city',t('Все города','Барлық қала'),'Алматы Астана Шымкент Қарағанды Ақтөбе Тараз Павлодар Өскемен Семей Атырау Ақтау Қостанай Қызылорда Орал Түркістан Петропавл Көкшетау Талдықорған'.split(' ')],['genre',t('Все жанры','Барлық жанр'),genres],['language',t('Все языки','Барлық тіл'),['Русский','Қазақша','English']]].map(([k,l,v])=>'<select aria-label="'+l+'" name="'+k+'"><option value="">'+l+'</option>'+options(v,p.get(k))+'</select>').join('')+'<button>'+t('Найти','Іздеу')+'</button></form>'
 p.set('page',page);p.set('limit',12)
 const rows=await api('/api/books?'+p)
 const pageLink=(n,label)=>{const q=new URLSearchParams(p);q.set('page',n);return link('/catalog?'+q,label)}
 main.insertAdjacentHTML('beforeend',cards(rows)+(rows.length?'':t('Книги не найдены','Кітаптар табылмады'))+'<div class="bar">'+(page>1?pageLink(page-1,t('Назад','Артқа')):'')+' '+page+' '+(rows.length===12?pageLink(page+1,t('Далее','Келесі')):'')+'</div>')
}
async function community(){
 const geo=await (await fetch('/static/kazakhstan.json')).json()
 const xy=([lon,lat])=>[(lon-46)*19,(56-lat)*30]
 const points=geo.features[0].geometry.coordinates[0].map(c=>xy(c).join(',')).join(' ')
 const stats=await api('/api/community')
 main.insertAdjacentHTML('beforeend','<section id=community><h2>'+t('Читатели Казахстана','Қазақстан оқырмандары')+'</h2><p>'+t('Профили читателей','Оқырман профильдері')+' · '+stats.readers+' &emsp; '+t('Города','Қалалар')+' · '+Object.keys(stats.cities).length+' &emsp; '+t('Доступные книги','Қолжетімді кітаптар')+' · '+stats.books+'</p>'+'<svg class="map" viewBox="-15 0 850 490" role="img" aria-label="'+t('Карта Казахстана','Қазақстан картасы')+'"><polygon points="'+points+'" fill="#dce7d8" stroke="#526f58"/>'+[['Алматы',76.9,43.24],['Астана',71.43,51.17],['Шымкент',69.59,42.32],['Ақтау',51.15,43.65],['Ақтөбе',57.17,50.28],['Семей',80.23,50.41]].map(([n,x,y])=>{const [cx,cy]=xy([x,y]);return '<a href="/catalog?city='+encodeURIComponent(n)+'"><circle cx="'+cx+'" cy="'+cy+'" r="5"/><text x="'+(cx+8)+'" y="'+cy+'">'+n+'</text></a>'}).join('')+'</svg><p>'+Object.entries(stats.cities).map(([city,n])=>link('/catalog?city='+encodeURIComponent(city),city+' · '+n)).join('　')+'</p><small>Natural Earth · world.geo.json</small></section>')
}
async function start(){
 if(sessionStorage.token){try{me=await api('/api/me')}catch{delete sessionStorage.token}}
 const path=location.pathname
 if(path==='/community'){location.replace('/#community');return}
 if(path.startsWith('/books/')){await detail();await readerReviews();await passport();return}
 if(path==='/favorites'){main.innerHTML=title(labels[path]);const rows=await Promise.all([...fav].map(id=>api('/api/books/'+id).catch(()=>null)));main.insertAdjacentHTML('beforeend',cards(rows.filter(Boolean))+(rows.some(Boolean)?'':t('Сохраните книгу на её странице','Кітапты өз бетінен сақтаңыз')));return}
 const handler={'/account':account,'/publish':publish,'/exchanges':exchanges,'/catalog':catalog}[path]
 if(handler){await handler();if(path==='/exchanges'&&me)await showMatches();return}
 if(path==='/guide'){guide();return}
 main.innerHTML='<section class="hero">'+title(library)+'<p>'+t('Обменивайтесь книгами с читателями своего города и следите за путешествием каждого экземпляра.','Өз қалаңыздағы оқырмандармен кітап алмасып, әр дананың жолын қадағалаңыз.')+'</p>'+'<a class="btn" href="/catalog">'+labels['/catalog']+' →</a></section><h2>'+t('Недавно добавленные','Жаңа қосылған кітаптар')+'</h2>'+cards(await api('/api/books?limit=4'))
 await community();if(location.hash==='#community')document.getElementById('community').scrollIntoView()
}
async function showMatches(){
 const pairs=await api('/api/matches')
 main.insertAdjacentHTML('beforeend','<section class="matches"><h2>'+t('Взаимные совпадения','Өзара сәйкестіктер')+'</h2>'+ (pairs.length?pairs.map(({give,get})=>'<article>'+link('/books/'+give.id,give.title)+' ⇄ '+link('/books/'+get.id,get.title)+'<p>'+esc(get.owner)+' · '+esc(get.city)+'</p><button class="primary" data-give="'+give.id+'" data-get="'+get.id+'">'+t('Предложить этот обмен','Осы айырбасты ұсыну')+'</button></article>').join(''):'<p>'+t('Добавьте в объявление названия желаемых книг. Здесь появятся читатели из вашего города, которые ищут вашу книгу и предлагают одну из нужных вам.','Хабарландыруға іздеген кітаптарыңыздың атауын енгізіңіз. Өз қалаңыздан өзара сәйкес ұсыныстар осы жерде көрсетіледі.')+'</p>')+'</section>')
 for(const button of main.querySelectorAll('[data-give]'))button.onclick=async()=>{
   await api('/api/books/'+button.dataset.get+'/requests','POST',{offered_id:Number(button.dataset.give),offer:pairs.find(p=>p.give.id===Number(button.dataset.give)).give.title})
   await exchanges();await showMatches()
 }
}
async function passport(){
 const id=Number(location.pathname.split('/')[2]),events=await api('/api/books/'+id+'/journey')
 main.insertAdjacentHTML('beforeend','<section id="passport"><h2>'+t('Паспорт экземпляра','Кітап данасының паспорты')+' <span class="serial">№ '+id+'</span>'+'</h2><img width="126" height="126" src="/api/books/'+id+'/qr" alt="QR"><p>'+t('QR-код ведёт к истории этого экземпляра.','QR-код осы дананың тарихын ашады.')+'</p>'+ (events.length?events.map(e=>'<p>'+esc(e.date)+' · '+esc(e.from)+' → '+esc(e.to)+'</p>').join(''):t('Подтверждённых передач пока нет.','Әзірге расталған табыстаулар жоқ.'))+'</section>')
 if(events.length&&me){const b=await api('/api/books/'+id);if(b.status==='traded'&&b.owner===me.name){$('#passport').insertAdjacentHTML('beforeend','<button id="relist">'+t('Вернуть в каталог','Каталогқа қайтару')+'</button>');$('#relist').onclick=async()=>{await api('/api/books/'+id+'/relist','POST');location.reload()}}}
 if(location.hash==='#passport')$('#passport').scrollIntoView()
}
function reviewForm(id){
 return '<details><summary>'+t('Оставить отзыв','Пікір қалдыру')+'</summary><form data-review="'+id+'"><label>'+t('Оценка','Баға')+'<select name="stars">'+[5,4,3,2,1].map(n=>'<option value="'+n+'">'+n+' ★</option>').join('')+'</select></label><textarea name="comment" required minlength="2" maxlength="600"></textarea><button>'+t('Сохранить отзыв','Пікірді сақтау')+'</button></form></details>'
}
main.addEventListener('submit',async e=>{
 if(!e.target.dataset.review)return
 e.preventDefault()
 const d=Object.fromEntries(new FormData(e.target))
 await api('/api/requests/'+e.target.dataset.review+'/review','PUT',d)
 notice(new Error(t('Отзыв сохранён','Пікір сақталды')))
})
async function readerReviews(){
 const id=Number(location.pathname.split('/')[2]),b=await api('/api/books/'+id)
 const [p,rows]=await Promise.all([api('/api/profile/'+encodeURIComponent(b.owner)),api('/api/reviews/'+encodeURIComponent(b.owner))])
 const panel=$('.detail section')
 panel.insertAdjacentHTML('beforeend','<p>'+link('#reviews',t('Читать отзывы о владельце','Иесі туралы пікірлерді оқу')+' · '+p.display)+'</p>')
 main.insertAdjacentHTML('beforeend','<section id="reviews"><h2>'+t('Отзывы о читателе','Оқырман туралы пікірлер')+' · '+esc(p.display)+'</h2>'+(rows.length?rows.map(r=>'<article><strong>'+esc(r.author)+' · '+r.stars+' ★</strong><p>'+esc(r.comment)+'</p></article>').join(''):t('Письменных отзывов пока нет. Партнёры могут оставить отзыв после завершения обмена.','Жазбаша пікірлер әзірге жоқ. Айырбас аяқталған соң қатысушылар пікір қалдыра алады.'))+'</section>')
}
async function editProfile(){
 const p=await api('/api/profile/'+encodeURIComponent(me.name))
 main.innerHTML=title(labels['/account'])+'<a class="btn" href="/docs">'+t('API-центр · Открыть Swagger','API орталығы · Swagger ашу')+'</a><section class="profile">'+(p.avatar?'<img class="portrait" src="'+esc(p.avatar)+'">':'<b class="portrait">'+esc(p.display[0])+'</b>')+'<div><h2>'+esc(p.display)+'</h2><p>'+t('Логин','Логин')+' · '+esc(me.name)+' · '+(me.role==='admin'?t('Администратор','Әкімші'):t('Читатель','Оқырман'))+'</p>'+link('/exchanges',labels['/exchanges'])+' · '+link('/favorites',labels['/favorites'])+'</div></section>'+form(field(t('Отображаемое имя','Көрсетілетін аты'),'<input name="display" required maxlength="60" value="'+esc(p.display)+'">')+field(t('Фото профиля · до 5 МБ','Профиль фотосы · 5 МБ дейін'),'<input id="avatar" type="file" accept="image/jpeg,image/png,image/webp">'),t('Сохранить профиль','Профильді сақтау'))+'<p><button id="out">'+t('Выйти','Шығу')+'</button></p>'
 $('#out').onclick=()=>{delete sessionStorage.token;location.reload()}
 onForm(async d=>{const f=$('#avatar').files[0];if(f){if(f.size>5000000)throw Error(t('Фото больше 5 МБ','Фото 5 МБ-тан үлкен'));d.photo=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)})}await api('/api/profile','PUT',d);await editProfile()})
}
function guide(){
 main.innerHTML=title(labels['/guide'])+'<img class="guidephoto" src="/static/guide-books.jpg" alt="'+t('Книги на полке','Сөредегі кітаптар')+'"><ol class="steps">'+[
 [labels['/publish'],t('Выберите город, загрузите фото своего экземпляра и опишите пометки или повреждения. Укажите желаемые книги по одной на строку.','Қаланы таңдап, кітабыңыздың фотосын жүктеңіз. Белгілер мен ақауларын сипаттап, қалаған атауларды жеке жолдарға жазыңыз.'),'/publish'],
 [labels['/catalog'],t('Откройте карточку и прочитайте отзывы о владельце. В поле предложения укажите свою книгу. В сообщении спросите о состоянии или предложите место встречи. Отправьте заявку — её увидит владелец.','Кітап бетін ашып, иесі туралы пікірлерді оқыңыз. Өз кітабыңызды ұсыныңыз. Хабарламада күйін сұраңыз немесе кездесу орнын көрсетіңіз. Өтінімді кітап иесі көреді.'),'/catalog'],
 [labels['/exchanges'],t('Во входящей заявке проверьте обе книги и сообщение. Примите или отклоните предложение. Для взаимного совпадения обе книги резервируются вместе.','Кіріс өтінімдегі екі кітап пен хабарламаны тексеріңіз. Ұсынысты қабылдаңыз немесе одан бас тартыңыз. Өзара сәйкестікте екі кітап қатар сақталады.'),'/exchanges'],
 [t('Подтвердите получение','Алғаныңызды растаңыз'),t('После встречи каждый участник отдельно нажимает «Я получил(а) книгу». После двух подтверждений обмен завершится, в паспорте появится запись и можно будет оставить отзыв.','Кездесуден кейін әр қатысушы «Кітапты алдым» түймесін басады. Екі растаудан кейін айырбас аяқталып, паспортқа жазба қосылады және пікір қалдыруға болады.'),'/exchanges']
 ].map(([name,body,url])=>'<li><h2>'+link(url,name)+'</h2><p>'+body+'</p></li>').join('')+'</ol>'
}
start().catch(notice)




