"""Check static image references and remove confirmed unavailable images."""
import concurrent.futures,json,re,time,urllib.request,urllib.error
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote
from bs4 import BeautifulSoup

ROOT=Path('static-site').resolve()
class Images(HTMLParser):
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img' and a.get('src'):self.urls.add(a['src'])
        if tag in ('img','source') and a.get('srcset'):
            self.urls.update(v.strip().split()[0] for v in a['srcset'].split(',') if v.strip())

def check(src):
    if src.startswith('data:'):return src,{'state':'ok'}
    u=urlsplit(urljoin('http://andbrowser.com/',src))
    if u.hostname in ('andbrowser.com','www.andbrowser.com'):
        path=ROOT/unquote(u.path.lstrip('/'))
        if not path.exists():path=ROOT/u.path.lstrip('/')
        return src,{'state':'ok' if path.is_file() else 'broken','reason':'local file check'}
    url=urljoin('https://andbrowser.com/',src)
    for attempt in range(2):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Andbrowser image migration check)'})
            with urllib.request.urlopen(req,timeout=15) as r:
                data=r.read(512);kind=r.headers.get('Content-Type','')
                ok=kind.startswith('image/') or data.startswith((b'\x89PNG',b'\xff\xd8',b'GIF8',b'RIFF'))
                return src,{'state':'ok' if ok else 'broken','reason':kind,'url':url}
        except urllib.error.HTTPError as e:
            if e.code in (404,410):return src,{'state':'broken','reason':f'HTTP {e.code}','url':url}
            reason=str(e)
        except Exception as e:reason=str(e)
        time.sleep(.3)
    # Repeated failures cannot provide a displayable image to this static copy.
    return src,{'state':'broken','reason':reason,'url':url}

def main():
    parser=Images();parser.urls=set()
    files=list(ROOT.rglob('*.html'))
    for file in files:parser.feed(file.read_text('utf-8'));parser.reset()
    print(f'Checking {len(parser.urls)} unique image references',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=dict(pool.map(check,sorted(parser.urls)))
    bad={u for u,r in results.items() if r['state']=='broken'}
    removed=0;changed=0
    for file in files:
        text=file.read_text('utf-8')
        if not any(u in text or u.replace('&','&amp;') in text for u in bad):continue
        soup=BeautifulSoup(text,'html.parser');count=0
        for img in list(soup.find_all('img')):
            if img.get('src') in bad:
                parent=img.parent;img.decompose();count+=1
                if parent.name=='a' and not parent.get_text(strip=True) and not parent.find(['img','svg']):parent.decompose()
        for el in soup.find_all(['img','source']):
            if el.get('srcset'):
                keep=[v.strip() for v in el['srcset'].split(',') if v.strip() and v.strip().split()[0] not in bad]
                if keep:el['srcset']=', '.join(keep)
                else:del el['srcset']
        if count or str(soup)!=text:
            file.write_text(str(soup),'utf-8');changed+=1
        removed+=count
    report={'checked_urls':len(results),'broken_urls':len(bad),'removed_images':removed,'changed_pages':changed,'results':results}
    # Broken legacy markup can be interpreted differently by the HTML parsers.
    class Remaining(HTMLParser):
        def handle_starttag(self,tag,attrs):
            if tag=='img' and dict(attrs).get('src') in bad:self.tags.append(self.get_starttag_text())
    for file in files:
        text=file.read_text('utf-8');p=Remaining();p.tags=[];p.feed(text)
        if p.tags:
            for tag in p.tags:text=text.replace(tag,'')
            file.write_text(text,'utf-8')
            report['removed_images']+=len(p.tags)
    Path('archive/image-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)

if __name__=='__main__':main()
