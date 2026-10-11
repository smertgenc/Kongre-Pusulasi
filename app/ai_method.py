"""The existing Excel model supplies all AHP weights; AI uses versioned criteria."""
from datetime import datetime, timezone
from app.congress_policy import POLICY_VERSION, policy_definitions

METHOD_VERSION = 'excel-ahp-project-policy-v3'
DEFAULT_CONTEXT = 'Excel AHP modeli · ' + POLICY_VERSION + ' · 0/1 kongre değerlendirmesi'

def method_snapshot(model, scoring_policy='legacy'):
    from app.scientific_policy import VERSION, PROFILE, definitions
    scientific=scoring_policy=='scientific'
    criteria=definitions() if scientific else policy_definitions()
    return {'version':METHOD_VERSION, 'policy_version':VERSION if scientific else POLICY_VERSION, 'criteria_profile':PROFILE if scientific else 'legacy',
            'analysis_date':datetime.now(timezone.utc).date().isoformat(),
            'model_id':model['id'], 'model_version':model['version'],
            'name':model['name'], 'weight_method':model['method'],
            'formula':'100 × Σ(global ağırlık × kriter değeri)',
            'accepted_values':{'true':1,'false':0,'null':'Bilinmiyor/uygulanamaz/çelişkili; puan aralığı gösterilir.' if scientific else 'Kanıt bulunamadı; sunucu kriterin proje varsayılanını uygular.'},
            'thresholds':model['thresholds'],
            'criteria':[{**c,'global_weight':model['weights'][c['code']]} for c in criteria]}
