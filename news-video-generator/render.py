#!/usr/bin/env python3
"""Persian news bulletin: RSS, market chart, images, Persian TTS, FFmpeg, Telegram."""
import html,io,os,re,subprocess,tempfile,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlparse
import requests
from PIL import Image,ImageDraw,ImageFont,ImageOps


ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"; OUT.mkdir(exist_ok=True)
W,H=1080,1920
BG=(12,19,34); PANEL=(24,35,55); WHITE=(245,247,250); MUTED=(177,190,208); CYAN=(75,205,220); GOLD=(245,190,82)
S=requests.Session(); S.headers.update({"User-Agent":"Mozilla/5.0 NetmanNewsVideo/1.0"})

def get(url,timeout=25):
 r=S.get(url,timeout=timeout); r.raise_for_status(); return r
def clean(s):
 return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(s or "")))).strip()
def fnt(size,bold=False):
 p="/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
 if not Path(p).exists(): p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 return ImageFont.truetype(p,size,layout_engine=ImageFont.Layout.RAQM)
def wrap(d,s,font,width):
 out=[]; line=""
 for word in clean(s).split():
  test=(line+" "+word).strip()
  if d.textbbox((0,0),test,font=font,direction="rtl")[2]<=width or not line: line=test
  else: out.append(line); line=word
 if line: out.append(line)
 return out
def draw(d,s,x,y,font,fill=WHITE,width=900,gap=18):
 for line in wrap(d,s,font,width):
  d.text((x,y),line,font=font,fill=fill,anchor="ra",direction="rtl",language="fa"); y+=font.size+gap
 return y
def rss(q,n):
 try:
  url="https://news.google.com/rss/search?q="+quote(q)+"&hl=fa&gl=IR&ceid=IR:fa"
  root=ET.fromstring(get(url).content); items=[]
  for it in root.findall(".//item")[:n]:
   title=clean(it.findtext("title")); link=clean(it.findtext("link")); src=clean(it.findtext("source")) or urlparse(link).netloc
   if title and link: items.append({"title":title,"link":link,"source":src})
  return items
 except Exception as e: print("RSS_ERROR",str(e)); return []
def og(url):
 try:
  page=get(url,15).text[:1500000]
  for pat in [r"<meta[^>]+property=['\"]og:image['\"][^>]+content=['\"]([^'\"]+)", r"<meta[^>]+content=['\"]([^'\"]+)['\"][^>]+property=['\"]og:image"]:
   m=re.search(pat,page,re.I)
   if m: return html.unescape(m.group(1))
 except Exception: pass
 return None
def market():
 prices=[]; price=change=usd=None
 try:
  j=get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7&interval=daily").json()
  prices=[float(x[1]) for x in j.get("prices",[])]; price=prices[-1] if prices else None
  change=(prices[-1]/prices[-2]-1)*100 if len(prices)>1 and prices[-2] else None
 except Exception as e: print("BTC_ERROR",str(e))
 try:
  j=get("https://raw.githubusercontent.com/iran-market/iran-market.github.io/main/data/popular.json").json()
  rows=j.get("data",[]) if isinstance(j,dict) else []
  item=next((x for x in rows if x.get("symbol")=="USD_IRR_FREE"),None)
  if item: usd=float(item["price"])
 except Exception as e: print("USD_ERROR",str(e))
 return prices,price,change,usd
def base(section,idx,total):
 im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
 for y in range(H):
  t=y/H; c=tuple(int(BG[k]*(1-t)+(23,52,77)[k]*t) for k in range(3)); d.line((0,y,W,y),fill=c)
 d.rounded_rectangle((52,55,W-52,155),radius=26,fill=PANEL,outline=(58,79,105),width=2)
 d.text((W-90,82),section,font=fnt(43,True),fill=CYAN,anchor="ra",direction="rtl",language="fa")
 d.text((90,95),f"{idx:02d}/{total:02d}",font=fnt(28),fill=MUTED)
 d.line((80,H-125,W-80,H-125),fill=(58,79,105),width=2)
 d.text((W-90,H-82),"گزارش خبری نت‌من | منابع در توضیحات",font=fnt(27),fill=MUTED,anchor="ra",direction="rtl",language="fa")
 return im
def chart(prices,path):
 im=Image.new("RGB",(920,500),PANEL); d=ImageDraw.Draw(im)
 d.rounded_rectangle((0,0,919,499),radius=25,outline=(65,87,114),width=2)
 if len(prices)<2: d.text((460,250),"نمودار در دسترس نیست",font=fnt(36),fill=MUTED,anchor="mm",direction="rtl",language="fa")
 else:
  lo,hi=min(prices),max(prices); span=max(hi-lo,1)
  pts=[(70+i*780/(len(prices)-1),400-(v-lo)/span*300) for i,v in enumerate(prices)]
  d.line(pts,fill=CYAN,width=8,joint="curve")
  d.text((65,35),f"\${hi:,.0f}",font=fnt(25),fill=MUTED)
  d.text((65,440),f"\${lo:,.0f}",font=fnt(25),fill=MUTED)
  d.text((850,38),"بیت‌کوین | ۷ روز",font=fnt(30,True),fill=WHITE,anchor="ra",direction="rtl",language="fa")
 im.save(path)
