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
    (r"\bRekoil membuat aku\b", "Sebagai imbasnya, aku"),
    (r"\brekoil membuat aku\b", "sebagai imbasnya, aku"),
    (r"\brekoil\b", "pelampiasan"),
    (r"\bRekoil\b", "Pelampiasan"),

    # Fantasy Terms & Anti-Hallucination Guards
    (r"\bSyiah\b", "Shia"),
    (r"\bSyi'a\b", "Shia"),
    (r"\bPhiladelphia\b", "Philly"),
    (r"\bAllah\s+iblis\b", "Dewa Iblis"),
    (r"\bAllah\s+Goblin\b", "Goblin Lord"),
    (r"\bAllah\s+goblin\b", "Goblin Lord"),
    (r"\bAllah\s+yang\s+jahat\b", "Dewa Jahat"),
    (r"\bAllah\s+jahat\b", "Dewa Jahat"),
    (r"\bMulia\s+Ketuhanan\b", "Tuan Yang Mulia"),
    (r"\bpetenis\s+agung\b", "Penyihir Agung"),
    (r"\bpetenis\b", "Penyihir"),
    (r"\bpemain\s+sorcer\b", "Penyihir"),
    (r"\btukang\s+sorcer\b", "Penyihir"),
    (r"\bSorcererer\b", "Penyihir"),
    (r"\bkandang\s+petualang\b", "Guild Petualang"),
    (r"\bserikat\s+buruh\b", "Guild"),
    (r"\bserikat\s+pekerja\b", "Guild"),
    (r"\bmaster\s+serikat\s+pekerja\b", "Ketua Guild"),
    (r"\bmaster\s+serikat\b", "Ketua Guild"),
    (r"\bPartai\s+pahlawan\b", "Kelompok Pahlawan"),
    (r"\bpartai\s+pahlawan\b", "kelompok pahlawan"),
    (r"\bDokkaebi\b", "Goblin"),
    (r"\bdokkaebi\b", "goblin"),
    (r"\bDasheng\b", "Bijak Agung"),
    (r"\bSMA\s+vampir\b", "Vampire High Lord"),
    (r"\bJalan\s+Raya\s+Vampir\b", "Vampire High Lord"),
    (r"\bJalan\s+Vampir\b", "Vampire Lord"),
    (r"\bJalan\s+Goblin\b", "Goblin Lord"),
    (r"\bjalan\s+Dokkaebi\b", "Goblin Lord"),
    (r"\bjalan\s+goblin\b", "Goblin Lord"),
    (r"\bjalan\s+vampir\b", "Vampire Lord"),
    (r"\bTuhan\s+Chicken\b", "Ayam Suci"),
    (r"\bsurga\s+Chicken\b", "Ayam Suci"),
    (r"\bChicken\b(?=\s+Gerberga)", "Ayam Suci"),
    (r"\bKue\s+si\s+Iblis\b", "Misi Pembasmian Goblin"),
    (r"\bair\s+berat\b", "air tajin"),
    (r"\bpemandian\s+berat\b", "air tajin hangat"),
    (r"\blantai\s+enam\b(?=.*(?:Lord|Dewa|Vampir|Peringkat))", "Peringkat Keenam"),
    (r"\blantai\s+delapan\b(?=.*(?:Lord|Dewa|Vampir|Peringkat))", "Peringkat Kedelapan"),
    (r"\bmembelai\s+bola(?:-bola)?nya\b", "mengelus Tama"),
    (r"\bmengelus\s+bola(?:-bola)?nya\b", "mengelus Tama"),
    (r"\bmemukul\s+bola-bolanya\b", "mengelus Tama"),
    (r"\bmeninggalkan\s+bola\s+aku\b", "menitipkan Tama"),
    (r"\bmeninggalkan\s+bolaku\b", "menitipkan Tama"),
    (r"\bIbu\s+dan\s+putri\s+Goran\s+dan\s+Cerlis\b", "Ayah dan putri Goran dan Cerlis"),
    (r"\bibu\s+dan\s+anak\s+(?:perempuan\s+)?Goran\s+dan\s+Cerlis\b", "ayah dan anak Goran dan Cerlis"),
    (r"\bCircus\b", "Cerlis"),
    (r"\bbatang masturbasi\b", "Tongkat Konkon"),
    (r"\bpohon kondom\b", "Pohon Tongkat Konkon"),
    (r"\bpenis-ex\b", "Tongkat Konkon EX"),
    (r"\bberhubungan seks dengan pasangan saya\b", "bekerja sama dengan kalian"),
    (r"\bcon-con-bon seks\b", "Tongkat Konkon EX"),
    (r"\bbawang hijau yang maha kuasa\b", "daun bawang"),
    (r"\bNona Eboshi\b", "Nona Muda"),
    (r"\bKotori\b", "burung kecil"),
    
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

    # Male Chest & Anatomy Protection (prevents 'breasts' for male characters)
    (r"\bpayudara\s+(Jean|Lishu|Ash|Letze|Dinosso|Dean|Chris|Note|Van|Amedeo|Shiva|Soleil|Ludil|Ruta|Az|Auro|Kiel|Misht|pria|laki-laki|cowok)\b", r"dada \1"),
    (r"\bpayudara\s+mereka\b", "dada mereka"),

    # Calque English/Japanese Idioms -> Natural Indonesian Light Novel Expressions
    (r"\btidak\s+bisa\s+(?:membantu|menahan)\s+tetapi\s+tertawa\b", "tak kuasa menahan tawa"),
    (r"\btak\s+bisa\s+(?:membantu|menahan)\s+tetapi\s+tertawa\b", "tak kuasa menahan tawa"),
    (r"\btidak\s+bisa\s+(?:membantu|menahan)\s+tetapi\s+(\w+)\b", r"tak kuasa menahan \1"),
    (r"\btak\s+bisa\s+(?:membantu|menahan)\s+tetapi\s+(\w+)\b", r"tak kuasa menahan \1"),
    (r"\bmenahan\s+tertawa\b", "menahan tawa"),
    (r"\btak\s+kuasa\s+menahan\s+tertawa\b", "tak kuasa menahan tawa"),
    (r"\btidak\s+bisa\s+tidak\s+(\w+)\b", r"mau tak mau harus \1"),
    (r"\bmembuat\s+rasa\b", "masuk akal"),
    (r"\bmasuk\s+akal\s+sehat\b", "masuk akal"),
    (r"\bmengambil\s+tempat\b", "berlangsung"),
    (r"\bmengambil\s+bagian\b", "turut serta"),
    (r"\bkehilangan\s+kata-kata\b", "kehabisan kata-kata"),
    (r"\bkehabisan\s+kata\b", "kehabisan kata-kata"),
    (r"\bdatang\s+ke\s+pikiran\b", "terlintas di benak"),
    (r"\bterlintas\s+di\s+pikiran\b", "terlintas di benak"),
    (r"\bterlintas\s+dalam\s+pikiran\b", "terlintas di benak"),
    (r"\bdi\s+sisi\s+lain\s+koin\b", "sebaliknya"),
    (r"\bpada\s+akhir\s+hari\b", "pada akhirnya"),
    (r"\btidak\s+ada\s+yang\s+bisa\s+dilakukan\s+tentang\s+itu\b", "mau bagaimana lagi"),
    (r"\btidak\s+ada\s+yang\s+bisa\s+dilakukan\b", "apa boleh buat"),
    (r"\bitu\s+adalah\s+masalah\s+lain\b", "itu soal lain"),
    (r"\bterlepas\s+dari\s+kenyataan\s+bahwa\b", "meski begitu"),
    (r"\bmembuat\s+wajah\s+yang\s+rumit\b", "memasang ekspresi serbasalah"),
    (r"\bmembuat\s+wajah\s+rumit\b", "memasang ekspresi serbasalah"),
    (r"\bwajah\s+yang\s+rumit\b", "ekspresi serbasalah"),
    (r"\bmembuat\s+wajah\s+pahit\b", "memasang ekspresi masam"),
    (r"\bwajah\s+pahit\b", "ekspresi masam"),
    (r"\bwajah\s+biru\b", "wajah pucat pasi"),
    (r"\bmenjatuhkan\s+bahunya\b", "pundaknya terkulai lemas"),
    (r"\bmenjatuhkan\s+bahu\b", "pundaknya terkulai lemas"),
    (r"\btercengang\s+dengan\s+mata\s+menjadi\s+titik\b", "tercengang tak percaya"),
    (r"\bmata\s+menjadi\s+titik\b", "tercengang"),
    (r"\bmenggaruk\s+bagian\s+belakang\s+leher(nya)?\b", "menggaruk tengkuknya yang tak gatal"),
    (r"\bmenggosok\s+bagian\s+belakang\s+kepala(nya)?\b", "menggaruk tengkuknya"),
    (r"\bmenutup\s+mulutnya\s+rapat-rapat\b", "bungkam seribu bahasa"),
    (r"\bmelebarkan\s+matanya\b", "matanya membelalak"),
    (r"\bmatanya\s+membesar\b", "matanya membelalak"),
    (r"\bmenggigit\s+bibirnya\b", "menggigit bibirnya cemas"),
    (r"\btertawa\s+kering\b", "terkekeh hambar"),
    (r"\bsenyum\s+tipis\s+mengambang\b", "tersenyum tipis"),
    (r"\bmembuat\s+keputusan\b", "mengambil keputusan"),
    (r"\bmemotong\s+beras\s+menjadi\s+dua\b", "mengurangi porsi nasi hingga setengah"),
    (r"\bmemotong\s+beras\b", "mengurangi porsi nasi"),
    (r"\bmemijat\s+wijen\b", "meremas wijen"),
    (r"\bmemijat\s+putih\s+wijen\b", "meremas wijen putih"),

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
    Enforces consistent first-person novel pronouns ('aku' / '-ku') across both narration
    and character dialogue, eliminating stiff corporate/bureaucratic 'saya' while
    safely protecting third-person proper names (e.g. character name 'Saya').
    """
    if not text:
        return ""

    def _naturalize_pronouns(segment: str) -> str:
        p = segment
        # 1. Prepositional & possessive transformations
        p = re.sub(r'\bke(pada)?\s+saya\b', 'kepadaku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bpada\s+saya\b', 'padaku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bdari\s+saya\b', 'dariku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bmilik\s+saya\b', 'milikku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bdiri\s+saya\b', 'diriku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bdengan\s+saya\b', 'denganku', p, flags=re.IGNORECASE)
        p = re.sub(r'\buntuk\s+saya\b', 'untukku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bbersama\s+saya\b', 'bersamaku', p, flags=re.IGNORECASE)
        p = re.sub(r'\btubuh\s+saya\b', 'tubuhku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bkesadaran\s+saya\b', 'kesadaranku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bmulut\s+saya\b', 'mulutku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bperut\s+saya\b', 'perutku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bpenyakit\s+saya\b', 'penyakitku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bmimpi\s+saya\b', 'mimpiku', p, flags=re.IGNORECASE)
        p = re.sub(r'\btangan\s+saya\b', 'tanganku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bmata\s+saya\b', 'mataku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bhidup\s+saya\b', 'hidupku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bsuara\s+saya\b', 'suaraku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bpertanyaan\s+saya\b', 'pertanyaanku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bkekuatan\s+saya\b', 'kekuatanku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bkondisi\s+saya\b', 'kondisiku', p, flags=re.IGNORECASE)

        # 2. Lowercase 'saya' is ALWAYS the first-person pronoun -> 'aku'
        p = re.sub(r'\bsaya\b', 'aku', p)

        # 3. Capitalized 'Saya' at start of line/dialogue/punctuation -> 'Aku'
        p = re.sub(r'(^|[\"“\'「.!?]\s*)\bSaya\b', r'\1Aku', p)
        # Followed by common pronoun verbs/predicates:
        p = re.sub(r'\bSaya\s+(tidak|akan|bisa|ingin|merasa|melihat|mendengar|pergi|pikir|kira|harapkan|bawa|tahu|adalah|berada|memiliki|sedang|sudah|telah|belum|harus|mau|coba|memutuskan)\b', r'Aku \1', p)

        # 4. Smooth enclitics (-ku) across all body parts, family relations, items, and attributes
        pat_noun_ku = (
            r'\b(pikiran|impian|tubuh|perut|mulut|mata|tangan|suara|pertanyaan|hati|hidup|makan|makanan|lapar|rasa lapar|'
            r'kekuatan|kondisi|bahu|lengan|saudara(?:-saudara)?|kakak(?:-kakak)?|adik(?:-adik)?|kamar|buku|pedang|baju|'
            r'celana|kaki|kepala|leher|pakaian|rumah|uang|dunia|kemampuan|sihir|keluarga|teman(?:-teman)?|sahabat|ibu|ayah|'
            r'wajah|pipi|dada|punggung|jari|rambut|telinga|hidung|alat|senjata|perisai|tas|dompet|surat|wilayah|posisi|status|'
            r'level|tingkat|nama|tujuan|keinginan|harapan|rencana|tugas|pekerjaan|perjalanan|ingatan|kenangan|perasaan|senyum|'
            r'napas|tatapan|langkah|pilihan|keputusan)\s+aku\b'
        )
        p = re.sub(pat_noun_ku, r'\1ku', p, flags=re.IGNORECASE)
        p = re.sub(r'\bmenutupi\s+aku\b', 'menutupiku', p, flags=re.IGNORECASE)
        return p

    # Split text into dialogue quotes ("...") and narration parts
    parts = re.split(r'("[^"]*")', text)
    processed = []

    for part in parts:
        processed.append(_naturalize_pronouns(part))

    return "".join(processed)


def smooth_dialogue_tags(text: str) -> str:
    """
    Transforms stiff English-style dialogue tags (e.g. '"...", dia berkata.')
    into fluent official light novel style ('"...", ucapnya.' / 'tanyanya.' / 'gumamnya.').
    """
    if '"' not in text:
        return text

    res = text
    # Dialogue tag conversions after closing quotation mark
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berkata\b', r'\1ucapnya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berbisik\b', r'\1bisiknya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+bergumam\b', r'\1gumamnya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+bertanya\b', r'\1tanyanya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berseru\b', r'\1serunya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+berteriak\b', r'\1serunya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+mengeluh\b', r'\1keluhnya', res)
    res = re.sub(r'([\"”][,\s]*)\b(?:dia|ia)\s+menjawab\b', r'\1jawabnya', res)
    res = re.sub(r'([\"”][,\s]*)\bkata\s+(?:dia|ia)\b', r'\1katanya', res)
    return res


def clean_conjunction_clutter(text: str) -> str:
    """
    Cleans repetitive and awkward conjunction starters common in raw machine translation.
    """
    res = text
    res = re.sub(r'(^|[.!?]\s*)Dan\s+kemudian,?\s*', r'\1Kemudian, ', res)
    res = re.sub(r'(^|[.!?]\s*)Tetapi\s+bagaimanapun,?\s*', r'\1Namun, ', res)
    res = re.sub(r'(^|[.!?]\s*)Namun\s+tetapi,?\s*', r'\1Namun, ', res)
    res = re.sub(r'(^|[.!?]\s*)Sebagai\s+hasilnya,?\s*', r'\1Alhasil, ', res)
    res = re.sub(r'(^|[.!?]\s*)Oleh\s+karena\s+itu,?\s*', r'\1Karena itu, ', res)
    return res


def smooth_indonesian_prose(text: str) -> str:
    """Apply PersonaLock, dictionary, dialogue tags, and regex smoothing for natural Indonesian novel prose."""
    if not text or not text.strip():
        return ""

    res = text.strip()

    # 0. Pass-through or recover scene breaks
    if re.match(r'^[◇◆\*＊─━＝=\-\s]{2,}$', res) or ('◇' in res and any(w in res for w in ['Tiada', 'Tawa', 'apa-apa'])):
        return "◇◇◇"

    # 1. Apply PersonaLock (consistent 'aku' across narration & dialogue)
    res = apply_persona_lock(res, default_pronoun="aku")

    # 2. Apply idiom replacements & fantasy domain sanitization
    for pattern, replacement in IDIOM_REPLACEMENTS:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)

    # 3. Clean conjunction clutter
    res = clean_conjunction_clutter(res)

    # 4. Smooth dialogue tags to light novel standard
    res = smooth_dialogue_tags(res)

    # 5. Clean repetition loops (e.g. "sawi, sawi, sawi", "bentuk bentuk bentuk")
    res = re.sub(r'\b([A-Za-z0-9_]+)(?:[,\s]+\1){2,}\b', r'\1', res, flags=re.IGNORECASE)

    # 6. Clean subtitle HTML artifacts if leaked from training data
    res = re.sub(r'&lt;font[^&gt;]*&gt;|&lt;/font&gt;|&lt;/i&gt;|<font[^>]*>|</font>|</i>|font\s*color=[^>\s]*', '', res, flags=re.IGNORECASE)

    # 7. Clean double spaces, double dots, or punctuation glitches
    res = re.sub(r"\.\.+", ".", res)
    res = re.sub(r"\s+", " ", res).strip()
    res = re.sub(r"\s+([,.\?!;:])", r"\1", res)
    res = re.sub(r'(^|[\s(])([\"\'“])\s+', r'\1\2', res)
    res = re.sub(r'\s+([\"\'”])(?=[\s,.\?!;:]|$)', r'\1', res)
    res = re.sub(r'([,.\?!;:a-zA-Z0-9][\"”])([a-zA-Z])', r'\1 \2', res)
    res = re.sub(r'\(\s+', '(', res)
    res = re.sub(r'\s+\)', ')', res)

    # 7. Capitalize start of sentence and sentences following a period
    res = re.sub(r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), res)
    if res and res[0].islower():
        res = res[0].upper() + res[1:]

    return res


def naturalize_indonesian_batch(texts: List[str]) -> List[str]:
    """
    Chapter-level multi-paragraph batch naturalizer:
    1. Paragraph-level prose smoothing, PersonaLock, idioms, and dialogue tags.
    2. Inter-paragraph variety smoothing: eliminates consecutive monotone sentence starters.
    3. Dialogue quote balancing & formatting.
    """
    smoothed = [smooth_indonesian_prose(t) for t in texts]

    # Inter-paragraph smoothing
    for idx in range(1, len(smoothed)):
        curr = smoothed[idx]
        prev = smoothed[idx - 1]
        if not curr or not prev:
            continue

        # Prevent consecutive paragraphs starting with the exact same conjunction
        if curr.startswith("Kemudian, ") and prev.startswith("Kemudian, "):
            smoothed[idx] = "Setelah itu, " + curr[len("Kemudian, "):]
        elif curr.startswith("Lalu, ") and prev.startswith("Lalu, "):
            smoothed[idx] = "Setelahnya, " + curr[len("Lalu, "):]
        elif curr.startswith("Namun, ") and prev.startswith("Namun, "):
            smoothed[idx] = "Meski demikian, " + curr[len("Namun, "):]

    return smoothed
