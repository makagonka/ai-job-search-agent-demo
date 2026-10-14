from fastapi.testclient import TestClient
from app.api import create_app
from app.llm import Analysis, OpenAIJobReviewer
from app.seed import examples
import pytest


def test_ai_review_disabled_without_key(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with TestClient(create_app(tmp_path/'jobs.sqlite3')) as c:
        c.post('/v1/demo/load')
        job_id=c.get('/v1/jobs').json()[0]['id']
        r=c.post(f'/v1/jobs/{job_id}/ai-review')
        assert r.status_code==503
        assert c.get('/v1/stats').json()['applied']==0


def test_ai_review_requires_known_job(tmp_path):
    with TestClient(create_app(tmp_path/'jobs.sqlite3')) as c:
        assert c.post('/v1/jobs/999/ai-review').status_code==404


def test_ai_analysis_does_not_change_job_score(tmp_path):
    class FakeReviewer:
        def analyze(self,job,profile):
            return Analysis(verdict='consider',explanation='Check the actual hiring eligibility',
                            relevant_skills=['Python'],questions_to_check=['Is Europe eligible?'])
    with TestClient(create_app(tmp_path/'jobs.sqlite3',ai_reviewer=FakeReviewer())) as c:
        c.post('/v1/demo/load')
        before=c.get('/v1/jobs').json()[0]
        analyzed=c.post(f"/v1/jobs/{before['id']}/ai-review").json()
        after=c.get('/v1/jobs').json()[0]
        assert analyzed['verdict']=='consider'
        assert before['score']==after['score']
        assert after['status']=='new'


def test_ai_provider_failure_does_not_update_state(tmp_path):
    class Failing:
        def analyze(self,job,profile):
            raise RuntimeError('sensitive provider error')
    with TestClient(create_app(tmp_path/'db.sqlite3',ai_reviewer=Failing())) as c:
        c.post('/v1/demo/load')
        id=c.get('/v1/jobs').json()[0]['id']
        r=c.post(f'/v1/jobs/{id}/ai-review')
        assert r.status_code==502
        assert 'sensitive provider error' not in r.text
        assert c.get('/v1/jobs').json()[0]['status']=='new'


class MockResponse:
    def raise_for_status(self): pass
    def json(self):
        return {'choices':[{'message':{'content':'{"verdict":"consider","explanation":"Location check needed","relevant_skills":["API"],"questions_to_check":["Eligible in region?"]}'}}]}

class MockClient:
    payload=None
    def __init__(self,*args,**kwargs): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def post(self,url,*,headers,json):
        self.__class__.payload=(url,headers,json)
        return MockResponse()


def test_openai_adapter_uses_structured_outputs(monkeypatch,tmp_path):
    monkeypatch.setattr('app.llm.httpx.Client',MockClient)
    with TestClient(create_app(tmp_path/'jobs.sqlite3')) as c:
        c.post('/v1/demo/load')
        job_id=c.get('/v1/jobs').json()[0]['id']
        result=OpenAIJobReviewer(api_key='mock-test-key').analyze(
            # Retrieve a full record in the same shape the adapter expects
            __import__('app.storage',fromlist=['JobStore']).JobStore(tmp_path/'jobs.sqlite3').get(job_id),
            __import__('app.schemas',fromlist=['CandidateProfile']).CandidateProfile())
    assert result.verdict=='consider'
    url,headers,payload=MockClient.payload
    assert url=='https://api.openai.com/v1/chat/completions'
    assert payload['response_format']['type']=='json_schema'
    assert payload['response_format']['json_schema']['strict'] is True
    assert headers['Authorization']=='Bearer mock-test-key'
