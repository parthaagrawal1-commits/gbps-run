from PIL import Image, ImageDraw, ImageFont, ImageFilter
F="/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FM="/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
BG=(11,18,32); CY=(34,211,238); WH=(248,250,252); MU=(148,163,184); GR=(34,197,94); AM=(245,158,11)

def font(p,s): return ImageFont.truetype(p,s)

def wrap(d,text,f,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t,font=f)<=maxw: cur=t
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines

def gauge(img,cx,cy,r,frac,label,sub,color):
    d=ImageDraw.Draw(img)
    bbox=[cx-r,cy-r,cx+r,cy+r]
    d.arc(bbox,150,390,fill=(30,41,59),width=int(r*0.16))
    d.arc(bbox,150,150+240*frac,fill=color,width=int(r*0.16))
    f=font(F,int(r*0.62)); fs=font(FM,int(r*0.2))
    d.text((cx,cy-r*0.05),label,font=f,fill=WH,anchor="mm")
    d.text((cx,cy+r*0.42),sub,font=fs,fill=MU,anchor="mm")

def card(W,H,head,sub,gval,gsub,gfrac,gcolor,badges,cta,out):
    img=Image.new("RGB",(W,H),BG)
    glow=Image.new("RGB",(W,H),BG); gd=ImageDraw.Draw(glow)
    gd.ellipse([W*0.1,H*0.25,W*0.9,H*0.75],fill=(14,60,80)); glow=glow.filter(ImageFilter.GaussianBlur(W*0.18))
    img=Image.blend(img,glow,0.9); d=ImageDraw.Draw(img)
    pad=int(W*0.08); y=int(H*0.09)
    d.rounded_rectangle([pad,y,pad+int(W*0.36),y+int(W*0.075)],radius=int(W*0.02),outline=CY,width=4)
    d.text((pad+int(W*0.18),y+int(W*0.037)),"gbps.run",font=font(F,int(W*0.04)),fill=CY,anchor="mm")
    y+=int(W*0.16)
    tall=H>W
    hf=font(F,int(W*(0.095 if tall else 0.07)))
    for ln in wrap(d,head,hf,W-2*pad):
        d.text((pad,y),ln,font=hf,fill=WH); y+=int(W*(0.115 if tall else 0.085))
    y+=int(W*0.02)
    sf=font(FM,int(W*(0.045 if tall else 0.036)))
    for ln in wrap(d,sub,sf,W-2*pad):
        d.text((pad,y),ln,font=sf,fill=MU); y+=int(W*(0.06 if tall else 0.048))
    r=int(W*0.27) if tall else int(W*0.15); cy=int(H*0.56) if tall else y+int(W*0.16)
    gauge(img,W//2,cy,r,gfrac,gval,gsub,gcolor); d=ImageDraw.Draw(img)
    by=cy+int(r*0.95) if tall else cy+int(r*0.85); bf=font(FM,int(W*(0.034 if tall else 0.03)))
    tot=sum(d.textlength(b,font=bf)+int(W*0.06) for b in badges)+int(W*0.02)*(len(badges)-1)
    x=(W-tot)//2
    cy2=H-int(H*(0.11 if tall else 0.09))
    if by+int(W*0.08) > cy2-int(W*0.07): badges=[]
    for b in badges:
        w=int(d.textlength(b,font=bf))+int(W*0.06)
        d.rounded_rectangle([x,by,x+w,by+int(W*0.07)],radius=int(W*0.035),fill=(30,41,59))
        d.text((x+w//2,by+int(W*0.035)),b,font=bf,fill=WH,anchor="mm"); x+=w+int(W*0.02)
    cy2=H-int(H*(0.11 if tall else 0.09))
    d.rounded_rectangle([pad,cy2-int(W*0.055),W-pad,cy2+int(W*0.055)],radius=int(W*0.03),fill=CY)
    d.text((W//2,cy2),cta,font=font(F,int(W*0.045)),fill=BG,anchor="mm")
    img.save(out,optimize=True)

sets=[
 ("hi_jio", "क्या Jio आपको पूरी स्पीड दे रहा है?", "15 सेकंड में असली स्पीड जानें। बिना ऐप, बिना विज्ञापन।", "287","Mbps",0.72,CY,["मुफ़्त","हिंदी में","कोई ऐप नहीं"],"अभी टेस्ट करें  ·  gbps.run"),
 ("hi_bgmi","BGMI में लैग? प्लान नहीं, पिंग देखो।","gbps.run लोड के दौरान पिंग मापता है और आपके राउटर को A+ से F तक ग्रेड देता है।","F","Bufferbloat",0.95,AM,["पिंग","जिटर","Bufferbloat"],"अपना ग्रेड देखें  ·  gbps.run"),
 ("en_pay","Paying for 300 Mbps. Getting 94?","Free speed test that also grades your router's bufferbloat. No ads, no app, 15 seconds.","94","Mbps",0.31,AM,["Free","No ads","No app"],"Test now  ·  gbps.run"),
 ("hi_wifi","WiFi धीमा है या इंटरनेट?","एक टेस्ट बताता है कि दिक्कत राउटर में है या प्रोवाइडर में।","A+","Bufferbloat",1.0,GR,["4K","वीडियो कॉल","गेमिंग"],"gbps.run पर टेस्ट करें"),
]
for name,*a in sets:
    card(1080,1920,*a,f"reel_{name}.png")
    card(1080,1080,*a,f"square_{name}.png")
print("ok")
