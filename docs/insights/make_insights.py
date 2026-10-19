"""README 6~7장(인사이트·활용)의 수치와 차트를 다시 만든다.

입력: 수용 검증을 통과한 Gold 폴더(g_stock_daily_analysis.csv, g_fin_rpt_analysis.csv)와 Silver s_stock.csv 폴더.
출력: 01-snapshot-20stocks.svg, 02-event-20obs.svg 와 표준출력 요약 수치.
사용: python3 docs/insights/make_insights.py <gold 폴더> <silver 폴더> <출력 폴더>
"""
import html
import sys

import numpy as np
import pandas as pd

G, S, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
C = {"IMPROVE_STRONG": "#2f7d4f", "IMPROVE_WEAK": "#e8663d", "SLOW_STRONG": "#3b6fd1", "SLOW_WEAK": "#8a8a8a"}
L = {"IMPROVE_STRONG": "실적 개선·강세 (동행)", "IMPROVE_WEAK": "실적 개선·약세 (괴리)",
     "SLOW_STRONG": "실적 둔화·강세 (괴리)", "SLOW_WEAK": "실적 둔화·약세 (동행)"}
FONT = "font-family=\"'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif\""

d = pd.read_csv(f"{G}/g_stock_daily_analysis.csv", dtype={"stock_cd": str})
f = pd.read_csv(f"{G}/g_fin_rpt_analysis.csv", dtype={"stock_cd": str})
nm = pd.read_csv(f"{S}/s_stock.csv", dtype=str, encoding="utf-8-sig").set_index("stock_cd")["stock_nm"]


def snapshot_bar(last):
    """기준일 20종목: 공시 후 시장 대비 성과 막대, 색은 동행·괴리 분류."""
    last = last.sort_values("event_excess_rt", ascending=False)
    W, rowh, t, l, rgt = 1100, 26, 96, 250, 40
    H = t + rowh * len(last) + 60
    lo, hi = -80, 120
    pw = W - l - rgt
    X = lambda v: l + (v - lo) / (hi - lo) * pw
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>',
         f'<rect width="{W}" height="{H}" fill="#fbfaf8"/>',
         '<text x="30" y="36" font-size="20" font-weight="700" fill="#222">2026-06-30 기준 20종목 — 매출은 15종목이 늘었지만, 시장보다 강했던 건 5종목</text>',
         '<text x="30" y="60" font-size="13" fill="#666">막대 = 2025 사업보고서 공시 후 시장 대비 성과(%p) · 괄호 = 매출 성장률 · 색 = 동행·괴리 분류</text>']
    cnt = last.co_move_cd.value_counts()
    x0 = 30
    for k in C:
        if cnt.get(k, 0):
            o.append(f'<rect x="{x0}" y="72" width="12" height="12" fill="{C[k]}"/><text x="{x0 + 18}" y="83" font-size="13" fill="#333">{L[k]} {cnt[k]}</text>')
            x0 += 240
    for v in range(lo, hi + 1, 20):
        o.append(f'<line x1="{X(v):.1f}" y1="{t}" x2="{X(v):.1f}" y2="{H - 50}" stroke="{"#777" if v == 0 else "#e6e2dc"}" stroke-width="{1.5 if v == 0 else 1}"/>'
                 f'<text x="{X(v):.1f}" y="{H - 32}" font-size="12" fill="#666" text-anchor="middle">{v:+d}</text>')
    for i, r in enumerate(last.itertuples()):
        y = t + i * rowh + 4
        v = r.event_excess_rt * 100
        x1, x2 = sorted((X(0), X(max(min(v, hi), lo))))
        o.append(f'<text x="{l - 10}" y="{y + 14}" font-size="13" fill="#222" text-anchor="end">{html.escape(r.nm)} ({r.rev_yoy_rt * 100:+.1f}%)</text>')
        o.append(f'<rect x="{x1:.1f}" y="{y}" width="{x2 - x1:.1f}" height="{rowh - 8}" fill="{C[r.co_move_cd]}"/>')
        tx = X(max(min(v, hi), lo)) + (6 if v >= 0 else -6)
        o.append(f'<text x="{tx:.1f}" y="{y + 14}" font-size="12" fill="#444" text-anchor="{"start" if v >= 0 else "end"}">{v:+.1f}</text>')
    o.append(f'<text x="{l + pw / 2}" y="{H - 10}" font-size="13" fill="#444" text-anchor="middle">공시 후 시장 대비 성과 (%p)</text></svg>')
    open(f"{OUT}/01-snapshot-20stocks.svg", "w", encoding="utf-8").write("\n".join(o))
    return cnt


