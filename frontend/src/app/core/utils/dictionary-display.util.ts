import { OxfordValidation } from '../../services/word.service';

export function getValidationSourceLabel(source?: string): string {
  const labels: Record<string, string> = {
    nhost: 'Cached',
    merriam_webster: 'Merriam-Webster',
    oxford_dictionaries_api: 'Oxford API',
    dictionary_api_dev: 'Dictionary API',
    freedictionary_api_com: 'Free Dictionary API',
    words_api_rapidapi: 'Words API',
    word_game_db: 'Word Game DB',
    datamuse: 'DataMuse',
    oxford_web: 'Oxford Learner\'s',
    freedictionary: 'TheFreeDictionary',
    freedictionary_encyclopedia: 'TheFreeDictionary',
    skipped: 'Validation skipped',
    none: 'No source',
  };
  return labels[source || ''] || (source ? source.replace(/_/g, ' ') : '');
}

export function hasWordOrigin(oxford?: OxfordValidation | null): boolean {
  if (!oxford) {
    return false;
  }
  return Boolean(
    oxford.etymology?.trim()
    || oxford.origin_language?.trim()
    || oxford.first_known_use?.trim()
  );
}

export function getDictionaryLinks(oxford?: OxfordValidation | null): { key: string; url: string }[] {
  if (!oxford) {
    return [];
  }
  const links: { key: string; url: string }[] = [];
  const seen = new Set<string>();
  const add = (key: string, url?: string) => {
    const value = (url || '').trim();
    if (!value || seen.has(value)) {
      return;
    }
    seen.add(value);
    links.push({ key, url: value });
  };

  if (oxford.links) {
    for (const [key, url] of Object.entries(oxford.links)) {
      add(key, url);
    }
  }
  add('dictionary', oxford.dictionary_url);
  add('encyclopedia', oxford.encyclopedia_url);
  return links;
}

export function hasDictionaryContent(oxford?: OxfordValidation | null): boolean {
  if (!oxford) {
    return false;
  }
  return Boolean(
    oxford.definitions?.length
    || oxford.synonyms?.length
    || oxford.antonyms?.length
    || oxford.rhymes?.length
    || oxford.frequency != null
    || oxford.pronunciations?.length
    || oxford.examples?.length
    || hasWordOrigin(oxford)
    || getDictionaryLinks(oxford).length
  );
}

export function showSummary(oxford?: OxfordValidation | null): boolean {
  if (!oxford?.summary?.trim()) {
    return false;
  }
  const summary = oxford.summary.trim();
  const firstDef = oxford.definitions?.[0]?.trim();
  return !firstDef || summary.toLowerCase() !== firstDef.toLowerCase();
}

export function speakWord(word: string): void {
  if (!word || typeof window === 'undefined' || !window.speechSynthesis) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(word);
  utterance.lang = 'en-US';
  utterance.rate = 0.9;
  window.speechSynthesis.speak(utterance);
}

export function playPronunciation(audioUrl: string | undefined, word: string | undefined): void {
  if (audioUrl) {
    const audio = new Audio(audioUrl);
    audio.play().catch(() => {
      if (word) {
        speakWord(word);
      }
    });
    return;
  }
  if (word) {
    speakWord(word);
  }
}
