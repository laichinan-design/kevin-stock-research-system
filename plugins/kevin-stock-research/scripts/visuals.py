"""工程圖解: spec-driven SVG diagrams whose text is converted to outlines, PNG previews and QA checks.

Live <text> depends on fonts installed where the SVG is viewed (Drive preview, mail, Windows without
思源黑體 show blank or tofu). Every delivered SVG therefore carries glyph outlines, never live text.
"""
from __future__ import annotations
import glob, html, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

PLUGIN_ROOT=Path(__file__).resolve().parents[1]
SVGNS='http://www.w3.org/2000/svg'; XLINK='http://www.w3.org/1999/xlink'
ET.register_namespace('',SVGNS); ET.register_namespace('xlink',XLINK)
def q(tag): return '{%s}%s'%(SVGNS,tag)
FONT_FAMILY="'Noto Sans TC','Microsoft JhengHei','PingFang TC',sans-serif"
CJK_FAMILIES=('Noto Sans CJK TC','Noto Sans TC','Source Han Sans TC','Microsoft JhengHei','PingFang TC','WenQuanYi Zen Hei')
EXTS=('.otf','.ttf','.ttc','.woff2','.woff')

def styles():
    return json.loads((PLUGIN_ROOT/'profiles/deck_styles.json').read_text(encoding='utf-8'))

# ---------- fonts ----------
def _files(d):
    return sorted(p for p in Path(d).rglob('*') if p.suffix.lower() in EXTS)

def _split_weights(files):
    bold=[f for f in files if re.search(r'bold|black|heavy|bd\.',f.name+'/'+f.parent.name,re.I) and not re.search(r'semibold|demibold',f.name,re.I)]
    regular=[f for f in files if f not in bold and not re.search(r'thin|light|medium|semibold|demibold|black',f.name+'/'+f.parent.name,re.I)]
    return regular,[f for f in bold if not re.search(r'black|heavy',f.name+'/'+f.parent.name,re.I)] or bold

