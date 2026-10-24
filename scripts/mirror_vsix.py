#!/usr/bin/env python3
"""Publish a byte-identical copy of the existing VSIX. Never replace assets."""
import hashlib
import os
from pathlib import Path
import urllib.error
from download_stats import API, REPOSITORY

ROOT = Path(__file__).resolve().parents[1]
NAME = 'tokumaru-vscode-themes-0.2.1.vsix'
TAG = 'vscode-themes-v0.2.1'
DIGEST = 'sha256:56a57076068c2244ec5ebd515f1b54043b89670fc118ff440db3aabfd387ffa5'
TITLE = 'Tokumaru Labs VS Code Themes 0.2.1 · direct download'


def mirror(api, source, commit):
    data = source.read_bytes()
    if 'sha256:' + hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError('VSIX differs from the reviewed public binary')
    prefix = f'/repos/{REPOSITORY}/releases'
    try:
        release = api.request(f'{prefix}/tags/{TAG}')
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        # The tag endpoint only finds published releases. Resume a prior draft
        # from the authenticated, paginated list after an interrupted upload.
        candidates = [r for r in api.pages(prefix) if r.get('tag_name') == TAG]
        if len(candidates) > 1:
            raise ValueError('Multiple releases use the reserved tag; refusing modification')
        if candidates:
            release = candidates[0]
        else:
            release = api.request(prefix, 'POST', {
                'tag_name': TAG, 'target_commitish': commit, 'name': TITLE, 'draft': True,
                'prerelease': False, 'make_latest': 'false',
                'body': 'Byte-identical mirror of the existing website VSIX for GitHub download statistics.\n\n'
                        'No extension changes. Marketplace distribution and the website fallback remain available.\n\n'
                        f'SHA-256: `{DIGEST.split(":")[1]}`'})
    release_id = int(release['id'])
    if release['draft'] and (release['name'] != TITLE or release['tag_name'] != TAG or release['prerelease']):
        raise ValueError('Unexpected draft metadata; refusing modification')
    if release['prerelease']:
        raise ValueError('Reserved mirror release must not be a prerelease')
    assets = list(api.pages(f'{prefix}/{release_id}/assets'))
    matches = [a for a in assets if a['name'] == NAME]
    if len(matches) > 1 or any(a['name'] != NAME for a in assets):
        raise ValueError('Unexpected assets in reserved mirror release; refusing modification')
    if matches:
        asset = matches[0]
    else:
        if not release['draft']:
            raise ValueError('Published mirror has no expected asset; refusing modification')
        asset = api.request(f'{prefix}/{release_id}/assets?name={NAME}', 'POST', raw=data, upload=True)
    if asset.get('digest') != DIGEST or asset.get('size') != len(data) or asset.get('state') != 'uploaded':
        raise ValueError('Uploaded asset verification failed; release is not published')
    if release['draft']:
        api.request(f'{prefix}/{release_id}', 'PATCH', {'draft': False, 'make_latest': 'false'})
    return asset['browser_download_url']


if __name__ == '__main__':
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise SystemExit('Release publication is restricted to the source repository main workflow')
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise SystemExit('Missing workflow token')
    print(mirror(API(token), ROOT / 'downloads' / NAME, os.environ['GITHUB_SHA']))
