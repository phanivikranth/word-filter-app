"""Add vm. prefix to TerseAppFacade fields missed by first pass."""
import re
from pathlib import Path

FEATURES = Path(__file__).resolve().parents[1] / "src" / "app" / "features"

PROPS = [
    "searchResult", "searchWord", "searchError", "isSearching", "quickSuggestions",
    "safeExploreLoading", "safeExploreError", "dailyScrambleLetters", "dailyScrambleHint",
    "dailyScrambleWord", "dailyScrambleLoading", "dailyScrambleError", "puzzleGuess",
    "puzzleChecked", "puzzleSuccess", "dailyWordChallenge", "dailyWordChallengeLoading",
    "dailyWordChallengeError", "wordleActive", "anagramActive", "wordleGrid", "wordleStatus",
    "wordleKeyboard", "wordleError", "wordleWord", "anagramTargetLetters", "anagramUserWords",
    "anagramWordInput", "anagramError", "anagramScore", "anagramValidSolutions",
    "performanceStats", "oxfordStats", "prometheusMetrics", "edgeLogs", "telemetryLoading",
    "telemetryError", "storageInfo", "cleanupSummary", "isAdminProcessing", "newWordText",
    "wordToRemoveText", "bulkWordsText", "skipOxfordValidation", "loading", "error", "words",
    "advancedFilterSource", "advancedFilterMode", "puzzleLength", "letterBoxes",
    "interactiveWords", "interactiveLoading", "interactiveError", "puzzleRegex", "puzzleAnagram",
    "puzzleAnagramExact", "puzzleMeansLike", "puzzleSoundsLike", "puzzleSpelledLike",
    "profileName", "activeTheme", "activeFont", "isClaymorphic", "fontOptions", "filterForm",
]

LET_VARS = {
    "letter", "word", "item", "sugg", "syn", "ant", "rhyme", "def", "ex", "pron", "link",
    "row", "cell", "char", "w", "key", "form", "opt", "log", "i", "index", "rIdx", "_",
}


def patch(text: str) -> str:
    text = text.replace("getDictionaryLinks(", "vm.getDictionaryLinks(")
    text = text.replace("vm.vm.", "vm.")
    for prop in sorted(PROPS, key=len, reverse=True):
        # let x of prop
        text = re.sub(
            rf"\bof {prop}\b",
            f"of vm.{prop}",
            text,
        )
        text = re.sub(
            rf"\(click\)=\"{prop}\.",
            f'(click)="vm.{prop}.',
            text,
        )
        # ngClass and other bindings - prop. or prop? or prop ===
        text = re.sub(
            rf"(?<![\w.]){prop}(?=\.|!|\?|\s*===|\s*\|\||\s*&&|\s*\))",
            f"vm.{prop}",
            text,
        )
        # !prop in ngIf
        text = re.sub(rf"!{re.escape(prop)}\b", f"!vm.{prop}", text)
    # fix double vm
    text = text.replace("vm.vm.", "vm.")
    # restore let loop vars wrongly prefixed
    for v in LET_VARS:
        text = re.sub(rf"vm\.{v}\b", v, text)
    text = re.sub(r"\{\{\s*vm\.(letter|word|item|char|key)\s*\}\}", r"{{ \1 }}", text)
    return text


def main() -> None:
    for path in FEATURES.glob("*/*.component.html"):
        path.write_text(patch(path.read_text(encoding="utf-8")), encoding="utf-8")
        print("patched", path.name)


if __name__ == "__main__":
    main()
