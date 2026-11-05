#!/usr/bin/env python3
"""cards.json and paper.json from the script's timing, so a new voice take moves every panel with it. Free.
    python3 make_cards.py CLIP_FOLDER"""
import json, sys
from pathlib import Path
C = Path(sys.argv[1]); L = {l['n']: l for l in json.loads((C / 'build/lines.json').read_text(encoding='utf-8'))}
def at(n, sub=None):
    l = L[n]
    if not sub:
        return l['a']
    i = l['t'].index(sub)
    return round(l['a'] + (l['b'] - l['a']) * i / len(l['t']), 2)
def card(a, b, kind, title, rows=(), times=(), panel=None, motion=None, who=None, zoom=None, frames=None):
    o = {}
    if times: o['times'] = list(times)
    if panel: o['panel'] = panel
    if motion: o['motion'] = motion
    if zoom: o['zoom'] = zoom
    if frames: o['frames'] = frames
    if who: o['who'] = who
    return ['ch01', a, b, kind, title, list(rows), o]
cards = [
 card(0.0, L[1]['b'], 'q', 'ดวงอาทิตย์กำลังมืดลง', ['มนุษย์เหลือไพ่ใบสุดท้าย แค่ใบเดียว'], [at(1, 'แล้วมนุษย์')], 'sun', 'flipbook', 'G', frames='sun_frames'),
 card(at(3), L[4]['b'], 'term', 'ครูวิทยาศาสตร์มัธยมต้น', ['แน่ใจนะ?'], [at(4)], 'chalk', 'drop', 'G', zoom=1.5),
 card(at(5), L[5]['b'], 'verdict', 'Project Hail Mary', ['ฟิล ลอร์ด และ คริสโตเฟอร์ มิลเลอร์', 'นำแสดงโดย ไรอัน กอสลิง'], [at(5, 'หนังของ'), at(5, 'นำแสดง')], 'ship', 'adrift', 'G'),
 card(at(7), L[7]['b'], 'term', 'Hail Mary', ['ศัพท์อเมริกันฟุตบอล', 'ขว้างยาวสุดแรงในจังหวะสิ้นหวัง', 'โอกาสสำเร็จน้อยมาก'], [at(7), at(7, 'คือการ'), at(7, 'โอกาส')], 'football', 'arc', 'G', zoom=1.15),
 card(at(9), L[9]['b'], 'take', 'สิ่งที่โยนออกไป', ['คือยานอวกาศทั้งลำ'], [at(9, 'คือยาน')], 'ship', 'throw', 'G'),
 card(at(11), L[11]['b'], 'rows', 'ไรแลนด์ เกรซ', ['ตื่นขึ้นมาบนยาน แทบจำอะไรไม่ได้', 'ลูกเรือ 3 คน รอดคนเดียว'], [at(11, 'ตื่นขึ้นมา'), at(11, 'ลูกเรือ')], 'ship', 'adrift', 'G'),
 card(at(13), L[13]['b'], 'term', 'แอสโตรเฟจ', ['จุลชีพที่ทำให้ดวงอาทิตย์หรี่ลง', 'ปลายทาง: ดาว Tau Ceti'], [at(13, 'กำลังทำให้'), at(13, 'ยานลำนี้')], 'dish', 'astro', 'G'),
 card(at(15, 'จนกระทั่ง'), L[15]['b'], 'term', 'ร็อคกี้', ['เอเลียนที่ไรแลนด์ได้พบ', 'ทั้งคู่กลายเป็นเพื่อนกัน'], [at(15, 'เอเลียน'), at(15, 'แล้วทั้งคู่')], 'rocky', 'rocky', 'G', zoom=1.2),
 card(at(18), L[18]['b'], 'stat', 'คนเชิด 5 คน', ['หุ่นเชิดจริงในกองถ่าย', 'นำโดย เจมส์ ออร์ติซ ผู้ให้เสียงร็อคกี้'], [at(18), at(18, 'นำโดย')], 'puppet', 'puppet', 'H'),
 card(at(20), L[20]['b'], 'stat', 'ราว 50 : 50', ['หุ่นเชิดครึ่งหนึ่ง', 'แอนิเมชันอีกครึ่งหนึ่ง'], [at(20, 'หุ่นเชิด'), at(20, 'แอนิเมชัน')], 'puppet', 'puppet_half', 'H'),
 card(at(21), L[21]['b'], 'take', 'ภายในยาน', ['สร้างเป็นฉากจริงทั้งหมด'], [at(21, 'ก็สร้าง')], who='G'),
 card(at(24), L[26]['b'], 'stat', '95%', ['ของ 430 รีวิวเป็นบวก · Rotten Tomatoes', 'รายได้ทั่วโลกเกิน 685 ล้านดอลลาร์', 'แต่บางคนว่ามีช่วงน่าเบื่อ'], [at(24, 'รีวิว'), at(24, 'รายได้'), at(26)], who='H'),
 card(at(27, 'นี่คือ'), L[27]['b'], 'take', 'เพื่อนสองคน', ['ที่มาจากคนละดาว'], [at(27, 'ที่มาจาก')], 'rocky', 'friends', 'G', zoom=1.25),
 card(at(28, 'แต่เฮลแมรี'), L[28]['b'], 'take', 'เฮลแมรีที่ดีที่สุด', ['คือตอนที่มีใครรออยู่อีกฝั่ง'], [at(28, 'คือตอนที่')], 'football', 'catch', 'H', zoom=1.12),
]
(C / 'cards.json').write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding='utf-8')
m = lambda s: f'{int(s // 60):02d}:{s % 60:05.2f}'
paper = {'title': 'Project Hail Mary', 'sub': '', 'clip': True, 'source': '1080p/EP01.mp4', 'voice': {'mix': 1.0, 'chain': 'none'},
         'chapters': [{'id': 'ch01', 'title': 'Project Hail Mary', 'keep': [[m(L[1]['a']), L[1]['t'].split(' ')[0], m(L[30]['b']), L[30]['t']]]}],
         'end_rows': ['โยนแล้วภาวนา แต่ไม่ได้ภาวนาคนเดียว'], 'wide': [[L[n]['a'], L[n]['b']] for n in (2, 14, 29, 30)]}
(C / 'paper.json').write_text(json.dumps(paper, ensure_ascii=False, indent=1), encoding='utf-8')
print('OK', len(cards), 'cards')
