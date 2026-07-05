/**
 * Pick a Material Symbol icon based on word + definition semantics.
 */
const ICON_RULES: { pattern: RegExp; icon: string }[] = [
  { pattern: /light|bright|shine|lumin|glow|radiant|illum/, icon: 'emoji_objects' },
  { pattern: /learn|teach|school|study|education|academic|professor|tuition/, icon: 'school' },
  { pattern: /book|read|literature|story|library|lexicon|vocab/, icon: 'auto_stories' },
  { pattern: /mind|think|psych|emotion|feel|poignant|profound|sentiment/, icon: 'psychology' },
  { pattern: /time|brief|short|ephemer|moment|temporal/, icon: 'hourglass_empty' },
  { pattern: /strong|resilient|endur|withstand|force|power|robust/, icon: 'fitness_center' },
  { pattern: /love|kind|friend|amic|affinit|altru|compassion|empath/, icon: 'favorite' },
  { pattern: /nature|earth|green|plant|organic|ecolog/, icon: 'park' },
  { pattern: /science|paradigm|theory|logic|reason|research|experiment/, icon: 'science' },
  { pattern: /art|creat|beaut|aesthetic|design|paint/, icon: 'palette' },
  { pattern: /music|sound|rhythm|melod|harmon/, icon: 'music_note' },
  { pattern: /growth|develop|evolv|progress|advance/, icon: 'trending_up' },
  { pattern: /help|aid|assist|support|care|serve/, icon: 'volunteer_activism' },
  { pattern: /war|conflict|fight|courage|shield|defend|brave/, icon: 'shield' },
  { pattern: /money|econom|finance|wealth|profit|market/, icon: 'payments' },
  { pattern: /space|star|cosmos|universe|planet|orbit/, icon: 'rocket_launch' },
  { pattern: /write|speech|word|language|grammar|eloqu/, icon: 'edit_note' },
  { pattern: /law|justice|legal|right|moral|ethic/, icon: 'gavel' },
  { pattern: /health|heal|medical|body|vital/, icon: 'health_and_safety' },
  { pattern: /water|ocean|river|rain|flow/, icon: 'water_drop' },
];

const FALLBACK_ICONS = [
  'auto_stories',
  'emoji_objects',
  'school',
  'local_library',
  'psychology',
  'lightbulb',
  'menu_book',
  'workspace_premium',
  'explore',
  'diamond',
];

export function pickWordIcon(word: string, definition = ''): string {
  const text = `${word} ${definition}`.toLowerCase();
  for (const rule of ICON_RULES) {
    if (rule.pattern.test(text)) {
      return rule.icon;
    }
  }
  let hash = 0;
  const key = word.toLowerCase();
  for (let i = 0; i < key.length; i++) {
    hash = (hash + key.charCodeAt(i) * (i + 1)) % 9973;
  }
  return FALLBACK_ICONS[hash % FALLBACK_ICONS.length];
}

export function withWordIcons<T extends { word: string; definition?: string }>(
  items: T[]
): (T & { icon: string })[] {
  return items.map((item) => ({
    ...item,
    icon: pickWordIcon(item.word, item.definition || ''),
  }));
}
