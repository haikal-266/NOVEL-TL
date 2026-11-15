/**
 * VelTL - Light Novel Prose Naturalizer & Speech Marker Gender Resolver
 * Client-side TypeScript port for 100% offline mobile execution.
 */

const FEMALE_PRONOUNS = new Set(['あたし', 'アタシ', 'あたくし', '彼女']);
const FEMALE_NOUNS = new Set(['少女', '女の子', '娘', 'お姉さん', '姉', '妹', '母', 'お嬢様', '令嬢', '女性', '女']);
const FEMALE_PARTICLES = ['わ', 'かしら', 'のよ', 'わよ', 'わね', 'のね', 'ちょうだい', 'てよ', 'もの'];

const MALE_PRONOUNS = new Set(['俺', 'オレ', 'おれ', '僕', 'ボク', 'ぼく', 'わし', '彼']);
const MALE_NOUNS = new Set(['少年', '男の子', '息子', 'お兄さん', '兄', '弟', '父', '男性', '男', '青年']);
const MALE_PARTICLES = ['ぜ', 'ぞ', 'だろ', 'かい', 'じゃねえ', 'だぜ', 'だぞ', 'な'];

// Known character gender registry
const KNOWN_CHARACTERS: Record<string, 'FEMALE' | 'MALE'> = {
  'レティーナ': 'FEMALE',
  'クルーゼス': 'MALE',
  'ノール': 'MALE',
  'リーン': 'FEMALE',
  'イネス': 'FEMALE',
  'デナ': 'FEMALE',
  'ロツェ': 'FEMALE',
  'アネット': 'FEMALE',
  '修司': 'MALE',
  'エルブラス': 'MALE',
};

export function detectGenderCues(jaText: string): 'FEMALE' | 'MALE' | null {
  if (!jaText) return null;

  let scoreFemale = 0;
  let scoreMale = 0;

  // 1. Check known characters
  for (const [name, gender] of Object.entries(KNOWN_CHARACTERS)) {
    if (jaText.includes(name)) {
      if (gender === 'FEMALE') scoreFemale += 3;
      else scoreMale += 3;
    }
  }

  // 2. Check pronouns & nouns
  for (const w of FEMALE_PRONOUNS) {
    if (jaText.includes(w)) scoreFemale += 2;
  }
  for (const w of FEMALE_NOUNS) {
    if (jaText.includes(w)) scoreFemale += 2;
  }
  for (const w of MALE_PRONOUNS) {
    if (jaText.includes(w)) scoreMale += 2;
  }
  for (const w of MALE_NOUNS) {
    if (jaText.includes(w)) scoreMale += 2;
  }

  // 3. Dialogue particle endings
  const dialogues = jaText.match(/[「『](.*?)[」』]/g) || [];
  for (const d of dialogues) {
    const clean = d.replace(/[「『」』!?！？…・。]/g, '').trim();
    for (const p of FEMALE_PARTICLES) {
      if (clean.endsWith(p)) scoreFemale += 1;
    }
    for (const p of MALE_PARTICLES) {
      if (clean.endsWith(p)) scoreMale += 1;
    }
  }

  if (scoreFemale > scoreMale) return 'FEMALE';
  if (scoreMale > scoreFemale) return 'MALE';
  return null;
}

export function correctPronounGender(jaText: string, enText: string): string {
  const gender = detectGenderCues(jaText);
  if (!gender || !enText) return enText;

  const hasExplicitMalePronoun = /彼(?!女)/.test(jaText);
  const hasExplicitFemalePronoun = jaText.includes('彼女');

  let text = enText;
  if (gender === 'FEMALE') {
    text = text.replace(/\bHe\b/g, 'She').replace(/\bhe\b/g, 'she');
    text = text.replace(/\bHimself\b/g, 'Herself').replace(/\bhimself\b/g, 'herself');
    if (!hasExplicitMalePronoun) {
      text = text.replace(/\bHis\b/g, 'Her').replace(/\bhis\b/g, 'her');
      text = text.replace(/\bHim\b/g, 'Her').replace(/\bhim\b/g, 'her');
    }
  } else if (gender === 'MALE') {
    text = text.replace(/\bShe\b/g, 'He').replace(/\bshe\b/g, 'he');
    text = text.replace(/\bHerself\b/g, 'Himself').replace(/\bherself\b/g, 'himself');
    if (!hasExplicitFemalePronoun) {
      text = text.replace(/\bHers\b/g, 'His').replace(/\bhers\b/g, 'his');
      text = text.replace(/\bHer\s+([a-zA-Z]+)/g, 'His $1').replace(/\bher\s+([a-zA-Z]+)/g, 'his $1');
      text = text.replace(/\bHer\b/g, 'Him').replace(/\bher\b/g, 'him');
    }
  }

  return text;
}

