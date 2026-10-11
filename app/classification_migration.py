"""Rename stored classification labels without rescoring or changing evidence."""
import json
from engine import LOW_SUITABILITY, MEDIUM_SUITABILITY, HIGH_SUITABILITY

LEGACY_LABELS = {'Geçersiz': LOW_SUITABILITY, 'Ortalama': MEDIUM_SUITABILITY,
                 'Geçerli': HIGH_SUITABILITY}
# Explicit paths prevent changes to quotes, notes, source text, or AI job states.
RESULT_PATHS = {
    'evaluations': [('result',)],
    'ai_analyses': [('analysis', 'result'), ('analysis', 'report', 'ahp_result')],
    'ai_reviews': [('saved', 'result')],
}

def migrate_classifications(connection):
    """Run inside the schema migration transaction, including deleted records."""
    for table, paths in RESULT_PATHS.items():
        for row_id, raw in connection.exec_driver_sql(f'SELECT id, data FROM {table}').all():
            data = json.loads(raw)
            changed = False
            for path in paths:
                result = data
                for key in path:
                    result = result.get(key) if isinstance(result, dict) else None
                if isinstance(result, dict) and isinstance(result.get('status'), str):
                    replacement = LEGACY_LABELS.get(result['status'])
                    if replacement:
                        result['status'] = replacement
                        changed = True
            if changed:
                connection.exec_driver_sql(f'UPDATE {table} SET data=? WHERE id=?',
                    (json.dumps(data, ensure_ascii=False, allow_nan=False), row_id))
