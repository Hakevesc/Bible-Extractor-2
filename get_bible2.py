import json
import requests
import os

# Standard Bible book abbreviations matching your screenshots
ABBREVIATIONS = {
    1: "GEN", 2: "EXO", 3: "LEV", 4: "NUM", 5: "DEU", 6: "JOS", 7: "JDG", 8: "RUT", 
    9: "1SA", 10: "2SA", 11: "1KI", 12: "2KI", 13: "1CH", 14: "2CH", 15: "EZR", 16: "NEH", 
    17: "EST", 18: "JOB", 19: "PSA", 20: "PRO", 21: "ECC", 22: "SNG", 23: "ISA", 24: "JER", 
    25: "LAM", 26: "EZK", 27: "DAN", 28: "HOS", 29: "JOE", 30: "AMO", 31: "OBA", 32: "JON", 
    33: "MIC", 34: "NAM", 35: "HAB", 36: "ZEP", 37: "HAG", 38: "ZEC", 39: "MAL",
    40: "MAT", 41: "MRK", 42: "LUK", 43: "JHN", 44: "ACT", 45: "ROM", 46: "1CO", 47: "2CO", 
    48: "GAL", 49: "EPH", 50: "PHP", 51: "COL", 52: "1TH", 53: "2TH", 54: "1TI", 55: "2TI", 
    56: "TIT", 57: "PHM", 58: "HEB", 59: "JAS", 60: "1PE", 61: "2PE", 62: "1JN", 63: "2JN", 
    64: "3JN", 65: "JUD", 66: "REV"
}

def get_amharic_bible_data():
    url = "https://raw.githubusercontent.com/magna25/amharic-bible-json/main/amharic_bible.json"
    cache_file = "full_amharic_bible_cache.json"
    
    if not os.path.exists(cache_file):
        print(" Downloading full Amharic Bible data (one time only, ~2MB)...")
        response = requests.get(url)
        response.raise_for_status()
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        print("✅ Download complete!\n")
    else:
        print("⏳ Loading cached Bible data...\n")
        
    with open(cache_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    formatted_books = {}
    books_list = raw_data.get("books", [])
    
    for book_index, book in enumerate(books_list, start=1):
        book_name = book.get("title", "Unknown Book").strip()
        formatted_books[book_index] = {
            "name": book_name,
            "id": book_index,
            "chapters": book.get("chapters", [])
        }
        
    return formatted_books

def format_book_verses(book_info):
    formatted_verses = []
    book_name = book_info["name"]
    book_id = book_info["id"]
    
    for chap in book_info["chapters"]:
        chapter_num_str = chap.get("chapter", "0")
        try:
            chapter_num = int(chapter_num_str)
        except ValueError:
            chapter_num = 0
            
        verses = chap.get("verses", [])
        for verse_index, verse_text in enumerate(verses, start=1):
            clean_text = str(verse_text).strip()
            if clean_text:
                formatted_verses.append({
                    "book_name": book_name,
                    "book": book_id,
                    "chapter": chapter_num,
                    "verse": verse_index,
                    "text": clean_text
                })
    return formatted_verses

def save_to_json(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 55)
    print(" 📖 Amharic Bible JSON Exporter")
    print("=" * 55)
    
    bible_data = get_amharic_bible_data()
    
    print("Available Books:")
    for idx, info in bible_data.items():
        abbr = ABBREVIATIONS.get(idx, "UNK")
        print(f"  {idx:2d}. {info['name']} ({abbr}.json)")
        
    print("\n" + "-" * 55)
    print("OPTIONS:")
    print("  • Type a number (e.g., 65) to download a specific book")
    print("  • Type 'all' to download ALL 66 books as separate files")
    print("  • Type 'quit' to exit")
    print("-" * 55)
    
    while True:
        choice = input("\n Enter your choice: ").strip().lower()
        
        if choice == 'quit':
            print("Exiting program. Goodbye!")
            break
            
        if choice == 'all':
            print("⏳ Compiling and saving all 66 books...")
            for book_idx, info in bible_data.items():
                export_data = format_book_verses(info)
                abbr = ABBREVIATIONS.get(book_idx, f"BOOK_{book_idx}")
                filename = f"{abbr}.json"
                save_to_json(export_data, filename)
            print(f"✅ SUCCESS: Saved all 66 books to your folder!")
            break
            
        try:
            book_num = int(choice)
            if book_num in bible_data:
                info = bible_data[book_num]
                abbr = ABBREVIATIONS.get(book_num, f"BOOK_{book_num}")
                
                print(f"⏳ Formatting '{info['name']}'...")
                export_data = format_book_verses(info)
                
                filename = f"{abbr}.json"
                save_to_json(export_data, filename)
                print(f"✅ SUCCESS: Saved '{info['name']}' ({len(export_data)} verses) to '{filename}'")
            else:
                print("❌ Invalid book number. Please check the list and try again.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number, 'all', or 'quit'.")

if __name__ == "__main__":
    main()