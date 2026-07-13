from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, ID, TEXT, KEYWORD
from whoosh.qparser import QueryParser, PrefixPlugin
import os
from pathlib import Path

from core.tools.common.app_paths import AppPaths

class SnippetSearchEngine:
    """
    מנוע חיפוש המבוסס על Whoosh לניהול וחיפוש שליפים.
    אחראי על יצירה, עדכון ושאילתות באינדקס החיפוש.
    """
    def __init__(self, index_dir: Path = AppPaths.SEARCH_INDEX_DIR):
        """
        מאתחל את מנוע החיפוש.
        :param index_dir: הנתיב לתיקיית האינדקס של Whoosh.
        """
        self.index_dir = index_dir
        self.schema = Schema(
            id=ID(stored=True, unique=True), # מזהה ייחודי לשליף, נשמר
            title=TEXT(stored=True),        # כותרת השליף, נשמר וניתן לחיפוש
            tags=KEYWORD(stored=True, commas=True), # תגים, נשמר וניתן לחיפוש (מופרדים בפסיקים)
            content_file=ID(stored=True)    # נתיב לקובץ התוכן, נשמר
        )
        self.ix = self._get_or_create_index()
        # מנתח שאילתות שיחפש כברירת מחדל בשדה 'tags'
        self.query_parser = QueryParser("tags", schema=self.schema)
        self.query_parser.add_plugin(PrefixPlugin())

    def _get_or_create_index(self):
        """
        פותח אינדקס קיים או יוצר אינדקס חדש אם התיקייה אינה קיימת או האינדקס פגום.
        """
        if not self.index_dir.exists():
            os.makedirs(self.index_dir)
            return create_in(self.index_dir, self.schema)
        else:
            try:
                return open_dir(self.index_dir)
            except Exception as e:
                # אם האינדקס פגום או הסכמה השתנתה, ניצור מחדש
                print(f"Error opening Whoosh index: {e}. Recreating index.")
                return create_in(self.index_dir, self.schema)

    def build_index(self, snippets_metadata: list[dict]):
        """
        בונה או בונה מחדש את אינדקס Whoosh מרשימת מטא-נתונים של שליפים.
        כל מילון snippet_meta צריך להכיל 'id', 'title', 'tags', 'content_file'.
        """
        writer = self.ix.writer()
        for snippet_meta in snippets_metadata:
            # ודא שכל השדות הנדרשים קיימים והמר ל-string במידת הצורך
            snippet_id = str(snippet_meta.get("id"))
            title = str(snippet_meta.get("title", ""))
            # נניח ש-tags מגיע כרשימה, נמיר למחרוזת מופרדת בפסיקים
            tags = ",".join(snippet_meta.get("tags", []))
            content_file = str(snippet_meta.get("content_file", ""))

            if snippet_id: # הוסף רק אם יש ID
                writer.add_document(
                    id=snippet_id,
                    title=title,
                    tags=tags,
                    content_file=content_file
                )
        writer.commit()

    def search(self, query_string: str) -> list[dict]:
        """
        מחפש באינדקס שליפים התואמים למחרוזת השאילתה.
        :param query_string: מחרוזת החיפוש (לדוגמה, תגים מופרדים ברווחים).
        :return: רשימה של מילונים, כל אחד מייצג את השדות השמורים של שליף תואם.
        """
        query_string = self._prepare_prefix_query(query_string)
        results = []
        with self.ix.searcher() as searcher:
            # ננתח את השאילתה. QueryParser מוגדר לחפש ב'tags' כברירת מחדל.
            query = self.query_parser.parse(query_string)
            for hit in searcher.search(query):
                results.append(hit.fields()) # hit.fields() מחזיר מילון של השדות השמורים
        return results

    @staticmethod
    def _prepare_prefix_query(query_string: str) -> str:
        terms = []
        for term in (query_string or "").split():
            term = term.strip()
            if not term:
                continue
            if term.endswith("*") or ":" in term:
                terms.append(term)
            else:
                terms.append(f"{term}*")
        return " ".join(terms)



#-----------------------------------------------------------------------------------
if __name__ == "__main__":
    sse = SnippetSearchEngine()
    import json
    with open(AppPaths.SNIPS_FILES / "python" / "snips.json", 'r', encoding="utf-8") as f:
        snippets_metadata = json.load(f)

    sse.build_index(snippets_metadata)
