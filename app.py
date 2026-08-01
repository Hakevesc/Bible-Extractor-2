import streamlit as st
import json
import os
from io import BytesIO
import zipfile

import step_bible_scraper as sb

# Bible book abbreviations and categories
BIBLE_BOOKS = {
    "Old Testament": {
        1: {"abbr": "GEN", "name": "ዘፍጥት"},
        2: {"abbr": "EXO", "name": "ጸአት"},
        3: {"abbr": "LEV", "name": "ዘሌዋውያን"},
        4: {"abbr": "NUM", "name": "ዘኍልቍ"},
        5: {"abbr": "DEU", "name": "ዘዳግም"},
        6: {"abbr": "JOS", "name": "ኢያሱ"},
        7: {"abbr": "JDG", "name": "መሳፍንት"},
        8: {"abbr": "RUT", "name": "ሩት"},
        9: {"abbr": "1SA", "name": "1ኛ ሳሙኤል"},
        10: {"abbr": "2SA", "name": "2ኛ ሳሙኤል"},
        11: {"abbr": "1KI", "name": "1ኛ ነገሥት"},
        12: {"abbr": "2KI", "name": "2ኛ ነገሥት"},
        13: {"abbr": "1CH", "name": "1ኛ ዜና መዋዕል"},
        14: {"abbr": "2CH", "name": "2ኛ ዜና መዋዕል"},
        15: {"abbr": "EZR", "name": "ዝራ"},
        16: {"abbr": "NEH", "name": "ነህሚያ"},
        17: {"abbr": "EST", "name": "እስቴር"},
        18: {"abbr": "JOB", "name": "ዮብ"},
        19: {"abbr": "PSA", "name": "መዝሙረ ዊት"},
        20: {"abbr": "PRO", "name": "ምሳሌ"},
        21: {"abbr": "ECC", "name": "መክብብ"},
        22: {"abbr": "SNG", "name": "መሃልያ መሃልይ"},
        23: {"abbr": "ISA", "name": "ሳይያስ"},
        24: {"abbr": "JER", "name": "ኤርምያስ"},
        25: {"abbr": "LAM", "name": "ወይኖ"},
        26: {"abbr": "EZK", "name": "ሕዝቅኤል"},
        27: {"abbr": "DAN", "name": "ዳንኤል"},
        28: {"abbr": "HOS", "name": "ሴዕ"},
        29: {"abbr": "JOE", "name": "ዮኤል"},
        30: {"abbr": "AMO", "name": "ዓሞጽ"},
        31: {"abbr": "OBA", "name": "ዖዱ"},
        32: {"abbr": "JON", "name": "ናስ"},
        33: {"abbr": "MIC", "name": "ክያስ"},
        34: {"abbr": "NAM", "name": "ናሑም"},
        35: {"abbr": "HAB", "name": "ባቁቅ"},
        36: {"abbr": "ZEP", "name": "ሶፎንያስ"},
        37: {"abbr": "HAG", "name": "ሐጌ"},
        38: {"abbr": "ZEC", "name": "ዘካርያስ"},
        39: {"abbr": "MAL", "name": "ልአክያስ"},
    },
    "New Testament": {
        40: {"abbr": "MAT", "name": "ማቴዎስ"},
        41: {"abbr": "MRK", "name": "ማርቆስ"},
        42: {"abbr": "LUK", "name": "ሉቃስ"},
        43: {"abbr": "JHN", "name": "ዮሐንስ"},
        44: {"abbr": "ACT", "name": "የሐዋርያት ሥራ"},
        45: {"abbr": "ROM", "name": "ሮሜ"},
        46: {"abbr": "1CO", "name": "1ኛ ቆሮንስ"},
        47: {"abbr": "2CO", "name": "2 ቆሮንቶስ"},
        48: {"abbr": "GAL", "name": "ገላትያ"},
        49: {"abbr": "EPH", "name": "ፌሶን"},
        50: {"abbr": "PHP", "name": "ፊልጵስዩስ"},
        51: {"abbr": "COL", "name": "ቈላስይስ"},
        52: {"abbr": "1TH", "name": "1ኛ ተሰሎንቄ"},
        53: {"abbr": "2TH", "name": "2 ተሰሎንቄ"},
        54: {"abbr": "1TI", "name": "1ኛ ሞቴዎስ"},
        55: {"abbr": "2TI", "name": "2ኛ ጢሞቴዎስ"},
        56: {"abbr": "TIT", "name": "ጢቶስ"},
        57: {"abbr": "PHM", "name": "ፊልሞን"},
        58: {"abbr": "HEB", "name": "ብራውያን"},
        59: {"abbr": "JAS", "name": "ያዕቆብ"},
        60: {"abbr": "1PE", "name": "1ኛ ጴጥሮስ"},
        61: {"abbr": "2PE", "name": "2ኛ ጴሮስ"},
        62: {"abbr": "1JN", "name": "1ኛ ዮሐንስ"},
        63: {"abbr": "2JN", "name": "2ኛ ዮሐንስ"},
        64: {"abbr": "3JN", "name": "3ኛ ዮሐንስ"},
        65: {"abbr": "JUD", "name": "የይሁዳ መልእክት"},
        66: {"abbr": "REV", "name": "እይ"},
    }
}

