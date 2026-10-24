#!/usr/bin/env python3
"""Record public release-asset counters. Python stdlib; no visitor tracking."""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

REPOSITORY = 'tokumaru-labs/tokumaru-labs.github.io'
BRANCH = 'download-stats-data'
FILE = 'downloads.json'
ROOT = Path(__file__).resolve().parents[1]


class API:
    def __init__(self, token=''):
        self.token = token

    def request(self, path, method='GET', payload=None, raw=None, upload=False, accept=None):
        host = 'https://uploads.github.com' if upload else 'https://api.github.com'
        if not path.startswith('/repos/tokumaru-labs/'):
            raise ValueError('Unexpected API path')
        headers = {'Accept': accept or 'application/vnd.github+json',
                   'User-Agent': 'Tokumaru-Labs-download-stats', 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        data = raw
        if payload is not None:
            data = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        if raw is not None:
            headers['Content-Type'] = 'application/octet-stream'
        request = urllib.request.Request(host + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    def pages(self, path):
        for page in range(1, 1001):
            items = self.request(f'{path}?per_page=100&page={page}')
            if not isinstance(items, list):
                raise ValueError('Expected a list from GitHub')
            yield from items
            if len(items) < 100:
                return
        raise ValueError('Pagination safety limit exceeded; no partial result saved')


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return parsed


def validate_history(history):
    if history.get('schema') != 1 or not isinstance(history.get('snapshots'), list):
        raise ValueError('Unknown history format; refusing to overwrite')
    previous = None
    for sample in history['snapshots']:
        now = timestamp(sample['observed_at'])
        if previous and now <= previous:
            raise ValueError('History timestamps must be strictly increasing')
        previous = now
        if not isinstance(sample.get('products'), dict):
            raise ValueError('Missing product observations')
        for product in sample['products'].values():
            if product.get('status') not in ('ok', 'no_assets', 'unavailable'):
                raise ValueError('Unknown product status')
            if product['status'] == 'ok':
                assets = product.get('assets')
                if not isinstance(assets, list) or not assets:
                    raise ValueError('Successful observation must contain assets')
                ids = set()
                for asset in assets:
                    if type(asset.get('count')) is not int or asset['count'] < 0:
                        raise ValueError('Invalid download counter')
                    if type(asset.get('id')) is not int or asset['id'] in ids:
                        raise ValueError('Invalid or duplicate asset ID')
                    ids.add(asset['id'])
                    timestamp(asset['created_at'])
                if product.get('total') != sum(a['count'] for a in assets):
                    raise ValueError('Total does not match asset counters')
            elif product.get('total') is not None:
                raise ValueError('Missing observations must not be represented as zero')
    return history


def collect_product(api, product):
    repo = product['repository']
    if not re.fullmatch(r'tokumaru-labs/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Unexpected source repository')
    pattern = re.compile(product['asset_pattern'])
    assets = []
    for release in api.pages(f'/repos/{repo}/releases'):
        if release['draft'] or release['prerelease']:
            continue
        # The embedded assets list can be truncated: paginate it explicitly.
        for asset in api.pages(f'/repos/{repo}/releases/{int(release["id"])}/assets'):
            if asset['state'] != 'uploaded' or not pattern.fullmatch(asset['name']):
                continue
            count = asset['download_count']
            if type(count) is not int or count < 0:
                raise ValueError('Invalid GitHub counter')
            url = asset['browser_download_url']
            if not url.startswith(f'https://github.com/{repo}/releases/download/'):
                raise ValueError('Unexpected download host or repository')
            assets.append({'id': asset['id'], 'name': asset['name'], 'version': release['tag_name'],
                           'count': count, 'created_at': asset['created_at'], 'url': url,
                           'digest': asset.get('digest')})
    assets.sort(key=lambda a: a['id'])
    return {'status': 'ok' if assets else 'no_assets',
            'total': sum(a['count'] for a in assets) if assets else None, 'assets': assets}


def collect(api, products, observed_at):
    values = {}
    for product in products:
        try:
            values[product['id']] = collect_product(api, product)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            code = getattr(error, 'code', None)
            # Do not save response bodies, credentials, or visitor information.
            values[product['id']] = {'status': 'unavailable', 'total': None, 'assets': [],
                                      'error': f'GitHub HTTP {code}' if code else 'GitHub data unavailable'}
    if all(p['status'] == 'unavailable' for p in values.values()):
        raise RuntimeError('All sources failed; existing history was not changed')
    sample = {'observed_at': observed_at, 'products': values}
    validate_history({'schema': 1, 'snapshots': [sample]})
    return sample


def append_sample(history, sample):
    validate_history(history)
    if history['snapshots'] and timestamp(sample['observed_at']) <= timestamp(history['snapshots'][-1]['observed_at']):
        raise ValueError('New observation must be later than existing history')
    result = {'schema': 1, 'snapshots': [*history['snapshots'], sample]}
    return validate_history(result)


def load_remote_history(api):
    prefix = f'/repos/{REPOSITORY}'
    try:
        api.request(f'{prefix}/git/ref/heads/{BRANCH}')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {'schema': 1, 'snapshots': []}, None, True
        raise
    # An existing branch with a missing/corrupt file is an error, never a reset.
    info = api.request(f'{prefix}/contents/{FILE}?ref={BRANCH}')
    if info.get('encoding') == 'base64':
        history = json.loads(base64.b64decode(info['content']))
    else:
        history = api.request(f'{prefix}/contents/{FILE}?ref={BRANCH}', accept='application/vnd.github.raw+json')
    return validate_history(history), info['sha'], False


def save_remote_history(api, history, sha, create_branch):
    validate_history(history)
    prefix = f'/repos/{REPOSITORY}'
    if create_branch:
        main = api.request(f'{prefix}/git/ref/heads/main')['object']['sha']
        base = api.request(f'{prefix}/git/commits/{main}')['tree']['sha']
        tree = api.request(f'{prefix}/git/trees', 'POST', {'base_tree': base, 'tree': [
            {'path': FILE, 'mode': '100644', 'type': 'blob',
             'content': json.dumps(history, ensure_ascii=False, separators=(',', ':')) + '\n'}]})
        commit = api.request(f'{prefix}/git/commits', 'POST', {
            'message': 'Start public release download history', 'tree': tree['sha'], 'parents': [main]})
        # Publish the ref only after its initial data commit is complete.
        return api.request(f'{prefix}/git/refs', 'POST', {
            'ref': f'refs/heads/{BRANCH}', 'sha': commit['sha']})
    body = {'message': 'Record public release download counters', 'branch': BRANCH,
            'content': base64.b64encode((json.dumps(history, ensure_ascii=False, separators=(',', ':')) + '\n').encode()).decode()}
    if sha:
        body['sha'] = sha  # GitHub rejects concurrent writes instead of losing history.
    return api.request(f'{prefix}/contents/{FILE}', 'PUT', body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true', help='Write only the dedicated statistics branch')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    api = API(os.environ.get('GH_TOKEN', ''))
    products = json.loads((ROOT / 'stats/products.json').read_text())['products']
    if args.publish:
        if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/main':
            raise RuntimeError('Publishing is restricted to the source repository main workflow')
        if not api.token:
            raise RuntimeError('Publishing requires the workflow token')
        history, sha, missing = load_remote_history(api)
        if missing:
            history = validate_history(json.loads((ROOT / "stats/initial.json").read_text()))
    else:
        history, sha, missing = {'schema': 1, 'snapshots': []}, None, False
    observed_at = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    result = append_sample(history, collect(api, products, observed_at))
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    if args.publish:
        save_remote_history(api, result, sha, missing)
    summary = [f"Observation: {observed_at}"] + [f"{p['name']}: {result['snapshots'][-1]['products'][p['id']]['status']} / {result['snapshots'][-1]['products'][p['id']]['total']}" for p in products]
    print('\n'.join(summary))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('\n'.join(summary) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError, OSError, KeyError) as error:
        print(f'Statistics update failed: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(1)