FALLBACK={'regular':['C:/Windows/Fonts/segoeui.ttf','C:/Windows/Fonts/arial.ttf','/System/Library/Fonts/Supplemental/Arial.ttf',
                     '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
          'bold':['C:/Windows/Fonts/segoeuib.ttf','C:/Windows/Fonts/arialbd.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']}
def discover_fonts(font_dir=None):
    """CJK stack plus Latin/Greek fallback (μ、Ω、± etc. are missing from sliced web fonts)."""
    found=_discover_cjk(font_dir)
    for w in ('regular','bold'):
        extra=[Path(f) for f in FALLBACK[w] if Path(f).exists()][:1]
        if found[w] or w=='regular': found[w]=list(found[w])+extra
    return found

def _discover_cjk(font_dir=None):
    """Order: argument/env dir, installed 思源/Noto TC, 微軟正黑體, 蘋方, fontconfig (Noto CJK TC … 文泉驛)."""
    for d in (font_dir,os.environ.get('KEVIN_FONT_DIR')):
        if d and Path(d).is_dir():
            reg,bold=_split_weights(_files(d))
            if reg: return {'regular':reg,'bold':bold,'source':'font_dir:'+str(d)}
    home=Path.home()
    local=[home/'AppData/Local/Microsoft/Windows/Fonts',Path('C:/Windows/Fonts'),home/'Library/Fonts',Path('/Library/Fonts'),home/'.fonts',home/'.local/share/fonts']
    for d in local:
        if d.is_dir():
            noto=[p for p in _files(d) if re.match(r'(NotoSans(CJK)?TC|SourceHanSansTC|NotoSansCJKtc)',p.name,re.I)]
            reg,bold=_split_weights(noto)
            if reg: return {'regular':reg,'bold':bold,'source':'installed Noto Sans TC: '+str(d)}
    win=Path('C:/Windows/Fonts')
    if (win/'msjh.ttc').exists():
        return {'regular':[win/'msjh.ttc'],'bold':[win/'msjhbd.ttc'] if (win/'msjhbd.ttc').exists() else [],'source':'Microsoft JhengHei'}
    if Path('/System/Library/Fonts/PingFang.ttc').exists():
        return {'regular':[Path('/System/Library/Fonts/PingFang.ttc')],'bold':[],'source':'PingFang TC'}
    try:
        out=subprocess.run(['fc-list','-f','%{file}|%{family}|%{style}\n',':lang=zh-tw'],capture_output=True,text=True,timeout=20).stdout
    except (OSError,subprocess.SubprocessError): out=''
    rows=[l.split('|',2) for l in out.splitlines() if l.count('|')==2]
    for fam in CJK_FAMILIES:
        hit=[r for r in rows if fam.lower() in r[1].lower()]
        if hit:
            reg=[Path(r[0]) for r in hit if re.search(r'regular|normal|book|^$',r[2],re.I) or r[2].strip()=='']
            bold=[Path(r[0]) for r in hit if re.fullmatch(r'bold',r[2].split(',')[0].strip(),re.I)]
            return {'regular':reg or [Path(hit[0][0])],'bold':bold,'source':'fontconfig: '+fam}
    raise RuntimeError('找不到繁中字型；請設定 KEVIN_FONT_DIR 指向思源黑體（Noto Sans TC）資料夾，或安裝微軟正黑體')

class FontStack:
    """Ordered fonts; each character comes from the first font whose cmap has it (handles sliced web fonts)."""
    def __init__(self,files):
        from fontTools.ttLib import TTFont, TTCollection
        self.fonts=[]
        for f in files:
            f=Path(f)
            if f.suffix.lower()=='.ttc':
                coll=TTCollection(str(f)); idx=0
                for i,font in enumerate(coll.fonts):
                    fam=' '.join(str(n) for n in font['name'].names if n.nameID in (1,16))
                    if re.search(r'\bTC\b|JhengHei|正黑|Zen Hei',fam): idx=i;break
                font=TTFont(str(f),fontNumber=idx)
            else: font=TTFont(str(f))
            self.fonts.append({'font':font,'cmap':font.getBestCmap() or {},'upem':font['head'].unitsPerEm,'glyphs':None})
        if not self.fonts: raise RuntimeError('empty font stack')
    def lookup(self,ch):
        for i,f in enumerate(self.fonts):
            name=f['cmap'].get(ord(ch))
            if name: return i,name
        return None
    def advance(self,i,name):
        f=self.fonts[i]; return f['font']['hmtx'][name][0]/f['upem']
    def path(self,i,name):
        from fontTools.pens.svgPathPen import SVGPathPen
        f=self.fonts[i]
        if f['glyphs'] is None: f['glyphs']=f['font'].getGlyphSet()
        pen=SVGPathPen(f['glyphs'],ntos=lambda v:'%d'%round(v))
        f['glyphs'][name].draw(pen); return pen.getCommands(),f['upem']

def load_fonts(font_dir=None):
    found=discover_fonts(font_dir)
    return {'regular':FontStack(found['regular']),'bold':FontStack(found['bold']) if found['bold'] else None,'source':found['source']}

# ---------- outline ----------
def _style(el):
    return dict(kv.split(':',1) for kv in (x.strip() for x in el.get('style','').split(';')) if ':' in kv)
def _prop(el,parents,name,default=None):
    while el is not None:
        v=_style(el).get(name) or el.get(name)
        if v not in (None,'','inherit'): return v.strip()
        el=parents.get(el)
    return default
def _num(v,default=0.0):
    if v is None: return default
    m=re.match(r'\s*(-?[\d.]+)',str(v)); return float(m[1]) if m else default
def _weight(v): return 700 if str(v) in ('bold','bolder') else int(_num(v,400))

def outline_svg(svg_text,fonts):
    """Replace every <text>/<tspan> with glyph outlines. Returns (svg_text, report)."""
    root=ET.fromstring(svg_text)
    parents={c:p for p in root.iter() for c in p}
    defs=root.find(q('defs'))
    if defs is None: defs=ET.Element(q('defs')); root.insert(0,defs)
    ids={};missing=set();count=0;fake_bold=False
    def glyph_id(stack_key,stack,i,name):
        key=(stack_key,i,name)
        if key not in ids:
            d,upem=stack.path(i,name); gid='g%d'%len(ids); ids[key]=(gid,upem)
            ET.SubElement(defs,q('path'),{'id':gid,'d':d})
        return ids[key]
    for text in [t for t in root.iter(q('text'))]:
        runs=[]
        def walk(el):
            if el.text: runs.append((el.text,el))
            for c in el:
                if c.tag==q('tspan'): walk(c)
                if c.tail: runs.append((c.tail,el))
        walk(text)
        x=_num((text.get('x') or '0').split()[0]); y=_num((text.get('y') or '0').split()[0])
        chunks=[[]]
        for s,el in runs:
            if el is not text and el.get('x') is not None and chunks[-1]: chunks.append([])
            chunks[-1].append((re.sub(r'\s+',' ',s),el))
        if chunks[0]: chunks[0][0]=(chunks[0][0][0].lstrip(),chunks[0][0][1])
        if chunks[-1]: chunks[-1][-1]=(chunks[-1][-1][0].rstrip(),chunks[-1][-1][1])
        group=ET.Element(q('g'),{'aria-label':''.join(s for c in chunks for s,_ in c),'role':'img'})
        if text.get('transform'): group.set('transform',text.get('transform'))
        for k in ('opacity','fill-opacity'):
            v=_prop(text,parents,k)
            if v: group.set(k,v)
        cur_x,cur_y=x,y
        for chunk in chunks:
            if not chunk: continue
            first=chunk[0][1]
            if first is not text:
                if first.get('x') is not None: cur_x=_num(first.get('x').split()[0])
                if first.get('y') is not None: cur_y=_num(first.get('y').split()[0])
            placed=[];width=0.0
            for s,el in chunk:
                size=_num(_prop(el,parents,'font-size','16'),16); bold=_weight(_prop(el,parents,'font-weight','400'))>=600
                dy=_num(el.get('dy'),0) if el is not text and el.get('dy') else 0
                for n,ch in enumerate(s):
                    stack=fonts['bold'] if bold and fonts['bold'] else fonts['regular']
                    hit=stack.lookup(ch)
                    if not hit and stack is not fonts['regular']: stack=fonts['regular'];hit=stack.lookup(ch)
                    if ch.isspace():
                        placed.append((None,width,size,el,bold,stack,dy if n==0 else 0));width+=(stack.advance(*hit) if hit else 0.3)*size;continue
                    if not hit: missing.add(ch);width+=size*0.5;continue
                    placed.append((hit,width,size,el,bold,stack,dy if n==0 else 0)); width+=stack.advance(*hit)*size
            anchor=_prop(first,parents,'text-anchor','start')
            shift={'middle':-width/2,'end':-width}.get(anchor,0)
            run_group=None;last_el=None
            for hit,off,size,el,bold,stack,dy in placed:
                cur_y+=dy
                if el is not last_el:
                    fill=_prop(el,parents,'fill','#000000')
                    run_group=ET.SubElement(group,q('g'),{'fill':fill}); last_el=el
                if hit is None: continue
                key='bold' if stack is fonts['bold'] else 'regular'
                gid,upem=glyph_id(key,stack,hit[0],hit[1]); s=size/upem
                attrs={'{%s}href'%XLINK:'#'+gid,'transform':'translate(%.2f %.2f) scale(%.5f %.5f)'%(cur_x+shift+off,cur_y,s,-s)}
                if bold and stack is not fonts['bold']:
                    attrs.update({'stroke':run_group.get('fill'),'stroke-width':'%d'%round(upem*0.035)}); fake_bold=True
                ET.SubElement(run_group,q('use'),attrs)
            cur_x+=shift+width
        parent=parents[text]; i=list(parent).index(text); parent.remove(text); parent.insert(i,group); count+=1
    out=ET.tostring(root,encoding='unicode')
    if 'xmlns:xlink' not in out[:500]: out=out.replace('<svg ','<svg xmlns:xlink="%s" '%XLINK,1)
    return out,{'texts_outlined':count,'unique_glyphs':len(ids),'missing_glyphs':''.join(sorted(missing)),'fake_bold':fake_bold,'font_source':fonts['source']}

def render_png(svg_text,dest,width=None):
    import cairosvg
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True)
    cairosvg.svg2png(bytestring=svg_text.encode('utf-8'),write_to=str(dest),output_width=width)
    return str(dest)

