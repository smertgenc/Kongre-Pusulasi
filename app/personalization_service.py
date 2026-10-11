"""Workspace-owned research profiles and independent academic match scores."""
import json
import uuid
from sqlalchemy import select
from app.models import UserResearchProfile
from app.services import now, encode
from app.intelligence_schemas import ResearchProfileInput
from app.text_similarity import LocalTextSimilarity

LOCAL_USER_ID = 'local-workspace'

class PersonalizationService:
    def __init__(self, db, text: LocalTextSimilarity):
        self.db,self.text=db,text

    def get_profile(self) -> dict:
        with self.db.session() as session:
            row=session.scalar(select(UserResearchProfile).where(UserResearchProfile.user_id==LOCAL_USER_ID))
            return ({'exists':True,'id':row.id,'created_at':row.created_at,'updated_at':row.updated_at,**json.loads(row.data)} if row
                    else {'exists':False,'enabled':False,'research_fields':[],'keywords':[]})

    def save_profile(self, request: ResearchProfileInput) -> dict:
        with self.db.session(write=True) as session:
            row=session.scalar(select(UserResearchProfile).where(UserResearchProfile.user_id==LOCAL_USER_ID))
            timestamp=now()
            if row:row.data=encode(request.model_dump());row.updated_at=timestamp
            else:session.add(UserResearchProfile(id=str(uuid.uuid4()),user_id=LOCAL_USER_ID,data=encode(request.model_dump()),created_at=timestamp,updated_at=timestamp))
        return self.get_profile()

    def delete_profile(self) -> dict:
        with self.db.session(write=True) as session:
            row=session.scalar(select(UserResearchProfile).where(UserResearchProfile.user_id==LOCAL_USER_ID))
            if row:session.delete(row)
        return self.get_profile()

    def personal_fit(self, congress: dict, profile: dict) -> dict:
        terms=list(dict.fromkeys(profile.get('research_fields',[])+profile.get('keywords',[])))
        base={'score':None,'matches':[],'method':self.text.version}
        if not profile.get('enabled') or not terms:return {**base,'status':'no_profile','message':'Kişisel uyum için araştırma profilinizi tanımlayıp etkinleştirin.'}
        text=congress.get('academic_text','')
        if not self.text.tokens(text):return {**base,'status':'insufficient_data','message':'Kişisel uyum için kongrenin konu bilgisi yetersiz.'}
        matches=[{'term':term,'score':self.text.term_match(term,text),'kind':'field' if term in profile.get('research_fields',[]) else 'keyword'} for term in terms]
        usable=[m for m in matches if m['score'] is not None]
        if not usable:return {**base,'status':'insufficient_data','message':'Eşleştirilebilir araştırma terimi bulunamadı.'}
        return {**base,'status':'ready','score':round(sum(m['score'] for m in usable)/len(usable),2),
                'matches':sorted(usable,key=lambda m:(-m['score'],m['term'])),'message':'Alan ve anahtar kelime kapsamı; AHP puanından bağımsızdır.'}
