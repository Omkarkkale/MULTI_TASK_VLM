"""Build a pandas exploration of 0 <= fill < 5; no training labels are propagated.

Training: up to five distinct camera pairs per GT event. Validation/test: one.
All rows are diagnostic candidates; no changes to the current dataset or splits.
"""
import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
from io import BytesIO
import json
import math
from pathlib import Path

import pandas as pd
from PIL import Image
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory
from audit_mcap_dataset import PROJECT, TOPICS, stamp_ns, utc


def week_role(timestamp):
    year, week, _ = datetime.fromtimestamp(timestamp / 1e9, timezone.utc).isocalendar()
    return {35: 'train', 36: 'validation', 37: 'test_normal'}.get(week, 'hold') if year == 2026 else 'hold'


def closest_frames(frames, timestamp, count):
    times = [t for t, _ in frames]
    pos = bisect_left(times, timestamp)
    local = frames[max(0, pos-count):pos+count]
    return sorted(local, key=lambda item: (abs(item[0]-timestamp), item[0], item[1]))[:count]


def choose_pairs(narrow, wide, timestamp, count):
    # Rank pairs by closeness to GT, not by silently changing the camera tolerance.
    combinations = [(n, w) for n in closest_frames(narrow, timestamp, count) for w in closest_frames(wide, timestamp, count)]
    combinations.sort(key=lambda pair: (max(abs(pair[0][0]-timestamp), abs(pair[1][0]-timestamp)), abs(pair[0][0]-timestamp)+abs(pair[1][0]-timestamp), abs(pair[0][0]-pair[1][0]), pair))
    selected, used_n, used_w = [], set(), set()
    for n, w in combinations:
        if n[1] in used_n or w[1] in used_w:
            continue
        selected.append((n, w)); used_n.add(n[1]); used_w.add(w[1])
        if len(selected) == count:
            break
    return selected


def gt_context(fills, timestamp, value, narrow_time, wide_time):
    times = [f['timestamp'] for f in fills]
    low, high = min(timestamp, narrow_time, wide_time), max(timestamp, narrow_time, wide_time)
    before = bisect_right(times, low) - 1
    after = bisect_left(times, high)
    previous = bisect_left(times, timestamp) - 1
    following = bisect_right(times, timestamp)
    complete = before >= 0 and after < len(fills)
    evidence = fills[max(0,before):min(len(fills),after+1)]
    same = complete and all(f['value'] == value for f in evidence)
    result = {'gt_bracket_complete': complete, 'bracketing_recorded_gt_all_equal': same, 'bracket_start_ns': str(times[before]) if before >= 0 else '', 'bracket_end_ns': str(times[after]) if after < len(times) else '', 'bracket_min_fill': min((f['value'] for f in evidence),default=None), 'bracket_max_fill': max((f['value'] for f in evidence),default=None), 'gt_evidence': 'recorded_bracket_agrees_not_continuous_proof' if same else 'recorded_bracket_changes' if complete else 'incomplete_gt_bracket'}
    for key, index in [('previous', previous), ('next', following)]:
        exists = 0 <= index < len(fills)
        result[key+'_gt_timestamp_ns'] = str(times[index]) if exists else ''
        result[key+'_gt_fill_level'] = fills[index]['value'] if exists else None
    return result


def scan_source(source):
    cameras = {v: [] for v in ('narrow','wide')}
    counts = Counter(); fills = []
    reverse = {topic: key for key, topic in TOPICS.items()}
    with source.open('rb') as stream:
        reader = make_reader(stream, decoder_factories=[DecoderFactory()])
        for _, channel, _, message in reader.iter_decoded_messages(topics=list(reverse), log_time_order=False):
            kind = reverse[channel.topic]; index = counts[kind]; counts[kind] += 1
            timestamp = stamp_ns(message)
            if kind == 'fill':
                value = float(message.data)
                fills.append({'timestamp': timestamp, 'value': value, 'index': index})
            else:
                cameras[kind].append((timestamp,index))
    for frames in cameras.values():
        frames.sort()
    fills.sort(key=lambda f:(f['timestamp'],f['index']))
    return cameras, fills


