#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf
import csv, hashlib, io, json, sys
from pathlib import Path
from urllib.parse import quote
import requests
from pypdf import PdfReader
import urllib3
urllib3.disable_warnings()

OUT=Path('notes_master_math_france_arquivo'); OUT.mkdir(parents=True,exist_ok=True)
HEAD={'User-Agent':'Academic-PDF-Recovery/1.0','Accept':'application/json,application/pdf,*/*'}
RECORDS=[
{'num':1,'title':'Cours de probabilités','path':'01 - Proba-stat/01.1 Probabilites M1/01 - Cours de probabilites - Yves Coudene (2015).pdf','urls':['https://perso.lpsm.paris/~coudene/probabilites.pdf','http://perso.lpsm.paris/~coudene/probabilites.pdf','https://www.lpsm.paris/~coudene/probabilites.pdf','http://www.proba.jussieu.fr/pageperso/coudene/probabilites.pdf']},
{'num':5,'title':'Probabilités approfondies : martingales et chaînes de Markov','path':'01 - Proba-stat/01.2 Processus, Markov et martingales/05 - Probabilites approfondies martingales et chaines de Markov - Thomas Duquesne (2012).pdf','urls':['https://perso.lpsm.paris/~broutinn/teaching/4M011_poly_duquesne.pdf','http://perso.lpsm.paris/~broutinn/teaching/4M011_poly_duquesne.pdf','https://www.lpsm.paris/~broutinn/teaching/4M011_poly_duquesne.pdf']},
{'num':11,'title':'Statistique, Partie 2 : approche bayésienne','path':'01 - Proba-stat/01.5 Bayesien et MCMC/11 - Statistique, Partie 2 approche bayesienne - Anna Ben-Hamou; Arnaud Guyader.pdf','urls':['https://perso.lpsm.paris/~aguyader/files/teaching/M1/PolycopiePartie2.pdf','http://perso.lpsm.paris/~aguyader/files/teaching/M1/PolycopiePartie2.pdf','https://www.lpsm.paris/~aguyader/files/teaching/M1/PolycopiePartie2.pdf']},
{'num':15,'title':'Calcul stochastique et processus de diffusion','path':'01 - Proba-stat/01.3 Calcul stochastique et diffusions/15 - Calcul stochastique et processus de diffusion - Nicolas Fournier.pdf','urls':['https://perso.lpsm.paris/~nfournier/PolyCS.pdf','http://perso.lpsm.paris/~nfournier/PolyCS.pdf','https://www.lpsm.paris/~nfournier/PolyCS.pdf','http://www.proba.jussieu.fr/pageperso/fournier/PolyCS.pdf']},
{'num':19,'title':'Modélisation et statistique bayésienne computationnelle','path':'01 - Proba-stat/01.5 Bayesien et MCMC/19 - Modelisation et statistique bayesienne computationnelle - Nicolas Bousquet (2026).pdf','urls':['https://perso.lpsm.paris/~bousquet/poly-complet-2026-V1.pdf','http://perso.lpsm.paris/~bousquet/poly-complet-2026-V1.pdf','https://www.lpsm.paris/~bousquet/poly-complet-2026-V1.pdf']},
{'num':25,'title':'Méthodes de tenseurs pour les problèmes en grande dimension','path':'03 - EDP et calcul scientifique/25 - Methodes de tenseurs pour les problemes en grande dimension (2024).pdf','urls':['https://www.ljll.fr/MathModel/enseignement/cours/TenseursM2_2024.pdf','http://www.ljll.fr/MathModel/enseignement/cours/TenseursM2_2024.pdf','https://www.ljll.math.upmc.fr/MathModel/enseignement/cours/TenseursM2_2024.pdf','http://www.ljll.math.upmc.fr/MathModel/enseignement/cours/TenseursM2_2024.pdf']},
{'num':33,'title':'Contrôle optimal : théorie et applications','path':'02 - Analyse, optimisation et outils/Optimisation et controle/33 - Controle optimal theorie et applications - Emmanuel Trelat.pdf','urls':['https://www.ljll.fr/~trelat/fichiers/livreopt.pdf','http://www.ljll.fr/~trelat/fichiers/livreopt.pdf','https://www.ljll.math.upmc.fr/~trelat/fichiers/livreopt.pdf','http://www.ljll.math.upmc.fr/~trelat/fichiers/livreopt.pdf','https://www.ljll.math.upmc.fr/trelat/fichiers/livreopt.pdf']},
{'num':34,'title':'Méthodes mathématiques et numériques pour les plasmas','path':'03 - EDP et calcul scientifique/34 - Methodes mathematiques et numeriques pour les plasmas - Bruno Despres (2021).pdf','urls':['https://www.ljll.fr/despres/BD_fichiers/m2_plasma.pdf','http://www.ljll.fr/despres/BD_fichiers/m2_plasma.pdf','https://www.ljll.math.upmc.fr/despres/BD_fichiers/m2_plasma.pdf','http://www.ljll.math.upmc.fr/despres/BD_fichiers/m2_plasma.pdf']},
{'num':35,'title':'Équations aux dérivées partielles elliptiques','path':'03 - EDP et calcul scientifique/35 - Equations aux derivees partielles elliptiques - Herve Le Dret (2010).pdf','urls':['https://www.ljll.fr/ledret/M2Elliptique/chapitre4.pdf','http://www.ljll.fr/ledret/M2Elliptique/chapitre4.pdf','https://www.ljll.math.upmc.fr/ledret/M2Elliptique/chapitre4.pdf','http://www.ljll.math.upmc.fr/ledret/M2Elliptique/chapitre4.pdf']},
]

