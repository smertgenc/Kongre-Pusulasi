"""Offline research metrics. Undefined quantities are None, never fictitious 0."""
import math
from collections import Counter

def binary_metrics(gold,pred):
    if len(gold)!=len(pred):raise ValueError('Etiket uzunlukları eşleşmeli.')
    pairs=[(g,p) for g,p in zip(gold,pred) if g is not None]
    if any(g not in (0,1) or p not in (0,1,None) for g,p in pairs):raise ValueError('İkili etiketler gerekli.')
    tp=sum(g==p==1 for g,p in pairs);fp=sum(g==0 and p==1 for g,p in pairs);fn=sum(g==1 and p!=1 for g,p in pairs)
    def f1(label):
        t=sum(g==p==label for g,p in pairs);f=sum(g!=label and p==label for g,p in pairs);n=sum(g==label and p!=label for g,p in pairs)
        return 2*t/(2*t+f+n) if 2*t+f+n else None
    fs=[f1(x) for x in (0,1)];fs=[x for x in fs if x is not None]
    return {'n':len(pairs),'prediction_coverage':sum(p is not None for _,p in pairs)/len(pairs) if pairs else None,
            'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,
            'f1_positive':f1(1),'macro_f1':sum(fs)/len(fs) if fs else None,'unknown_gold_excluded':len(gold)-len(pairs)}

def ranks(x):
    out=[0.]*len(x);order=sorted(range(len(x)),key=x.__getitem__);start=0
    while start<len(x):
        end=start+1
        while end<len(x) and x[order[start]]==x[order[end]]:end+=1
        for i in order[start:end]:out[i]=(start+1+end)/2
        start=end
    return out

def spearman(x,y):
    if len(x)!=len(y):raise ValueError('Dizi uzunlukları eşleşmeli.')
    if len(x)<2:return None
    a=ranks(x);b=ranks(y);ma=sum(a)/len(a);mb=sum(b)/len(b)
    den=math.sqrt(sum((v-ma)**2 for v in a)*sum((v-mb)**2 for v in b))
    return sum((v-ma)*(w-mb) for v,w in zip(a,b))/den if den else None

def kendall(x,y):
    if len(x)!=len(y):raise ValueError('Dizi uzunlukları eşleşmeli.')
    concordant=discordant=ties_x=ties_y=0
    for i in range(len(x)):
        for j in range(i):
            a=(x[i]>x[j])-(x[i]<x[j]);b=(y[i]>y[j])-(y[i]<y[j])
            if a==b==0:continue
            if not a:ties_x+=1
            elif not b:ties_y+=1
            elif a==b:concordant+=1
            else:discordant+=1
    n=concordant+discordant;den=math.sqrt((n+ties_x)*(n+ties_y))
    return (concordant-discordant)/den if den else None

def kappa(a,b):
    pairs=[(x,y) for x,y in zip(a,b) if x is not None and y is not None]
    if len(a)!=len(b):raise ValueError('Uzman etiket uzunlukları eşleşmeli.')
    if not pairs:return None
    n=len(pairs);ca=Counter(x for x,_ in pairs);cb=Counter(y for _,y in pairs)
    expected=sum(ca[k]*cb[k] for k in ca)/n**2;observed=sum(x==y for x,y in pairs)/n
    return (observed-expected)/(1-expected) if expected<1 else None

def ndcg(relevance,k,ideal_relevance=None):
    ideal=relevance if ideal_relevance is None else ideal_relevance
    if type(k)!=int or k<1 or any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=20 for x in list(relevance)+list(ideal)):raise ValueError('NDCG için pozitif K ve sonlu 0–20 relevance gereklidir.')
    def dcg(v):return sum((2**r-1)/math.log2(i+2) for i,r in enumerate(v[:k]))
    denom=dcg(sorted(ideal,reverse=True));return dcg(relevance)/denom if denom else None
