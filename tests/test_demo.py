import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.cli import report
from app.ranking import rank_job
from app.schemas import CandidateProfile, JobIn
from app.seed import examples, seed
from app.storage import JobStore, canonical_url

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)

@pytest.fixture
def profile():
    return CandidateProfile()

@pytest.fixture
def client(tmp_path,profile):
    with TestClient(create_app(tmp_path / "demo.sqlite3", profile=profile)) as c:
        yield c


def test_health(client):
    assert client.get('/health').json() == {'status':'ok'}


def test_home_serves_dashboard(client):
    r=client.get('/')
    assert r.status_code==200 and 'Find better matches.' in r.text
    assert 'No auto-apply' in r.text


def test_seed_contains_only_fictional_example_urls():
    jobs=examples(NOW)
    assert len(jobs)==10
    assert all(j.url.startswith('https://jobs.example.org/') for j in jobs)
    assert all(j.published_at.tzinfo for j in jobs)


def test_seed_idempotence(client):
    first=client.post('/v1/demo/load').json()
    second=client.post('/v1/demo/load').json()
    assert first['inserted']==10 and second['inserted']==0
    assert len(client.get('/v1/jobs').json())==10


def test_ranking_order(client):
    client.post('/v1/demo/load')
    jobs=client.get('/v1/jobs').json()
    priority={'strong':0,'review':1,'low':2,'geo_restricted':3,'stale':4,'future_date':5}
    keys=[(priority[j['decision']], -j['score']) for j in jobs]
    assert keys==sorted(keys)
    # Hiring-restricted high-score jobs never outrank location-compatible matches.
    restricted=[i for i,j in enumerate(jobs) if j['decision']=='geo_restricted']
    strong=[i for i,j in enumerate(jobs) if j['decision']=='strong']
    assert max(strong)<min(restricted)


def test_explanation_has_reasons(profile):
    ranked=rank_job(examples(NOW)[0],profile,NOW)
    assert ranked.score>=75
    assert ranked.decision=='strong'
    assert any('Skill overlap' in x for x in ranked.reasons)


def test_geography_not_hidden(profile):
    ranked=rank_job(examples(NOW)[4],profile,NOW)
    assert ranked.decision=='geo_restricted'
    assert ranked.geography_warning
    assert ranked.score>=0


def test_stale_job_flagged(profile):
    ranked=rank_job(examples(NOW)[7],profile,NOW)
    assert ranked.decision=='stale'
    assert ranked.age_days==26


def test_language_requirement_does_not_reduce_score(profile):
    job=examples(NOW)[1]
    with_requirement=rank_job(job,profile,NOW)
    without_requirement=rank_job(job.model_copy(update={'english_requirement':None}),profile,NOW)
    assert with_requirement.score==without_requirement.score
    assert 'C1' in with_requirement.english_note
    assert without_requirement.english_note is None


def test_deep_backend_role_is_demoted(profile):
    backend=rank_job(examples(NOW)[3],profile,NOW)
    automation=rank_job(examples(NOW)[0],profile,NOW)
    assert backend.score<automation.score
    assert any('outside target scope' in r for r in backend.reasons)


def test_salary_unknown_is_not_rejection(profile):
    ranked=rank_job(examples(NOW)[2],profile,NOW)
    assert any('Salary not comparable' in r for r in ranked.reasons)
    assert ranked.decision != 'stale'


def test_remote_not_equivalent_worldwide(profile):
    bad=examples(NOW)[4]
    assert bad.remote is True
    assert rank_job(bad,profile,NOW).decision=='geo_restricted'


def test_on_site_lower_score(profile):
    a=examples(NOW)[0]
    b=a.model_copy(update={'remote':False})
    assert rank_job(a,profile,NOW).score>rank_job(b,profile,NOW).score


def test_future_publication_date(profile):
    job=examples(NOW)[0].model_copy(update={'published_at':NOW+timedelta(days=2)})
    assert rank_job(job,profile,NOW).decision=='future_date'


def test_canonical_url_drops_tracking():
    a='https://JOBS.example.org/example/?utm_source=newsletter&x=1#part'
    b='https://jobs.example.org/example?x=1'
    assert canonical_url(a)==canonical_url(b)


def test_duplicate_external_id_not_added(tmp_path,profile):
    store=JobStore(tmp_path/'db.sqlite3')
    job=examples(NOW)[0]
    first,created=store.ingest(job,profile,NOW)
    again,created2=store.ingest(job,profile,NOW)
    assert created and not created2 and first.id==again.id


def test_cross_source_same_url_is_deduped(tmp_path,profile):
    store=JobStore(tmp_path/'db.sqlite3')
    job=examples(NOW)[0]
    first,_=store.ingest(job,profile,NOW)
    mirror=job.model_copy(update={'source':'other_board','external_id':'mirror','url':job.url+'?utm_source=mirror'})
    copy,created=store.ingest(mirror,profile,NOW)
    assert not created and first.id==copy.id


def test_save_and_mark_applied_is_manual(client):
    client.post('/v1/demo/load')
    job_id=client.get('/v1/jobs').json()[0]['id']
    saved=client.post(f'/v1/jobs/{job_id}/review',json={'status':'saved'}).json()
    assert saved['status']=='saved'
    assert client.get('/v1/stats').json()['saved']==1
    assert client.get('/v1/jobs?status=saved').json()[0]['id']==job_id
    applied=client.post(f'/v1/jobs/{job_id}/review',json={'status':'applied'}).json()
    assert applied['status']=='applied'
    assert client.get('/v1/stats').json()['applied']==1


def test_review_unknown_id_404(client):
    assert client.post('/v1/jobs/999/review',json={'status':'saved'}).status_code==404


def test_bad_review_state_rejected(client):
    assert client.post('/v1/jobs/2/review',json={'status':'auto_submitted'}).status_code==422


def test_invalid_job_ingest_rejected(client):
    data=examples(NOW)[0].model_dump(mode='json')
    data['url']='file:///etc/passwd'
    assert client.post('/v1/jobs',json=data).status_code==422


def test_api_can_ingest_synthetic_post(client):
    item=examples()[0]
    response=client.post('/v1/jobs',json=item.model_dump(mode='json'))
    assert response.status_code==200
    assert response.json()['source']=='board_a'


def test_cli_report_is_explainable(tmp_path):
    db=str(tmp_path/'data.sqlite3')
    seed(db,CandidateProfile(),NOW)
    report_text=report(JobStore(db).list())
    assert 'SYNTHETIC' in report_text
    assert 'Hiring regions' in report_text
    assert 'Skill overlap' in report_text


def test_no_vacancies_before_loading(client):
    assert client.get('/v1/jobs').json()==[]
    assert client.get('/v1/stats').json()['total']==0


def test_profile_is_fictional_and_generic(client):
    profile=client.get('/v1/profile').json()
    assert profile['eligible_regions']==['Worldwide','Europe']
    assert not any('makagon' in x.lower() for x in profile['target_roles'])


def test_score_clamped(profile):
    job=examples(NOW)[0].model_copy(update={
        'description':'Python API Docker LLM automation CRM integration workflow ' * 30,
    })
    rank=rank_job(job,profile,NOW)
    assert 0<=rank.score<=100


def test_default_profile_freshness_20_days(profile):
    assert profile.freshness_days==20


def test_failed_review_keeps_original_state(client):
    client.post('/v1/demo/load')
    original=client.get('/v1/jobs').json()[0]
    client.post(f"/v1/jobs/{original['id']}/review",json={'status':'wrong'})
    after=next(x for x in client.get('/v1/jobs').json() if x['id']==original['id'])
    assert after['status']=='new'
