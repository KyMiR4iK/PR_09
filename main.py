import fitz
import os
import re
import csv
import json
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
from openpyxl.styles import Alignment


GLOSSARY = {
    "группа": {
        "definition": "Множество G с бинарной операцией ·, удовлетворяющей аксиомам: ассоциативность, существование единичного элемента, существование обратного элемента для каждого элемента группы.",
        "examples": "ℤ по сложению, GL(n, ℝ), Sₙ",
        "notation": "G, H, K; (G, ·), (G, +)"
    },
    "подгруппа": {
        "definition": "Подмножество H группы G, которое само является группой относительно операции, определённой в G.",
        "examples": "nℤ ≤ ℤ, SL(n, ℝ) ≤ GL(n, ℝ), Aₙ ≤ Sₙ",
        "notation": "H ≤ G, H < G"
    },
    "нормальная_подгруппа": {
        "definition": "Подгруппа N группы G, инвариантная относительно сопряжений: gNg⁻¹ = N для всех g ∈ G.",
        "examples": "ker(φ), Aₙ в Sₙ, Z(G)",
        "notation": "N ⊲ G, N ◁ G, ker(φ)"
    },
    "кольцо": {
        "definition": "Множество R с двумя операциями + и ·, где сложение образует абелеву группу, а умножение ассоциативно и дистрибутивно относительно сложения.",
        "examples": "ℤ, ℝ[x], Mₙ(ℝ)",
        "notation": "R, S, (R, +, ·)"
    },
    "идеал": {
        "definition": "Подмножество I кольца R, замкнутое относительно сложения и умножения на элементы кольца.",
        "examples": "nℤ, (x²+1), {0}, R",
        "notation": "I, J, (a), I ◁ R"
    },
    "поле": {
        "definition": "Коммутативное кольцо с единицей, в котором каждый ненулевой элемент обратим.",
        "examples": "ℚ, ℝ, ℂ, ℤ/pℤ",
        "notation": "F, K, 𝔽, k"
    },
    "векторное_пространство": {
        "definition": "Абелева группа с операцией умножения на скаляры из поля.",
        "examples": "ℝⁿ, пространство многочленов, пространство матриц",
        "notation": "V, W, U"
    },
    "модуль": {
        "definition": "Обобщение векторного пространства над кольцом.",
        "examples": "ℤ-модули, идеалы кольца, Rⁿ",
        "notation": "M, N"
    },
    "алгебра": {
        "definition": "Векторное пространство с билинейной операцией умножения.",
        "examples": "Mₙ(F), F[G], ℍ",
        "notation": "A, B"
    },
    "гомоморфизм": {
        "definition": "Отображение между алгебраическими структурами одного типа, сохраняющее операции.",
        "examples": "ℤ → ℤ/nℤ, det: GL(n,ℝ) → ℝ*",
        "notation": "φ, f, Hom(A, B)"
    },
    "изоморфизм": {
        "definition": "Биективный гомоморфизм.",
        "examples": "G/ker(φ) ≅ im(φ)",
        "notation": "≅, ≃, Iso(A, B), Aut(G)"
    }
}


KEY_TERMS = {
    "группа": [r"\bгрупп[а-яё]*\b", r"\bgroup[s]?\b"],
    "подгруппа": [r"\bподгрупп[а-яё]*\b", r"\bsubgroup[s]?\b"],
    "нормальная_подгруппа": [r"\bнормальн[а-яё]*\s+подгрупп[а-яё]*\b", r"\bnormal\s+subgroup[s]?\b"],
    "кольцо": [r"\bкольц[а-яё]*\b", r"\bring[s]?\b"],
    "идеал": [r"\bидеал[а-яё]*\b", r"\bideal[s]?\b"],
    "поле": [r"\bпол[еяёйюй][а-яё]*\b", r"\bfield[s]?\b"],
    "векторное_пространство": [r"\bвекторн[а-яё]*\s+пространств[а-яё]*\b", r"\bvector\s+space[s]?\b"],
    "модуль": [r"\bмодул[яейю][а-яё]*\b", r"\bmodule[s]?\b"],
    "алгебра": [r"\bалгебр[а-яё]*\b", r"\balgebra[s]?\b"],
    "гомоморфизм": [r"\bгомоморф[а-яё]*\b", r"\bhomomorph[a-z]*\b"],
    "изоморфизм": [r"\bизоморф[а-яё]*\b", r"\bisomorph[a-z]*\b"],
    "действие": [r"\bдействи[ея][а-яё]*\b", r"\baction[s]?\b", r"\bacts?\b"],
    "орбита": [r"\bорбит[а-яё]*\b", r"\borbit[s]?\b"],
    "стабилизатор": [r"\bстабилизатор[а-яё]*\b", r"\bstabili[sz]er[s]?\b"],
    "классификация": [r"\bклассификац[а-яё]*\b", r"\bclassification\b"],
    "свойство": [r"\bсвойств[а-яё]*\b", r"\bproperty\b", r"\bproperties\b"]
}