def save_images(source, source_uid, rows, output):
    wanted = {v: {r[v+'_index']: int(r[v+'_timestamp_ns']) for r in rows} for v in ('narrow','wide')}
    found = {v:{} for v in wanted}; counts=Counter()
    reverse={TOPICS[v]:v for v in wanted}
    destination=output/'images'/source_uid; destination.mkdir(parents=True)
    with source.open('rb') as stream:
        reader=make_reader(stream,decoder_factories=[DecoderFactory()])
        for _, channel, _, message in reader.iter_decoded_messages(topics=list(reverse),log_time_order=False):
            view=reverse[channel.topic]; index=counts[view]; counts[view]+=1
            if index not in wanted[view]:
                continue
            if stamp_ns(message)!=wanted[view][index]:
                raise ValueError('Source image timestamp changed')
            try:
                data=bytes(message.data)
                with Image.open(BytesIO(data)) as image:
                    image.load()
                    suffix={'JPEG':'.jpg','PNG':'.png'}[image.format]
                path=destination/f'{view}_{index:06d}{suffix}'
                path.write_bytes(data)
                found[view][index]={'image':path.relative_to(output).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'decode_error':''}
            except Exception as exc:
                found[view][index]={'image':'','sha256':'','decode_error':str(exc)}
    for row in rows:
        for view in wanted:
            info=found[view].get(row[view+'_index'],{'image':'','sha256':'','decode_error':'frame_not_found'})
            row.update({view+'_'+key:value for key,value in info.items()})
        row['decode_ok']=not row['narrow_decode_error'] and not row['wide_decode_error']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=PROJECT/'extracted/low_fill_pilot_v1')
    args=parser.parse_args(); output=args.output
    if output.exists():
        parser.error('Choose a new output directory; existing pilot results are preserved')
    audit_root=PROJECT/'extracted/dataset_audit_v3'
    source_metadata=PROJECT/'extracted/crusher_dataset_v3_candidates/metadata.csv'
    baseline=pd.read_csv(source_metadata,dtype={'sample_id':str,'fill_timestamp_ns':str})
    baseline_lookup={r['sample_id']:r for r in baseline.to_dict('records')}
    assessment=pd.read_csv(audit_root/'lighting_assessment.csv').set_index('source_uid')['suggested_lighting'].to_dict()
    sources=[]
    for path in sorted((audit_root/'recordings').glob('*/audit.json')):
        audit=json.loads(path.read_text())
        labels=pd.read_csv(path.parent/'fill_labels.csv')
        if ((labels.fill_level>=0)&(labels.fill_level<5)).any():
            sources.append(audit)
    if not sources:
        parser.error('No raw labels in [0,5)')
    output.mkdir(parents=True)
    all_rows=[]; recording_stats=[]
    for audit in sources:
        source=PROJECT/'data'/audit['source_mcap']; stat=source.stat()
        if (stat.st_size,stat.st_mtime_ns)!=(audit['size_bytes'],audit['mtime_ns']):
            raise ValueError(f'Source changed since audit: {source}')
        print(f"Reading camera timestamps and GT: recording {audit['recording_id']}",flush=True)
        cameras,fills=scan_source(source)
        targets=[f for f in fills if 0<=f['value']<5]
        rows=[]
        for fill in targets:
            gt=fill['timestamp']; role=week_role(gt); count=5 if role=='train' else 1
            gt_id=f"{audit['source_uid']}_fill_{fill['index']:06d}"
            base=baseline_lookup.get(gt_id)
            for rank,(n,w) in enumerate(choose_pairs(cameras['narrow'],cameras['wide'],gt,count),1):
                delta_n,delta_w=n[0]-gt,w[0]-gt
                original=bool(base is not None and n[1]==int(base['narrow_index']) and w[1]==int(base['wide_index']))
                row={'candidate_id':f'{gt_id}_pair_{rank:02d}','gt_event_id':gt_id,'source_uid':audit['source_uid'],'recording_id':audit['recording_id'],'source_mcap':audit['source_mcap'],'proposed_split':role,'suggested_lighting':assessment.get(audit['source_uid'],'pending'),'bucket':'[0,5)','gt_fill_level':fill['value'],'gt_timestamp_ns':str(gt),'gt_timestamp_utc':utc(gt),'pair_rank':rank,'narrow_index':n[1],'narrow_timestamp_ns':str(n[0]),'narrow_timestamp_utc':utc(n[0]),'wide_index':w[1],'wide_timestamp_ns':str(w[0]),'wide_timestamp_utc':utc(w[0]),'narrow_gt_delta_ms':delta_n/1e6,'wide_gt_delta_ms':delta_w/1e6,'camera_pair_delta_ms':abs(n[0]-w[0])/1e6,'passes_existing_gt_1s':max(abs(delta_n),abs(delta_w))<=1_000_000_000,'passes_pair_100ms':abs(n[0]-w[0])<=100_000_000,'passes_pair_250ms':abs(n[0]-w[0])<=250_000_000,'is_original_pair':original,'prompt':'Estimate the crusher fill level using both camera views. Return a percentage from 0 to 100.','assigned_training_target':'','label_assignment':'pending_no_propagation','visual_qc':'pending','lighting':'pending'}
                row.update(gt_context(fills,gt,fill['value'],n[0],w[0]));rows.append(row)
        print(f"Exporting {len(rows)} diagnostic pairs for {len(targets)} GT events",flush=True)
        save_images(source,audit['source_uid'],rows,output)
        all_rows.extend(rows)
        for view,frames in cameras.items():
            intervals=pd.Series([b[0]-a[0] for a,b in zip(frames,frames[1:])],dtype='int64')/1e9
            recording_stats.append({'recording_id':audit['recording_id'],'source_uid':audit['source_uid'],'camera':view,'frames':len(frames),'median_interval_seconds':float(intervals.median()),'p95_interval_seconds':float(intervals.quantile(.95)),'low_fill_gt_events':len(targets),'source_size_bytes':stat.st_size,'source_mtime_ns':stat.st_mtime_ns})
    df=pd.DataFrame(all_rows)
    good=df['decode_ok']
    df['pair_content_key']=df.narrow_sha256+':'+df.wide_sha256
    df['pair_reuse_count']=df.groupby(['source_uid','narrow_index','wide_index']).candidate_id.transform('size')
    df['content_pair_reuse_count']=0
    df.loc[good,'content_pair_reuse_count']=df[good].groupby('pair_content_key').candidate_id.transform('size')
    df['image_reuse_narrow']=df.groupby(['source_uid','narrow_index']).candidate_id.transform('size')
    df['image_reuse_wide']=df.groupby(['source_uid','wide_index']).candidate_id.transform('size')
    df['diagnostic_hold_reason']=df.apply(lambda r:';'.join(reason for condition,reason in [(not r.decode_ok,'decode_failure'),(not r.passes_existing_gt_1s,'outside_gt_1s'),(not r.bracketing_recorded_gt_all_equal,'gt_bracket_not_constant_or_incomplete'),(r.pair_reuse_count>1,'pair_reused_across_gt_events')] if condition) or 'manual_label_and_visual_review_required',axis=1)
    df.to_csv(output/'pilot_pairs.csv',index=False)
    pd.DataFrame(recording_stats).to_csv(output/'recording_camera_cadence.csv',index=False)
    rank_counts=df.groupby(['proposed_split','pair_rank']).agg(candidate_pairs=('candidate_id','size'),passes_gt_1s=('passes_existing_gt_1s','sum'),bracketing_gt_agrees=('bracketing_recorded_gt_all_equal','sum'),passes_pair_100ms=('passes_pair_100ms','sum'),passes_pair_250ms=('passes_pair_250ms','sum')).reset_index()
    rank_counts.to_csv(output/'counts_by_rank.csv',index=False)
    train_extra=df[(df.proposed_split=='train')&(~df.is_original_pair)]
    shortlist=train_extra[train_extra.passes_existing_gt_1s & train_extra.bracketing_recorded_gt_all_equal & train_extra.decode_ok & (train_extra.pair_reuse_count==1)]
    shortlist.to_csv(output/'additional_training_shortlist.csv',index=False)
    summaries=[]
    for role in ['train','validation','test_normal']:
        subset=df[df.proposed_split==role]
        summaries.append({'role':role,'gt_events':int(subset.gt_event_id.nunique()),'diagnostic_pairs':len(subset),'gt_fill_min':float(subset.gt_fill_level.min()) if len(subset) else None,'gt_fill_max':float(subset.gt_fill_level.max()) if len(subset) else None,'pairs_within_gt_1s':int(subset.passes_existing_gt_1s.sum()),'pairs_within_gt_1s_and_pair_100ms':int((subset.passes_existing_gt_1s&subset.passes_pair_100ms).sum()),'pairs_within_gt_1s_and_pair_250ms':int((subset.passes_existing_gt_1s&subset.passes_pair_250ms).sum())})
    summary={'status':'diagnostic_pilot_only_no_training_labels_assigned','bucket':'0 <= fill < 5','gt_events':int(df.gt_event_id.nunique()),'diagnostic_pairs':len(df),'all_images_decoded':bool(df.decode_ok.all()),'roles':summaries,'extra_training_pairs':len(train_extra),'additional_training_shortlist_pending_review':len(shortlist),'extra_training_pairs_within_existing_gt_1s':int(train_extra.passes_existing_gt_1s.sum()),'extra_training_pairs_within_gt_1s_and_pair_100ms':int((train_extra.passes_existing_gt_1s&train_extra.passes_pair_100ms).sum()),'extra_training_pairs_within_gt_1s_and_pair_250ms':int((train_extra.passes_existing_gt_1s&train_extra.passes_pair_250ms).sum()),'rows_reusing_same_pair':int((df.pair_reuse_count>1).sum()),'unique_encoded_image_pairs':int(df.loc[good,'pair_content_key'].nunique()),'pair_selection':'Greedy one-to-one selection among five nearest frames per view for training; minimize maximum distance to GT, then total distance to GT, then camera gap. Validation/test use one independent-nearest pair. Not an optimized rematching experiment.','camera_cutoff':'100/250ms sensitivity flags only; neither threshold activated','label_caveat':'Matching bracketing GT readings are evidence only; no continuous label stability or sensor accuracy guarantee. No GT labels are copied to extra frames.','metadata_sha256':hashlib.sha256(source_metadata.read_bytes()).hexdigest()}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    intro='Diagnostic candidates only. GT fill shown below is the anchor measurement, not an approved label for every nearby pair. Red timing/GT flags must be reviewed. Training uses up to five pairs; test uses one; validation has no samples if absent.'
    parts=['<!doctype html><html><meta charset="utf-8"><title>Low-fill pilot</title><style>body{font:16px system-ui;background:#eee;margin:24px}article{background:white;margin:20px 0;padding:16px}img{width:48%;max-height:400px;object-fit:contain}p{overflow-wrap:anywhere}.hold{color:#9c2727}</style><h1>0–5% exploratory camera pairs</h1><p>'+intro+'</p>']
    for r in df.to_dict('records'):
        parts.append('<article><h2>'+html.escape(f"{r['proposed_split']} · GT {r['gt_fill_level']}% · pair rank {r['pair_rank']}")+'</h2><p>'+html.escape(r['candidate_id'])+'</p><p>'+html.escape(f"GT: {r['gt_timestamp_utc']} | narrow: {r['narrow_timestamp_utc']} | wide: {r['wide_timestamp_utc']}")+'</p><p>'+html.escape(f"GT offsets: {r['narrow_gt_delta_ms']:.1f} / {r['wide_gt_delta_ms']:.1f} ms · camera gap: {r['camera_pair_delta_ms']:.1f} ms · original pair: {r['is_original_pair']}")+'</p><p class="hold">'+html.escape(r['diagnostic_hold_reason']+'; '+r['gt_evidence'])+'</p><p>Narrow (left), wide (right). Click for full resolution.</p>')
        for view in ['narrow','wide']:
            path=html.escape(r[view+'_image'],quote=True)
            parts.append(f'<a href="{path}" target="_blank"><img src="{path}" loading="lazy" alt="{view}"></a>' if path else '<p>Decode failed</p>')
        parts.append('</article>')
    (output/'review.html').write_text('\n'.join(parts)+'</html>')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
