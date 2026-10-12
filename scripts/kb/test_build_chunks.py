import unittest

from build_chunks import drop_trailing_headers, find_heading, normalize, parse_toc, split_long, strip_page_furniture


class NormalizeTest(unittest.TestCase):
    def test_strips_invisible_chars_bullets_and_trailing_colon(self):
        self.assertEqual(normalize("— Цвет (Color):"), "цвет (color)")
        self.assertEqual(normalize("1.​ Установка"), "1. установка")
        self.assertEqual(normalize("ЁЛКА  и  ёж"), "елка и еж")

    def test_unifies_dashes(self):
        self.assertEqual(normalize("РАЗДЕЛ 1 — ТЕОРИЯ"), normalize("Раздел 1 - теория"))


class StripPageFurnitureTest(unittest.TestCase):
    def test_removes_running_header_and_page_number(self):
        page = "ГЛАВА 8: СЛОВАРЬ ЭЛЕМЕНТОВ UI\n\nТекст страницы.\nЕщё строка.\n\n68\n"
        lines, printed, header = strip_page_furniture(page, "ГЛАВА 8: СЛОВАРЬ ЭЛЕМЕНТОВ UI")
        self.assertEqual((printed, header), (68, "ГЛАВА 8: СЛОВАРЬ ЭЛЕМЕНТОВ UI"))
        self.assertEqual([line for line in lines if line], ["Текст страницы.", "Ещё строка."])

    def test_keeps_header_on_chapter_first_page(self):
        page = "ГЛАВА 3: ТЕСТИРОВАНИЕ ТРЕБОВАНИЙ\nТекст\n25"
        lines, _, _ = strip_page_furniture(page, "ГЛАВА 2: ВИДЫ И МЕТОДЫ")
        self.assertEqual([line for line in lines if line], ["ГЛАВА 3: ТЕСТИРОВАНИЕ ТРЕБОВАНИЙ", "Текст"])

    def test_page_without_footer(self):
        lines, printed, _ = strip_page_furniture("Просто текст")
        self.assertIsNone(printed)
        self.assertEqual(lines, ["Просто текст"])


class ParseTocTest(unittest.TestCase):
    def test_levels_numbers_and_wrapped_entries(self):
        lines = [
            "СОДЕРЖАНИЕ",
            "РАЗДЕЛ 5 — ТЕСТИРОВАНИЕ ДОСТУПНОСТИ........ 382",
            "ГЛАВА 3: УПРАВЛЯЕМОСТЬ — Я МОГУ НА ЭТО НАЖАТЬ?....... 408",
            "2.3 СУДОРОГИ И ФИЗИЧЕСКИЕ РЕАКЦИИ (SEIZURES AND PHYSICAL",
            "REACTIONS)..........................420",
            "7",
            "— Цвет (Color):.............. 501",
            "Практика 1: Подмена (Пустое состояние) 516 Практика 2: Проверка адаптива........520",
        ]
        self.assertEqual(parse_toc(lines), [
            ("section", 5, "РАЗДЕЛ 5 — ТЕСТИРОВАНИЕ ДОСТУПНОСТИ", 382),
            ("chapter", 3, "ГЛАВА 3: УПРАВЛЯЕМОСТЬ — Я МОГУ НА ЭТО НАЖАТЬ?", 408),
            ("sub", None, "2.3 СУДОРОГИ И ФИЗИЧЕСКИЕ РЕАКЦИИ (SEIZURES AND PHYSICAL REACTIONS)", 420),
            ("sub", None, "— Цвет (Color):", 501),
            ("sub", None, "Практика 1: Подмена (Пустое состояние)", 516),
            ("sub", None, "Практика 2: Проверка адаптива", 520),
        ])