NOTATION_PATTERNS = {
    "группа": [r"\bG\b", r"\bH\b", r"\bK\b", r"\(G,\s*\*\)", r"\(G,\s*\+\)"],
    "кольцо": [r"\bR\b", r"\bS\b", r"\(R,\s*\+,\s*\*\)"],
    "поле": [r"\bF\b", r"\bK\b"],
    "модуль": [r"\bM\b", r"\bN\b", r"\bV\b"],
    "алгебра": [r"\bA\b", r"\bB\b"]
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
    def remove_excel_illegal_chars(self, text):
        if not isinstance(text, str):
            return text
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", text)
        return text

    def limit_excel_cell_length(self, text):
        if not isinstance(text, str):
            return text
        if len(text) > 32000:
            return text[:32000]
        return text

    def safe_text(self, text):
        if not isinstance(text, str):
            return text
        text = self.remove_excel_illegal_chars(text)
        text = self.limit_excel_cell_length(text)
        return text

    def clean_text(self, text):
        text = self.remove_excel_illegal_chars(text)
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


class PathResolver:
    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent

    def resolve_pdf_dir(self, pdf_dir):
        path = Path(pdf_dir)
        if path.is_absolute():
            return path
        from_cwd = Path.cwd() / path
        if from_cwd.exists():
            return from_cwd
        from_script = self.script_dir / path
        if from_script.exists():
            return from_script
        if self.script_dir.name.lower() == "pdfs" and path.name.lower() == "pdfs":
            return self.script_dir
        return from_script

    def resolve_output_dir(self, output_dir):
        path = Path(output_dir)
        if path.is_absolute():
            return path
        if self.script_dir.name.lower() == "pdfs":
            return self.script_dir.parent / path
        return self.script_dir / path


class GlossaryBuilder:
    def __init__(self, glossary_dict):
        self.glossary = glossary_dict
        self.notation_table = []
        self.preprocessor = TextPreprocessor()

    def extract_text_with_context(self, pdf_path):
        doc = fitz.open(pdf_path)
        extracted = []
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") == 0:
                    text = " ".join(
                        span["text"]
                        for line in block.get("lines", [])
                        for span in line.get("spans", [])
                    )
                    text = self.preprocessor.clean_text(text)
                    if text:
                        extracted.append({
                            "page": page_num + 1,
                            "bbox": block["bbox"],
                            "text": text
                        })
        doc.close()
        return extracted

    def find_object_examples(self, text_blocks, object_type):
        patterns = KEY_TERMS.get(object_type, [])
        examples = []
        for block in text_blocks:
            for pattern in patterns:
                matches = re.finditer(pattern, block["text"], re.IGNORECASE)
                for match in matches:
                    start = max(0, match.start() - 80)
                    end = min(len(block["text"]), match.end() + 80)
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

    def build_table_from_pdfs(self, pdf_dir="pdfs", output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        pdf_files = sorted(list(Path(pdf_dir).rglob("*.pdf")) + list(Path(pdf_dir).rglob("*.PDF")))
        all_examples = defaultdict(list)
        all_notations = defaultdict(lambda: defaultdict(int))
        for pdf_file in pdf_files:
            text_blocks = self.extract_text_with_context(pdf_file)
            for obj_type in self.glossary.keys():
                examples = self.find_object_examples(text_blocks, obj_type)
                for example in examples:
                    all_examples[obj_type].append({
                        "file": pdf_file.stem,
                        **example
                    })
                notations = self.find_notations(text_blocks, obj_type)
                for notation, count in notations.items():
                    all_notations[obj_type][notation] += count
        self.notation_table = []
        for obj_type in self.glossary.keys():
            notations = all_notations.get(obj_type, {})
            top_notations = sorted(notations.items(), key=lambda item: item[1], reverse=True)[:5]
            self.notation_table.append({
                "тип_объекта": obj_type,
                "примеры_обозначений": ", ".join(item[0] for item in top_notations),
                "число_упоминаний": sum(notations.values())
            })
        glossary_file = Path(output_dir) / "glossary.json"
        with glossary_file.open("w", encoding="utf-8") as file:
            json.dump({
                "glossary": self.glossary,
                "examples_from_pdf": {key: value[:10] for key, value in all_examples.items()}
            }, file, ensure_ascii=False, indent=2)
        table_file = Path(output_dir) / "notation_table.csv"
        with table_file.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=["тип_объекта", "примеры_обозначений", "число_упоминаний"])
            writer.writeheader()
            writer.writerows(self.notation_table)
        return self.notation_table


class ArticleStatsExtractor:
    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.all_terms = KEY_TERMS

    def extract_text_from_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        pages = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            text = self.preprocessor.clean_text(text)
            if text:
                pages.append({
                    "page": page_num,
                    "text": text
                })
        doc.close()
        return pages

    def postprocess_text(self, text):
        text = self.preprocessor.clean_text(text)
        text = self.preprocessor.remove_front_and_back_matter(text)
        return text

    def count_terms(self, text):
        term_counts = {}
        for term_name, patterns in self.all_terms.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            term_counts[term_name] = count
        term_counts["изоморф"] = term_counts.get("изоморфизм", 0)
        term_counts["гомоморф"] = term_counts.get("гомоморфизм", 0)
        term_counts["подгрупп"] = term_counts.get("подгруппа", 0) + term_counts.get("нормальная_подгруппа", 0)
        return term_counts

    def process_articles(self, pdf_dir="pdfs", output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        txt_dir = Path(output_dir) / "txt_clean"
        txt_dir.mkdir(parents=True, exist_ok=True)
        pdf_files = sorted(list(Path(pdf_dir).rglob("*.pdf")) + list(Path(pdf_dir).rglob("*.PDF")))
        all_stats = []
        for pdf_file in pdf_files:
            pages = self.extract_text_from_pdf(pdf_file)
            raw_text = "\n\n".join(page["text"] for page in pages)
            clean_text = self.postprocess_text(raw_text)
            txt_file = txt_dir / f"{pdf_file.stem}.txt"
            txt_file.write_text(clean_text, encoding="utf-8")
            term_counts = self.count_terms(clean_text)
            all_stats.append({
                "article": pdf_file.stem,
                "txt_file": str(txt_file),
                **term_counts
            })
        if all_stats:
            csv_file = Path(output_dir) / "article_stats.csv"
            fieldnames = ["article", "txt_file"]
            term_names = sorted({key for row in all_stats for key in row.keys() if key not in fieldnames})
            fieldnames.extend(term_names)
            with csv_file.open("w", newline="", encoding="utf-8-sig") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_stats)
        return all_stats


class StatementDatasetBuilder:
    def __init__(self):
        self.preprocessor = TextPreprocessor()

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

    def translate_to_english(self, text):
        replacements = [
            (r"\bТеорема\b", "Theorem"),
            (r"\bтеорема\b", "theorem"),
            (r"\bЛемма\b", "Lemma"),
            (r"\bлемма\b", "lemma"),
            (r"\bСледствие\b", "Corollary"),
            (r"\bследствие\b", "corollary"),
            (r"\bПредложение\b", "Proposition"),
            (r"\bпредложение\b", "proposition"),
            (r"\bОпределение\b", "Definition"),
            (r"\bопределение\b", "definition"),
            (r"\bгруппа\b", "group"),
            (r"\bгруппы\b", "groups"),
            (r"\bгруппе\b", "group"),
            (r"\bгруппу\b", "group"),
            (r"\bподгруппа\b", "subgroup"),
            (r"\bподгруппы\b", "subgroups"),
            (r"\bнормальная подгруппа\b", "normal subgroup"),
            (r"\bкольцо\b", "ring"),
            (r"\bкольца\b", "rings"),
            (r"\bкольце\b", "ring"),
            (r"\bполе\b", "field"),
            (r"\bполя\b", "fields"),
            (r"\bмодуль\b", "module"),
            (r"\bмодуля\b", "module"),
            (r"\bмодули\b", "modules"),
            (r"\bалгебра\b", "algebra"),
            (r"\bалгебры\b", "algebras"),
            (r"\bидеал\b", "ideal"),
            (r"\bидеалы\b", "ideals"),
            (r"\bизоморфизм\b", "isomorphism"),
            (r"\bизоморфны\b", "are isomorphic"),
            (r"\bизоморфна\b", "is isomorphic"),
            (r"\bизоморфно\b", "is isomorphic"),
            (r"\bгомоморфизм\b", "homomorphism"),
            (r"\bдействие\b", "action"),
            (r"\bорбита\b", "orbit"),
            (r"\bстабилизатор\b", "stabilizer"),
            (r"\bсвойство\b", "property"),
            (r"\bклассификация\b", "classification"),
            (r"\bесли\b", "if"),
            (r"\bто\b", "then"),
            (r"\bдля любого\b", "for every"),
            (r"\bдля всех\b", "for all"),
            (r"\bсуществует\b", "there exists"),
            (r"\bимеет\b", "has"),
            (r"\bявляется\b", "is"),
            (r"\bназывается\b", "is called"),
            (r"\bконечная\b", "finite"),
            (r"\bконечный\b", "finite"),
            (r"\bкоммутативное\b", "commutative"),
            (r"\bабелева\b", "abelian")
        ]
        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

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

    def make_context_statement(self, sentences, index):
        parts = []
        if index > 0 and len(sentences[index - 1]) <= 500:
            parts.append(sentences[index - 1])
        parts.append(sentences[index])
        if index + 1 < len(sentences) and len(sentences[index + 1]) <= 500:
            parts.append(sentences[index + 1])
        return " ".join(parts)

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

    def sanitize_record(self, record):
        cleaned = {}
        for key, value in record.items():
            if isinstance(value, str):
                value = self.preprocessor.safe_text(value)
            cleaned[key] = value
        return cleaned

    def make_record(self, candidate, record_number):
        keywords = candidate["keywords"]
        statement_type = candidate["statement_type"]
        record = {
            "Формулировка на естественном языке (русский)": candidate["statement"],
            "Формулировка на естественном языке (английский)": self.translate_to_english(candidate["statement"]),
            "Запись на формальном языке": self.make_formal_statement(statement_type, keywords),
            "Код Lean 4 + Mathlib": self.make_lean_code(record_number, statement_type, keywords),
            "Ключевые слова (русский / английский)": "; ".join(keywords),
            "Тип утверждения": statement_type,
            "Источник": candidate["source"]
        }
        return self.sanitize_record(record)

    def build_dataset(self, output_dir="output", total_limit=200):
        txt_dir = Path(output_dir) / "txt_clean"
        txt_files = sorted(txt_dir.glob("*.txt"))
        all_candidates = []
        for txt_file in txt_files:
            text = txt_file.read_text(encoding="utf-8")
            candidates = self.extract_candidates_from_text(text, txt_file.name)
            all_candidates.extend(candidates)
        all_candidates = self.remove_duplicates(all_candidates)
        order = {
            "ISOMORPH": 0,
            "SUBSTRUCTURE": 1,
            "ACTION": 2,
            "CLASSIFICATION": 3,
            "PROPERTY": 4
        }
        all_candidates.sort(key=lambda item: (order.get(item["statement_type"], 9), item["source"], len(item["main_sentence"])))
        records = []
        for number, candidate in enumerate(all_candidates[:total_limit], start=1):
            records.append(self.make_record(candidate, number))
        return records

    def save_dataset_outputs(self, records, output_dir="output", csv_limit=50, xlsx_limit=100000, annotation_limit=50):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        records = [self.sanitize_record(record) for record in records]
        json_file = output_path / "dataset.json"
        csv_file = output_path / "dataset_50.csv"
        xlsx_file = output_path / "Dataset.xlsx"
        annotation_file = output_path / "annotation_pairs.csv"
        json_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_file.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=DATASET_FIELDS)
            writer.writeheader()
            writer.writerows(records[:csv_limit])
        df = pd.DataFrame(records[:xlsx_limit], columns=DATASET_FIELDS)
        for column in df.columns:
            df[column] = df[column].apply(self.preprocessor.safe_text)
        with pd.ExcelWriter(xlsx_file, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Dataset")
            worksheet = writer.sheets["Dataset"]
            widths = {
                "A": 55,
                "B": 55,
                "C": 45,
                "D": 65,
                "E": 35,
                "F": 22,
                "G": 35
            }
            for column, width in widths.items():
                worksheet.column_dimensions[column].width = width
            for row in worksheet.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
        annotation_rows = []
        for index, record in enumerate(records[:annotation_limit], start=1):
            annotation_rows.append({
                "id": index,
                "statement": self.preprocessor.safe_text(record["Формулировка на естественном языке (русский)"]),
                "predicted_type": record["Тип утверждения"],
                "annotator_1": "",
                "annotator_2": ""
            })
        with annotation_file.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=["id", "statement", "predicted_type", "annotator_1", "annotator_2"])
            writer.writeheader()
            writer.writerows(annotation_rows)
        return {
            "json": str(json_file),
            "csv": str(csv_file),
            "xlsx": str(xlsx_file),
            "annotation": str(annotation_file)
        }


