"""Produce readable articles and a local static mirror from the raw archive."""
import hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit, urljoin, unquote
from bs4 import BeautifulSoup

root=Path('archive')
manifest=json.loads((root/'manifest.json').read_text('utf-8'))
success={u:m for u,m in manifest.items() if m.get('status')==200}

def local(u,m):
    p=urlsplit(u)
    parts=[v for v in p.path.split('/') if v]
    # Encode characters forbidden in Windows filenames without changing hierarchy.
    parts=[re.sub(r'[<>:"\\|?*\x00-\x1f]',lambda x:'%'+format(ord(x[0]),'02X'),v).rstrip('.') for v in parts]
    path='/'.join(parts)
    if 'html' in m['type'] and (not parts or '.' not in parts[-1]): path+='/index.html'
    elif not path or p.path.endswith('/'): path+='/index.xml'
    path=path.lstrip('/')
    if p.query:
        # Cache-busting parameters are not needed for local assets.
        pass
    return path

paths={u:local(u,m) for u,m in success.items()}
def rewrite(value,base):
    target=urlsplit(urljoin(base,value))
    if target.hostname not in ('andbrowser.com','www.andbrowser.com'): return value
    key='http://andbrowser.com'+(target.path or '/')+('?' +target.query if target.query else '')
    fallback=key.split('?')[0]
    dest=paths.get(key) or paths.get(fallback)
    if dest: return '/'+dest+('#'+target.fragment if target.fragment else '')
    return value

out=Path('static-site');out.mkdir(exist_ok=True)
articles=[]
pages=[]
for u,m in success.items():
    data=Path(m['file']).read_bytes()
    if 'html' in m['type']:
        soup=BeautifulSoup(data,'html.parser')
        post=soup.select_one('.post')
        if urlsplit(u).path in ('/about/','/kanji/','/minjuku/','/minjuku/licenses/'):
            body=soup.select_one('#content') or soup.body or soup
            pages.append({'url':u,'title':soup.title.get_text(' ',strip=True) if soup.title else '', 'html':str(body),'text':body.get_text('\n',strip=True)})
        if post and re.search(r'^/(?!date/|category/|tag/|page/).+?/\d+/[^/]+/?$',urlsplit(u).path):
            title=post.find(['h1','h2']) or soup.title
            body=post.select_one('.entry') or post.select_one('.entry-content') or post
            articles.append({'url':u,'title':title.get_text(' ',strip=True),'html':str(body),'text':body.get_text('\n',strip=True)})
        for el in soup.find_all(True):
            for attr in ('href','src','poster'):
                if el.get(attr): el[attr]=rewrite(el[attr],u)
            if el.get('srcset'):
                el['srcset']=', '.join(' '.join([rewrite(v.strip().split()[0],u)]+v.strip().split()[1:]) for v in el['srcset'].split(',') if v.strip())
            if el.get('style'):
                el['style']=re.sub(r'url\(([\'"]?)([^)\'" ]+)\1\)',lambda x:'url('+rewrite(x[2],u)+')',el['style'])
        # Server-dependent submission endpoints cannot operate on a static host.
        for form in soup.find_all('form'):
            note=soup.new_tag('p');note.string='保存版のため、検索・コメント送信機能は利用できません。'
            form.replace_with(note)
        for script in soup.find_all('script'):
            if not script.get('src','').startswith('/'):
                script.decompose()
        data=str(soup).encode('utf-8')
    elif 'css' in m['type']:
        css=data.decode('utf-8','replace')
        data=re.sub(r'url\(([\'"]?)([^)\'" ]+)\1\)',lambda x:'url('+rewrite(x[2],u)+')',css).encode('utf-8')
    dest=out/paths[u];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)

(root/'articles.json').write_text(json.dumps(articles,ensure_ascii=False,indent=2),'utf-8')
(root/'pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),'utf-8')
article_dir=root/'articles';article_dir.mkdir(exist_ok=True)
for a in articles:
    ident=re.search(r'/(\d+)/',a['url'])[1]
    (article_dir/(ident+'.md')).write_text('# '+a['title']+'\n\n元URL: '+a['url']+'\n\n'+a['text']+'\n','utf-8')
errors={u:m for u,m in manifest.items() if 'error' in m}
(root/'errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2),'utf-8')
summary={'successful_urls':len(success),'articles':len(articles),'additional_pages':len(pages),'failed_urls':len(errors),'raw_bytes':sum(m['bytes'] for m in success.values()),'static_files':len(list(out.rglob('*.*')))}
(root/'summary.json').write_text(json.dumps(summary,indent=2),'utf-8')
print(json.dumps(summary))
from clean_static import clean_site
clean_site()
from clean_images import main as clean_images
clean_images()
