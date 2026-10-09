"""Publish a pending gate immediately; accept only this attempt's aggregate result.

The waiting job has read-only Actions access. GitHub publishes its check status;
this script never writes statuses or checks. Polling is bounded to 55 minutes,
leaving five minutes for runner cleanup under the job's 60-minute timeout.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

POLL_SECONDS = 15
TIMEOUT_SECONDS = 55 * 60


def qualification_state(jobs, name, run_id, attempt, sha):
    matches = [job for job in jobs if job.get('name') == name]
    if not matches:
        return 'pending'
    if len(matches) != 1:
        raise ValueError('ambiguous qualification result jobs')
    job = matches[0]
    if (job.get('run_id'), job.get('run_attempt'), job.get('head_sha')) != (run_id, attempt, sha):
        raise ValueError('qualification evidence belongs to another run, attempt or SHA')
    status, conclusion = job.get('status'), job.get('conclusion')
    if status in ('queued', 'in_progress', 'waiting', 'pending'):
        if conclusion is not None:
            raise ValueError('unfinished qualification has a terminal conclusion')
        return 'pending'
    if status != 'completed':
        raise ValueError('unknown qualification status')
    if conclusion == 'success':
        return 'success'
    if conclusion in ('failure', 'cancelled', 'skipped', 'timed_out', 'neutral',
                      'action_required', 'stale', 'startup_failure'):
        return 'failure'
    raise ValueError('unknown completed qualification conclusion')


def fetch_jobs(base_url, repository, run_id, attempt, token):
    jobs = []
    page = 1
    while True:
        url = (f'{base_url}/repos/{repository}/actions/runs/{run_id}'
               f'/attempts/{attempt}/jobs?per_page=100&page={page}')
        request = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        batch = data['jobs']
        if not isinstance(batch, list) or not isinstance(data['total_count'], int):
            raise ValueError('invalid Actions jobs response')
        jobs.extend(batch)
        if len(jobs) >= data['total_count']:
            return jobs
        if not batch:
            raise ValueError('incomplete Actions pagination')
        page += 1


def main():
    sha = os.environ['EXPECTED_HEAD_SHA']
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if actual != sha:
        raise SystemExit('gate checkout is not the intended event head')
    run_id = int(os.environ['GITHUB_RUN_ID'])
    attempt = int(os.environ['GITHUB_RUN_ATTEMPT'])
    name = os.environ['QUALIFICATION_JOB_NAME']
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            jobs = fetch_jobs(os.environ['GITHUB_API_URL'], os.environ['GITHUB_REPOSITORY'],
                              run_id, attempt, os.environ['GITHUB_TOKEN'])
            state = qualification_state(jobs, name, run_id, attempt, sha)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise SystemExit(f'Actions evidence inaccessible: HTTP {error.code}')
            print(f'Actions evidence temporarily unavailable: HTTP {error.code}', flush=True)
        except urllib.error.URLError:
            print('Actions evidence temporarily unavailable: network failure', flush=True)
        else:
            if state == 'success':
                print(f'Gate PASS: run={run_id} attempt={attempt} head={sha}', flush=True)
                return
            if state == 'failure':
                raise SystemExit('current-attempt qualification did not succeed')
            print(f'Awaiting {name}: run={run_id} attempt={attempt} head={sha}', flush=True)
        time.sleep(POLL_SECONDS)
    raise SystemExit('qualification evidence timeout; no passing gate published')


if __name__ == '__main__':
    main()
