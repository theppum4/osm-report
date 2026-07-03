"""
รายงานผลงาน อสม.แกนนำสุขภาพ - จ.อุบลราชธานี เขตสุขภาพที่ 10
สร้างแดชบอร์ด HTML รายวัน โดยดึงข้อมูลจาก 3doctor.hss.moph.go.th

วิธีใช้:
    python osm_dashboard.py

ผลลัพธ์:
    รายงาน_อสม_YYYY-MM-DD.html  (บันทึกใน C:\CO-WORK\7.บทบาท อสม.แกนนำสุขภาพ\)
"""

import re
import json
import sys
from datetime import datetime
from pathlib import Path

# ===== CONFIG =====
ZONE          = "10"
PROVINCE      = "34"          # อุบลราชธานี
PROVINCE_NAME = "อุบลราชธานี"
TARGET_PCT    = 90.0           # เป้าหมาย ร้อยละ
OUTPUT_DIR    = Path(__file__).parent  # C:\CO-WORK\7.บทบาท อสม.แกนนำสุขภาพ\


def fetch_data_via_requests():
    """ดึงข้อมูลผ่าน requests (ใช้เมื่อรันบนเครื่อง user โดยตรง)"""
    try:
        import requests
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://3doctor.hss.moph.go.th/osm-potential/report-follow-community",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.post(
            "https://3doctor.hss.moph.go.th/osm-potential/load-follow-community",
            data=f"zone={ZONE}&province={PROVINCE}&amphur=&tambon=",
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[WARN] requests failed: {e}")
        return None


def parse_osm_data(raw_text):
    """Parse ตาราง อสม. จาก text ที่ดึงจากเว็บ"""
    data = []
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]

    pattern = re.compile(
        r'^(?!รวม|อำเภอ|A\b|B\b|หมายเหตุ|ข้อมูล)(.+?)\s+'
        r'([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+'
        r'([\d.]+)\s*%?'
    )

    for line in lines:
        m = pattern.match(line)
        if m:
            name = m.group(1).strip()
            if len(name) < 2 or name.isdigit():
                continue
            try:
                nums = [int(m.group(i).replace(',', '')) for i in range(2, 9)]
                pct  = float(m.group(9))
                data.append({
                    "อำเภอ": name,
                    "A_อสม_ทั้งหมด":    nums[0],
                    "B_คัดกรอง":         nums[1],
                    "C_แนะนำพฤติกรรม":  nums[2],
                    "D_สร้าง_อสค":       nums[3],
                    "E_เยี่ยมบ้าน":      nums[4],
                    "F_รณรงค์":          nums[5],
                    "G_แกนนำ":           nums[6],
                    "H_ร้อยละ":          pct
                })
            except (ValueError, IndexError):
                continue

    date_match = re.search(r'ข้อมูลอัพเดต ณ วันที่ (.+?) เวลา', raw_text)
    update_date = date_match.group(1) if date_match else datetime.now().strftime('%d %b %Y')
    return data, update_date


def classify(pct):
    if pct >= TARGET_PCT: return "good"
    elif pct >= 80:       return "warn"
    else:                 return "bad"