def validate(data:bytes):
 p=data.find(b'%PDF-')
 if p<0 or p>4096: raise ValueError(f'absence signature PDF {data[:20]!r}')
 data=data[p:]
 n=len(PdfReader(io.BytesIO(data),strict=False).pages)
 if n<1: raise ValueError('aucune page')
 return data,n

def direct(url):
 r=requests.get(url,headers=HEAD,timeout=(8,40),verify=False,allow_redirects=True); r.raise_for_status()
 data,n=validate(r.content); return data,n,r.url,'direct'

def arquivo_items(url):
 r=requests.get('https://arquivo.pt/textsearch',params={'versionHistory':url,'maxItems':100,'prettyPrint':'false'},headers=HEAD,timeout=(10,50))
 if r.status_code!=200: return []
 try: return r.json().get('response_items',[])
 except Exception: return []

def recover(rec):
 errors=[]
 for u in rec['urls']:
  try:
   data,n,src,kind=direct(u); return {**rec,'status':'ok','data':data,'pages':n,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_url':src,'source_kind':kind,'detail':''}
  except Exception as e: errors.append(f'direct {u}: {type(e).__name__}: {e}')
 candidates=[]
 with cf.ThreadPoolExecutor(max_workers=min(12,len(rec['urls']))) as ex:
  futs={ex.submit(arquivo_items,u):u for u in rec['urls']}
  for f,u in [(f,u) for f,u in futs.items()]:
   try:
    for item in f.result():
     if item.get('linkToOriginalFile'): candidates.append(item)
   except Exception as e: errors.append(f'arquivo index {u}: {e}')
 candidates.sort(key=lambda i:i.get('tstamp',''),reverse=True)
 seen=set()
 for item in candidates:
  link=item.get('linkToOriginalFile')
  if not link or link in seen: continue
  seen.add(link)
  try:
   r=requests.get(link,headers=HEAD,timeout=(10,90),verify=False,allow_redirects=True); r.raise_for_status()
   data,n=validate(r.content)
   return {**rec,'status':'ok','data':data,'pages':n,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_url':link,'source_kind':'arquivo.pt','detail':f'{len(candidates)} captures trouvées'}
  except Exception as e: errors.append(f'arquivo {link}: {type(e).__name__}: {e}')
 return {**rec,'status':'error','data':b'','pages':0,'bytes':0,'sha256':'','source_url':'','source_kind':'','detail':f'{len(candidates)} captures. '+ ' | '.join(errors)[-14000:]}

results=[]
with cf.ThreadPoolExecutor(max_workers=5) as ex:
 fs={ex.submit(recover,r):r for r in RECORDS}
 for f in cf.as_completed(fs):
  rec=fs[f]
  try: x=f.result()
  except BaseException:
   import traceback
   x={**rec,'status':'error','data':b'','pages':0,'bytes':0,'sha256':'','source_url':'','source_kind':'','detail':'UNHANDLED '+traceback.format_exc()}
  if x['status']=='ok':
   d=OUT/x['path']; d.parent.mkdir(parents=True,exist_ok=True); d.write_bytes(x.pop('data'))
  else: x.pop('data',None)
  results.append(x); print(f"[{x['num']:02d}] {x['status']} pages={x['pages']} bytes={x['bytes']} {x['title']} {x['detail'][-250:]}",flush=True)
results.sort(key=lambda x:x['num'])
fields=['num','title','path','urls','status','source_url','source_kind','pages','bytes','sha256','detail']
rows=[]
for x in results:
 y=dict(x); y['urls']=' | '.join(y['urls']); rows.append(y)
with (OUT/'manifest.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
(OUT/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
err=[x for x in results if x['status']!='ok']; print(f'SUCCES={len(results)-len(err)} ECHECS={len(err)}',flush=True)
sys.exit(1 if err else 0)
