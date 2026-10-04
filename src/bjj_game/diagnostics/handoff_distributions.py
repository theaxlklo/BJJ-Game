"""Render recorded D1 traces; no engine or candidate measurement.

Run after handoff_characterization: python -m bjj_game.diagnostics.handoff_distributions
"""

def main():
    import gzip
    import json
    from collections import Counter
    from statistics import median
    from pathlib import Path
    r=json.loads(gzip.decompress(Path('docs/evidence/handoff_d1_trace.json.gz').read_bytes()))
    lines=['# D1 adopted-policy distributions','', 'Counts are exact; histograms show `value: count`. Windows include the action at clear and the endpoint. Partial windows stop at match end; they are explicitly separated from complete 10/20/30 s exposure. Recovery after re-entry remains included in window totals. Censored episodes are never counted as stable successes.','']
    def hist(vals):
     return ', '.join(f'{k}: {v}' for k,v in sorted(Counter(vals).items(),key=lambda kv:str(kv[0]))) or 'none'
    for label,es,vs,n in [(k,v['episodes'],[v],100) for k,v in sorted(r.items())]+ [('pooled',sum([v['episodes'] for v in r.values()],[]),list(r.values()),200)]:
     lines += [f'## {label} ({n} matches)', '', f'Clears: {len(es)}. Before/at clear: {hist((e["clear"]["before"],e["clear"]["after"]) for e in es)}.', '', '| Horizon s | Re-entry | Survived through | Censored | Episode rate | Match rapid/admissible |','|---:|---:|---:|---:|---:|---:|']
     for idx,h in enumerate((5,10,15,20,30)):
      k=sum(v['horizons'][idx]['reexhausted_within'] for v in vs);s=sum(v['horizons'][idx]['survived_through'] for v in vs);c=sum(v['horizons'][idx]['right_censored'] for v in vs)
      mk=sum(v['match_sensitivity'][str(h)]['matches_with_rapid_reexhaustion'] for v in vs);mn=sum(v['match_sensitivity'][str(h)]['matches_with_admissible_clear'] for v in vs)
      lines += [f'| {h} | {k} | {s} | {c} | {k}/{k+s} = {k/(k+s):.6f} | {mk}/{mn} |']
     keyed={}
     for vi,v in enumerate(vs):
      for e in v['episodes']:keyed.setdefault((vi,e['match_index']),[]).append(e)
     first=[min(e['clear_time'] for e in ee) for ee in keyed.values()]
     lines += ['', f'Clear times (all): {hist(e["clear_time"] for e in es)}.', '', f'First-clear times: {hist(first)}. Median {median(first)} s.', '', f'Clear cycles per match: 0: {n-len(keyed)}, {hist(len(ee) for ee in keyed.values())}.', '', f'Re-entry cycles per match: {hist(sum(any(not m["exhausted_before"] and m["exhausted_after"] for ev in e["following"] for m in ev["mutations"]) for e in ee) for ee in keyed.values())} (among clear matches).', '',f'First action: {hist(e["following"][1]["inputs"].get("action_id",e["following"][1]["kind"]) if len(e["following"])>1 else "timeout" for e in es)}.', '',f'First spend delay: {hist(next((ev["offset"] for ev in e["following"] if any(m.get("charged",0)>0 for m in ev["mutations"])), "censored") for e in es)}.', '',f'Re-entry delay: {hist(next((ev["offset"] for ev in e["following"] if any(not m["exhausted_before"] and m["exhausted_after"] for m in ev["mutations"])), "censored") for e in es)}.', '']
     for h in (10,20,30):
      for complete in (True,False):
       chosen=[e for e in es if (e['match_end']-e['clear_time']>=h)==complete]
       lines += [f'{h} s {"complete" if complete else "partial/censored"} windows (n={len(chosen)}): spend {hist(sum(m.get("charged",0) for ev in e["following"] if ev["offset"]<=h for m in ev["mutations"]) for e in chosen)}; recovery {hist(sum(m.get("recovered",0) for ev in e["following"] if ev["offset"]<=h for m in ev["mutations"]) for e in chosen)}.', '']
    Path('docs/HANDOFF_OSCILLATION_D1_DISTRIBUTIONS.md').write_text('\n'.join(lines).rstrip()+'\n')


if __name__ == "__main__":
    main()