class FindHeadingTest(unittest.TestCase):
    def setUp(self):
        self.lines = [normalize(s) for s in [
            "Вступление", "", "2.3 СУДОРОГИ И ФИЗИЧЕСКИЕ РЕАКЦИИ (SEIZURES AND PHYSICAL",
            "REACTIONS)", "текст", "Цвет (Color)", "Анализ Граничных Значений (Boundary Value Analysis)",
            "РАЗДЕЛ 6 — ТЕСТИРОВАНИЕ", "МОБИЛЬНЫХ ПРИЛОЖЕНИЙ И", "ВИДЕОИГР", "Итоговая Матрица Подходов в Тестировании:",
        ]]

    def test_exact_bulleted_and_wrapped(self):
        self.assertEqual(find_heading(self.lines, "— Цвет (Color):", 0, len(self.lines)), 5)
        self.assertEqual(find_heading(
            self.lines, "2.3 СУДОРОГИ И ФИЗИЧЕСКИЕ РЕАКЦИИ (SEIZURES AND PHYSICAL REACTIONS)",
            0, len(self.lines)), 2)

    def test_three_line_wrap_and_prefix(self):
        n = len(self.lines)
        self.assertEqual(find_heading(self.lines, "РАЗДЕЛ 6 — ТЕСТИРОВАНИЕ МОБИЛЬНЫХ ПРИЛОЖЕНИЙ И ВИДЕОИГР", 0, n), 7)
        self.assertEqual(find_heading(self.lines, "Итоговая Матрица Подходов в Тестировании (Шпаргалка QA)", 0, n), 10)

    def test_scattered_justified_heading(self):
        lines = [normalize(x) for x in ["Текст абзаца.", "ПРАКТИКУМ:", "ПРОЕКТА", "", "КЛОНИРОВАНИЕ", "", "И",
                                        "", "ЛОКАЛЬНЫЙ ЗАПУСК", "Обычный текст"]]
        self.assertEqual(find_heading(lines, "ПРАКТИКУМ: КЛОНИРОВАНИЕ И ЛОКАЛЬНЫЙ ЗАПУСК ПРОЕКТА", 0, len(lines)), 1)
        self.assertIsNone(find_heading(lines[:7], "ПРАКТИКУМ: КЛОНИРОВАНИЕ И ЛОКАЛЬНЫЙ ЗАПУСК ПРОЕКТА", 0, 7))

    def test_fuzzy_and_window_and_miss(self):
        self.assertEqual(find_heading(
            self.lines, "Анализ Граничных Значений (Boundary Value Analysis — BVA)", 0, len(self.lines)), 6)
        self.assertIsNone(find_heading(self.lines, "Цвет (Color)", 0, 5))
        self.assertIsNone(find_heading(self.lines, "Совсем другой заголовок", 0, len(self.lines)))


class DropTrailingHeadersTest(unittest.TestCase):
    def test_drops_next_chapter_header_only_at_end(self):
        text = "ГЛАВА 7: СЕРВЕРНАЯ\nТекст.\n\n\n\nКонец.\n\nГЛАВА 1: ПОНЯТИЕ ДОСТУПНОСТИ\n"
        self.assertEqual(drop_trailing_headers(text), "ГЛАВА 7: СЕРВЕРНАЯ\nТекст.\n\nКонец.")

    def test_keeps_header_only_chunk(self):
        self.assertEqual(drop_trailing_headers("ГЛАВА 2: ВВЕДЕНИЕ"), "ГЛАВА 2: ВВЕДЕНИЕ")


class SplitLongTest(unittest.TestCase):
    def test_splits_on_paragraphs_under_limit(self):
        text = "\n\n".join(["слово " * 10] * 5)
        parts = split_long(text, max_words=25)
        self.assertEqual(len(parts), 3)
        self.assertEqual(sum(p.count("слово") for p in parts), 50)

    def test_oversized_paragraph_kept_whole(self):
        self.assertEqual(len(split_long("а " * 100, max_words=10)), 1)


if __name__ == "__main__":
    unittest.main()