def event_scatter(e, same):
    """보고서별 공시 후 20번째 거래일: 매출 성장률 vs 시장 대비 성과."""
    W, H, l, t, rr, b = 1100, 640, 80, 70, 30, 70
    xr, yr = (-60, 120), (-60, 60)
    pw, ph = W - l - rr, H - t - b
    X = lambda v: l + (v - xr[0]) / (xr[1] - xr[0]) * pw
    Y = lambda v: t + ph - (v - yr[0]) / (yr[1] - yr[0]) * ph
    ec = e.co_move_cd.value_counts()
    title = f"보고서 {len(e)}건 — 매출 방향과 공시 후 주가 방향이 같았던 건 {same * 100:.1f}%"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>',
         f'<rect width="{W}" height="{H}" fill="#fbfaf8"/>',
         f'<text x="{l}" y="38" font-size="20" font-weight="700" fill="#222">{html.escape(title)}</text>']
    for v in np.linspace(xr[0], xr[1], 7):
        o.append(f'<line x1="{X(v):.1f}" y1="{t}" x2="{X(v):.1f}" y2="{t + ph}" stroke="#e6e2dc"/><text x="{X(v):.1f}" y="{t + ph + 20}" font-size="12" fill="#666" text-anchor="middle">{v:.0f}</text>')
    for v in np.linspace(yr[0], yr[1], 7):
        o.append(f'<line x1="{l}" y1="{Y(v):.1f}" x2="{l + pw}" y2="{Y(v):.1f}" stroke="#e6e2dc"/><text x="{l - 8}" y="{Y(v) + 4:.1f}" font-size="12" fill="#666" text-anchor="end">{v:.0f}</text>')
    o.append(f'<line x1="{X(0):.1f}" y1="{t}" x2="{X(0):.1f}" y2="{t + ph}" stroke="#777" stroke-width="1.5"/><line x1="{l}" y1="{Y(0):.1f}" x2="{l + pw}" y2="{Y(0):.1f}" stroke="#777" stroke-width="1.5"/>')
    for r in e.itertuples():
        x = min(max(r.rev_yoy_rt * 100, xr[0]), xr[1])
        y = min(max(r.event_excess_rt * 100, yr[0]), yr[1])
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5" fill="{C[r.co_move_cd]}" fill-opacity="0.7" stroke="#fff"/>')
    o.append(f'<text x="{l + pw / 2}" y="{H - 22}" font-size="14" fill="#444" text-anchor="middle">보고서 매출 성장률 (%, -60~120 밖은 끝에 표시)</text>')
    o.append(f'<text transform="translate(22,{t + ph / 2}) rotate(-90)" font-size="14" fill="#444" text-anchor="middle">공시 후 20번째 관측일 시장 대비 성과 (%p)</text>')
    for i, k in enumerate(C):
        yy = t + 14 + i * 22
        o.append(f'<circle cx="{l + pw - 250}" cy="{yy - 4}" r="6" fill="{C[k]}"/><text x="{l + pw - 238}" y="{yy}" font-size="13" fill="#333">{L[k]} {ec.get(k, 0)}건</text>')
    o.append("</svg>")
    open(f"{OUT}/02-event-20obs.svg", "w", encoding="utf-8").write("\n".join(o))
    return ec


# 기준일 스냅샷
last = d[d.trd_dt == d.trd_dt.max()].copy()
last["nm"] = last.stock_cd.map(nm)
cnt = snapshot_bar(last)

# 보고서별: 공시 후 해당 보고서가 연결된 20번째 거래일
d = d.sort_values(["stock_cd", "trd_dt"])
ev = d[d.fin_rpt_id.notna() & d.event_excess_rt.notna() & d.rev_yoy_rt.notna()].copy()
ev["k"] = ev.groupby(["stock_cd", "fin_rpt_id"]).cumcount() + 1
e = ev[ev.k == 20]
same = (np.sign(e.rev_yoy_rt) == np.sign(e.event_excess_rt)).mean()
ec = event_scatter(e, same)

av = d[d.co_move_cd != "UNAVAILABLE"]
x = f[f.rev_yoy_rt.notna() & f.op_cf_delta_amt.notna()]
up = x[x.rev_yoy_rt > 0]
print("기준일", d.trd_dt.max(), "분류", cnt.to_dict())
print("보고서 이벤트", len(e), "부호 일치율", round(same, 4),
      "스피어만", round(e[["rev_yoy_rt", "event_excess_rt"]].corr(method="spearman").iloc[0, 1], 4), "분류", ec.to_dict())
print("일별 분류 가능", len(av), "동행 비율", round(av.co_move_cd.isin(["IMPROVE_STRONG", "SLOW_WEAK"]).mean(), 4))
print("매출 증가 보고서", len(up), "그중 영업현금 감소", int((up.op_cf_delta_amt < 0).sum()))
print("영업이익 전환", f.op_prft_transition_cd.value_counts().to_dict())
print("복합 동반 개선 Y", int((d.joint_improve_yn == "Y").sum()), "/ 판단 가능", int((d.joint_improve_stts_cd == "OK").sum()))
print("기준일 매출↑·현금↓", list(last[(last.rev_yoy_rt > 0) & (last.op_cf_delta_amt < 0)].nm))
print("기준일 외국인·기관 동시 순매수", [(r.nm, r.co_move_cd) for r in last[(last.frgn_net_20d_qty > 0) & (last.inst_net_20d_qty > 0)].itertuples()])
