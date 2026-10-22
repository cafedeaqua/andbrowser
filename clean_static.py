"""Remove legacy CMS UI and metadata from the public static copy."""
import html,json,re,shutil
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup,Comment

def clean_site(files=None):
    root=Path('static-site').resolve()
    count=0
    for file in (files if files is not None else root.rglob('*.html')):
        source=file.read_text('utf-8')
        # Literal Android SDK XML contains CDATA; escape code before parsing HTML.
        source=re.sub(r'(<pre\b[^>]*>)(.*?)(</pre>)',lambda m:m[1]+(html.escape(html.unescape(m[2])) if '<sdk:license' in m[2] else m[2])+m[3],source,flags=re.S|re.I)
        soup=BeautifulSoup(source,'html.parser')
        for node in list(soup.select('#searchBox, #searchbox, #searchform, #search-form, .search-form, .search-box, .searchform, input[type="search"], .search-field, .search-submit, #searchsubmit, #respond, #commentform, #postcomment, .cancel-comment-reply, .comment-reply-link, .storyComment, .widget_meta, .widget_search, .wp_social_bookmarking_light, .wp_social_bookmarking_light_clear')):
            if node.parent: node.decompose()
        for node in list(soup.find_all(['meta','link','a','form','script'])):
            if not node.parent: continue
            href=node.get('href','')
            rel=node.get('rel',[])
            if (node.name=='form'
                or node.name=='meta' and node.get('name','').lower()=='generator'
                or node.name=='link' and any(v in rel for v in ('EditURI','wlwmanifest','pingback'))
                or re.search(r'wordpress\.org|wp-login|wp-admin|xmlrpc\.php|wlwmanifest|/comments/feed/|/comment-page-',href,re.I)
                or '#respond' in href or 'replytocom=' in href):
                parent=node.parent
                node.decompose()
                if parent.name=='li' and not parent.get_text(strip=True) and not parent.find(['img','a']): parent.decompose()
        for node in list(soup.find_all(string=lambda s:isinstance(s,Comment))): node.extract()
        for node in list(soup.find_all('p')):
            if node.get_text(strip=True)=='保存版のため、検索・コメント送信機能は利用できません。':node.decompose()
        for node in soup.select('.postcomments'):
            if not node.get_text(strip=True):node.decompose()
        for node in soup.find_all(True):
            for attr in list(node.attrs):
                if attr.lower().startswith('on'):del node[attr]
        text=str(soup)
        text=text.replace('/wp-content/','/assets/content/').replace('/wp-includes/','/assets/includes/')
        file.write_text(text,'utf-8');count+=1
    # Preserve theme/media/plugin assets and their license notices under neutral paths.
    for old,new in [('wp-content','assets/content'),('wp-includes','assets/includes')]:
        source=root/old;dest=root/new
        if source.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(source,dest,dirs_exist_ok=True)
            assert source.resolve().is_relative_to(root)
            shutil.rmtree(source)
    for file in (root/'assets').rglob('*'):
        if file.suffix.lower() in ('.css','.js'):
            text=file.read_text('utf-8',errors='replace')
            text=text.replace('/wp-content/','/assets/content/').replace('/wp-includes/','/assets/includes/')
            file.write_text(text,'utf-8')
    for file in (root/'assets/includes').glob('*.xml'):file.unlink()
    print(f'Cleaned {count} HTML pages')

if __name__=='__main__':clean_site()