# ---------- QA ----------
def check_svg(text,illustrative=None):
    issues=[];warnings=[]
    try: root=ET.fromstring(text)
    except ET.ParseError as e: return {'status':'failed','issues':['XML parse error: '+str(e)],'warnings':[]}
    if any(True for _ in root.iter(q('text'))): issues.append('仍有 <text> 活字：檢視端缺字型時不會顯示，請先 outline')
    if not root.get('viewBox'): issues.append('缺 viewBox，縮放會變形')
    labels=' '.join(g.get('aria-label','') for g in root.iter(q('g')))
    if '來源' not in labels and '資料來源' not in labels: issues.append('缺資料來源標註（頁腳「來源：…」含頁碼）')
    if illustrative is not False and '示意' not in labels: warnings.append('未標「示意圖」；若非公司原圖或實物照片須標示')
    if re.search(r'<image[^>]+href="(?!data:)',text): warnings.append('引用外部圖片，離線或 Drive 預覽可能看不到')
    if len(text.encode())>3*1024*1024: warnings.append('SVG 超過 3MB')
    return {'status':'failed' if issues else 'passed','issues':issues,'warnings':warnings}

# ---------- spec builder ----------
def esc(s): return html.escape(str(s),quote=False)
class Canvas:
    def __init__(self,spec,palette,neutral):
        self.s=spec;self.w=int(spec.get('width',1600));self.h=int(spec.get('height',900))
        self.P='#'+palette['primary'];self.S='#'+palette['secondary']
        self.INK,self.MUTE,self.LINE,self.PALE='#'+neutral['ink'],'#'+neutral['muted'],'#'+neutral['line'],'#'+neutral['pale']
        self.parts=[];self.boxes={}
    def color(self,name,default):
        return {'primary':self.P,'secondary':self.S,'ink':self.INK,'muted':self.MUTE,'line':self.LINE,None:default}.get(name,name if str(name).startswith('#') else default)
    def text(self,x,y,s,size=18,color=None,anchor='start',weight=400):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{self.color(color,self.INK)}" text-anchor="{anchor}">{esc(s)}</text>')
    def box(self,e):
        x,y,w,h=(float(e[k]) for k in ('x','y','w','h')); style=e.get('style','primary')
        fill,stroke,tc,lc={'primary':(self.PALE,self.P,self.INK,self.MUTE),'muted':(self.PALE,self.LINE,self.INK,self.MUTE),
                          'solid':(self.P,self.P,'#FFFFFF','#FFFFFF'),'secondary':('#FFFFFF',self.S,self.INK,self.MUTE)}.get(style,(self.PALE,self.P,self.INK,self.MUTE))
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{e.get("rx",14)}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
        lines=e.get('lines',[]);ts=e.get('title_size',24);ls=e.get('line_size',17)
        ty=y+34 if lines else y+h/2+ts*0.35
        self.text(x+w/2,ty,e.get('title',''),ts,tc,'middle',700)
        for i,ln in enumerate(lines): self.text(x+w/2,y+46+(i+1)*(ls+7),ln,ls,lc,'middle')
        if e.get('id'): self.boxes[e['id']]=(x,y,w,h)
    def anchor_points(self,a,b):
        ax,ay,aw,ah=self.boxes[a];bx,by,bw,bh=self.boxes[b]
        acx,acy,bcx,bcy=ax+aw/2,ay+ah/2,bx+bw/2,by+bh/2
        if abs(bcx-acx)>abs(bcy-acy):
            return (ax+aw,acy,bx,bcy) if bcx>acx else (ax,acy,bx+bw,bcy)
        return (acx,ay+ah,bcx,by) if bcy>acy else (acx,ay,bcx,by+bh)
    def arrow(self,e):
        x1,y1,x2,y2=self.anchor_points(e['from'],e['to']) if 'from' in e else e['points']
        dash=' stroke-dasharray="8 6"' if e.get('dash') else ''
        col=self.color(e.get('color'),self.P); mid='ah2' if e.get('color')=='secondary' else 'ah'
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="3"{dash} marker-end="url(#{mid})"/>')
        if e.get('label'): self.text(e.get('lx',(x1+x2)/2),e.get('ly',(y1+y2)/2-10),e['label'],16,'muted','middle')
    def lane(self,e):
        self.parts.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" rx="18" fill="none" stroke="{self.LINE}" stroke-width="1.5" stroke-dasharray="6 6"/>')
        if e.get('label'): self.text(float(e['x'])+16,float(e['y'])+28,e['label'],17,'muted','start',700)
    def line(self,e):
        pts=e['points'];d=' '.join(f'{pts[i]},{pts[i+1]}' for i in range(0,len(pts),2))
        self.parts.append(f'<polyline points="{d}" fill="none" stroke="{self.color(e.get("color"),self.LINE)}" stroke-width="{e.get("width",2)}"/>')
    def render(self,footer_right):
        s=self.s;W,H=self.w,self.h
        head=(f'<svg xmlns="{SVGNS}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT_FAMILY}"><defs>'
              f'<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{self.P}"/></marker>'
              f'<marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{self.S}"/></marker></defs>'
              f'<rect width="{W}" height="{H}" fill="#FFFFFF"/><rect width="{W}" height="10" fill="{self.P}"/>')
        body=self.parts;self.parts=[]
        self.text(60,72,s['title'],36,'ink','start',800)
        if s.get('subtitle'): self.text(60,108,s['subtitle'],19,'muted')
        header=self.parts;self.parts=[]
        self.parts.append(f'<line x1="60" y1="{H-52}" x2="{W-60}" y2="{H-52}" stroke="{self.LINE}" stroke-width="1"/>')
        self.text(60,H-24,'來源：'+s['source'],14,'muted')
        self.text(W-60,H-24,footer_right,14,'muted','end')
        footer=self.parts;self.parts=body
        return head+''.join(header)+''.join(body)+''.join(footer)+'</svg>'

