# Terse Word Filter App — UI/UX Sitemap & Functionality Spec

> **Purpose:** Planning document for navigation redesign, page splits, and feature updates.  
> **Last audited:** 2026-07-27 (post-modularization on `refactor/modularize`)  
> **Source of truth:** `frontend/src/app/layout/app-shell/`, `frontend/src/app/features/*`, `frontend/src/app/core/facades/terse-app.facade.ts`, `frontend/src/app/app.routes.ts`, `backend/api/`

### Implementation status (modular layout)

| Layer | Location |
|-------|----------|
| Routes | `/word-check`, `/filters`, `/puzzles`, `/games`, `/admin`, `/performance`, `/profile` — see `app.routes.ts` |
| Shell (nav + sidebar) | `layout/app-shell/` |
| Feature pages | `features/<name>/` |
| Shared UI state / actions | `core/facades/terse-app.facade.ts` (to be split into smaller services) |
| HTTP clients | `services/word.service.ts` + `core/api/*.api.ts` delegates |
| Backend entry | `main.py` → `api/app.py` + `api/routers/*` |

Legacy monolith templates: `app.component.html` (unused; safe to delete in follow-up).

---

## Table of Contents

1. [App Overview](#1-app-overview)
2. [Information Architecture](#2-information-architecture)
3. [Global Shell (Always Visible)](#3-global-shell-always-visible)
4. [View 1 — Word Check](#4-view-1--word-check-searchmode-basic)
5. [View 2 — Filters](#5-view-2--filters-searchmode-advanced)
6. [View 3 — Puzzles](#6-view-3--puzzles-searchmode-puzzle)
7. [View 4 — Games Zone](#7-view-4--games-zone-searchmode-games)
8. [View 5 — Admin Control](#8-view-5--admin-control-searchmode-admin)
9. [View 6 — Performance](#9-view-6--performance-searchmode-performance)
10. [View 7 — Profile](#10-view-7--profile-searchmode-profile)
11. [Persistent Right Sidebar](#11-persistent-right-sidebar)
12. [User Flows](#12-user-flows)
13. [API Dependency Map](#13-api-dependency-map)
14. [LocalStorage Keys](#14-localstorage-keys)
15. [Global Notifications & Cross-Cutting Behavior](#15-global-notifications--cross-cutting-behavior)
16. [Known Gaps & Redesign Notes](#16-known-gaps--redesign-notes)
17. [Suggested Future Route Structure](#17-suggested-future-route-structure)

---

## 1. App Overview

| Property | Value |
|----------|-------|
| **Product name** | Terse |
| **App type** | Single-page application (SPA) |
| **Framework** | Angular (module-based: `app.module.ts`) |
| **Routing** | **None** — all views toggled via `searchMode` state in `AppComponent` |
| **Layout** | 2-column grid on desktop (main 2/3 + sidebar 1/3); stacked on mobile |
| **Backend API (dev)** | `http://localhost:8000` (`environment.apiUrl`) |
| **Design system** | Tailwind + Material Symbols + claymorphism cards (`clay-card`, `clay-input`, `clay-primary`) |
| **Theme** | Light default; dark mode via `html.dark` class |

---

## 2. Information Architecture

```
Terse (Home / Logo)
│
├── Global Shell
│   ├── Top Navbar (desktop, lg+)
│   ├── Mobile Tab Bar (below navbar, < lg)
│   ├── Dark Mode Toggle
│   └── Floating decorative icons (visual only)
│
├── Main Content (left column, lg:col-span-2)
│   ├── Word Check          searchMode = basic
│   ├── Filters             searchMode = advanced
│   ├── Puzzles             searchMode = puzzle
│   ├── Games Zone          searchMode = games
│   ├── Admin Control       searchMode = admin
│   ├── Performance         searchMode = performance
│   └── Profile             searchMode = profile
│
└── Persistent Sidebar (right column, lg:col-span-1)
    ├── Quick Tips
    ├── Daily Safe Word
    └── Parental Safety Advice
```

### Navigation state variable

```typescript
searchMode: 'basic' | 'advanced' | 'puzzle' | 'games' | 'admin' | 'performance' | 'profile'
```

Default on load: `'basic'`

### Tab enter side effects (`setSearchMode`)

| Mode | Side effect on tab enter |
|------|--------------------------|
| `basic` | None |
| `advanced` | Auto-runs `searchWords()` (loads ~100 browse results if no filters) |
| `puzzle` | None |
| `games` | Auto-starts Wordle if neither Wordle nor Anagram is active |
| `admin` | Calls `loadAdminData()` → fetches storage info |
| `performance` | Calls `loadTelemetryData()` → metrics + Prometheus |
| `profile` | None |

---

## 3. Global Shell (Always Visible)

### 3.1 Decorative Background Elements

| Element | Location | Functionality |
|---------|----------|---------------|
| Cloud icon | Top-left area | Decorative only |
| Star icon | Top-right area | Decorative only |
| Eco icon | Bottom-left area | Decorative only |
| Cruelty-free icon | Mid-right area | Decorative only |
| Ambient blur circles | Main content background | Decorative only |

---

### 3.2 Top Navbar

| Box / Element | Type | Interaction | Functionality |
|---------------|------|-------------|---------------|
| **Logo (shield + "Terse")** | Brand link | Click | `setSearchMode('basic')` — returns to Word Check |
| **Word Check** | Nav tab | Click | `setSearchMode('basic')` |
| **Filters** | Nav tab | Click | `setSearchMode('advanced')` + auto-query |
| **Puzzles** | Nav tab | Click | `setSearchMode('puzzle')` |
| **Games Zone** | Nav tab | Click | `setSearchMode('games')` + auto-start Wordle |
| **Admin Control** | Nav tab | Click | `setSearchMode('admin')` + load storage info |
| **Performance** | Nav tab | Click | `setSearchMode('performance')` + load telemetry |
| **Profile** | Nav tab | Click | `setSearchMode('profile')` |
| **Dark Mode Toggle** | Icon button | Click | `toggleTheme()` — toggles light/dark, persists to `localStorage.theme` |

**Visibility:** Desktop nav hidden below `lg` breakpoint; mobile tab bar shown instead.

---

### 3.3 Mobile Tab Bar

Same 7 tabs as desktop with shorter labels:

| Label | Maps to `searchMode` |
|-------|----------------------|
| Word Check | `basic` |
| Filters | `advanced` |
| Puzzles | `puzzle` |
| Games | `games` |
| Admin | `admin` |
| Performance | `performance` |
| Profile | `profile` |

**Behavior:** Active tab highlighted with `bg-primary text-on-primary`. Same side effects as desktop on tab switch.

---

## 4. View 1 — Word Check (`searchMode === 'basic'`)

**Purpose:** Primary dictionary lookup, safety validation, daily engagement widgets, and word discovery.

---

### 4.1 Search Hero

| Box | Type | Interaction | Functionality |
|-----|------|-------------|---------------|
| Search icon | Visual | — | Decorative prefix in input |
| **Search input** | Text field | Type, Enter | Binds `searchWord`; `(input)` clears prior result/errors via `onSearchInput()`; Enter triggers `searchWordBasic()` |
| **Check Word** button | Primary CTA | Click | `searchWordBasic()` — disabled while `isSearching` |
| Loading spinner (button) | State | — | Shown on button during search |

**Validation rules:**
- Empty input → error: "Please enter a word to search."
- Non-alphabetic characters → error: "Word must contain only letters."

**API flow:** `WordService.searchBasicWord()` → checks collection + validates via backend.

---

### 4.2 Search Loading State

| Box | Shown when | Content |
|-----|------------|---------|
| Loading panel | `isSearching === true` | Spinner + "Analyzing word safety and definitions..." |

---

### 4.3 Search Error State

| Box | Shown when | Content |
|-----|------------|---------|
| Error banner | `searchError` is set | Red error container with message |

---

### 4.4 Word Analysis Result Panel

**Shown when:** `searchResult && !isSearching`

#### Header row

| Box | Functionality |
|-----|---------------|
| Status badge circle | Green (verified) if `oxford.is_valid` or `inCollection`; red (cancel) otherwise |
| **Word title** | Titlecase display of `searchResult.word` |
| **Pronunciation button** | Shown if pronunciations exist; `playPronunciation(url, word)` — audio URL or Web Speech fallback |
| **Word form chips** | Up to 4 parts of speech from `oxford.word_forms` |
| **"In Dictionary File" badge** | Shown if word exists in local collection |
| **Validation source badge** | Label from `getValidationSourceLabel(validation_source)` |
| **Safety Status** | "100% Safe" or "Unverified" |

#### Empty dictionary state

| Box | Shown when | Content |
|-----|------------|---------|
| No entry panel | No dictionary content AND not in collection | Prompt to try another spelling |

#### Content sections (conditional)

| Section | Data source | Interaction |
|---------|-------------|-------------|
| **Summary lead** | `oxford.summary` | Read-only |
| **Source note** | `oxford.reason` | Read-only info banner |
| **Definitions** | `oxford.definitions[]` | Numbered list |
| **Example sentences** | `oxford.examples[]` | Italic quotes |
| **Synonyms** | `oxford.synonyms[]` | Click chip → `exploreWord(syn)` |
| **Antonyms** | `oxford.antonyms[]` | Click chip → `exploreWord(ant)` |
| **Rhymes** | `oxford.rhymes[]` | Click chip → `exploreWord(rhyme)` |
| **Word frequency** | `oxford.frequency` | Read-only (Words API score) |
| **Pronunciation list** | `oxford.pronunciations[]` | Per-variant play button |
| **Word origin** | `etymology`, `origin_language`, `first_known_use` | Read-only |
| **Reference links** | `getDictionaryLinks(oxford)` | External links open in new tab |

#### Footer action

| Box | Shown when | Interaction |
|-----|------------|-------------|
| **Add Word to Local Dictionary** | Valid word NOT in collection | `addWordToCollection(word)` → `POST /words/add` |

---

### 4.5 Safe Words to Explore

| Box | Functionality |
|-----|---------------|
| Section title | "Safe Words to Explore" |
| Loading text | `safeExploreLoading` |
| Error text | `safeExploreError` |
| **Word chips** | Icon + word; click → `exploreWord(word)` |

| Property | Detail |
|----------|--------|
| **API** | `GET /datamuse/daily-safe-explore` |
| **Count** | 10 eight-letter words |
| **Cache** | Daily in localStorage (`dailySafeExploreDate`, `dailySafeExploreWords`) |
| **Icons** | Index-based rotation from fixed icon list (not semantic per word) |
| **Fallback** | Static 10-word list if API fails |

---

### 4.6 Word Fact of the Day

| Box | Functionality |
|-----|---------------|
| Static fact card | Hardcoded: *"set" has 430+ definitions* |

> **Note:** Not API-driven. Candidate for removal or wiring to a facts endpoint.

---

### 4.7 Word Puzzle of the Day (Daily Scramble)

| Box | Functionality |
|-----|---------------|
| Title + description | "Word Puzzle of the Day" |
| Loading / error states | `dailyScrambleLoading`, `dailyScrambleError` |
| **Scrambled letter tiles** | From `dailyScrambleLetters[]` |
| **Hint** | `dailyScrambleHint` |
| **Guess input** | Binds `puzzleGuess`; Enter → `checkPuzzleGuess()` |
| **Check button** | `checkPuzzleGuess()` — client-side compare to `dailyScrambleWord` |
| **Result message** | Success/fail after `puzzleChecked` |

| Property | Detail |
|----------|--------|
| **API** | `GET /puzzle/daily-scramble` |
| **Cache** | Daily in localStorage (`dailyScrambleDate`, `dailyScrambleWord`, `dailyScrambleScrambled`, `dailyScrambleHint`) |

---

### 4.8 Word Challenge (4 cards)

| Box per card | Functionality |
|--------------|---------------|
| Dynamic icon | From `pickWordIcon(word, definition)` |
| Word (uppercase) | Display |
| Definition | Italic quote |
| Card click | `exploreWord(item.word)` |
| Section badge | "Today's Quests" |
| Skeleton loading | 4 placeholder cards while loading |
| Error text | `dailyWordChallengeError` |

| Property | Detail |
|----------|--------|
| **API** | `GET /datamuse/daily-word-challenge` |
| **Count** | 4 education-topic words with definitions |
| **Cache** | Daily in localStorage (`dailyWordChallengeDate`, `dailyWordChallengeItems`) |
| **Fallback** | 4 static words if API fails |

---

## 5. View 2 — Filters (`searchMode === 'advanced'`)

**Purpose:** Query external word APIs by letter pattern and length constraints.

---

### 5.1 Header

| Box | Content |
|-----|---------|
| Title | "Advanced Word Query Filters" |
| Description | Explains Words API params: `letterPattern`, `letters`, `lettersMin`, `lettersMax` with Word Game DB fallback |

---

### 5.2 Filter Form (`filterForm` — reactive)

| Field | Form control | API mapping | Behavior |
|-------|--------------|-------------|----------|
| Contains Letters | `contains` | `letterPattern` (regex) | Auto-search on form `(change)` |
| Starts With | `starts_with` | `letterPattern` | Auto-search on change |
| Ends With | `ends_with` | `letterPattern` | Auto-search on change |
| Exact Length | `exact_length` | `letters` | Auto-search on change |
| Min Length | `min_length` | `lettersMin` | Auto-search on change |
| Max Length | `max_length` | `lettersMax` | Auto-search on change |
| Max Results Limit | `limit` | `limit` (max 100) | Default 100 |

| Button | Action |
|--------|--------|
| **Reset Filters** | `clearFilters()` — resets form, limit=100, re-queries |
| **Apply Query** | `searchWords()` |

---

### 5.3 Results Area

| Box | Functionality |
|-----|---------------|
| Count header | "Filtered Results (N found)" |
| Source badge | Words API / Word Game DB + optional "browse" mode label |
| Hint text | "Click word to copy" |
| **Word chips** | Click → `copyWordToClipboard(word)` |
| Empty state | "No words match your filters..." |
| Loading spinner | While `loading` |
| Error banner | `error` message |

| Property | Detail |
|----------|--------|
| **API** | `GET /words/advanced-filter` |
| **Browse mode** | When no filters set, returns ~100 diversified random words |
| **Filter mode** | When any filter field has a value |

---

## 6. View 3 — Puzzles (`searchMode === 'puzzle'`)

**Purpose:** Crossword, Scrabble, regex, anagram, and DataMuse-assisted word finding.

---

### 6.1 Header

| Box | Content |
|-----|---------|
| Title | "Advanced Puzzle Solver & Wildcards" |
| Wildcard legend | `?` any letter, `@` vowels, `#` consonants |

---

### 6.2 Position-Specific Pattern Grid

| Box | Functionality |
|-----|---------------|
| **Word Length** input | 2–15; `(change)` → `onPuzzleLengthChange()` resets letter boxes |
| **Letter boxes** | One char each; empty = `?` wildcard; `updateLetter(i, event)` |
| **Current Pattern** display | Live preview via `getCurrentPattern()` |

---

### 6.3 Additional Constraints

| Field | Binds to | Purpose |
|-------|----------|---------|
| Regular Expression Pattern | `puzzleRegex` | Full Python regex passed to backend |
| Anagram letters | `puzzleAnagram` | Letter pool for anagram matching |
| **Exact** checkbox | `puzzleAnagramExact` | Exact-length anagrams only |
| Means like (DataMuse) | `puzzleMeansLike` | Semantic similarity |
| Sounds like (DataMuse) | `puzzleSoundsLike` | Phonetic similarity |
| Spelled like (DataMuse) | `puzzleSpelledLike` | Spelling pattern with `?` |

---

### 6.4 Action Buttons

| Button | Functionality |
|--------|---------------|
| **Reset Puzzle** | `clearInteractive()` — clears all puzzle fields |
| **Randomize Grid** | `randomizePattern()` — fills random letters/wildcards |
| **Find Matches** | `findMatchingWords()` → `GET /words/puzzle` (limit 200) |

---

### 6.5 Results Area

| Box | Functionality |
|-----|---------------|
| Loading panel | While `interactiveLoading` |
| Error banner | `interactiveError` |
| **Matching Solutions** list | Click word → `copyWordToClipboard(word)` |
| Count header | "Matching Solutions (N found)" |

---

## 7. View 4 — Games Zone (`searchMode === 'games'`)

**Purpose:** Casual vocabulary games — Wordle clone and Anagram Builder.

---

### 7.1 Game Mode Selector

| Tab | Action |
|-----|--------|
| **Wordle** | `selectGameMode('wordle')` → `startWordleGame()` |
| **Anagrams** | `selectGameMode('anagram')` → `startAnagramGame()` |

**Default on tab enter:** Wordle auto-starts if no game is active.

---

### 7.2 Subgame: Wordle Challenge

| Box | Functionality |
|-----|---------------|
| Title + badge | "Wordle Challenge" — 5 letters |
| Rules text | Guess secret word in 6 attempts |
| Error banner | `wordleError` (invalid length, not in dictionary) |
| **6×5 grid** | Letter cells: empty / correct (green) / present (yellow) / absent (gray) |
| **Win/Lose panel** | Shows answer + **Play Again** when game ends |
| **On-screen keyboard** | QWERTY + ENTER + DEL; keys colored by guess history |
| Secret word source | `GET /words/random?length=5`; fallback `"HAPPY"` |

**Guess validation:** Must be 5 letters AND exist in local dictionary (`searchBasicWord` → `inCollection`).

**Scoring:** Standard Wordle letter-position logic (two-pass green/yellow).

---

### 7.3 Subgame: Anagram Explorer

| Box | Functionality |
|-----|---------------|
| Title + badge | "Anagram Explorer" — Scrabble mode |
| **Letter pool tiles** | Scrambled letters from random 7-letter word |
| **Word input** | Min 3 letters; Enter or Submit |
| **Submit button** | `submitAnagramWord()` |
| Error banner | `anagramError` |
| **Your Found Words** panel | List + score (`anagramScore`) |
| **Total Solutions** panel | Count of valid solutions; hidden list |
| **Next Letter Pool** button | `startAnagramGame()` — new random letters |

| Property | Detail |
|----------|--------|
| Letter source | `GET /words/random?length=7` |
| Solutions prefetch | `GET /words/puzzle?anagram=...&limit=100` |
| Scoring | 3 letters = 100pts, 4 = 200, 5 = 400, 6+ = 700 |
| Fallback pool | `"TEACHER"` with preset solutions |

---

## 8. View 5 — Admin Control (`searchMode === 'admin'`)

**Purpose:** Dictionary CRUD, bulk import, and maintenance operations.

---

### 8.1 Header

| Box | Content |
|-----|---------|
| Title | "Dictionary Management Dashboard" |
| Description | Admin console for database maintenance and wordlist imports |

---

### 8.2 Processing State

| Box | Shown when | Content |
|-----|------------|---------|
| Admin spinner | `isAdminProcessing` | "Processing admin instructions..." |

---

### 8.3 Storage Info Block

**Loaded on tab enter via `GET /storage/info`**

| Field | Source key |
|-------|------------|
| Storage Provider | `storageInfo.provider` |
| Connection Type | `storageInfo.type` |
| Region | `storageInfo.region` (fallback "Local") |
| Dictionary file | `storageInfo.key` (fallback "words.txt") |

---

### 8.4 Add Single Word

| Box | Functionality |
|-----|---------------|
| Text input | `newWordText` |
| **Skip Oxford validation** checkbox | `skipOxfordValidation` |
| **Add** button | `addNewWord()` → `POST /words/add` or validated add |

---

### 8.5 Remove Single Word

| Box | Functionality |
|-----|---------------|
| Text input | `wordToRemoveText` |
| **Delete** button | `deleteWord()` → `POST /words/remove` |

---

### 8.6 Bulk Import

| Box | Functionality |
|-----|---------------|
| Textarea | `bulkWordsText` — comma or newline separated |
| **Import Batch List** button | `uploadBulkWords()` → `POST /words/add-batch` |

---

### 8.7 System Maintenance

| Action | Button | API | Purpose |
|--------|--------|-----|---------|
| Reload dictionary cache | **Reload Dictionary** | `POST /words/reload` | Refresh in-memory word list from storage |
| Database sanitization | **Run Sanitization Sweep** | `POST /words/cleanup` | Remove invalid/duplicate words |

#### Sanitization Report (post-cleanup)

| Field | Source |
|-------|--------|
| Found invalid words | `cleanupSummary.found_invalid` |
| Permanently purged count | `cleanupSummary.removed_count` |
| Summary action | `cleanupSummary.action_taken` |

---

## 9. View 6 — Performance (`searchMode === 'performance'`)

**Purpose:** Backend telemetry, cache stats, simulated edge logs, Prometheus metrics.

---

### 9.1 Header

| Box | Content |
|-----|---------|
| Title | "Enterprise Edge Gateway & Metrics Dashboard" |
| Description | Live metrics, cache telemetry, Cloudflare Worker routing logs |

---

### 9.2 Loading & Error States

| Box | Shown when |
|-----|------------|
| Telemetry loading | `telemetryLoading && !performanceStats` |
| Connection error | `telemetryError` |

**Auto-refresh:** Stats reload every 10 seconds while on Performance tab.

---

### 9.3 Metrics Cards (when `performanceStats` loaded)

#### Dictionary Cache (`oxfordStats`)

| Metric | Field |
|--------|-------|
| Cache hits / misses | `oxfordStats.hits` / `oxfordStats.misses` |
| Cached items | `oxfordStats.cached_words` |

#### System Status

| Metric | Field |
|--------|-------|
| Words loaded | `performanceStats.words_loaded` |
| Thread pool workers | `performanceStats.thread_pool_workers` |
| Process pool workers | `performanceStats.process_pool_workers` |

#### Memory Usage

| Metric | Field |
|--------|-------|
| Words list size | `performanceStats.memory_usage.words_list_size` |
| Words set size | `performanceStats.memory_usage.words_set_size` |

#### Optimizations

| Box | Content |
|-----|---------|
| Feature checklist | `performanceStats.optimization_features[]` — green checkmarks |

---

### 9.4 Cloudflare Edge Worker Logs

| Box | Functionality |
|-----|---------------|
| Live indicator | Animated ping dot — "Live updates active" |
| **Log console** | `edgeLogs[]` — **simulated** entries, new entry every 4 seconds |
| Log fields | time, IP, method, path, status, action |

> **Note:** Logs are client-side simulated, not real Cloudflare data.

---

### 9.5 Prometheus Metrics

| Box | Functionality |
|-----|---------------|
| Raw `/metrics` stream | `prometheusMetrics` text block from backend |

---

### 9.6 Hidden / Loaded but Not Displayed

| Data | Loaded via | Displayed in UI? |
|------|------------|------------------|
| `wordStats` | `loadWordStats()` on app init | **No** — used only in Prometheus text generation |

---

## 10. View 7 — Profile (`searchMode === 'profile'`)

**Purpose:** Personalization — theme, font, display preferences.

---

### 10.1 Header

| Box | Content |
|-----|---------|
| Title | "User Profile & Theme Settings" |
| Description | Customize colors, display name, view local stats |

---

### 10.2 Profile Details

| Box | Functionality |
|-----|---------------|
| Avatar placeholder | Static account_circle icon |
| **Display Name** input | `#nameInput` bound to `profileName` |
| **Save** button | `saveProfileName(value)` → `localStorage.profileName` |

---

### 10.3 Customization Panel

#### Accent Theme (8 options)

| Theme | Action |
|-------|--------|
| Blue, Green, Indigo, Amber, Rose, Violet, Slate, Teal | `changeTheme(id)` → CSS vars + `localStorage.activeTheme` |

#### Display Font

| Option | Action |
|--------|--------|
| DM Sans, Lora | `changeFont(id)` → `localStorage.activeFont` |

#### Style Switches

| Switch | Action | Persistence |
|--------|--------|-------------|
| **Dark Theme Mode** | `toggleTheme()` | `localStorage.theme` |
| **Claymorphism Mode** | `toggleClaymorphic()` | `localStorage.isClaymorphic` — toggles `claymorphic` body class |

---

### 10.4 User Dashboard Statistics

| Stat card | Shows |
|-----------|-------|
| Active Theme | Current `activeTheme` (capitalized) |
| Preferred Mode | "Dark" or "Light" from `isDarkMode` |

---

## 11. Persistent Right Sidebar

**Visible on all tabs.** Stacks below main content on mobile.

| Box | Content | Interaction | Data source |
|-----|---------|-------------|-------------|
| **Quick Tips** | 2 static tips about slang and open discussion | Read-only | Hardcoded |
| **Daily Safe Word** | Word + definition | Read-only | `GET /words-api/random`; daily localStorage cache |
| **Parental Safety Advice** | Static paragraph about using tool with children | Read-only | Hardcoded |

### Daily Safe Word detail

| State | Display |
|-------|---------|
| Loading | "Loading today's word…" |
| Success | Word (titlecase) + definition |
| Error | `dailySafeWordError` message |

**Cache keys:** `dailySafeWordDate`, `dailySafeWord`, `dailySafeWordDefinition`

---

## 12. User Flows

### Flow A — Look up a word

```
Word Check → type word → Check Word
  → result panel (definitions, synonyms, etc.)
  → click synonym/rhyme/antonym → exploreWord() → new lookup
  → Add Word to Local Dictionary (if valid, not in file)
```

### Flow B — Daily content on app load

```
ngOnInit:
  → loadDailySafeWord()      (sidebar)
  → loadDailyScramble()      (Word Check)
  → loadDailySafeExplore()   (Safe Words chips)
  → loadDailyWordChallenge() (Word Challenge cards)
All cached per calendar day in localStorage.
```

### Flow C — Filter words by pattern

```
Filters tab (auto-query on enter)
  → enter constraints (auto-search on change)
  → results chips → click copies to clipboard
  → Reset Filters → clears and re-browses
```

### Flow D — Solve a crossword pattern

```
Puzzles tab → set word length → fill grid / regex / anagram / DataMuse fields
  → Find Matches → click result to copy
  → Randomize Grid or Reset Puzzle
```

### Flow E — Play Wordle

```
Games Zone (Wordle auto-starts)
  → type guesses via keyboard
  → win/lose panel → Play Again
```

### Flow F — Play Anagrams

```
Games Zone → Anagrams tab
  → build words from letter pool → Submit
  → score accumulates → Next Letter Pool
```

### Flow G — Admin maintenance

```
Admin Control → view storage info
  → add/remove single word OR bulk import
  → Reload Dictionary OR Run Sanitization Sweep
  → read sanitization report
```

### Flow H — Customize appearance

```
Profile → change theme / font / dark mode / claymorphism
  → settings persist in localStorage
  → User Dashboard Statistics reflects choices
```

---

## 13. API Dependency Map

| UI Feature | HTTP | Endpoint |
|------------|------|----------|
| Word Check lookup | POST + check | `/words/check`, `/words/validate` |
| Add word (result panel) | POST | `/words/add` |
| Advanced Filters | GET | `/words/advanced-filter` |
| Puzzle solver | GET | `/words/puzzle` |
| Daily scramble | GET | `/puzzle/daily-scramble` |
| Safe explore chips | GET | `/datamuse/daily-safe-explore` |
| Word challenge cards | GET | `/datamuse/daily-word-challenge` |
| Daily safe word (sidebar) | GET | `/words-api/random` |
| Wordle random word | GET | `/words/random?length=5` |
| Anagram random word | GET | `/words/random?length=7` |
| Anagram solutions | GET | `/words/puzzle?anagram=...` |
| Admin storage info | GET | `/storage/info` |
| Admin add word | POST | `/words/add` |
| Admin remove word | POST | `/words/remove` |
| Admin bulk import | POST | `/words/add-batch` |
| Admin reload | POST | `/words/reload` |
| Admin cleanup | POST | `/words/cleanup` |
| Performance stats | GET | `/performance/stats` |
| Oxford cache stats | GET | `/words/oxford-stats` |
| Word stats (background) | GET | `/words/stats` |
| Prometheus metrics | GET | `/metrics` (via telemetry loader) |

---

## 14. LocalStorage Keys

| Key | Purpose | Set by |
|-----|---------|--------|
| `theme` | `"dark"` or light (absent) | `toggleTheme()` |
| `activeTheme` | Accent color id (e.g. `blue`) | `changeTheme()` |
| `activeFont` | Font id (e.g. `dm-sans`) | `changeFont()` |
| `isClaymorphic` | `"true"` / absent | `toggleClaymorphic()` |
| `profileName` | Display name string | `saveProfileName()` |
| `dailySafeWordDate` | ISO date string | Daily safe word loader |
| `dailySafeWord` | Word string | Daily safe word loader |
| `dailySafeWordDefinition` | Definition string | Daily safe word loader |
| `dailyScrambleDate` | ISO date string | Daily scramble loader |
| `dailyScrambleWord` | Answer word | Daily scramble loader |
| `dailyScrambleScrambled` | Scrambled string | Daily scramble loader |
| `dailyScrambleHint` | Hint string | Daily scramble loader |
| `dailySafeExploreDate` | ISO date string | Safe explore loader |
| `dailySafeExploreWords` | JSON array of words | Safe explore loader |
| `dailyWordChallengeDate` | ISO date string | Word challenge loader |
| `dailyWordChallengeItems` | JSON array of `{word, definition}` | Word challenge loader |

---

## 15. Global Notifications & Cross-Cutting Behavior

| Behavior | Implementation |
|----------|----------------|
| Toast notifications | `showNotification(message, type)` via Angular Material `MatSnackBar` |
| Tab switch toast | Info notification: "Switched to {mode} panel" |
| Clipboard copy | `copyWordToClipboard(word)` — used in Filters and Puzzles results |
| Cross-word navigation | `exploreWord(word)` — sets `searchWord`, switches to `basic`, runs search |
| Pronunciation | `playPronunciation(url, word)` — HTML5 audio or Web Speech API |

---

## 16. Known Gaps & Redesign Notes

Use this section when editing the plan. Check items you want to address.

| # | Issue | Current state | Suggested change |
|---|-------|---------------|------------------|
| 1 | No URL routes | Tab state only — no deep links, no browser back | Add Angular Router with paths per view |
| 2 | Monolithic component | ~1475 lines HTML, ~1500 lines TS in one component | Split into feature modules/components |
| 3 | Word Fact of the Day | Hardcoded static text | Wire to API or remove |
| 4 | `wordStats` | Loaded on init, not shown in UI | Add stats widget to sidebar or Profile |
| 5 | Safe Explore icons | Index-based, not word-semantic | Use `pickWordIcon()` like Word Challenge |
| 6 | Mobile nav | 7 pills wrap on small screens | Bottom nav drawer or hamburger menu |
| 7 | Sidebar | Identical on all tabs | Contextual sidebar content per view |
| 8 | Parental tips | Static hardcoded | Rotating tips or CMS |
| 9 | Edge Worker logs | Simulated client-side | Connect to real logs or label as demo |
| 10 | Admin / Performance | No auth gate | Restrict to authenticated operators |
| 11 | Games auto-start | Wordle starts on every Games tab visit | Remember last game or show game picker |
| 12 | Filters auto-query | Fires on every form change | Debounce or require explicit Apply |

---

## 17. Suggested Future Route Structure

When splitting the monolith into real pages, consider:

```
/                         → Word Check (basic)
/filters                  → Advanced Filters
/puzzles                  → Puzzle Solver
/games                    → Games Zone (picker)
/games/wordle             → Wordle
/games/anagrams           → Anagram Builder
/admin                    → Admin Control (auth-gated)
/performance              → Metrics Dashboard (auth-gated)
/profile                  → User Settings
```

### Proposed navigation groups (for redesign)

| Group | Pages |
|-------|-------|
| **Discover** | Word Check, Safe Explore, Word Challenge, Daily Scramble |
| **Tools** | Filters, Puzzles |
| **Play** | Games Zone |
| **Manage** | Admin Control |
| **System** | Performance |
| **Account** | Profile |

---

## Appendix: Component File Map

| Concern | File |
|---------|------|
| All UI templates | `frontend/src/app/app.component.html` |
| All view logic & state | `frontend/src/app/app.component.ts` |
| API client | `frontend/src/app/services/word.service.ts` |
| Word icon utility | `frontend/src/app/core/utils/word-icon.util.ts` |
| Models | `frontend/src/app/models/word.model.ts` |
| Styles | `frontend/src/app/app.component.css`, `frontend/src/styles.css` |
| Environment | `frontend/src/environments/environment.ts` |

---

*Edit this document freely, then feed it to your implementation plan. When ready to refactor, switch sections 16–17 into actionable tickets.*
