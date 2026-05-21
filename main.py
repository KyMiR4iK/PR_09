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
        self.all_terms = {**KEY_TERMS, **EXTRA_TERMS}
    
    def extract_text_from_pdf(self, pdf_path):

        doc = fitz.open(pdf_path)
        full_text = []
        
        for page in doc:
            full_text.append(page.get_text())
        
        return "\n".join(full_text)
    
    def postprocess_text(self, text):

        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        

        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        

        text = re.sub(r'\s+', ' ', text)
        

        text = re.sub(r'[^\S\n]+', ' ', text)
        
        return text.strip()
    
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