def build_svg(spec,config=None):
    """spec → live-text SVG (intermediate). Required: title, source (含頁碼), elements."""
    for k in ('title','source','elements'):
        if not spec.get(k): raise ValueError('diagram spec requires '+k)
    if not re.search(r'p\.|頁|第\s*\d+|https?://|法說|公告',spec['source']): raise ValueError('source must cite page, URL or filing (例：2025 年報 p.70–74)')
    st=styles(); pal_id=spec.get('palette') or ((config or {}).get('deck_style') or {}).get('palette') or '07'
    c=Canvas(spec,st['palettes'][pal_id],st['neutral'])
    for e in spec['elements']:
        t=e.get('type')
        if t=='box': c.box(e)
        elif t=='lane': c.lane(e)
        elif t=='line': c.line(e)
        elif t=='text': c.text(e['x'],e['y'],e['text'],e.get('size',18),e.get('color'),e.get('anchor','start'),e.get('weight',400))
        elif t!='arrow': raise ValueError('unknown element type: '+str(t))
    for e in spec['elements']:
        if e.get('type')=='arrow':
            if 'from' in e and (e['from'] not in c.boxes or e['to'] not in c.boxes): raise ValueError('arrow references unknown box id')
            c.arrow(e)
    who=f"{config['name']} {config['ticker']} " if config else ''
    right=f"{who}工程圖解｜{spec.get('asof',date.today().isoformat())}"+('｜示意圖，非公司原圖' if spec.get('illustrative',True) else '')
    return c.render(right)