def scene(sc,idx,total,tmp):
 im=base(sc["section"],idx,total); d=ImageDraw.Draw(im); y=230
 if sc.get("chart"):
  p=tmp/f"chart{idx}.png"; chart(sc["chart"],p); im.paste(Image.open(p).resize((920,500)),(80,235)); y=800
 elif sc.get("image"):
  try:
   pic=Image.open(io.BytesIO(get(sc["image"],18).content)).convert("RGB")
   im.paste(ImageOps.fit(pic,(920,590)),(80,235)); y=880
  except Exception as e: print("IMAGE_ERROR",str(e))
 if sc.get("accent"):
  d.text((W-90,y),sc["accent"],font=fnt(58,True),fill=GOLD,anchor="ra",direction="rtl",language="fa"); y+=105
 y=draw(d,sc["title"],W-90,y,fnt(53,True),WHITE,900,22)+25
 draw(d,sc.get("body",""),W-90,y,fnt(38),MUTED,900,18)
 p=tmp/f"scene{idx:02d}.png"; im.save(p); return p
def main():
 crypto=rss("bitcoin OR ethereum OR cryptocurrency when:6h",4)
 iran=rss("Iran conflict OR Iran war OR Iran attack when:1d",4)
 fx=rss("Iran dollar free market OR Iranian rial OR USD IRR when:1d",3)
 prices,btc,chg,usd=market(); scenes=[]
 body=("قیمت آخرین داده بیت‌کوین حدود "+f"{btc:,.0f} دلار است. " if btc else "قیمت بیت‌کوین در این نوبت دریافت نشد. ")
 if chg is not None: body+=f"تغییر آخرین نقطه نسبت به روز قبل {chg:+.2f} درصد است. نمودار مسیر هفت روز اخیر را نشان می‌دهد."
 scenes.append({"section":"بازار رمزارز","title":"بیت‌کوین؛ نمای هفت‌روزه بازار","body":body,"chart":prices})
 scenes.append({"section":"بازار ارز ایران","title":"آخرین نرخ دلار آزاد","accent":f"{usd:,.0f} تومان" if usd else "داده ناموجود","body":f"آخرین نرخ دریافتی از منبع بازار ایران: {usd:,.0f} تومان." if usd else "نرخ دلار آزاد در زمان تولید گزارش دریافت نشد."})
 for section,items in [("خبرهای کریپتو",crypto),("تحولات ایران",iran),("اخبار ارز",fx)]:
  for item in items: scenes.append({"section":section,"title":item["title"],"body":"منبع: "+item["source"],"image":og(item["link"])})
 if len(scenes)==2: scenes.append({"section":"جمع‌بندی","title":"خبر تازه‌ای از خوراک خبری دریافت نشد","body":"اطلاعات بازار در صورت دسترس بودن در بخش‌های قبل آمده است."})
 now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td); clips=[]
  for i,sc in enumerate(scenes,1):
   pic=scene(sc,i,len(scenes),tmp); audio=tmp/f"voice{i:02d}.mp3"
   subprocess.run(["edge-tts","--voice","fa-IR-DilaraNeural","--text",sc["section"]+". "+sc["title"]+". "+sc.get("body",""),"--write-media",str(audio)],check=True)
   clip=tmp/f"clip{i:02d}.mp4"
   subprocess.run(["ffmpeg","-y","-loglevel","error","-loop","1","-i",str(pic),"-i",str(audio),"-vf","scale=1080:1920,format=yuv420p","-c:v","libx264","-preset","veryfast","-tune","stillimage","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(clip)],check=True)
   clips.append(clip)
  listing=tmp/"concat.txt"; listing.write_text("".join("file '"+str(p)+"'\\n" for p in clips),encoding="utf-8")
  final=OUT/"netman-persian-news.mp4"
  subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(listing),"-c","copy","-movflags","+faststart",str(final)],check=True)
 (OUT/"sources.txt").write_text("\\n".join(x["link"] for x in crypto+iran+fx),encoding="utf-8")
 print("VIDEO_READY",final); print("SCENES",len(scenes)); print("SIZE_BYTES",final.stat().st_size)
 token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID") or "-1001523446411"
 if token:
  with final.open("rb") as f:
   r=S.post(f"https://api.telegram.org/bot{token}/sendVideo",data={"chat_id":chat,"caption":f"گزارش ویدئویی نت‌من | {now}\\nکریپتو، دلار آزاد و خبرهای ایران","supports_streaming":"true"},files={"video":("netman-persian-news.mp4",f,"video/mp4")},timeout=240)
  r.raise_for_status()
  if not r.json().get("ok"): raise RuntimeError(r.text[:500])
  print("TELEGRAM_SENT=true")
 else: print("TELEGRAM_SENT=false: Telegram secret is not configured")
 print("NEWS_SOURCES",len(crypto+iran+fx))
if __name__=="__main__": main()