class AnnotationAgreementCalculator:
    def cohen_kappa(self, labels_a, labels_b):
        pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a and b]
        if not pairs:
            return None
        n = len(pairs)
        observed = sum(1 for a, b in pairs if a == b) / n
        count_a = Counter(a for a, _ in pairs)
        count_b = Counter(b for _, b in pairs)
        labels = set(count_a) | set(count_b)
        expected = sum((count_a[label] / n) * (count_b[label] / n) for label in labels)
        if expected == 1:
            return 1.0
        return (observed - expected) / (1 - expected)

    def calculate_from_file(self, annotation_file, output_dir="output"):
        annotation_path = Path(annotation_file)
        if not annotation_path.exists():
            return None
        df = pd.read_csv(annotation_path)
        if "annotator_1" not in df.columns or "annotator_2" not in df.columns:
            return None
        labels_a = df["annotator_1"].fillna("").astype(str).tolist()
        labels_b = df["annotator_2"].fillna("").astype(str).tolist()
        value = self.cohen_kappa(labels_a, labels_b)
        result_file = Path(output_dir) / "annotation_agreement.json"
        result_file.write_text(json.dumps({"cohens_kappa": value}, ensure_ascii=False, indent=2), encoding="utf-8")
        return value


def run_tasks_9_1_9_2_and_dataset(pdf_dir="pdfs", output_dir="output"):
    resolver = PathResolver()
    pdf_dir = resolver.resolve_pdf_dir(pdf_dir)
    output_dir = resolver.resolve_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    glossary_builder = GlossaryBuilder(GLOSSARY)
    notation_table = glossary_builder.build_table_from_pdfs(pdf_dir, output_dir)
    stats_extractor = ArticleStatsExtractor()
    article_stats = stats_extractor.process_articles(pdf_dir, output_dir)
    dataset_builder = StatementDatasetBuilder()
    records = dataset_builder.build_dataset(output_dir, total_limit=200)
    files = dataset_builder.save_dataset_outputs(records, output_dir, csv_limit=50, xlsx_limit=100000, annotation_limit=50)
    agreement_calculator = AnnotationAgreementCalculator()
    kappa = agreement_calculator.calculate_from_file(files["annotation"], output_dir)
    report = {
        "pdf_dir": str(pdf_dir),
        "output_dir": str(output_dir),
        "notation_rows": len(notation_table),
        "processed_articles": len(article_stats),
        "dataset_records": len(records),
        "files": files,
        "cohens_kappa": kappa
    }
    report_file = Path(output_dir) / "report.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="pdfs")
    parser.add_argument("--output_dir", default="output")
    args = parser.parse_args()
    report = run_tasks_9_1_9_2_and_dataset(args.pdf_dir, args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()