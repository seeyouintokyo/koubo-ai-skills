import sys,os,re,glob,collections,difflib
root=sys.argv[1]
for d in sorted(glob.glob(root+'/*/')):
    id=os.path.basename(d.rstrip('/')); rows=[]
    for l in open(d+'ocr.tsv',encoding='utf8'):
        p=l.rstrip('\n').split('\t'); t=int(re.search(r'(\d+)',p[0]).group(1))-1
        items=[]
        if len(p)>1 and p[1]:
            for it in p[1].split(' ;; '):
                m=re.match(r'(.*)\|y=([\d.-]+)\|h=([\d.-]+)\|x=([\d.-]+)\|w=([\d.-]+)$',it)
                if m: items.append((m[1],float(m[2]),float(m[3]),float(m[4]),float(m[5])))
        rows.append((t,items))
    c=collections.Counter()
    for t,it in rows:
        for s,y,h,x,w in it:
            if y>.7 and re.search(r'[一-鿿]',s) and abs(x-.5)<.12: c[round(y*50)/50]+=1
    band=c.most_common(1)[0][0]
    lines=[];ov=[];seen={}
    for t,it in rows:
        cur=''.join(s for s,y,h,x,w in it if abs(y-band)<=.025 and abs(x-.5)<.2 and re.search(r'[一-鿿]',s))
        if cur:
            if lines and difflib.SequenceMatcher(None,lines[-1][2],cur).ratio()>.6:
                lines[-1][1]=t
                if len(cur)>len(lines[-1][2]): lines[-1][2]=cur
            else: lines.append([t,t,cur])
        for s,y,h,x,w in it:
            if abs(y-band)>.04 and h>.035 and 1<len(s)<=16 and re.search(r'[一-鿿A-Za-z0-9]',s):
                if not(s in seen and t-seen[s]<20): ov.append((t,s))
                seen[s]=t
    dur=rows[-1][0]; ch=sum(len(l[2]) for l in lines)
    f=open(d+'clean.txt','w',encoding='utf8')
    f.write(' '.join(f'[{l[0]}]{l[2]}' for l in lines)+'\n\nOVER: '+' | '.join(f'{t}:{s}' for t,s in ov))
    print(id,'dur',dur,'band',band,'lines',len(lines),'chars',ch,'cps %.1f'%(ch/dur),'overlays/min %.0f'%(len(ov)/dur*60))
