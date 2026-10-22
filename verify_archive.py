import collections,json
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit

root=Path('archive');m=json.loads((root/'manifest.json').read_text('utf-8'))
urls=json.loads(Path('sitemap-urls.json').read_text('utf-8'))
missing=[u for u in urls if m.get(u,{}).get('status')!=200]
broken=[]
cms_residue=[]
class Check(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src','poster') and v and v.startswith('/') and not v.startswith('//'):
                path=urlsplit(v).path.lstrip('/')
                if not (Path('static-site')/path).exists():broken.append((str(self.file),v))
p=Check()
for file in Path('static-site').rglob('*.html'):
    text=file.read_text('utf-8')
    import re
    if re.search(r'wordpress\.org|WordPress 2\.9|wp-login|xmlrpc\.php|wlwmanifest|<form\b|id=[\"\'](?:respond|commentform)[\"\']',text,re.I):cms_residue.append(str(file))
    p.file=file;p.feed(text);p.reset()
report={'sitemap_urls':len(urls),'sitemap_missing':missing,'broken_local_references':broken,'cms_residue_pages':cms_residue,'failed_url_statuses':dict(collections.Counter(v.get('error') for v in m.values() if 'error'in v))}
(root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(report,ensure_ascii=True)[:2000])