def produce(spec,out_dir,config=None,fonts=None,png_width=1600):
    """Write 工程圖解/NN_名稱.svg (outlined), 原始碼/NN_名稱.json (editable spec) and PNG預覽/NN_名稱.png."""
    out_dir=Path(out_dir); name=f"{spec['id']}_{spec['name']}" if spec.get('id') else spec['name']
    if re.search(r'[\\/:*?"<>|]',name): raise ValueError('invalid diagram name')
    fonts=fonts or load_fonts()
    svg,report=outline_svg(build_svg(spec,config),fonts)
    if report['missing_glyphs']: raise ValueError('字型缺字：'+report['missing_glyphs']+'（換字型或改字）')
    qa=check_svg(svg,spec.get('illustrative',True))
    if qa['status']!='passed': raise ValueError('; '.join(qa['issues']))
    (out_dir/'原始碼').mkdir(parents=True,exist_ok=True)
    (out_dir/(name+'.svg')).write_text(svg,encoding='utf-8')
    (out_dir/'原始碼'/(name+'.json')).write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    png=None
    try: png=render_png(svg,out_dir/'PNG預覽'/(name+'.png'),png_width)
    except Exception as e: report['png_error']=type(e).__name__+': '+str(e)[:200]
    return {'svg':str(out_dir/(name+'.svg')),'png':png,'spec':str(out_dir/'原始碼'/(name+'.json')),'bytes':len(svg.encode()),**report,'qa':qa}

def outline_file(src,dest=None,fonts=None,png=None,keep_dir=None):
    """Outline an existing SVG. When overwriting in place, the live-text original is kept once in keep_dir."""
    src=Path(src); fonts=fonts or load_fonts(); original=src.read_text(encoding='utf-8')
    if '<text' not in original and dest is None:
        return {'file':str(src),'skipped':'already outlined','qa':check_svg(original)}
    svg,report=outline_svg(original,fonts)
    if report['missing_glyphs']: raise ValueError(src.name+' 字型缺字：'+report['missing_glyphs'])
    if keep_dir and dest is None:
        keep=Path(keep_dir)/(src.stem+'_活字原檔.svg'); keep.parent.mkdir(parents=True,exist_ok=True)
        if not keep.exists(): keep.write_text(original,encoding='utf-8')
    dest=Path(dest) if dest else src; dest.write_text(svg,encoding='utf-8')
    if png: render_png(svg,png)
    return {'file':str(dest),'png':str(png) if png else None,'bytes':len(svg.encode()),**report,'qa':check_svg(svg)}