const DIALOGUE_CONTRACTIONS: [RegExp, string][] = [
  [/\b([Ii])\s+am\b/g, "$1'm"],
  [/\b([Yy]ou|[Ww]e|[Tt]hey)\s+are\b/g, "$1're"],
  [/\b([Hh]e|[Ss]he|[Ii]t|[Tt]here|[Ww]hat|[Ww]ho|[Tt]hat)\s+is\b/g, "$1's"],
  [/\b([Ii]|[Yy]ou|[Hh]e|[Ss]he|[Ww]e|[Tt]hey)\s+have\b/g, "$1've"],
  [/\b([Ii]|[Yy]ou|[Hh]e|[Ss]he|[Ww]e|[Tt]hey)\s+will\b/g, "$1'll"],
  [/\b([Ii]|[Yy]ou|[Hh]e|[Ss]he|[Ww]e|[Tt]hey)\s+would\b/g, "$1'd"],
  [/\b([Cc]an)not\b/g, "$1't"],
  [/\b([Dd]o|[Dd]oes|[Dd]id|[Ww]ould|[Cc]ould|[Ss]hould|[Hh]ave|[Hh]as|[Hh]ad|[Ii]s|[Aa]re|[Ww]as|[Ww]ere)\s+not\b/g, "$1n't"],
  [/\b([Ww]ill)\s+not\b/g, "won't"],
  [/\b([Ll]et)\s+us\b/g, "$1's"],
];

export function smoothDialogueContractions(text: string): string {
  if (!text.includes('"')) return text;
  return text.replace(/"([^"]+)"/g, (_, inner) => {
    let s = inner;
    for (const [pattern, repl] of DIALOGUE_CONTRACTIONS) {
      s = s.replace(pattern, repl);
    }
    return `"${s}"`;
  });
}

const LIGHT_NOVEL_IDIOMS: [RegExp, string][] = [
  [/\bmade a nodding motion\b/gi, 'nodded'],
  [/\bmade a nod\b/gi, 'nodded'],
  [/\bnodded (?:his|her|their) head\b/gi, 'nodded'],
  [/\blet out a sigh\b/gi, 'sighed'],
  [/\bheaved a sigh\b/gi, 'sighed'],
  [/\bbreathed a sigh\b/gi, 'sighed'],
  [/\blet out a deep sigh\b/gi, 'sighed deeply'],
  [/\blet out a breath of relief\b/gi, 'breathed a sigh of relief'],
  [/\bshowed a wry smile\b/gi, 'smiled wryly'],
  [/\bfloated a wry smile\b/gi, 'smiled wryly'],
  [/\bformed a wry smile\b/gi, 'smiled wryly'],
  [/\bshowed a bitter smile\b/gi, 'smiled bitterly'],
  [/\btilted his head in wonder\b/gi, 'tilted his head curiously'],
  [/\btilted her head in wonder\b/gi, 'tilted her head curiously'],
  [/\bopened his eyes wide\b/gi, 'widened his eyes'],
  [/\bopened her eyes wide\b/gi, 'widened her eyes'],
  [/\bfell into silence\b/gi, 'fell silent'],
  [/\bfell into a state of silence\b/gi, 'fell silent'],
  [/\bwas in a state of confusion\b/gi, 'was bewildered'],
  [/\bwas in a state of panic\b/gi, 'panicked'],
  [/\bwas in a state of surprise\b/gi, 'was taken aback'],
  [/\bThe voice of a girl could be heard\b/gi, "A girl's voice called out"],
  [/\bThe voice of a girl was heard\b/gi, "A girl's voice rang out"],
  [/\bThe voice of a boy was heard\b/gi, "A boy's voice rang out"],
  [/\bwith a trembling voice\b/gi, 'in a trembling voice'],
  [/\bspoke with a loud voice\b/gi, 'spoke loudly'],
  [/\bspoke in a small voice\b/gi, 'spoke softly'],
];

export function smoothLightNovelProse(text: string): string {
  let s = text;
  for (const [pattern, repl] of LIGHT_NOVEL_IDIOMS) {
    s = s.replace(pattern, repl);
  }
  return s;
}

export function polishTranslation(jaText: string, enText: string): string {
  const genderCorrected = correctPronounGender(jaText, enText);
  const contracted = smoothDialogueContractions(genderCorrected);
  return smoothLightNovelProse(contracted);
}

