import unittest

from spec_lint import lint_text, skip_regex, vague_regex

SKIP = skip_regex()
VAGUE = vague_regex([])


def lint(text, vague=VAGUE, skip=SKIP):
    return [(f["line"], f["check"], f["match"]) for f in lint_text("spec.md", text, vague, skip)]


class FiresTest(unittest.TestCase):
    def test_ac_bullet_and_requirement_lines(self):
        text = "## 3. Acceptance criteria\n- Поиск работает быстро.\n- Форма корректно сохраняет данные.\n"
        self.assertEqual(lint(text), [(2, "vague-word", "быстро"), (3, "vague-word", "корректно")])

    def test_phrase_and_negated_form(self):
        text = "## Требования\nПоказывать подсказку при необходимости, интерфейс неудобный.\n"
        self.assertEqual([m for _, _, m in lint(text)], ["при необходимости", "неудобный"])

    def test_unfinished_markers(self):
        text = "## Флоу\n- Лимит: TBD\n- ??? что при обрыве\n- Срок — уточнить у продакта\n"
        self.assertEqual([c for _, c, _ in lint(text)], ["unfinished"] * 3)

    def test_extra_words_from_project(self):
        text = "## AC\n- Отображается адекватно и шустро.\n"
        self.assertEqual([m for _, _, m in lint(text, vague=vague_regex(["шустр"]))], ["адекватно", "шустро"])
        self.assertEqual(lint("## AC\n- 20 нормальных документов\n"), [])


class HeadingScopeTest(unittest.TestCase):
    def test_feature_headings_are_not_skipped(self):
        for heading in ["Change password", "Change email", "Изменение пароля", "Order history", "История заказов",
                        "Purchase history", "Context menu", "Why us page", "Exchange rates"]:
            self.assertFalse(SKIP.search(heading), heading)

    def test_meta_headings_are_skipped(self):
        for heading in ["1a. Изменения 2026-08-29", "4. Открытые решения", "1. Цель и контекст", "Rationale",
                        "Open questions", "Changelog", "История изменений", "Alternatives considered", "Почему так"]:
            self.assertTrue(SKIP.search(heading), heading)

    def test_project_patterns_are_added(self):
        self.assertTrue(skip_regex([r"^Заметки"]).search("Заметки дизайнера"))


class EnglishTest(unittest.TestCase):
    def test_english_vague_words_and_draft(self):
        text = "## Acceptance criteria\n- The list loads fast and renders correctly.\n- Status: DRAFT\n- Breakfast is a draft of steadfast.\n"
        self.assertEqual(lint(text), [(2, "vague-word", "fast"), (2, "vague-word", "correctly"), (3, "unfinished", "DRAFT")])


class QuietTest(unittest.TestCase):
    def test_quotes_and_code(self):
        text = ("## AC\n- Боль: «не могу быстро найти документ».\n- Кнопка \"Быстрый вход\".\n"
                "- Флаг `fast_mode` и `TODO()` в коде.\n```\nбыстро TODO\n```\n")
        self.assertEqual(lint(text), [])

    def test_skipped_sections_until_same_level_heading(self):
        text = ("## 4. Открытые решения\n- Inline быстрее, но сложнее.\n### Детали\n- удобнее TBD\n"
                "## 1a. Изменения 2026-08-29\n- стало удобно\n## 5. Acceptance criteria\n- Список грузится быстро.\n")
        self.assertEqual(lint(text), [(8, "vague-word", "быстро")])

    def test_lowercase_draft_noun_and_dated_decision(self):
        text = ("## AC\n- черновик тега коммитится по blur\n"
                "- **Product decision 2026-06-13:** форма раскрывает email, иначе быстрый вход ломается.\n"
                "- Статус: ЧЕРНОВИК\n")
        self.assertEqual(lint(text), [(4, "unfinished", "ЧЕРНОВИК")])

    def test_quantified_flag(self):
        found = lint_text("s.md", "## AC\n- Фильтры быстрые: debounce 250 мс.\n- Поиск быстрый.\n", VAGUE, SKIP)
        self.assertEqual([f["quantified"] for f in found], [True, False])

    def test_ordinary_words_do_not_match(self):
        text = "## AC\n- При нажатии на кнопку и при отсутствии сети показать ошибку.\n- Гибкость не нужна? нет.\n"
        self.assertEqual([m for _, _, m in lint(text)], ["Гибкость"])


if __name__ == "__main__":
    unittest.main()
