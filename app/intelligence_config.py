"""Validated, centralized settings for the three local decision-support layers."""
import json
import math
from pathlib import Path
from copy import deepcopy

CONFIG_PATH = Path(__file__).with_name('intelligence_config.json')

def load_intelligence_config(path: Path = CONFIG_PATH) -> dict:
    config = json.loads(path.read_text(encoding='utf-8'))
    for key, names in {
        'recommendation_weights': {'similarity', 'ahp', 'personal_fit'},
        'similarity_weights': {'text', 'tags', 'fields', 'criteria'},
        'fingerprint_weights': {'organizer', 'domain', 'email_domains', 'committee', 'text', 'address', 'publication', 'history'},
    }.items():
        weights = config[key]
        if set(weights) != names or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in weights.values()) or not math.isclose(sum(weights.values()), 1):
            raise ValueError(key + ': ağırlıklar sonlu ve negatif olmayan sayılar olmalı, toplamı 1 olmalıdır.')
    levels = config['fingerprint_thresholds']
    if len(levels) != 3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in levels) or not 0 < levels[0] < levels[1] < levels[2] <= 100:
        raise ValueError('Organizasyonel benzerlik eşikleri sıralı olmalıdır.')
    for key in ('minimum_similarity', 'minimum_topic_similarity'):
        if type(config[key]) not in (int,float) or not 0 <= config[key] <= 100:
            raise ValueError('Benzerlik eşiği 0–100 olmalıdır.')
    lo,hi=config['minimum_recommendations'],config['maximum_recommendations']
    if type(lo) is not int or type(hi) is not int or not 3 <= lo <= hi <= 5:
        raise ValueError('Öneri sayısı 3–5 aralığında olmalıdır.')
    cap=config['maximum_text_characters']
    if type(cap) is not int or not 1000 <= cap <= 100000:
        raise ValueError('Metin sınırı 1.000–100.000 aralığında olmalıdır.')
    if not isinstance(config['aliases'],dict) or any(not isinstance(k,str) or not isinstance(v,list) or any(not isinstance(x,str) or not x.strip() for x in v) for k,v in config['aliases'].items()):
        raise ValueError('Terim eşleştirmeleri metin listeleri olmalıdır.')
    return deepcopy(config)

def weighted_available(values: dict[str, float | None], weights: dict[str, float]) -> tuple[float | None, float]:
    """Missing evidence is absent, never a zero match; return score and coverage."""
    present = {k:v for k,v in values.items() if v is not None and weights.get(k,0)>0}
    coverage = sum(weights[k] for k in present)
    return (sum(weights[k]*v for k,v in present.items()) / coverage if coverage else None, coverage)
