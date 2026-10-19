"""Render README figures from pinned historical CSV and the verified DB snapshot.

Run from repository root with Python + matplotlib. No DB credentials required.
"""
import csv
import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/media/insights'
COLORS = {'000660': '#d66a28', '005930': '#087f8c'}
NAMES = {'000660': 'SK하이닉스', '005930': '삼성전자'}


def style():
    apple = Path('/System/Library/Fonts/AppleSDGothicNeo.ttc')
    if apple.exists():
        font_manager.fontManager.addfont(str(apple))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(apple)).get_name()
    else:
        plt.rcParams['font.family'] = ['Malgun Gothic', 'NanumGothic', 'DejaVu Sans']
    plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.spines.left': False, 'axes.spines.bottom': False,
                         'axes.titleweight': 'bold', 'text.color': '#182c42',
                         'axes.labelcolor': '#526276', 'xtick.color': '#526276',
                         'ytick.color': '#526276', 'figure.facecolor': '#f4f7fb',
                         'axes.facecolor': '#f4f7fb', 'grid.color': '#d9e2ec'})


def historical():
    path = ROOT / 'data/03_C_integration_20261014/04_output/gold/g_ai_stock_daily.csv'
    with path.open(encoding='utf-8-sig') as f:
        rows = [r for r in csv.DictReader(f) if r['stock_cd'] in NAMES
                and '2026-06-01' <= r['trd_dt'] <= '2026-06-30']
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.3))
    fig.subplots_adjust(left=.06, right=.97, top=.70, bottom=.24, wspace=.33)
    fig.text(.055, .91, '주가 상승과 외국인 이탈은 함께 나타날 수 있다', fontsize=21, weight='bold')
    fig.text(.055, .83, '같은 기간을 세 가지 관점으로 비교  |  2026.06.01 → 06.30', color='#526276', fontsize=12)
    titles = ['주가 · 시작일 = 100', '외국인 누적 순매수 · 백만 주', '외국인 보유율 · %']
    expected = {'000660': (Decimal('2640000'), Decimal('-7392456')),
                '005930': (Decimal('333000'), Decimal('-76545220'))}
    for stock, color in COLORS.items():
        group = sorted((r for r in rows if r['stock_cd'] == stock), key=lambda r: r['trd_dt'])
        assert len(group) == 21 and len({r['trd_dt'] for r in group}) == 21
        dates = [dt.date.fromisoformat(r['trd_dt']) for r in group]
        price = [Decimal(r['close_prc']) for r in group]
        flow = [Decimal(0)]
        for row in group[1:]:
            assert row['frgn_net_buy_qty'] != ''
            flow.append(flow[-1] + Decimal(row['frgn_net_buy_qty']))
        assert (price[-1], flow[-1]) == expected[stock]
        values = [[float(p / price[0] * 100) for p in price],
                  [float(v / 1000000) for v in flow],
                  [float(Decimal(r['frgn_hold_rt']) * 100) for r in group]]
        for i, (ax, series) in enumerate(zip(axes, values)):
            ax.plot(dates, series, color=color, lw=2.4, label=NAMES[stock])
            ax.scatter(dates[-1], series[-1], color=color, s=25, zorder=3)
            label = f'{(price[-1] / price[0] - 1) * 100:+.2f}%' if i == 0 else f'{series[-1]:.2f}'
            ax.annotate(label, (dates[-1], series[-1]), xytext=(4, 4),
                        textcoords='offset points', fontsize=10, color=color, weight='bold')
    for ax, title in zip(axes, titles):
        ax.set_title(title, loc='left', fontsize=12, pad=14)
        ax.grid(axis='y', alpha=.7)
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.margins(x=.13, y=.2)
        ax.tick_params(length=0, pad=8)
    axes[0].axhline(100, color='#8b9aab', lw=.8, ls='--')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc='upper right', bbox_to_anchor=(.97, .84), ncol=2)
    fig.text(.055, .10, '순매수는 시작일 이후 20거래일 합산. 출처: 고정 인계본 g_ai_stock_daily · 제공 종가 기준.', fontsize=10, color='#526276')
    fig.text(.055, .045, '관측된 괴리는 추가 검토의 출발점이며, 거품 여부나 매도 원인을 확정하지 않는다.', fontsize=10, color='#526276')
    fig.savefig(OUT / '03-price-foreign-divergence.png', dpi=160)
    plt.close(fig)


