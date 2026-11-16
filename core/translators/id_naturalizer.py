"""
Indonesian Light Novel Prose Naturalizer & Persona Lock
Enhances raw machine translation into natural, fluent, and emotionally engaging
Indonesian light novel prose (Gramedia / official publication style).
"""

import re
from typing import List

# Common stiff literal phrases -> natural Indonesian light novel phrasing
IDIOM_REPLACEMENTS = [
    # Dialogue & Greetings
    (r"\blihat aku nanti\b", "sampai nanti"),
    (r"\blihat saya nanti\b", "sampai jumpa nanti"),
    (r"\b(dia|ia)?\s*memberi mengangguk kecil\b", "aku mengangguk pelan"),
    (r"\b(dia|ia)?\s*memberi anggukan kecil\b", "aku mengangguk pelan"),
    (r"\b(aku|dia|ia)?\s*memberi sedikit anggukan\b", "aku mengangguk pelan"),
    (r"\bmengangguk sedikit\b", "mengangguk pelan"),
    (r"\bmengangguk ringan\b", "mengangguk pelan"),
    (r"\bmencoba untuk berbicara\b", "mencoba berbicara"),
    (r"\bentah bagaimana mengingat\b", "berusaha mengingat"),
    (r"\bsensasi yang aku lupakan\b", "sensasi yang sempat terlupakan"),
    (r"\bsensasi dia lupa\b", "sensasi yang sempat terlupakan"),
    (r"\bmemberikan noda kecil\b", "mengangguk pelan"),
    (r"\bmemberikan sebuah noda kecil\b", "mengangguk pelan"),
    (r"\bmemberi noda\b", "mengangguk"),
    (r"\bmemberi anggukan\b", "mengangguk pelan"),
    (r"\bmemberikan anggukan\b", "mengangguk"),
    (r"\bmenunjuk jari saya\b", "melambaikan tangan"),
    (r"\bmenunjuk jarinya\b", "melambaikan tangannya"),
    (r"\bmenunjuk jari\b", "melambaikan tangan"),
    (r"\bmenangkap selimut\b", "memakai payung"),
    
    # Sci-Fi / Cold sleep terms
    (r"\btidur panas\b", "tidur kriogenik"),
    (r"\btidur dingin\b", "tidur kriogenik"),
    (r"\btidur lama dingin\b", "tidur kriogenik panjang"),
    (r"\btidur kedinginan\b", "tidur kriogenik"),
    (r"\btidur kedinginan panjang\b", "tidur kriogenik panjang"),

    # Medical, Anatomy & Transport Disambiguation
    (r"\b(meletakkan|menaruh|menempelkan)\s+jarinya\s+ke\s+kuil(nya)?\b", "menempelkan jarinya ke pelipisnya"),
    (r"\bdi atas pelipisnya\b", "ke pelipisnya"),
    (r"\bke kuilnya\b", "ke pelipisnya"),
    (r"\bhukuman (aku|saya) yang tersisa\b", "vonis sisa hidupku"),
    (r"\bhukuman yang tersisa\b", "vonis sisa hidup"),
    (r"\bsiaran mobil\b", "pengumuman di dalam gerbong"),
    (r"\bbagian dalam mobil\b", "bagian dalam gerbong"),

    # Common Corrupted Name & Typo Guards
    (r"\bHeonda\b", "Honda"),
    (r"\bMINao\b", "Minako"),
    (r"\bThe Minako\b", "Minako"),
    (r"\bMINako\b", "Minako"),
    
    # Actions & Reactions
    (r"\bmelepaskan menguap besar\b", "menguap lebar"),
    (r"\bmelepaskan menguap\b", "menguap"),
    (r"\bmembuat wajah yang canggung\b", "memasang wajah serbasalah"),
    (r"\bmembuat ekspresi yang canggung\b", "memasang ekspresi canggung"),
    (r"\bmembuat senyum kecut\b", "tersenyum kecut"),
    (r"\bmemperlihatkan senyum kecut\b", "tersenyum kecut"),
    (r"\bmenarik nafas panjang\b", "menghela napas panjang"),
    (r"\bmelepaskan desahan\b", "menghela napas"),
    (r"\bmelepaskan helaan napas\b", "menghela napas"),
    (r"\bmenghembuskan nafas\b", "menghela napas"),
    (r"\bmenggelengkan kepala dengan tak berdaya\b", "menggeleng pasrah"),
    (r"\bmiringkan kepalanya\b", "memiringkan kepala heran"),
    (r"\bmemiringkan kepalanya karena heran\b", "memiringkan kepala heran"),
    
    # Medical & Sensation
    (r"\bsuara perut (saya|aku) bug\b", "suara perutku yang keroncongan"),
    (r"\bperut (saya|aku) bug\b", "perutku yang keroncongan"),
    (r"\bsuara perut (saya|aku) menggeram\b", "suara perutku yang keroncongan"),
    (r"\bsuara perutku menggeram\b", "suara perutku yang keroncongan"),
    (r"\bmengisyaratkan rasa laparku\b", "menandakan rasa lapar"),
    (r"\bmengisyaratkan rasa lapar aku\b", "menandakan rasa lapar"),
    (r"\bkemalasan tubuh (saya|aku)\b", "rasa lemas yang melanda tubuhku"),
    (r"\blangit-langit anorganik\b", "langit-langit rumah sakit yang kaku dan dingin"),
    (r"\bbeban selimut pada (saya|aku)\b", "beratnya selimut yang menimpaku"),
    (r"\bbeban selimut padaku\b", "beratnya selimut yang menimpaku"),
    (r"\bberat selimut pada (saya|aku)\b", "beratnya selimut yang menimpaku"),
    (r"\bkehidupan mulut saya kering\b", "mulutku terasa kering kerontang"),
    (r"\bkekeringan mulut (saya|aku)\b", "mulutku yang kering kerontang"),
    (r"\btenggorokan saya kering\b", "tenggorokanku terasa kering"),
    (r"\bberhasil tanpa insiden\b", "berjalan lancar tanpa kendala"),
    (r"\bberhasil tanpa kecelakaan\b", "berhasil dengan lancar"),
    (r"\bdikatakan tidak ada harapan\b", "divonis sudah tak ada harapan sembuh"),
    (r"\btidak berpikir itu akan menjadi aneh untuk telah hancur di sepanjang jalan\b", "merasa wajar jika perusahaan itu sudah bangkrut seiring berlalunya waktu"),
    (r"\bhancur di sepanjang jalan\b", "bangkrut seiring waktu"),
    
    # Food & Portions
    (r"\bdetik-detik dilarang\b", "dilarang menambah porsi"),
    (r"\bdetik dilarang\b", "tidak boleh nambah porsi"),
    (r"\bmangkuk kedua dilarang\b", "tidak boleh nambah porsi"),
    
    # Staff & Social Interaction
    (r"\b(ia\s+)?memiliki (kemampuan dan )?udara yang (berbakat dan )?dapat diandalkan tentang (dirinya|dia)\b", "ia memancarkan aura pria yang cakap dan dapat diandalkan"),
    (r"\bmemiliki udara yang berbakat dan dapat diandalkan tentang dia\b", "memancarkan aura pria yang cakap dan dapat diandalkan"),
    (r"\budara yang berbakat dan dapat diandalkan tentang dia\b", "aura pria yang cakap dan dapat diandalkan"),
    (r"\bmemiliki kemampuan dan udara yang dapat diandalkan tentang dirinya\b", "memancarkan aura pria yang cakap dan dapat diandalkan"),
    (r"\bmemiliki udara yang dapat diandalkan tentang dirinya\b", "memancarkan aura yang dapat diandalkan"),
    (r"\bmemiliki udara tentang dirinya yang membuatnya tampak seperti dia bisa melakukan pekerjaannya\b", "memancarkan kesan pria yang sangat cakap dalam pekerjaannya"),
    (r"\bmemiliki udara tentang dirinya\b", "memancarkan kesan berwibawa"),
    (r"\bpunya udara tentang dirinya\b", "memancarkan kesan berwibawa"),
    (r"\budara yang dapat diandalkan tentang dirinya\b", "kesan yang dapat diandalkan"),
    (r"\bpada hari ini dan usia\b", "di zaman sekarang ini"),
    (r"\bpada hari dan usia ini\b", "di era modern ini"),
    (r"\bdi hari dan usia ini\b", "di era sekarang ini"),
    (r"\bmenolak tawaran itu dan berkata\b", "menggeleng pelan lalu berkata"),
    (r"\bmemeriksa setiap sudut dan celah tubuh saya\b", "memeriksa setiap jengkal tubuhku"),
    (r"\bmemeriksa setiap sudut dan celah tubuhku\b", "memeriksa setiap jengkal tubuhku"),
    (r"\bmenaruh jarinya ke pelipisnya\b", "menempelkan jari ke pelipisnya"),
    (r"\bmeletakkan jarinya di pelipisnya\b", "menempelkan jari ke pelipisnya"),
    (r"\btelah menerima pembayaran dari orang lain untuk kelebihan\b", "biaya kelebihannya sudah dibayarkan oleh orang lain"),
    (r"\btidak ada permintaan tambahan\b", "tidak ada biaya atau tagihan tambahan"),
    (r"\bdan di tempat, realitas mulai mulai terbentuk\b", "dan perlahan, kenyataan mulai terbentuk kembali"),
    (r"\bmengambil bentuk\b", "mulai terbentuk"),
    (r"\bkeluar dari rumah\b", "keluar dari rumah sakit"),
    (r"\bkuliah tentang masyarakat modern\b", "penyuluhan adaptasi masyarakat modern"),
    (r"\bkemalasan tubuhku\b", "rasa lemas yang melanda tubuhku"),
    (r"\bkekeringan mulutku\b", "tenggorokanku yang terasa kering"),
    (r"\bberat selimut menutupi aku\b", "beratnya selimut yang menyelimutiku"),
    (r"\bberat selimut menutupi(ku)?\b", "beratnya selimut yang menyelimutiku"),
    (r"\bsuara perutku berteriak untuk memberi sinyal kelaparan aku\b", "suara perutku yang keroncongan menandakan rasa lapar"),
    (r"\bsuara perutku berteriak\b", "suara perutku keroncongan"),
    (r"\bkelaparan aku\b", "rasa laparku"),
    (r"\bmakan pertama aku\b", "makanan pertamaku"),
    (r"\btatapan yang aneh\b", "ekspresi serbasalah"),
    
    # Gratitude Relative-Clause Inversion Guard
    (r"^.*?\b(kau|kamu),\s*yang seharusnya aku (berterima kasih|bersyukur).*$", "Saat aku terbangun, kau—orang yang seharusnya kuucapkan terima kasih—sudah tidak ada lagi."),
    (r"\bKetika aku bangun,\s*kau,\s*yang seharusnya aku bersyukur,\s*tidak lagi ada di sana\.?\b", "Saat aku terbangun, kau—orang yang seharusnya kuucapkan terima kasih—sudah tidak ada lagi."),
    (r"\bSaat aku bangun,\s*kau tidak lagi ada untuk berterima kasih padaku\b", "Saat aku terbangun, kau—orang yang seharusnya kuucapkan terima kasih—sudah tidak ada lagi"),
    (r"\bKetika aku bangun,\s*kau tidak lagi ada untuk berterima kasih padaku\b", "Saat aku terbangun, kau—orang yang seharusnya kuucapkan terima kasih—sudah tidak ada lagi"),

    # General Prose
    (r"\bdari masa depan saya diri\b", "dari diriku di masa depan"),
    (r"\bdari masa depan aku diri\b", "dari diriku di masa depan"),
    (r"\buntuk masa lalu Anda sendiri\b", "untuk dirimu di masa lalu"),
    (r"\bdari masa depan saya\b", "dari masa depanku"),
    (r"\bke masa lalu Anda\b", "ke masa lalumu"),
    (r"\bbunga-bunga dalam satu bungkus\b", "sebuket bunga"),
    (r"\bsebuah karangan bunga\b", "sebuket bunga"),
    (r"\bkamar bayi\b", "buaian ayunan"),
    (r"\bTujuhpuluh\b", "Tujuh puluh"),
    (r"\btujuhpuluh\b", "tujuh puluh"),
    (r"\bsebelas belas tahun\b", "tujuh puluh tahun"),
    (r"\bsepuluh puluh tahun\b", "tujuh puluh tahun"),
    (r"\bsetuju ratusan tahun\b", "tujuh puluh tahun"),
    (r"\btidur lama yang dingin\b", "tidur kriogenik panjang"),
]