def build_html(data, update_date):
    if not data:
        return "<html><body><h1>ไม่พบข้อมูล</h1></body></html>"

    total_osm    = sum(d["A_อสม_ทั้งหมด"] for d in data)
    total_leader = sum(d["G_แกนนำ"] for d in data)
    overall_pct  = (total_leader / total_osm * 100) if total_osm else 0
    pcts         = [d["H_ร้อยละ"] for d in data]
    avg_pct      = sum(pcts) / len(pcts)
    count_good   = sum(1 for p in pcts if p >= TARGET_PCT)
    count_warn   = sum(1 for p in pcts if 80 <= p < TARGET_PCT)
    count_bad    = sum(1 for p in pcts if p < 80)

    sorted_data  = sorted(data, key=lambda x: x["H_ร้อยละ"], reverse=True)
    labels  = [d["อำเภอ"] for d in sorted_data]
    values  = [d["H_ร้อยละ"] for d in sorted_data]
    colors  = ["#16a34a" if p >= TARGET_PCT else "#ca8a04" if p >= 80 else "#dc2626" for p in values]

    table_rows = ""
    for d in sorted_data:
        cls  = classify(d["H_ร้อยละ"])
        icon = "✅" if cls == "good" else "⚠️" if cls == "warn" else "🔴"
        table_rows += f"""
        <tr class="{cls}">
          <td>{d['อำเภอ']}</td>
          <td class="num">{d['A_อสม_ทั้งหมด']:,}</td>
          <td class="num">{d['B_คัดกรอง']:,}</td>
          <td class="num">{d['C_แนะนำพฤติกรรม']:,}</td>
          <td class="num">{d['D_สร้าง_อสค']:,}</td>
          <td class="num">{d['E_เยี่ยมบ้าน']:,}</td>
          <td class="num">{d['F_รณรงค์']:,}</td>
          <td class="num">{d['G_แกนนำ']:,}</td>
          <td class="num pct">{icon} {d['H_ร้อยละ']:.2f}%</td>
        </tr>"""

    labels_json = json.dumps(labels, ensure_ascii=False)
    values_json = json.dumps(values)
    colors_json = json.dumps(colors)
    gen_time    = datetime.now().strftime('%d/%m/%Y %H:%M น.')
    overall_cls = "green" if overall_pct >= TARGET_PCT else "yellow" if overall_pct >= 80 else "red"

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>รายงาน อสม.แกนนำสุขภาพ | จ.อุบลราชธานี</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Sarabun',sans-serif;background:#f0f4f8;color:#1a202c}}
.header{{background:linear-gradient(135deg,#1a56db,#1e429f);color:#fff;padding:28px 32px}}
.header h1{{font-size:1.6em;font-weight:700}}
.header p{{opacity:.85;margin-top:4px;font-size:.95em}}
.badge{{display:inline-block;background:rgba(255,255,255,.2);border-radius:20px;padding:3px 12px;font-size:.82em;margin-top:8px;margin-right:6px}}
.content{{max-width:1300px;margin:0 auto;padding:24px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.kpi{{background:#fff;border-radius:12px;padding:20px 16px;box-shadow:0 2px 8px rgba(0,0,0,.06);text-align:center;border-top:4px solid #1a56db}}
.kpi.green{{border-color:#16a34a}}.kpi.yellow{{border-color:#ca8a04}}.kpi.red{{border-color:#dc2626}}
.kpi-val{{font-size:2.4em;font-weight:700;line-height:1;margin:6px 0}}
.kpi-val.green{{color:#16a34a}}.kpi-val.yellow{{color:#ca8a04}}.kpi-val.red{{color:#dc2626}}.kpi-val.blue{{color:#1a56db}}
.kpi-label{{font-size:.85em;color:#6b7280}}
.card{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:24px}}
.card h2{{font-size:1.1em;font-weight:700;color:#1e429f;margin-bottom:16px;border-left:4px solid #1a56db;padding-left:10px}}
.chart-wrap{{position:relative;height:420px}}
table{{width:100%;border-collapse:collapse;font-size:.9em}}
th{{background:#1e429f;color:#fff;padding:10px 8px;text-align:center;font-weight:600}}
td{{padding:8px;border-bottom:1px solid #f0f0f0}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
td.pct{{font-weight:700}}
tr.good{{background:#f0fdf4}}tr.warn{{background:#fffbeb}}tr.bad{{background:#fff5f5}}
tr:hover{{filter:brightness(.97)}}
.legend{{display:flex;gap:20px;margin-bottom:12px;font-size:.88em}}
.dot{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:5px}}
.summary-box{{background:#eff6ff;border-radius:10px;padding:16px;margin-top:16px;font-size:.92em;line-height:1.8}}
.footer{{text-align:center;color:#9ca3af;font-size:.8em;padding:20px}}
@media(max-width:768px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 รายงานติดตามผลงาน อสม.แกนนำสุขภาพ</h1>
  <p>ตัวชี้วัดร้อยละแกนนำสุขภาพมีศักยภาพในการจัดการสุขภาพชุมชน</p>
  <span class="badge">จ.{PROVINCE_NAME} | เขตสุขภาพที่ {ZONE}</span>
  <span class="badge">ข้อมูล ณ {update_date}</span>
</div>
<div class="content">
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">อสม. ทั้งหมด</div><div class="kpi-val blue">{total_osm:,}</div><div class="kpi-label">คน</div></div>
    <div class="kpi"><div class="kpi-label">แกนนำสุขภาพ</div><div class="kpi-val blue">{total_leader:,}</div><div class="kpi-label">คน</div></div>
    <div class="kpi {overall_cls}"><div class="kpi-label">ร้อยละรวมจังหวัด</div><div class="kpi-val {overall_cls}">{overall_pct:.2f}%</div><div class="kpi-label">เป้าหมาย ≥ {TARGET_PCT:.0f}%</div></div>
    <div class="kpi"><div class="kpi-label">ค่าเฉลี่ยรายอำเภอ</div><div class="kpi-val {'green' if avg_pct>=TARGET_PCT else 'yellow' if avg_pct>=80 else 'red'}">{avg_pct:.2f}%</div><div class="kpi-label">จาก {len(data)} อำเภอ</div></div>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:24px">
    <div class="kpi green"><div class="kpi-label">✅ ≥{TARGET_PCT:.0f}% ดีมาก</div><div class="kpi-val green">{count_good}</div><div class="kpi-label">อำเภอ</div></div>
    <div class="kpi yellow"><div class="kpi-label">⚠️ 80–89% ควรพัฒนา</div><div class="kpi-val yellow">{count_warn}</div><div class="kpi-label">อำเภอ</div></div>
    <div class="kpi red"><div class="kpi-label">🔴 &lt;80% ต้องเร่งรัด</div><div class="kpi-val red">{count_bad}</div><div class="kpi-label">อำเภอ</div></div>
  </div>
  <div class="card">
    <h2>📈 ร้อยละแกนนำสุขภาพ แยกรายอำเภอ (เรียงจากมากไปน้อย)</h2>
    <div class="legend">
      <span><span class="dot" style="background:#16a34a"></span>≥{TARGET_PCT:.0f}% ดีมาก</span>
      <span><span class="dot" style="background:#ca8a04"></span>80–89% ควรพัฒนา</span>
      <span><span class="dot" style="background:#dc2626"></span>&lt;80% ต้องเร่งรัด</span>
    </div>
    <div class="chart-wrap"><canvas id="barChart"></canvas></div>
  </div>
  <div class="card">
    <h2>📋 ตารางข้อมูลรายละเอียดรายอำเภอ</h2>
    <div style="overflow-x:auto">
    <table>
      <thead><tr>
        <th>อำเภอ</th><th>A<br>อสม.ทั้งหมด</th><th>B<br>คัดกรอง NCDs</th>
        <th>C<br>แนะนำพฤติกรรม</th><th>D<br>สร้าง อสค.</th><th>E<br>เยี่ยมบ้าน</th>
        <th>F<br>รณรงค์ NCDs</th><th>G<br>แกนนำ</th><th>H<br>ร้อยละ (G/A)</th>
      </tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
    </div>
    <div class="summary-box">
      <strong>สรุปผลการวิเคราะห์:</strong><br>
      • อสม. ทั้งหมด {len(data)} อำเภอ รวม {total_osm:,} คน เป็นแกนนำสุขภาพ {total_leader:,} คน
        คิดเป็นร้อยละ <strong>{overall_pct:.2f}%</strong>
        {'(✅ บรรลุเป้าหมาย)' if overall_pct >= TARGET_PCT else f'(⚠️ ต่ำกว่าเป้าหมาย — ขาดอีก {TARGET_PCT-overall_pct:.2f}%)'}<br>
      • อำเภอผลงานสูงสุด 3 อันดับ: {', '.join(f'{d["อำเภอ"]} ({d["H_ร้อยละ"]:.1f}%)' for d in sorted_data[:3])}<br>
      • อำเภอที่ต้องให้ความสนใจ: {', '.join(f'{d["อำเภอ"]} ({d["H_ร้อยละ"]:.1f}%)' for d in sorted_data[-3:]) if count_bad+count_warn>0 else 'ทุกอำเภอบรรลุเป้าหมายแล้ว ✅'}
    </div>
  </div>
</div>
<div class="footer">สร้างอัตโนมัติโดย Claude AI | {gen_time} | ข้อมูลจาก 3doctor.hss.moph.go.th</div>
<script>
new Chart(document.getElementById('barChart').getContext('2d'),{{
  type:'bar',
  data:{{labels:{labels_json},datasets:[{{label:'ร้อยละแกนนำสุขภาพ',data:{values_json},backgroundColor:{colors_json},borderRadius:4}}]}},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.parsed.y.toFixed(2)}}%`}}}}}},
    scales:{{
      x:{{ticks:{{font:{{family:'Sarabun',size:11}},maxRotation:45}}}},
      y:{{min:0,max:105,ticks:{{callback:v=>v+'%',font:{{family:'Sarabun'}}}},grid:{{color:'#f0f0f0'}}}}
    }}
  }},
  plugins:[{{afterDraw(chart){{
    const{{ctx,scales:{{y,x}}}}=chart,yPx=y.getPixelForValue({TARGET_PCT});
    ctx.save();ctx.strokeStyle='#1e429f';ctx.lineWidth=2;ctx.setLineDash([6,4]);
    ctx.beginPath();ctx.moveTo(x.left,yPx);ctx.lineTo(x.right,yPx);ctx.stroke();
    ctx.fillStyle='#1e429f';ctx.font='bold 12px Sarabun';
    ctx.fillText('เป้าหมาย {TARGET_PCT:.0f}%',x.right-85,yPx-6);ctx.restore();
  }}}}]
}});
</script>
</body></html>"""


def save_report(html_content):
    today    = datetime.now().strftime('%Y-%m-%d')
    filepath = OUTPUT_DIR / f"รายงาน_อสม_{today}.html"
    filepath.write_text(html_content, encoding='utf-8')
    print(f"[OK] บันทึกที่: {filepath}")
    return filepath


def main():
    print("=" * 60)
    print(f"รายงานผลงาน อสม.แกนนำสุขภาพ | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"บันทึกใน: {OUTPUT_DIR}")
    print("=" * 60)

    raw = fetch_data_via_requests()
    if not raw:
        print("[INFO] ไม่สามารถดึงข้อมูลจาก API ได้")
        print("       ให้ Claude ใช้ Chrome tools แทน หรือรัน scheduled task")
        sys.exit(1)

    data, update_date = parse_osm_data(raw)
    if not data:
        print("[ERROR] Parse ข้อมูลไม่สำเร็จ")
        sys.exit(1)

    print(f"[OK] พบข้อมูล {len(data)} อำเภอ | อัพเดท: {update_date}")
    html     = build_html(data, update_date)
    filepath = save_report(html)

    total  = sum(d["A_อสม_ทั้งหมด"] for d in data)
    leader = sum(d["G_แกนนำ"] for d in data)
    pct    = leader / total * 100 if total else 0
    print(f"\n📊 สรุป: อสม. {total:,} คน | แกนนำ {leader:,} คน | ร้อยละ {pct:.2f}%")
    print(f"📁 รายงาน: {filepath}")


if __name__ == "__main__":
    main()