def valuation():
    # Collected provider values are local only (build/ is git-ignored); keep the committed PNG otherwise.
    path = ROOT / 'build/research/valuation-snapshot.json'
    if not path.exists():
        print('skip 04-valuation-evidence.png: local build/research/valuation-snapshot.json absent')
        return
    data = json.loads(path.read_text())['rows']
    assert len(data) == 6 and all(r['observed_at'].startswith('2026-10-16') for r in data)
    values = {(r['stock_cd'], r['metric']): float(r['value']) for r in data}
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.3))
    fig.subplots_adjust(left=.08, right=.96, top=.69, bottom=.25, wspace=.35)
    fig.text(.065, .91, '가격 수준을 해석할 근거를 더하다', fontsize=21, weight='bold')
    fig.text(.065, .83, '추가 수집 사례  |  2026.10.16 수집 시점의 평가 배수', fontsize=12, color='#526276')
    for i, stock in enumerate(COLORS):
        color = COLORS[stock]
        for offset, metric, alpha in [(-.18, 'per', 1), (.18, 'cnsPer', .4)]:
            value = values[stock, metric]
            axes[0].bar(i + offset, value, width=.31, color=color, alpha=alpha,
                        hatch='//' if metric == 'cnsPer' else None,
                        label=('PER' if metric == 'per' else '추정 PER') if i == 0 else None)
            axes[0].text(i + offset, value + .18, f'{value:.2f}', ha='center', fontsize=11)
        value = values[stock, 'pbr']
        axes[1].bar(i, value, width=.42, color=color)
        axes[1].text(i, value + .08, f'{value:.2f}', ha='center', fontsize=11)
    for ax, title in zip(axes, ['이익 대비 가격 · PER / 추정 PER', '장부가치 대비 가격 · PBR']):
        ax.set_title(title, loc='left', fontsize=12, pad=14)
        ax.set_xticks([0, 1], list(NAMES.values()))
        ax.set_ylabel('배')
        ax.set_ylim(0, ax.get_ylim()[1] * 1.18)
        ax.grid(axis='y', alpha=.6); ax.set_axisbelow(True)
        ax.tick_params(length=0, pad=8)
    axes[0].legend(frameon=False, loc='upper right', fontsize=9)
    fig.text(.065, .10, '출처: 네이버 증권 공개 응답 → research_valuation. 추정 PER는 전망치이며 확정 실적과 구분한다.', fontsize=10, color='#526276')
    fig.text(.065, .045, '6월 분석에 소급하지 않는 별도 스냅샷. 두 기업의 배수 차이만으로 고평가·저평가를 판정하지 않는다.', fontsize=10, color='#526276')
    fig.savefig(OUT / '04-valuation-evidence.png', dpi=160)
    plt.close(fig)


def cleaned_forecast():
    from matplotlib.colors import ListedColormap
    data = json.loads((ROOT / 'docs/research/cleaned-data-forecast.json').read_text())
    rows = sorted(data['rows'], key=lambda r: (-r['positive_count'],r['stock_cd']))
    assert len(rows) == 20 and all(len(r['positive_flags'])==5 for r in rows)
    fig, ax = plt.subplots(figsize=(12,10))
    fig.subplots_adjust(left=.23,right=.74,top=.80,bottom=.12)
    fig.text(.055,.94,'정제한 데이터로 우리는 이렇게 예상한다',fontsize=21,weight='bold')
    fig.text(.055,.89,'2026.06.30 기준 → 다음 20거래일 시장 대비 방향에 대한 팀의 가설',color='#526276',fontsize=12)
    ax.imshow([[int(v) for v in r['positive_flags']] for r in rows],
              cmap=ListedColormap(['#e1e7ee','#087f8c']),vmin=0,vmax=1,aspect='auto')
    ax.set_xticks(range(5),['매출 성장','시장 대비 성과','영업CF 증가','외국인 순매수','기관 순매수'])
    ax.xaxis.tick_top();ax.tick_params(axis='x',length=0,pad=12,labelsize=10)
    ax.set_yticks(range(20),[r['stock_nm'] for r in rows]);ax.tick_params(axis='y',length=0,pad=12)
    for i,row in enumerate(rows):
        for k,flag in enumerate(row['positive_flags']):
            ax.text(k,i,'+' if flag else '- / 0',ha='center',va='center',fontsize=11,
                    color='white' if flag else '#526276')
        ax.text(4.7,i,f"{row['positive_count']}/5  {row['forecast']}",va='center',fontsize=10,
                color='#087f8c' if row['positive_count']>=4 else '#b86028' if row['positive_count']<=1 else '#526276')
    fig.text(.055,.065,'강세 4종목 · 혼조 12종목 · 약세 4종목  |  추가 수집 자료 없이 정제 인계본만 사용',fontsize=11,weight='bold')
    fig.text(.055,.025,'양수 신호 4~5개: 강세 / 2~3개: 혼조 / 0~1개: 약세. 탐색용 규칙이며 미래 적중률은 미검증.',fontsize=10,color='#526276')
    fig.savefig(OUT/'05-cleaned-data-forecast.png',dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    style(); historical(); valuation(); cleaned_forecast()
    print('Rendered 3 charts; historical endpoints, snapshot dates and twenty cleaned-data forecasts checked.')
