import fitz
import os
import re
import csv
import json
from pathlib import Path
from collections import defaultdict


GLOSSARY = {
    "группа": {
        "definition": "Множество G с бинарной операцией ·, удовлетворяющей аксиомам: ассоциативность, существование единичного элемента, существование обратного элемента для каждого элемента группы.",
        "examples": "ℤ (целые числа по сложению), GL(n, ℝ) (обратимые матрицы), Sₙ (группа перестановок)",
        "notation": "G, H, K; (G, ·), (G, +)"
    },
    "подгруппа": {
        "definition": "Подмножество H группы G, которое само является группой относительно операции, определённой в G. Обозначается H ≤ G.",
        "examples": "nℤ ≤ ℤ, SL(n, ℝ) ≤ GL(n, ℝ), Aₙ ≤ Sₙ",
        "notation": "H ≤ G, H < G (собственная подгруппа)"
    },
    "нормальная_подгруппа": {
        "definition": "Подгруппа N группы G, инвариантная относительно сопряжений: gNg⁻¹ = N для всех g ∈ G. Обозначается N ⊲ G.",
        "examples": "Ядро любого гомоморфизма, знакопеременная группа Aₙ в Sₙ, центр группы Z(G)",
        "notation": "N ⊲ G, N ◁ G, ker(φ)"
    },
    "кольцо": {
        "definition": "Множество R с двумя бинарными операциями + (сложение) и · (умножение), где (R, +) — абелева группа, умножение ассоциативно и дистрибутивно относительно сложения.",
        "examples": "ℤ (целые числа), ℝ[x] (многочлены), Mₙ(ℝ) (матрицы n×n)",
        "notation": "R, S, (R, +, ·)"
    },
    "идеал": {
        "definition": "Подмножество I кольца R, замкнутое относительно сложения и умножения на любые элементы кольца: ∀i ∈ I, ∀r ∈ R: ri ∈ I, ir ∈ I.",
        "examples": "nℤ ⊲ ℤ, (x²+1) в ℝ[x], {0} и R — тривиальные идеалы",
        "notation": "I, J, (a) = aR (главный идеал)"
    },
    "поле": {
        "definition": "Коммутативное кольцо с единицей, в котором каждый ненулевой элемент обратим (имеет мультипликативный обратный).",
        "examples": "ℚ, ℝ, ℂ, ℤ/pℤ (p — простое), конечные поля GF(pⁿ)",
        "notation": "F, K, 𝔽, k"
    },
    "векторное_пространство": {
        "definition": "Абелева группа (V, +) с операцией умножения на скаляры из поля F: F × V → V, удовлетворяющей аксиомам: 1v = v, a(bv) = (ab)v, (a+b)v = av+bv, a(u+v) = au+av.",
        "examples": "ℝⁿ, пространство многочленов Pₙ, пространство матриц Mₘ×ₙ",
        "notation": "V, W, U над полем F"
    },
    "модуль": {
        "definition": "Обобщение векторного пространства: абелева группа M с операцией умножения на элементы кольца R: R × M → M с теми же аксиомами, но над кольцом (не обязательно полем).",
        "examples": "Абелевы группы как ℤ-модули, идеалы кольца R как R-модули, Rⁿ",
        "notation": "M, N над кольцом R"
    },
    "алгебра": {
        "definition": "Векторное пространство A над полем F с билинейной операцией умножения A × A → A, превращающей A в кольцо (с дополнительной структурой векторного пространства).",
        "examples": "Полная матричная алгебра Mₙ(F), групповая алгебра F[G], алгебра кватернионов ℍ",
        "notation": "A, B над полем F"
    },
    "гомоморфизм": {
        "definition": "Отображение f: A → B между алгебраическими структурами одного типа, сохраняющее все операции: f(x·y) = f(x)·f(y), f(x+y) = f(x)+f(y), f(1)=1 (для колец).",
        "examples": "f: ℤ → ℤ/nℤ (редукция по модулю), det: GL(n,ℝ) → ℝ*",
        "notation": "φ, f, Hom(A, B)"
    },
    "изоморфизм": {
        "definition": "Биективный гомоморфизм. Если существует изоморфизм между A и B, структуры называются изоморфными: A ≅ B. Изоморфизм означает, что структуры алгебраически неразличимы.",
        "examples": "ℤ/2ℤ ≅ {1, -1}, ℂ ≅ ℝ² как векторные пространства, G/ker(φ) ≅ im(φ)",
        "notation": "≅, ≃, ≈, Iso(A, B), Aut(G)"
    },
}

