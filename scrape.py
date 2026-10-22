"""Archive public andbrowser.com pages and assets. pip install beautifulsoup4"""
import concurrent.futures, hashlib, json, re, sys, time, urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, urldefrag, quote
from bs4 import BeautifulSoup

ROOT = Path('archive')
ROOT.mkdir(exist_ok=True)
records = {}
pending = {'http://andbrowser.com/','http://andbrowser.com/robots.txt','http://andbrowser.com/sitemap.xml'}
if Path('sitemap-urls.json').exists():
    pending.update(json.loads(Path('sitemap-urls.json').read_text('utf-8')))
seen = set()
articles = {}

def normalize(url, base):
    u = urlsplit(urljoin(base, url))
    if u.hostname not in ('andbrowser.com', 'www.andbrowser.com') or u.scheme not in ('http','https'):
        return None
    path = u.path or '/'
    if re.search(r'/(wp-admin|wp-login|xmlrpc|wp-comments-post)', path): return None
    # Query pages duplicate canonical posts or invoke dynamic WordPress actions.
    if u.query and not path.startswith(('/wp-content/','/wp-includes/')): return None
    return urlunsplit(('http','andbrowser.com',path,u.query,''))

def fetch(url):
    name = hashlib.sha256(url.encode()).hexdigest()
    dest = ROOT/'raw'/name
    dest.parent.mkdir(exist_ok=True)
    try:
        req=urllib.request.Request(quote(url,safe=':/?=&%+;,@!~*\'()[]'),headers={'User-Agent':'AndbrowserMigrationArchive/1.0'})
        with urllib.request.urlopen(req,timeout=25) as r:
            data=r.read(); kind=r.headers.get('Content-Type',''); final=r.url
        dest.write_bytes(data)
        return url, {'status':200,'type':kind,'file':str(dest),'bytes':len(data),'final_url':final}, data
    except Exception as e:
        return url, {'error':str(e)}, b''

if (ROOT/'manifest.json').exists():
    records=json.loads((ROOT/'manifest.json').read_text('utf-8'))
    if '--fill' in sys.argv: seen.update(records)
    # Reparse cached successful responses to resume link discovery.

while pending:
    batch=sorted(pending-seen)[:12]
    if not batch: break
    pending.difference_update(batch); seen.update(batch)
    results=[]
    missing=[]
    for url in batch:
        old=records.get(url,{})
        if old.get('status')==200: results.append((url,old,Path(old['file']).read_bytes()))
        else: missing.append(url)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results.extend(pool.map(fetch,missing))
    for url,meta,data in results:
        records[url]=meta
        if meta.get('status')!=200: continue
        links=[]
        if 'html' in meta['type']:
            soup=BeautifulSoup(data,'html.parser')
            for el in soup.find_all(True):
                for attr in ('href','src','poster'):
                    if el.get(attr): links.append(el[attr])
                if el.get('srcset'):
                    links.extend(v.strip().split()[0] for v in el['srcset'].split(',') if v.strip())
                if el.get('style'): links.extend(re.findall(r'url\([\'"]?([^\)\'" ]+)',el['style']))
            post=soup.select_one('.post')
            if post and re.search(r'^/(?!date/|category/|tag/|page/).+?/\d+/[^/]+/?$',urlsplit(url).path):
                body=post.select_one('.entry') or post.select_one('.entry-content') or post
                title=post.find(['h1','h2']) or soup.title
                articles[url]={'url':url,'title':title.get_text(' ',strip=True) if title else '', 'html':str(body),'text':body.get_text('\n',strip=True)}
        elif 'css' in meta['type']:
            links.extend(re.findall(r'url\([\'"]?([^\)\'" ]+)',data.decode('utf-8','replace')))
        for link in links:
            target=normalize(link,url)
            if target and target not in seen: pending.add(target)
    (ROOT/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf-8')
    (ROOT/'articles.json').write_text(json.dumps(list(articles.values()),ensure_ascii=False,indent=2),'utf-8')
    print(f'Fetched {len(seen)}; queued {len(pending-seen)}; articles {len(articles)}; errors {sum("error" in r for r in records.values())}',flush=True)
    time.sleep(.3)
print('Archive complete',flush=True)
