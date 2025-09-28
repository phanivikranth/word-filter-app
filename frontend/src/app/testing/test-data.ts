import { WordStats, WordFilter, WordsByLength } from '../models/word.model';
import { BasicSearchResult, OxfordValidation, OxfordValidationResponse, AddWordResponse, Pronunciation } from '../services/word.service';

/**
 * Mock data for testing purposes
 */

export const MOCK_WORD_STATS: WordStats = {
  total_words: 416309,
  min_length: 2,
  max_length: 28,
  avg_length: 8.5
};

export const MOCK_WORDS_LIST = [
  'apple', 'application', 'appreciate', 'appropriate',
  'banana', 'band', 'bandana', 'basic', 'basketball',
  'cat', 'catch', 'catching', 'category', 'celebration',
  'dog', 'digital', 'development', 'data', 'dictionary',
  'elephant', 'engineering', 'example', 'excellent', 'education',
  'filter', 'function', 'fantastic', 'framework', 'frontend',
  'great', 'generate', 'general', 'government', 'graphics',
  'house', 'hello', 'health', 'history', 'homepage',
  'interactive', 'interesting', 'implementation', 'information', 'integration',
  'javascript', 'journey', 'judgment', 'junior', 'justice',
  'keyboard', 'knowledge', 'kitchen', 'kindness', 'kingdom',
  'learning', 'language', 'library', 'literature', 'lifestyle',
  'programming', 'python', 'project', 'performance', 'professional'
];

export const MOCK_WORDS_BY_LENGTH: WordsByLength = {
  length: 5,
  count: 12543,
  words: ['apple', 'grape', 'bench', 'chair', 'dance', 'earth', 'fiber', 'ghost', 'heart', 'index']
};

export const MOCK_PRONUNCIATIONS: Pronunciation[] = [
  {
    prefix: 'BrE',
    ipa: '/ɪɡˈzɑːmpl/',
    url: 'https://audio.oxforddictionaries.com/example_uk.mp3'
  },
  {
    prefix: 'NAmE',
    ipa: '/ɪɡˈzæmpl/',
    url: 'https://audio.oxforddictionaries.com/example_us.mp3'
  }
];

export const MOCK_OXFORD_VALIDATION: OxfordValidation = {
  word: 'example',
  is_valid: true,
  definitions: [
    'A thing characteristic of its kind or illustrating a general rule.',
    'A person or thing regarded in terms of their fitness to be imitated.'
  ],
  word_forms: ['example', 'examples', 'exemplary'],
  pronunciations: MOCK_PRONUNCIATIONS,
  examples: [
    'This is a good example of modern architecture.',
    'She followed her sister\'s example and became a doctor.'
  ],
  reason: 'Word found in Oxford Dictionary'
};

export const MOCK_BASIC_SEARCH_RESULT: BasicSearchResult = {
  word: 'example',
  inCollection: true,
  oxford: MOCK_OXFORD_VALIDATION
};

export const MOCK_BASIC_SEARCH_RESULT_NOT_IN_COLLECTION: BasicSearchResult = {
  word: 'uncommon',
  inCollection: false,
  oxford: {
    ...MOCK_OXFORD_VALIDATION,
    word: 'uncommon',
    definitions: ['Not occurring very often.'],
    examples: ['Such attitudes are uncommon among teenagers.']
  }
};

export const MOCK_BASIC_SEARCH_RESULT_NO_OXFORD: BasicSearchResult = {
  word: 'localword',
  inCollection: true,
  oxford: null
};

export const MOCK_OXFORD_VALIDATION_RESPONSE: OxfordValidationResponse = {
  success: true,
  word: 'example',
  oxford_validation: MOCK_OXFORD_VALIDATION,
  message: 'Word validated successfully'
};

export const MOCK_OXFORD_VALIDATION_RESPONSE_INVALID: OxfordValidationResponse = {
  success: false,
  word: 'invalidword',
  oxford_validation: {
    word: 'invalidword',
    is_valid: false,
    definitions: [],
    word_forms: [],
    pronunciations: [],
    examples: [],
    reason: 'Word not found in Oxford Dictionary'
  },
  message: 'Word not found'
};

export const MOCK_ADD_WORD_RESPONSE_SUCCESS: AddWordResponse = {
  success: true,
  word: 'newword',
  was_new: true,
  oxford_validation: MOCK_OXFORD_VALIDATION,
  message: 'Word added successfully',
  total_words: 416310
};

export const MOCK_ADD_WORD_RESPONSE_EXISTS: AddWordResponse = {
  success: true,
  word: 'existing',
  was_new: false,
  oxford_validation: MOCK_OXFORD_VALIDATION,
  message: 'Word already exists in collection',
  total_words: 416309
};

export const MOCK_ADD_WORD_RESPONSE_FAILURE: AddWordResponse = {
  success: false,
  word: 'invalidword',
  was_new: false,
  message: 'Word is not valid according to Oxford Dictionary'
};

export const MOCK_INTERACTIVE_WORDS = ['apple', 'ample', 'angle'];