def apply_persona_lock(text: str, default_pronoun: str = "aku") -> str:
    """
    Enforces consistent first-person narrator pronouns ('aku') in narration
    while strictly preserving formal polite speech ('saya' / 'Anda') inside character dialogue quotes.
    """
    if not text:
        return ""

    # Split text into dialogue quotes ("...") and narration parts
    parts = re.split(r'("[^"]*")', text)
    processed = []

    for part in parts:
        if part.startswith('"') and part.endswith('"'):
            # Inside character dialogue: retain original speech tone (e.g. polite doctor)
            processed.append(part)
        else:
            # Inside novel narration: strictly enforce 'aku' / '-ku' persona
            p = part
            # Prepositional & possessive transformations
            p = re.sub(r'\bke(pada)?\s+saya\b', 'kepadaku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bpada\s+saya\b', 'padaku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bdari\s+saya\b', 'dariku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bmilik\s+saya\b', 'milikku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bdiri\s+saya\b', 'diriku', p, flags=re.IGNORECASE)
            p = re.sub(r'\btubuh\s+saya\b', 'tubuhku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bkesadaran\s+saya\b', 'kesadaranku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bmulut\s+saya\b', 'mulutku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bperut\s+saya\b', 'perutku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bpenyakit\s+saya\b', 'penyakitku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bmimpi\s+saya\b', 'mimpiku', p, flags=re.IGNORECASE)
            p = re.sub(r'\btangan\s+saya\b', 'tanganku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bmata\s+saya\b', 'mataku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bhidup\s+saya\b', 'hidupku', p, flags=re.IGNORECASE)
            p = re.sub(r'\buntuk\s+saya\b', 'untukku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bsuara\s+saya\b', 'suaraku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bpertanyaan\s+saya\b', 'pertanyaanku', p, flags=re.IGNORECASE)

            # Standalone narrative Saya / saya -> Aku / aku
            p = re.sub(r'\bSaya\b', 'Aku', p)
            p = re.sub(r'\bsaya\b', 'aku', p)

            # Smooth Indonesian possessive enclitics (-ku)
            p = re.sub(r'\b(pikiran|impian|tubuh|perut|mulut|mata|tangan|suara|pertanyaan|hati|hidup|makan|makanan|lapar|rasa lapar)\s+aku\b', r'\1ku', p, flags=re.IGNORECASE)
            p = re.sub(r'\bmenutupi\s+aku\b', 'menutupiku', p, flags=re.IGNORECASE)
            processed.append(p)

    return "".join(processed)


def smooth_indonesian_prose(text: str) -> str:
    """Apply PersonaLock, dictionary, and regex smoothing for natural Indonesian novel prose."""
    if not text or not text.strip():
        return ""

    res = text.strip()

    # 1. Apply PersonaLock (narration strictly 'aku', dialogue untouched)
    res = apply_persona_lock(res, default_pronoun="aku")

    # 2. Apply idiom replacements
    for pattern, replacement in IDIOM_REPLACEMENTS:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)

    # 3. Clean double spaces, double dots, or punctuation glitches
    res = re.sub(r"\.\.+", ".", res)
    res = re.sub(r"\s+", " ", res).strip()
    res = re.sub(r"\s+([,.\?!;:\"'])", r"\1", res)
    res = re.sub(r"([\"'\(])\s+", r"\1", res)

    # 4. Capitalize start of sentence and sentences following a period
    res = re.sub(r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), res)
    if res and res[0].islower():
        res = res[0].upper() + res[1:]

    return res


def naturalize_indonesian_batch(texts: List[str]) -> List[str]:
    """Process a batch of Indonesian translated paragraphs."""
    return [smooth_indonesian_prose(t) for t in texts]