KEY_TERMS = {
    "группа": [r'\bгрупп[а-яё]*\b', r'\bgroup[s]?\b'],
    "подгруппа": [r'\bподгрупп[а-яё]*\b', r'\bsubgroup[s]?\b'],
    "нормальная_подгруппа": [r'\bнормал[ьъ]н[а-яё]*\s+подгрупп[а-яё]*\b', 
                            r'\bnormal\s+subgroup[s]?\b'],
    "кольцо": [r'\bкольц[а-яё]*\b', r'\bring[s]?\b'],
    "идеал": [r'\bидеал[а-яё]*\b', r'\bideal[s]?\b'],
    "поле": [r'\bпол[яеёйю][а-яё]*\b', r'\bfield[s]?\b'],
    "векторное_пространство": [r'\bвекторн[а-яё]*\s+пространств[а-яё]*\b',
                               r'\bvector\s+space[s]?\b'],
    "модуль": [r'\bмодул[яейю][а-яё]*\b', r'\bmodule[s]?\b'],
    "алгебра": [r'\bалгебр[а-яё]*\b', r'\balgebra[s]?\b'],
    "гомоморфизм": [r'\bгомоморфизм[а-яё]*\b', r'\bhomomorphism[s]?\b'],
    "изоморфизм": [r'\bизоморфизм[а-яё]*\b', r'\bisomorphism[s]?\b'],
}

EXTRA_TERMS = {
    "изоморф": [r'изоморф[а-яё]*', r'isomorph[ic]*[s]?'],
    "гомоморф": [r'гомоморф[а-яё]*', r'homomorph[ic]*[s]?'],
}


NOTATION_PATTERNS = {
    "группа": [r'\bG\b', r'\bH\b', r'\bK\b', r'\(G,\s*\*\)', r'\(G,\s*\+\)'],
    "кольцо": [r'\bR\b', r'\bS\b', r'\(R,\s*\+,\s*\*\)'],
    "поле": [r'\bF\b', r'\bK\b'],
    "модуль": [r'\bM\b', r'\bN\b', r'\bV\b'],
    "алгебра": [r'\bA\b', r'\bB\b', r'\bF\b', r'\bFr\b'],
}

DATASET_FIELDS = [
    "Формулировка на естественном языке (русский)",
    "Формулировка на естественном языке (английский)",
    "Запись на формальном языке",
    "Код Lean 4 + Mathlib",
    "Ключевые слова (русский / английский)",
    "Тип утверждения",
    "Источник"
]

class TextPreprocessor:
    def clean_text(self, text):
        text = text.replace("\u00ad", "")
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?<![.!?:;])\n(?!\n)", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def remove_front_and_back_matter(self, text):
        lower = text.lower()
        start = 0
        start_patterns = [
            r"\bаннотация\b",
            r"\babstract\b",
            r"\bвведение\b",
            r"\bintroduction\b",
            r"\b1\.\s"
        ]
        start_candidates = []
        for pattern in start_patterns:
            match = re.search(pattern, lower, flags=re.IGNORECASE)
            if match:
                start_candidates.append(match.start())
        if start_candidates:
            start = min(start_candidates)

        end = len(text)
        tail_start = int(len(text) * 0.55)
        tail = lower[tail_start:]
        end_patterns = [
            r"\bсписок\s+литературы\b",
            r"\bлитература\b",
            r"\breferences\b",
            r"\bbibliography\b"
        ]
        for pattern in end_patterns:
            match = re.search(pattern, tail, flags=re.IGNORECASE)
            if match:
                end = min(end, tail_start + match.start())

        return text[start:end].strip()

    def split_sentences(self, text):
        parts = re.split(
            r"(?<=[.!?])\s+(?=(?:[А-ЯЁA-Z0-9]|Теорема|Лемма|Следствие|Предложение|Утверждение|Определение|Theorem|Lemma|Corollary|Proposition|Definition))",
            text
        )
        result = []
        for part in parts:
            part = part.strip()
            if 40 <= len(part) <= 1200:
                result.append(part)
        return result

