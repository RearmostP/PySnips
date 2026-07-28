import json
from datetime import datetime
from pathlib import Path

from core.tools.common.app_paths import AppPaths
from core.tools.common.atomic_json import write_json_atomic
from core.tools.snips.snippet_name_utils import sanitize_snippet_name


class SnippetMetadataManager:
    def normalize_tags(self, tags_value) -> list[str]:
        if isinstance(tags_value, list):
            raw_tags = tags_value
        else:
            raw_tags = str(tags_value or "").split(",")

        seen = set()
        tags = []
        for tag in raw_tags:
            clean_tag = str(tag).strip()
            if not clean_tag or clean_tag in seen:
                continue
            seen.add(clean_tag)
            tags.append(clean_tag)
        return tags

    def get_created_at(self, snippet_meta: dict) -> str:
        created_at = str(snippet_meta.get("created_at") or "").strip()
        if created_at:
            return created_at

        content_file = Path(str(snippet_meta.get("content_file") or ""))
        try:
            if content_file.exists():
                return datetime.fromtimestamp(content_file.stat().st_ctime).isoformat(timespec="seconds")
        except OSError:
            pass
        return datetime.now().isoformat(timespec="seconds")

    def load_current(self, snippet_meta: dict) -> dict | None:
        category = str(snippet_meta.get("category") or "").strip()
        snippet_id = str(snippet_meta.get("id") or "").strip()
        if not category or not snippet_id:
            return None

        snips_json_path = AppPaths.SNIPS_FILES / sanitize_snippet_name(category) / "snips.json"
        try:
            with open(snips_json_path, "r", encoding="utf-8") as f:
                snippets = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(snippets, list):
            return None

        for item in snippets:
            if isinstance(item, dict) and str(item.get("id") or "") == snippet_id:
                return item
        return None

    def save(self, updated_meta: dict, original_category: str | None = None) -> bool:
        category = str(updated_meta.get("category") or "").strip()
        original_category = str(original_category or category).strip()
        snippet_id = str(updated_meta.get("id") or "").strip()
        if not category or not original_category or not snippet_id:
            return False

        original_snips_json_path = AppPaths.SNIPS_FILES / sanitize_snippet_name(original_category) / "snips.json"
        target_snips_json_path = AppPaths.SNIPS_FILES / sanitize_snippet_name(category) / "snips.json"
        try:
            original_snippets = self._read_snippets_list(original_snips_json_path)
            if original_snippets is None:
                return False

            source_index = None
            for index, item in enumerate(original_snippets):
                if isinstance(item, dict) and str(item.get("id") or "") == snippet_id:
                    source_index = index
                    break

            if source_index is None:
                return False

            if original_snips_json_path.resolve() == target_snips_json_path.resolve():
                updated_snippets = list(original_snippets)
                updated_snippets[source_index] = updated_meta
                write_json_atomic(original_snips_json_path, updated_snippets)
                return True

            target_existed = target_snips_json_path.exists()
            target_snippets = self._read_snippets_list(target_snips_json_path)
            if target_snippets is None:
                return False

            original_content_file = Path(str(updated_meta.get("content_file") or ""))
            if not original_content_file.is_file():
                return False

            moved_meta = self.move_content_file(updated_meta, category)
            moved_content_file = Path(str(moved_meta.get("content_file") or ""))
            if moved_content_file.resolve() == original_content_file.resolve():
                return False

            updated_original_snippets = list(original_snippets)
            updated_original_snippets.pop(source_index)
            updated_target_snippets = [
                item for item in target_snippets
                if not (isinstance(item, dict) and str(item.get("id") or "") == snippet_id)
            ]
            updated_target_snippets.append(moved_meta)

            try:
                write_json_atomic(target_snips_json_path, updated_target_snippets)
                write_json_atomic(original_snips_json_path, updated_original_snippets)
            except OSError:
                self._rollback_category_move(
                    original_content_file=original_content_file,
                    moved_content_file=moved_content_file,
                    target_snips_json_path=target_snips_json_path,
                    target_snippets=target_snippets,
                    target_existed=target_existed,
                )
                return False
            return True
        except (OSError, json.JSONDecodeError, ValueError):
            return False

    def move_content_file(self, snippet_meta: dict, category: str) -> dict:
        content_file = Path(str(snippet_meta.get("content_file") or ""))
        if not content_file.exists():
            return snippet_meta

        target_dir = AppPaths.SNIPS_FILES / sanitize_snippet_name(category)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / content_file.name

        if content_file.resolve() == target_file.resolve():
            return snippet_meta

        if target_file.exists():
            target_file = target_dir / f"{content_file.stem}-{snippet_meta.get('id', 'snippet')}{content_file.suffix}"

        try:
            content_file.rename(target_file)
        except OSError:
            return snippet_meta

        return {
            **snippet_meta,
            "content_file": str(target_file),
        }

    def _read_snippets_list(self, snips_json_path: Path) -> list[dict] | None:
        if not snips_json_path.exists():
            return []
        with open(snips_json_path, "r", encoding="utf-8") as f:
            snippets = json.load(f)
        return snippets if isinstance(snippets, list) else None

    def _rollback_category_move(
        self,
        original_content_file: Path,
        moved_content_file: Path,
        target_snips_json_path: Path,
        target_snippets: list[dict],
        target_existed: bool,
    ) -> None:
        try:
            if moved_content_file.exists() and not original_content_file.exists():
                original_content_file.parent.mkdir(parents=True, exist_ok=True)
                moved_content_file.rename(original_content_file)
        except OSError:
            pass

        try:
            if target_existed:
                write_json_atomic(target_snips_json_path, target_snippets)
            else:
                target_snips_json_path.unlink(missing_ok=True)
        except OSError:
            pass
