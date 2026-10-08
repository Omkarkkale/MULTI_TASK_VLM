"""Build the agreed chronological split plan and interactive candidate QC page.

The plan is provisional: only samples explicitly reviewed as daylight + keep may
enter train/validation/test-normal. This script never freezes or approves rows.
"""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from audit_mcap_dataset import PROJECT, write_csv
from camera_sync_policy import evaluate, load_policy


def main():
    root = PROJECT / "extracted/crusher_dataset_v3_candidates"
    rows = list(csv.DictReader((root / "metadata.csv").open()))
    sync_policy = load_policy(root) if (root / "sync_policy.json").exists() else None
    reviews = []
    for row in rows:
        captured = datetime.fromtimestamp(int(row["fill_timestamp_ns"]) / 1e9, timezone.utc)
        year, week, _ = captured.isocalendar()
        role = {35: "train", 36: "validation", 37: "test_normal"}.get(week, "hold") if year == 2026 else "hold"
        suggested = row["suggested_lighting"]
        planned = role if suggested == "daylight_candidate" else "test_night" if suggested == "night_candidate" else "hold_lighting_review"
        if sync_policy and evaluate(row, sync_policy)["sync_status"] != "pass":
            planned = "excluded_sync"
        reviews.append({"sample_id": row["sample_id"], "source_uid": row["source_uid"], "recording_id": row["recording_id"], "timestamp_utc": captured.isoformat(), "fill_level": row["fill_level"], "suggested_lighting": suggested, "daylight_week_role": role, "proposed_split": planned, "lighting": "pending", "qc": "pending", "reason": "", "export_status": row["export_status"], "narrow_image": row["narrow_image"], "wide_image": row["wide_image"]})
    write_csv(root / "review_template.csv", reviews, list(reviews[0]))
    roles = {r["sample_id"]: r["proposed_split"] for r in reviews}
    exact_pairs = defaultdict(list)
    for row in rows:
        if row["export_status"] == "decoded_candidate":
            exact_pairs[(row["narrow_sha256"], row["wide_sha256"])].append(row)
    duplicate_groups = [[r["sample_id"] for r in group] for group in exact_pairs.values() if len(group) > 1]
    cross_role_duplicates = [group for group in duplicate_groups if len({roles[sample_id] for sample_id in group}) > 1]
    bins = defaultdict(lambda: [0] * 10)
    for row in rows:
        if row["export_status"] == "decoded_candidate":
            bins[roles[row["sample_id"]]][min(int(float(row["fill_level"]) // 10), 9)] += 1
    quality = {
        "candidate_rows": len(rows),
        "unique_sample_ids": len({r["sample_id"] for r in rows}),
        "export_status_counts": dict(Counter(r["export_status"] for r in rows)),
        "proposed_split_counts_before_qc": dict(Counter(r["proposed_split"] for r in reviews)),
        "decoded_fill_bins_by_proposed_split": dict(bins),
        "bin_edges": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "last_bin_includes_100": True,
        "identical_encoded_camera_pair_groups": duplicate_groups,
        "identical_encoded_pairs_across_proposed_roles": cross_role_duplicates,
        "duplicate_check_limit": "SHA256 of encoded camera pairs; does not detect near-duplicates or prove session independence",
        "max_absolute_label_delta_seconds": {v: max(abs(float(r[f"{v}_signed_delta_seconds"])) for r in rows) for v in ("narrow", "wide")},
        "visual_qc_status": "pending",
        "sync_policy": sync_policy,
    }
    (root / "candidate_quality_report.json").write_text(json.dumps(quality, indent=2))
    plan = {
        "status": "agreed_chronology_pending_sample_qc",
        "time_basis": "observed ROS header timestamps in UTC; verify recorder clock against collection records before freeze",
        "train_daylight": ["2026-08-24", "2026-08-30"],
        "validation_daylight": ["2026-08-31", "2026-09-06"],
        "test_normal_daylight": ["2026-09-07", "2026-09-13"],
        "night_policy": "No night in training or validation. Reviewed night samples form a separate held-out test pool.",
        "transition_policy": "Review per sample; keep mixed-light/dawn/dusk samples on hold unless clearly assigned to a defined lighting domain. Do not assign a whole transitioning source to daylight.",
        "release_requirements": ["Every exported row has an explicit QC decision", "Accepted rows have reviewed lighting", "Group related recordings/sessions and remove duplicate leakage", "Confirm dates against collection records", "Confirm fill distribution in each split", "Write immutable version manifests and content checksums"],
        "experiments": {"exp1": "test_normal", "exp2": "fixed declared mixture drawn only from test_normal and test_night", "exp3": "test_night"},
        "model_selection": "Use daylight validation only. Freeze model, prompts, preprocessing and thresholds before the three tests.",
        "sync_policy": sync_policy,
    }
    (root / "split_plan.json").write_text(json.dumps(plan, indent=2))
    payload = json.dumps(reviews).replace("<", "\\u003c")
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><title>V3 candidate review</title>
<style>body{font:16px system-ui;margin:24px;background:#f4f4f4;color:#222}header{background:white;padding:16px;position:sticky;top:0;z-index:2;border-bottom:1px solid #ccc}button,select,input{font:inherit;margin:4px;padding:6px}article{background:white;margin:18px 0;padding:16px}img{width:48%;vertical-align:top;max-height:400px;object-fit:contain}p{max-width:1000px}.note{color:#694000}</style>
<header><h1>V3 candidate review</h1><p>Review both camera views. Mark <b>reject</b> if the crusher fill region is blocked or the pair is unusable. A truck elsewhere in the image alone is not a rejection. Lighting suggestions come from sparse recording previews; confirm each sample. Keep uncertain dusk/dawn as <b>transition</b>.</p>
<label>Recording <select id="source"><option value="">All</option></select></label>
<label><input type="checkbox" id="pending">Pending QC only</label>
<button id="prev">Previous</button><span id="page"></span><button id="next">Next</button>
<button id="download">Download decisions CSV</button><label>Restore decisions <input type="file" id="restore" accept=".json"></label><button id="backup">Download JSON backup</button>
<p id="progress"></p><p class="note">Decisions stay in this browser until exported. Save the CSV in this dataset folder as review_decisions.csv. No dataset split is finalized by this page.</p></header><main id="items"></main>
<script>const rows=__DATA__;const key='crusher-v3-review-2026-09-24';let decisions={};try{decisions=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}let page=0;const size=30;
const el=id=>document.getElementById(id);const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const options=(values,current)=>values.map(v=>`<option ${v===current?'selected':''}>${v}</option>`).join('');
[...new Set(rows.map(r=>r.recording_id))].sort((a,b)=>Number(a)-Number(b)).forEach(id=>{const o=document.createElement('option');o.value=id;o.textContent=id;el('source').appendChild(o)});
function filtered(){return rows.filter(r=>(!el('source').value||r.recording_id===el('source').value)&&(!el('pending').checked||!decisions[r.sample_id]?.qc||decisions[r.sample_id].qc==='pending'))}
function render(){const selected=filtered();const pages=Math.max(1,Math.ceil(selected.length/size));page=Math.min(page,pages-1);el('page').textContent=` ${page+1} / ${pages} (${selected.length} samples) `;el('progress').textContent=`QC decisions: ${rows.filter(r=>['keep','reject'].includes(decisions[r.sample_id]?.qc)).length} / ${rows.length}`;
el('items').innerHTML=selected.slice(page*size,(page+1)*size).map(r=>{const d=decisions[r.sample_id]||{};return `<article data-id="${escapeHtml(r.sample_id)}"><h2>Recording ${escapeHtml(r.recording_id)} · Fill ${escapeHtml(r.fill_level)}%</h2><p>${escapeHtml(r.sample_id)} · ${escapeHtml(r.timestamp_utc)}<br>Preview suggestion: ${escapeHtml(r.suggested_lighting)} · Proposed: ${escapeHtml(r.proposed_split)} · Export: ${escapeHtml(r.export_status)}</p>${['narrow','wide'].map(v=>r[v+'_image']?`<img loading="lazy" src="${escapeHtml(r[v+'_image'])}" alt="${v} view">`:`<p>Missing ${v} image</p>`).join('')}<p><label>Lighting <select data-field="lighting">${options(['pending','daylight','night','transition','uncertain'],d.lighting||'pending')}</select></label><label>QC <select data-field="qc">${options(['pending','keep','reject'],d.qc||'pending')}</select></label><label>Reason <input data-field="reason" value="${escapeHtml(d.reason||'')}" placeholder="Obstruction / blur / mismatch / other"></label></p></article>`}).join('')}
el('items').addEventListener('change',e=>{const field=e.target.dataset.field;if(!field)return;const id=e.target.closest('article').dataset.id;decisions[id]={...(decisions[id]||{}),[field]:e.target.value};try{localStorage.setItem(key,JSON.stringify(decisions))}catch(e){alert('Browser storage unavailable. Download a backup before closing.')}el('progress').textContent=`QC decisions: ${rows.filter(r=>['keep','reject'].includes(decisions[r.sample_id]?.qc)).length} / ${rows.length}`});
el('source').onchange=el('pending').onchange=()=>{page=0;render()};el('prev').onclick=()=>{page=Math.max(0,page-1);render()};el('next').onclick=()=>{page++;render()};
function save(name,data,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
el('download').onclick=()=>{const fields=['sample_id','lighting','qc','reason'];const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';save('review_decisions.csv',[fields.join(','),...rows.map(r=>{const d=decisions[r.sample_id]||{};return [r.sample_id,d.lighting||'pending',d.qc||'pending',d.reason||''].map(quote).join(',')})].join('\\n'),'text/csv')};
el('backup').onclick=()=>save('review_decisions_backup.json',JSON.stringify(decisions,null,2),'application/json');
el('restore').onchange=async e=>{try{const parsed=JSON.parse(await e.target.files[0].text());if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')throw Error('Expected object');const ids=new Set(rows.map(r=>r.sample_id));for(const [id,d] of Object.entries(parsed)){if(!ids.has(id)||!d||typeof d!=='object')throw Error('Unknown sample or invalid decision');if(d.qc&&!['pending','keep','reject'].includes(d.qc))throw Error('Invalid QC value');if(d.lighting&&!['pending','daylight','night','transition','uncertain'].includes(d.lighting))throw Error('Invalid lighting')}decisions=parsed;localStorage.setItem(key,JSON.stringify(decisions));render()}catch(e){alert('Could not restore: '+e.message)}};render();</script></html>"""
    (root / "review.html").write_text(html.replace("__DATA__", payload))
    print(f"Created review page, template and split plan for {len(reviews)} candidates")


if __name__ == "__main__":
    main()