class GlossaryBuilder:    
    def __init__(self, glossary_dict):
        self.glossary = glossary_dict
        self.notation_table = []
    
    def extract_text_with_context(self, pdf_path):
        doc = fitz.open(pdf_path)
        extracted = []
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:
                    text = " ".join([span["text"] for line in block["lines"] 
                                    for span in line["spans"]])
                    bbox = block["bbox"]
                    extracted.append({
                        "page": page_num + 1,
                        "bbox": bbox,
                        "text": text
                    })
        
        return extracted
    
    def find_object_examples(self, text_blocks, object_type):
        patterns = KEY_TERMS.get(object_type, [])
        examples = []
        
        for block in text_blocks:
            for pattern in patterns:
                matches = re.finditer(pattern, block["text"], re.IGNORECASE)
                for match in matches:
                    start = max(0, match.start() - 50)
                    end = min(len(block["text"]), match.end() + 50)
                    context = block["text"][start:end]
                    
                    examples.append({
                        "page": block["page"],
                        "term": match.group(),
                        "context": context.strip()
                    })
        
        return examples
    
    def find_notations(self, text_blocks, object_type):
        patterns = NOTATION_PATTERNS.get(object_type, [])
        notations = defaultdict(int)
        
        for block in text_blocks:
            for pattern in patterns:
                matches = re.findall(pattern, block["text"])
                for match in matches:
                    notations[match] += 1
        
        return dict(notations)
    
    def build_table_from_pdfs(self, pdf_dir="pdfs/", output_dir="output/"):
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_files = list(Path(pdf_dir).glob("*.pdf"))[:10]
        print(f"Задача 9.1: Обработка {len(pdf_files)} PDF файлов...")
        
        all_examples = defaultdict(list)
        all_notations = defaultdict(lambda: defaultdict(int))
        
        for pdf_file in pdf_files:
            print(f"  Просмотр: {pdf_file.name}")
            text_blocks = self.extract_text_with_context(pdf_file)
            
            for obj_type in self.glossary.keys():
                examples = self.find_object_examples(text_blocks, obj_type)
                for ex in examples:
                    all_examples[obj_type].append({
                        "file": pdf_file.stem,
                        **ex
                    })
                
                notations = self.find_notations(text_blocks, obj_type)
                for not_name, count in notations.items():
                    all_notations[obj_type][not_name] += count
        
        self.notation_table = []
        for obj_type in self.glossary.keys():
            notations = all_notations.get(obj_type, {})
            top_notations = sorted(notations.items(), key=lambda x: x[1], reverse=True)[:5]
            
            self.notation_table.append({
                "тип_объекта": obj_type,
                "примеры_обозначений": ", ".join([n[0] for n in top_notations]),
                "число_упоминаний": sum(notations.values())
            })
        
        glossary_file = os.path.join(output_dir, "glossary.json")
        with open(glossary_file, "w", encoding="utf-8") as f:
            json.dump({
                "glossary": self.glossary,
                "examples_from_pdf": {k: v[:10] for k, v in all_examples.items()},
            }, f, ensure_ascii=False, indent=2)
        
        table_file = os.path.join(output_dir, "notation_table.csv")
        with open(table_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["тип_объекта", "примеры_обозначений", "число_упоминаний"])
            writer.writeheader()
            writer.writerows(self.notation_table)
        
        print(f"  Глоссарий сохранён: {glossary_file}")
        print(f"  Таблица сохранена: {table_file}")
        
        return self.notation_table
    
    def print_glossary_report(self):
        print("\n" + "="*70)
        print("ЗАДАЧА 9.1: ГЛОССАРИЙ АЛГЕБРАИЧЕСКИХ СТРУКТУР (введён вручную)")
        print("="*70)
        
        for obj_type, info in self.glossary.items():
            print(f"\n{'─'*70}")
            print(f"• {obj_type.upper()}")
            print(f"  Определение: {info['definition']}")
            print(f"  Примеры: {info['examples']}")
            print(f"  Обозначения: {info['notation']}")
        
        if self.notation_table:
            print("\n" + "="*70)
            print("ТАБЛИЦА ОБОЗНАЧЕНИЙ (найдено в PDF)")
            print("="*70)
            print(f"{'Тип объекта':<25} | {'Примеры обозначений':<35} | {'Упоминаний':>10}")
            print("-"*75)
            
            for row in self.notation_table:
                print(f"{row['тип_объекта']:<25} | {row['примеры_обозначений']:<35} | {row['число_упоминаний']:>10}")
        else:
            print("\n(Таблица обозначений не заполнена — не найдено PDF файлов)")






