"""Local TF-IDF adapter. Can be replaced by an embedding adapter without changing AHP."""
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache

STOP_WORDS = set('''the and for with from that this will are was were has have our your about their into its not but all also you can on of in to at by as an a is be or it we de da ve ile icin bir bu olarak olan gibi daha kongre kongresi conference conferences congress congresses international national uluslararasi annual symposium sempozyum summit workshop edition event etkinlik scientific academic bilimsel akademik research arastirma welcome registration register submission submissions deadline abstract abstracts paper papers call accepted proceedings committee program programme published publication university universitesi professor dr prof ltd inc january february march april may june july august september october november december ocak subat mart nisan mayis haziran temmuz agustos eylul ekim kasim aralik http https www com org html'''.split())

def normalize_text(value: str) -> str:
    value = unicodedata.normalize('NFKC', str(value or '')).casefold().replace('ı','i')
    value = ''.join(c for c in unicodedata.normalize('NFKD',value) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w\s]', ' ', value, flags=re.UNICODE).split())

def normalized_list(values: list[str]) -> list[str]:
    return sorted({normalize_text(v) for v in values if normalize_text(v)})

def jaccard(left, right) -> float | None:
    a,b=set(left),set(right)
    return 100*len(a&b)/len(a|b) if a and b else None

class LocalTextSimilarity:
    """Token/alias matching and pairwise TF-IDF cosine on a 0–100 scale."""
    version = 'local-tfidf-v1'

    def __init__(self, aliases: dict[str,list[str]]):
        pairs=sorted(((normalize_text(v),k) for k,values in aliases.items() for v in values),key=lambda x:len(x[0]),reverse=True)
        self.aliases=[(re.compile(r'(?<!\w)'+re.escape(v)+r'(?!\w)'),k) for v,k in pairs]

    @lru_cache(maxsize=1024)
    def tokens(self, text: str) -> tuple[str,...]:
        text=normalize_text(text)
        for pattern,canonical in self.aliases:text=pattern.sub(canonical,text)
        return tuple(w for w in text.split() if len(w)>1 and w not in STOP_WORDS and not w.isdigit())

    def similarity(self, left: str, right: str) -> float | None:
        a,b=Counter(self.tokens(left)),Counter(self.tokens(right))
        if not a or not b:return None
        vocabulary=a.keys()|b.keys()
        idf={k:math.log(3/(1+(k in a)+(k in b)))+1 for k in vocabulary}
        av={k:(1+math.log(v))*idf[k] for k,v in a.items()}
        bv={k:(1+math.log(v))*idf[k] for k,v in b.items()}
        denominator=math.sqrt(sum(x*x for x in av.values())*sum(x*x for x in bv.values()))
        return min(100,max(0,100*sum(v*bv.get(k,0) for k,v in av.items())/denominator))

    def term_match(self, term: str, text: str) -> float | None:
        wanted,available=set(self.tokens(term)),set(self.tokens(text))
        return 100*len(wanted&available)/len(wanted) if wanted and available else None

    def tag_similarity(self, left: list[str], right: list[str]) -> float | None:
        return jaccard(self.tokens(' '.join(left)),self.tokens(' '.join(right)))