@st.cache_data(ttl="1d", max_entries=10)
def load_book_verses(book_id, book_name):
    """Fetch a book's verses from STEP Bible (Selenium if available,
    otherwise the REST API fallback)."""
    try:
        return sb.get_book_verses(book_id, book_name)
    except Exception as e:
        st.error(f"Error fetching book data: {e}")
        return []

def main():
    st.set_page_config(
        page_title="Amharic Bible Downloader",
        page_icon="📖",
        layout="wide"
    )
    
    st.title(" Amharic Bible JSON Downloader")
    st.markdown("---")
    
    st.info(
        f"Data source: STEP Bible ({sb.AMHARIC_VERSION}) · "
        f"Uses Selenium (`span[data-osisid]`) when a browser is available, "
        f"otherwise the STEP Bible REST API."
    )
    
    # Sidebar for category selection
    st.sidebar.header("📚 Download Options")
    
    category = st.sidebar.selectbox(
        "Select Testament",
        ["All Books", "Old Testament", "New Testament"]
    )
    
    # Build book selection based on category
    available_books = {}
    if category == "All Books":
        for cat_name, books in BIBLE_BOOKS.items():
            available_books.update(books)
    elif category == "Old Testament":
        available_books = BIBLE_BOOKS["Old Testament"]
    else:
        available_books = BIBLE_BOOKS["New Testament"]
    
    # Create book options for multiselect
    book_options = {f"{info['abbr']} - {info['name']}": (book_id, info) 
                    for book_id, info in available_books.items()}
    
    selected_books = st.sidebar.multiselect(
        "Select Book(s) to Download",
        options=list(book_options.keys()),
        help="Hold Ctrl (or Cmd on Mac) to select multiple books"
    )
    
    # Quick select buttons
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("Select All"):
            st.session_state.selected = list(book_options.keys())
    with col2:
        if st.button("Clear"):
            st.session_state.selected = []
    
    # Main content area
    st.header("Download Amharic Bible Books")
    st.markdown("Select books from the sidebar and click download")
    
    if not selected_books:
        st.info("👈 Please select at least one book from the sidebar")
        st.stop()
    
    # Show selected books
    st.subheader(f"Selected Books ({len(selected_books)})")
    for book_label in selected_books:
        book_id, info = book_options[book_label]
        st.markdown(f"- **{info['abbr']}** - {info['name']} (Book {book_id})")
    
    # Download options
    st.markdown("---")
    download_format = st.radio(
        "Download Format",
        ["Individual JSON Files (ZIP)", "Single Combined JSON File"],
        horizontal=True
    )
    
    if st.button("📥 Download Selected Books", type="primary", width="stretch"):
        with st.spinner("Fetching selected books from STEP Bible..."):
            try:
                if download_format == "Individual JSON Files (ZIP)":
                    # Create ZIP file with individual JSON files
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for book_label in selected_books:
                            book_id, info = book_options[book_label]
                            verses = load_book_verses(book_id, info["name"])
                            if verses:
                                json_str = json.dumps(verses, ensure_ascii=False, indent=2)
                                zip_file.writestr(f"{info['abbr']}.json", json_str)
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="⬇️ Download ZIP File",
                        data=zip_buffer,
                        file_name="amharic_bible_books.zip",
                        mime="application/zip",
                        width="stretch"
                    )
                
                else:
                    # Single combined JSON file
                    all_verses = []
                    for book_label in selected_books:
                        book_id, info = book_options[book_label]
                        verses = load_book_verses(book_id, info["name"])
                        all_verses.extend(verses)
                    
                    json_str = json.dumps(all_verses, ensure_ascii=False, indent=2)
                    # Name the file after the selected book(s):
                    # single book -> e.g. MAT.json
                    # multiple books -> e.g. amharic_bible_combined.json
                    selected_abbrs = [book_options[bl][1]["abbr"] for bl in selected_books]
                    if len(selected_abbrs) == 1:
                        file_name = f"{selected_abbrs[0]}.json"
                    else:
                        file_name = "amharic_bible_combined.json"
                    st.download_button(
                        label="⬇️ Download Combined JSON",
                        data=json_str,
                        file_name=file_name,
                        mime="application/json",
                        width="stretch"
                    )
                
                st.success("✅ Download ready!")
                
            except Exception as e:
                st.error(f"Error preparing download: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Amharic Bible JSON Downloader | Data source: STEP Bible (AmhNASV)</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()