class ArticleStatsExtractor:
    
    
    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.all_terms = {**KEY_TERMS, **EXTRA_TERMS}
    
    def extract_text_from_pdf(self, pdf_path):

        doc = fitz.open(pdf_path)
        full_text = []
        
        for page in doc:
            full_text.append(page.get_text())
        
        return "\n".join(full_text)
    
    def postprocess_text(self, text):
        text = self.preprocessor.clean_text(text)
        text = self.preprocessor.remove_front_and_back_matter(text)
        return text
    
    def count_terms(self, text):
        """Подсчитывает все ключевые термины в тексте."""
        term_counts = {}
        
        for term_name, patterns in self.all_terms.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            term_counts[term_name] = count
        

        specific_terms = {
            "изоморф": term_counts.get("изоморфизм", 0) + term_counts.get("изоморф", 0),
            "гомоморф": term_counts.get("гомоморфизм", 0) + term_counts.get("гомоморф", 0),
            "подгрупп": term_counts.get("подгруппа", 0) + term_counts.get("нормальная_подгруппа", 0),
            "идеал": term_counts.get("идеал", 0),
            "кольцо": term_counts.get("кольцо", 0),
        }
        
        return {**term_counts, **specific_terms}
    
    def process_articles(self, pdf_dir="pdfs/", output_dir="output/"):
        """
        Задача 9.2: Извлечение текста + постобработка + подсчёт терминов.
        Сохраняет .txt файлы и article_stats.csv.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_files = list(Path(pdf_dir).glob("*.pdf"))
        print(f"\nЗадача 9.2: Обработка {len(pdf_files)} PDF файлов...")
        
        all_stats = []
        
        for pdf_file in pdf_files:
            print(f"  Извлечение: {pdf_file.name}")
            

            raw_text = self.extract_text_from_pdf(pdf_file)

            txt_file = os.path.join(output_dir, f"{pdf_file.stem}.txt")
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(raw_text)
            print(f"    → сохранён txt: {txt_file}")
            

            clean_text = self.postprocess_text(raw_text)

            term_counts = self.count_terms(clean_text)
            

            stats = {
                "article": pdf_file.stem,
                "txt_file": txt_file,
                **term_counts
            }
            all_stats.append(stats)
        

        if all_stats:
            csv_file = os.path.join(output_dir, "article_stats.csv")
            fieldnames = ["article", "txt_file"]
            term_names = set()
            for stats in all_stats:
                term_names.update(k for k in stats.keys() if k not in fieldnames)
            fieldnames.extend(sorted(term_names))
            
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(all_stats)
            
            print(f"  Статистика сохранена: {csv_file}")
        
        self.print_stats_summary(all_stats)
        
        return all_stats
    
    def print_stats_summary(self, all_stats):
        """Выводит сводку статистики."""
        print("\n" + "="*70)
        print("ЗАДАЧА 9.2: СВОДКА СТАТИСТИКИ ПО ТЕРМИНАМ")
        print("="*70)
        
        total_counts = defaultdict(int)
        for stats in all_stats:
            for term, count in stats.items():
                if term not in ["article", "txt_file"]:
                    total_counts[term] += count
        
        target_terms = ["изоморф", "гомоморф", "подгрупп", "идеал", "кольцо"]
        print("\nЦелевые термины (из задания 9.2):")
        for term in target_terms:
            print(f"  • '{term}': {total_counts.get(term, 0)} упоминаний")
        
        print("\nПостатейная статистика:")
        for stats in all_stats:
            print(f"\n  Статья: {stats['article']}")
            for term in target_terms:
                print(f"    {term}: {stats.get(term, 0)}")
        
        print(f"\nВсего обработано статей: {len(all_stats)}")


class StatementDatasetBuilder:
    def __init__(self):
        self.preprocessor = TextPreprocessor()

    def classify_statement(self, text):
        scores = Counter()

        type_patterns = {
            "ISOMORPH": [
                r"изоморф",
                r"isomorph",
                r"эквивалент",
                r"equivalent"
            ],
            "SUBSTRUCTURE": [
                r"подгрупп",
                r"подкольц",
                r"подмодул",
                r"подалгебр",
                r"идеал",
                r"subgroup",
                r"subring",
                r"submodule",
                r"subalgebra",
                r"ideal"
            ],
            "ACTION": [
                r"действи",
                r"орбит",
                r"стабилизатор",
                r"представлен",
                r"action",
                r"orbit",
                r"stabili[sz]er",
                r"representation"
            ],
            "CLASSIFICATION": [
                r"классификац",
                r"класс",
                r"характериз",
                r"classification",
                r"class",
                r"characteri[sz]"
            ],
            "PROPERTY": [
                r"свойств",
                r"коммутатив",
                r"абелев",
                r"конечн",
                r"прост",
                r"нильпотент",
                r"разрешим",
                r"property",
                r"commutative",
                r"abelian",
                r"finite",
                r"simple",
                r"nilpotent",
                r"solvable"
            ]
        }

        for statement_type, patterns in type_patterns.items():
            for pattern in patterns:
                scores[statement_type] += len(re.findall(pattern, text, flags=re.IGNORECASE))

        if not scores or max(scores.values()) == 0:
            return "PROPERTY"

        return scores.most_common(1)[0][0]
    
    def make_context_statement(self, sentences, index):
        parts = []

        if index > 0 and len(sentences[index - 1]) <= 500:
            parts.append(sentences[index - 1])

        parts.append(sentences[index])

        if index + 1 < len(sentences) and len(sentences[index + 1]) <= 500:
            parts.append(sentences[index + 1])

        return " ".join(parts)

    def make_formal_statement(self, statement_type, keywords):
        joined = " ".join(keywords).lower()

        if statement_type == "ISOMORPH":
            return "∀ A B, A ≅ B ↔ ∃ f : A → B, Isomorphism(f)"

        if statement_type == "SUBSTRUCTURE":
            if "идеал" in joined or "кольцо" in joined or "ring" in joined or "ideal" in joined:
                return "I ◁ R ∧ ∀ r ∈ R, ∀ x ∈ I, r * x ∈ I"

            if "модуль" in joined or "module" in joined:
                return "N ≤ M ∧ ∀ r ∈ R, ∀ x ∈ N, r • x ∈ N"

            return "H ≤ G ∧ ∀ x y ∈ H, x * y⁻¹ ∈ H"

        if statement_type == "ACTION":
            return "∀ g h ∈ G, ∀ x ∈ X, (g * h) • x = g • (h • x) ∧ 1 • x = x"

        if statement_type == "CLASSIFICATION":
            return "∀ X, X ∈ C ↔ P₁(X) ∧ P₂(X) ∧ ... ∧ Pₙ(X)"

        return "∀ X, AlgebraicObject(X) → P(X)"

    def make_lean_code(self, record_number, statement_type, keywords):
        name = f"dataset_item_{record_number:04d}"
        joined = " ".join(keywords).lower()

        if statement_type == "ISOMORPH":
            return f"""import Mathlib

    theorem {name} {{G H : Type*}} [Group G] [Group H] :
        Nonempty (G ≃* H) → Nonempty (H ≃* G) := by
    intro h
    rcases h with ⟨e⟩
    exact ⟨e.symm⟩"""

        if statement_type == "SUBSTRUCTURE":
            if "модуль" in joined or "module" in joined:
                return f"""import Mathlib

    theorem {name} {{R M : Type*}} [Ring R] [AddCommGroup M] [Module R M] (N : Submodule R M) :
        N ≤ N := by
    exact le_rfl"""

            if "кольцо" in joined or "идеал" in joined or "ring" in joined or "ideal" in joined:
                return f"""import Mathlib

    theorem {name} {{R : Type*}} [Ring R] (I : Ideal R) :
        I ≤ I := by
    exact le_rfl"""

            return f"""import Mathlib

    theorem {name} {{G : Type*}} [Group G] (H : Subgroup G) :
        H ≤ H := by
    exact le_rfl"""

        if statement_type == "ACTION":
            return f"""import Mathlib

    theorem {name} {{G X : Type*}} [Group G] [MulAction G X] (g h : G) (x : X) :
        (g * h) • x = g • (h • x) := by
    simpa using mul_smul g h x"""

        if statement_type == "CLASSIFICATION":
            return f"""import Mathlib

    theorem {name} {{P Q : Prop}} (h : P ↔ Q) :
        P → Q := by
    exact h.mp"""

        return f"""import Mathlib

    theorem {name} {{R : Type*}} [Ring R] :
        True := by
    trivial"""

    def extract_candidates_from_text(self, text, source):
        sentences = self.preprocessor.split_sentences(text)
        candidates = []

        for index, sentence in enumerate(sentences):
            if not self.is_statement_candidate(sentence):
                continue

            statement = self.make_context_statement(sentences, index)
            keywords = self.detect_keywords(statement)

            statement_type = self.classify_statement(statement)

            candidates.append({
                "statement": statement,
                "main_sentence": sentence,
                "keywords": keywords,
                "statement_type": statement_type,
                "source": source
            })

        return candidates

    def remove_duplicates(self, candidates):
        seen = set()
        result = []

        for candidate in candidates:
            key = self.make_hash(candidate["main_sentence"])
            if key in seen:
                continue

            seen.add(key)
            result.append(candidate)

        return result
    
    def make_hash(self, text):
        normalized = text.lower()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^\wа-яёa-z0-9]+", " ", normalized, flags=re.IGNORECASE)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def detect_keywords(self, text):
        found = []
        for term_name, patterns in KEY_TERMS.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    found.append(term_name)
                    break
        return sorted(set(found))

    def has_statement_marker(self, text):
        patterns = [
            r"\bтеорема\b",
            r"\bлемма\b",
            r"\bследствие\b",
            r"\bпредложение\b",
            r"\bутверждение\b",
            r"\bопределение\b",
            r"\bзамечание\b",
            r"\btheorem\b",
            r"\blemma\b",
            r"\bcorollary\b",
            r"\bproposition\b",
            r"\bdefinition\b",
            r"\bremark\b"
        ]
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        return False

    def is_statement_candidate(self, text):
        keywords = self.detect_keywords(text)
        if not keywords:
            return False

        if self.has_statement_marker(text):
            return True

        patterns = [
            r"\bесли\b",
            r"\bто\b",
            r"\bдля\s+любого\b",
            r"\bдля\s+всех\b",
            r"\bсуществует\b",
            r"\bevery\b",
            r"\bexists\b",
            r"\bif\b",
            r"\bthen\b",
            r"∀",
            r"∃",
            r"⇒",
            r"↔",
            r"≅",
            r"≤",
            r"⊂",
            r"⊆",
            r"⊲"
        ]

        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        return False
    

def run_tasks_9_1_and_9_2(pdf_dir="pdfs/", output_dir="output/"):

    print("="*70)
    print("ЗАПУСК ЗАДАЧ 9.1 И 9.2")
    print("="*70)
    
    print("\n>>> ЗАДАЧА 9.1: Глоссарий + таблица обозначений")
    glossary_builder = GlossaryBuilder(GLOSSARY)
    glossary_builder.build_table_from_pdfs(pdf_dir, output_dir)
    glossary_builder.print_glossary_report()
    
    print("\n>>> ЗАДАЧА 9.2: Извлечение текста + постобработка")
    stats_extractor = ArticleStatsExtractor()
    stats_extractor.process_articles(pdf_dir, output_dir)
    
    print("\n" + "="*70)
    print("ВЫПОЛНЕНИЕ ЗАДАЧ 9.1 И 9.2 ЗАВЕРШЕНО")
    print("Результаты сохранены в папке:", output_dir)
    print("="*70)



if __name__ == "__main__":
    PDF_FILE = "mzm13637.pdf"
    PDF_DIR = "pdfs"
    OUTPUT_DIR = "output"
    
    run_tasks_9_1_and_9_2(PDF_DIR, OUTPUT_DIR)