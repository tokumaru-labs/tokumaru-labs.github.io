"""Counter/history regression cases. No network calls and no release writes."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import download_stats as ds
import mirror_vsix as mv

P = {'id':'control','repository':'tokumaru-labs/toku-control','asset_pattern':r'^app.*\.zip$'}
NOW = '2026-10-24T15:17:00Z'
ASSET = {'id':1,'name':'app.zip','state':'uploaded','download_count':6,'created_at':'2026-10-21T00:00:00Z','browser_download_url':'https://github.com/tokumaru-labs/toku-control/releases/download/v1/app.zip','digest':'sha256:example'}
RELEASE = {'id':10,'tag_name':'v1','draft':False,'prerelease':False}

class Fake:
    def __init__(self, releases=None, assets=None):
        self.releases = [deepcopy(RELEASE)] if releases is None else releases
        self.assets = [deepcopy(ASSET)] if assets is None else assets
        self.calls=[]
    def pages(self,path):
        self.calls.append(path)
        return iter(self.assets if path.endswith('/assets') else self.releases)


def history(count=6):
    a={'id':1,'name':'app.zip','count':count,'created_at':ASSET['created_at'],'url':ASSET['browser_download_url']}
    return {'schema':1,'snapshots':[{'observed_at':NOW,'products':{'control':{'status':'ok','total':count,'assets':[a]}}}]}

class CollectorTests(unittest.TestCase):
    def test_collects_only_distribution_files(self):
        extra=deepcopy(ASSET);extra.update(id=2,name='SHA256SUMS.txt',download_count=99)
        api=Fake(assets=[ASSET,extra]);p=ds.collect_product(api,P)
        self.assertEqual(p['total'],6);self.assertEqual(len(p['assets']),1)
        self.assertTrue(any(c.endswith('/10/assets') for c in api.calls))
    def test_skips_drafts_and_prereleases(self):
        releases=[dict(RELEASE,draft=True),dict(RELEASE,prerelease=True)]
        p=ds.collect_product(Fake(releases=releases),P)
        self.assertEqual(p['status'],'no_assets');self.assertIsNone(p['total'])
    def test_zero_is_a_valid_observed_count(self):
        p=ds.collect_product(Fake(assets=[dict(ASSET,download_count=0)]),P)
        self.assertEqual((p['status'],p['total']),('ok',0))
    def test_invalid_counter_or_host_is_rejected(self):
        for change in [{'download_count':-1},{'download_count':True},{'browser_download_url':'https://bad.invalid/a'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                ds.collect_product(Fake(assets=[dict(ASSET,**change)]),P)
    def test_pagination_includes_later_pages(self):
        api=ds.API();pages=[]
        def get(path):
            pages.append(path);return list(range(100)) if path.endswith('&page=1') else [101]
        api.request=get
        self.assertEqual(len(list(api.pages('/repos/tokumaru-labs/demo/releases'))),101)
        self.assertEqual(len(pages),2)
    def test_partial_failure_is_missing_not_zero(self):
        def get(api,p):
            if p['id']=='broken':raise HTTPError('u',403,'Forbidden',{},None)
            return {'status':'no_assets','total':None,'assets':[]}
        with patch.object(ds,'collect_product',get):
            s=ds.collect(Fake(),[P,dict(P,id='broken')],NOW)
        self.assertIsNone(s['products']['broken']['total'])
        self.assertEqual(s['products']['broken']['error'],'GitHub HTTP 403')
    def test_all_failures_abort_without_a_sample(self):
        with patch.object(ds,'collect_product',side_effect=OSError('failed')):
            with self.assertRaises(RuntimeError):ds.collect(Fake(),[P],NOW)
    def test_append_preserves_existing_records(self):
        old=history();saved=deepcopy(old);sample=deepcopy(old['snapshots'][0]);sample['observed_at']='2026-10-25T15:17:00Z'
        result=ds.append_sample(old,sample)
        self.assertEqual(old,saved);self.assertEqual(result['snapshots'][0],saved['snapshots'][0]);self.assertEqual(len(result['snapshots']),2)
    def test_duplicate_or_earlier_snapshot_is_rejected(self):
        old=history()
        with self.assertRaises(ValueError):ds.append_sample(old,old['snapshots'][0])
    def test_corrupt_totals_and_duplicate_ids_rejected(self):
        for mode in ['total','id','negative']:
            h=history();p=h['snapshots'][0]['products']['control']
            if mode=='total':p['total']=100
            if mode=='id':p['assets']*=2;p['total']=12
            if mode=='negative':p['assets'][0]['count']=-6;p['total']=-6
            with self.subTest(mode=mode),self.assertRaises(ValueError):ds.validate_history(h)
    def test_existing_branch_with_missing_data_is_not_reset(self):
        api=ds.API()
        def request(path,**kw):
            if '/contents/' in path:raise HTTPError('u',404,'Not found',{},None)
            return {'object':{'sha':'existing'}}
        api.request=request
        with self.assertRaises(HTTPError):ds.load_remote_history(api)
    def test_missing_branch_bootstraps_but_403_does_not(self):
        api=ds.API()
        for status in [404,403]:
            api.request=lambda *a,**k: (_ for _ in ()).throw(HTTPError('u',status,'error',{},None))
            if status==404:self.assertTrue(ds.load_remote_history(api)[2])
            else:
                with self.assertRaises(HTTPError):ds.load_remote_history(api)
    def test_existing_history_updates_with_expected_blob_sha(self):
        api=ds.API();calls=[]
        api.request=lambda path,method,payload: calls.append((path,method,payload)) or {}
        ds.save_remote_history(api,history(),'old-sha',False)
        payload=calls[0][2];self.assertEqual(payload['sha'],'old-sha');self.assertEqual(payload['branch'],ds.BRANCH)
        self.assertEqual(json.loads(base64.b64decode(payload['content'])),history())
    def test_new_branch_is_published_after_data_commit(self):
        api=ds.API();calls=[]
        def request(path,method='GET',payload=None):
            calls.append((path,method,payload))
            if path.endswith('/heads/main'):return {'object':{'sha':'main'}}
            if path.endswith('/git/commits/main'):return {'tree':{'sha':'tree0'}}
            if path.endswith('/git/trees'):return {'sha':'tree1'}
            if path.endswith('/git/commits'):return {'sha':'commit1'}
            return {}
        api.request=request;ds.save_remote_history(api,history(),None,True)
        self.assertEqual(calls[-1][2],{'ref':'refs/heads/'+ds.BRANCH,'sha':'commit1'})
        self.assertEqual(json.loads(calls[2][2]['tree'][0]['content']),history())

class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/mv.NAME;self.path.write_bytes(b'reviewed VSIX fixture')
        self.digest='sha256:'+hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.patcher=patch.object(mv,'DIGEST',self.digest);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.asset={'name':mv.NAME,'digest':self.digest,'size':self.path.stat().st_size,'state':'uploaded','browser_download_url':'https://github.com/example'}
        self.release={'id':1,'name':mv.TITLE,'tag_name':mv.TAG,'draft':False,'prerelease':False}
        self.calls=[]
        self.api=ds.API();self.api.pages=lambda _:iter([self.asset])
        def request(path,method='GET',payload=None,**kw):
            self.calls.append((path,method,payload));return self.release
        self.api.request=request
    def test_identical_published_mirror_is_read_only(self):
        self.assertEqual(mv.mirror(self.api,self.path,'commit'),'https://github.com/example')
        self.assertTrue(all(c[1]=='GET' for c in self.calls))
    def test_changed_local_binary_stops_before_api(self):
        self.path.write_bytes(b'changed')
        with self.assertRaises(ValueError):mv.mirror(self.api,self.path,'commit')
        self.assertFalse(self.calls)
    def test_existing_asset_mismatch_is_never_replaced(self):
        self.asset['digest']='sha256:other'
        with self.assertRaises(ValueError):mv.mirror(self.api,self.path,'commit')
        self.assertTrue(all(c[1]=='GET' for c in self.calls))
    def test_missing_asset_in_published_release_is_not_uploaded(self):
        self.api.pages=lambda _:iter([])
        with self.assertRaises(ValueError):mv.mirror(self.api,self.path,'commit')
        self.assertTrue(all(c[1]=='GET' for c in self.calls))
    def test_unexpected_draft_is_not_modified(self):
        self.release.update(draft=True,name='Someone else draft');self.api.pages=lambda _:iter([])
        with self.assertRaises(ValueError):mv.mirror(self.api,self.path,'commit')
        self.assertTrue(all(c[1]=='GET' for c in self.calls))
    def test_new_release_is_draft_until_upload_verified(self):
        self.api.pages=lambda _:iter([])
        def request(path,method='GET',payload=None,**kw):
            self.calls.append((path,method,payload))
            if method=='GET':raise HTTPError('u',404,'Not found',{},None)
            if method=='POST' and path.endswith('/releases'):return dict(self.release,draft=True)
            if 'assets?' in path:return self.asset
            return {}
        self.api.request=request;mv.mirror(self.api,self.path,'commit')
        self.assertTrue(self.calls[1][2]['draft']);self.assertEqual(self.calls[-1][1],'PATCH');self.assertFalse(self.calls[-1][2]['draft'])
    def test_bad_upload_never_publishes_draft(self):
        self.release['draft']=True;self.api.pages=lambda _:iter([])
        def request(path,method='GET',payload=None,**kw):
            self.calls.append((path,method,payload))
            return self.release if method=='GET' else dict(self.asset,digest='wrong')
        self.api.request=request
        with self.assertRaises(ValueError):mv.mirror(self.api,self.path,'commit')
        self.assertFalse(any(c[1]=='PATCH' for c in self.calls))

if __name__=='__main__':unittest.main()