export const MOCK_WORD_FILTERS: { [key: string]: WordFilter } = {
  empty: {},
  contains: { contains: 'app', limit: 100 },
  starts_with: { starts_with: 'pro', limit: 50 },
  ends_with: { ends_with: 'ing', limit: 75 },
  length_range: { min_length: 5, max_length: 10, limit: 200 },
  exact_length: { exact_length: 7, limit: 150 },
  complex: {
    contains: 'tion',
    starts_with: 'edu',
    min_length: 8,
    max_length: 15,
    limit: 25
  }
};

/**
 * Helper functions for creating test data
 */

export function createMockBasicSearchResult(overrides: Partial<BasicSearchResult> = {}): BasicSearchResult {
  return {
    ...MOCK_BASIC_SEARCH_RESULT,
    ...overrides
  };
}

export function createMockOxfordValidation(overrides: Partial<OxfordValidation> = {}): OxfordValidation {
  return {
    ...MOCK_OXFORD_VALIDATION,
    ...overrides
  };
}

export function createMockWordStats(overrides: Partial<WordStats> = {}): WordStats {
  return {
    ...MOCK_WORD_STATS,
    ...overrides
  };
}

export function createMockWordsByLength(overrides: Partial<WordsByLength> = {}): WordsByLength {
  return {
    ...MOCK_WORDS_BY_LENGTH,
    ...overrides
  };
}

export function createMockAddWordResponse(overrides: Partial<AddWordResponse> = {}): AddWordResponse {
  return {
    ...MOCK_ADD_WORD_RESPONSE_SUCCESS,
    ...overrides
  };
}

/**
 * Test scenarios for different use cases
 */

export const TEST_SCENARIOS = {
  // Basic search scenarios
  BASIC_SEARCH: {
    VALID_WORD_IN_COLLECTION: {
      input: 'example',
      expected: MOCK_BASIC_SEARCH_RESULT
    },
    VALID_WORD_NOT_IN_COLLECTION: {
      input: 'uncommon',
      expected: MOCK_BASIC_SEARCH_RESULT_NOT_IN_COLLECTION
    },
    WORD_WITHOUT_OXFORD: {
      input: 'localword',
      expected: MOCK_BASIC_SEARCH_RESULT_NO_OXFORD
    }
  },

  // Interactive search scenarios
  INTERACTIVE_SEARCH: {
    SIMPLE_PATTERN: {
      length: 5,
      pattern: 'a??le',
      expected: ['apple', 'angle']
    },
    COMPLEX_PATTERN: {
      length: 7,
      pattern: 'p?og??m',
      expected: ['program']
    },
    NO_MATCHES: {
      length: 4,
      pattern: 'zxqw',
      expected: []
    }
  },

  // Filter scenarios
  FILTERS: {
    SINGLE_CONTAINS: {
      filter: { contains: 'ing' },
      expected: ['programming', 'interesting', 'engineering']
    },
    LENGTH_RANGE: {
      filter: { min_length: 8, max_length: 12 },
      expected: ['programming', 'javascript', 'education']
    },
    COMPLEX_FILTER: {
      filter: { contains: 'pro', starts_with: 'p', min_length: 7 },
      expected: ['programming', 'professional', 'project']
    }
  }
};

/**
 * Error scenarios for testing error handling
 */

export const ERROR_SCENARIOS = {
  NETWORK_ERROR: new Error('Network connection failed'),
  TIMEOUT_ERROR: new Error('Request timeout'),
  SERVER_ERROR: { status: 500, message: 'Internal server error' },
  NOT_FOUND_ERROR: { status: 404, message: 'Endpoint not found' },
  BAD_REQUEST_ERROR: { status: 400, message: 'Invalid request' },
  OXFORD_API_ERROR: { status: 503, message: 'Oxford Dictionary API unavailable' }
};

/**
 * Mock HTML events for testing
 */

export function createMockInputEvent(value: string): any {
  return {
    target: { value: value }
  };
}

export function createMockKeyboardEvent(key: string, keyCode?: number): KeyboardEvent {
  return new KeyboardEvent('keydown', {
    key: key,
    keyCode: keyCode,
    bubbles: true
  });
}

/**
 * Validation helpers
 */

export const VALIDATION_PATTERNS = {
  LETTERS_ONLY: /^[a-zA-Z]+$/,
  ALPHANUMERIC: /^[a-zA-Z0-9]+$/,
  WORD_PATTERN: /^\w+$/
};

export function isValidWord(word: string): boolean {
  return VALIDATION_PATTERNS.LETTERS_ONLY.test(word.trim());
}

export function createWordList(count: number, prefix: string = 'word'): string[] {
  return Array.from({ length: count }, (_, i) => `${prefix}${i + 1}`);
}

export function generateRandomPattern(length: number, fillRatio: number = 0.3): string[] {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz';
  const pattern = new Array(length).fill('');
  const fillPositions = Math.floor(length * fillRatio);
  
  const positions = new Set<number>();
  while (positions.size < fillPositions) {
    positions.add(Math.floor(Math.random() * length));
  }
  
  positions.forEach(pos => {
    pattern[pos] = alphabet[Math.floor(Math.random() * alphabet.length)];
  });
  
  return pattern;
}

