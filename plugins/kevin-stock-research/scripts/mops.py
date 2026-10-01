"""Public MOPS discovery. Download only links actually returned by official index."""
import re,urllib.request,urllib.parse,csv,io,time
from html import unescape
from research import period
BASE='https://doc.twse.com.tw'
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40) as r: b=r.read()
 if '查詢過量' in b.decode('cp950',errors='ignore'): raise RuntimeError('MOPS rate limit: pause retrieval; do not rotate identity or bypass')
 return b
def discover(ticker,roc_year,kind):
 url=BASE+'/server-java/t57sb01?'+urllib.parse.urlencode({'step':1,'colorchg':1,'co_id':ticker,'year':roc_year,'seamon':'','mtype':kind})
 b=get(url); t=b.decode('cp950',errors='replace'); rows=[]
 for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',t,flags=re.S|re.I):
  m=re.search(r'readfile2\("([A-Z])","(\d+)","([^"]+)"\)',tr)
  if not m or m[2]!=str(ticker): continue
  f=m[3]
  if kind=='F' and not re.search(r'F(?:04|E4)\.pdf$',f): continue
  if kind=='A' and not f.endswith('_AI1.pdf'): continue
  dates=re.findall(r'(\d{2,3})/(\d{2})/(\d{2})\s+(\d{2}:\d{2}:\d{2})',tr)
  published=None
  if dates:
   y,mo,d,tm=dates[-1]; published=f'{int(y)+1911:04d}-{mo}-{d}T{tm}+08:00'
  rows.append({'kind':kind,'ticker':str(ticker),'filename':f,'published':published,'index_url':url})
 return b,url,rows
def download(row):
 url=BASE+'/server-java/t57sb01?'+urllib.parse.urlencode({'step':9,'kind':row['kind'],'co_id':row['ticker'],'filename':row['filename']})
 landing=get(url)
 if landing.startswith(b'%PDF-'): return url,landing
 t=landing.decode('cp950',errors='replace'); links=re.findall(r'''href=['"]([^'"]+\.pdf)['"]''',t,re.I)
 if len(links)!=1: raise ValueError('official PDF link unavailable')
 resolved=urllib.parse.urljoin(BASE,unescape(links[0]))
 if urllib.parse.urlsplit(resolved).hostname!='doc.twse.com.tw': raise ValueError('unexpected PDF host')
 b=get(resolved)
 if not b.startswith(b'%PDF-'): raise ValueError('MOPS returned non-PDF')
 return url,b
def monthly(ticker,year,month,market='TWSE'):
 folder={'TWSE':'sii','TPEX':'otc'}[market]
 url=f'https://mopsov.twse.com.tw/nas/t21/{folder}/t21sc03_{year-1911}_{month}.csv'
 b=get(url); text=b.decode('utf-8-sig'); rows=list(csv.DictReader(io.StringIO(text)))
 found=[r for r in rows if str(r.get('公司代號','')).strip()==str(ticker)]
 if len(found)!=1: raise ValueError('monthly ticker missing or ambiguous')
 r=found[0]
 raw=str(r.get('資料年月',''))
 parts=raw.split('/')
 valid=(len(parts)==2 and (int(parts[0]) in (year,year-1911)) and int(parts[1])==month) or raw in (f'{year-1911}{month:02d}',f'{year}{month:02d}')
 if not valid: raise ValueError('monthly source period mismatch: '+raw)
 return url,b,r
