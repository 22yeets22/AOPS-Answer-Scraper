import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from fake_useragent import UserAgent
from pylatexenc.latex2text import LatexNodes2Text

from cli_utils import (
    get_valid_int,
    print_error,
    print_header,
    print_info,
    print_success,
    prompt,
)

# Create fake useragent, latex reader, and initialize colorama
ua = UserAgent()
converter = LatexNodes2Text()
init(autoreset=True)

# Years that AMC tests started and ended
TEST_AVAILABILITY = {
    "AJHSME": {
        "start_year": 1985,
        "end_year": 1998,
        "description": "American Junior High School Mathematics Examination",
        "url_format": "AJHSME",
    },
    "AHSME": {
        "start_year": 1950,
        "end_year": 1998,
        "description": "American High School Mathematics Examination",
        "url_format": "AHSME",
    },
    "8": {"start_year": 1999, "end_year": None, "description": "AMC 8", "url_format": "AMC_8"},
    "10A": {"start_year": 2002, "end_year": None, "description": "AMC 10A", "url_format": "AMC_10A"},
    "10B": {"start_year": 2002, "end_year": None, "description": "AMC 10B", "url_format": "AMC_10B"},
    "10": {"start_year": 2000, "end_year": 2001, "description": "AMC 10", "url_format": "AMC_10"},  # Legacy format
    "12A": {"start_year": 2002, "end_year": None, "description": "AMC 12A", "url_format": "AMC_12A"},
    "12B": {"start_year": 2002, "end_year": None, "description": "AMC 12B", "url_format": "AMC_12B"},
    "12": {"start_year": 2000, "end_year": 2001, "description": "AMC 12", "url_format": "AMC_12"},  # Legacy format
    "AIME": {
        "start_year": 1983,
        "end_year": 1999,
        "description": "American Invitational Mathematics Examination",
        "url_format": "AIME",
    },
    "AIME_I": {
        "start_year": 2000,
        "end_year": None,
        "description": "American Invitational Mathematics Examination I",
        "url_format": "AIME_I",
    },
    "AIME_II": {
        "start_year": 2000,
        "end_year": None,
        "description": "American Invitational Mathematics Examination II",
        "url_format": "AIME_II",
    },
}


def get_valid_test_type(year):
    """Get a valid test type based on the year."""
    year_int = int(year)

    try:
        print_header(f"\n📋 Available test types for {year}:")

        # Get the available tests for the year
        valid_tests = []
        for test, config in TEST_AVAILABILITY.items():
            if config["start_year"] <= year_int and (config["end_year"] is None or year_int <= config["end_year"]):
                valid_tests.append(test)
                print(f"{Fore.GREEN}  • {test} ({config['description']})")

        print()
        while True:
            test_type = prompt("🔤 Enter the test type: ").strip().upper()
            if not test_type:
                print_error("Test type cannot be empty. Please try again.")
                continue

            # Validate test type based on year
            if test_type in valid_tests:
                print_success(f"Test type '{test_type}' is valid for the year {year}.")
                return test_type
            else:
                print_error("Invalid test type. Please choose from the available options.")
                continue
    except KeyboardInterrupt:
        sys.exit(0)


def construct_url(year, test_type):
    """Construct the AoPS wiki URL for the given year and test type."""
    base_url = "https://artofproblemsolving.com/wiki/index.php"

    if test_type in ["AIME", "AIME_I", "AIME_II", "AJHSME", "AHSME"]:
        return f"{base_url}/{year}_{test_type}_Answer_Key"
    else:
        return f"{base_url}/{year}_AMC_{test_type}_Answer_Key"


def scrape_answers(url):
    """Scrape answers from the AoPS wiki page."""
    try:
        print_info(f"Fetching data from: {url}")

        response = requests.get(url, headers={"User-Agent": ua.random}, timeout=10)
        response.raise_for_status()

        print_success("Successfully fetched webpage!")

        soup = BeautifulSoup(response.text, "html.parser")

        elements = soup.select("div.mw-parser-output > ol > li")
        if elements:
            print_success("Found answer elements on the page.")
            return [li.text.strip() for li in elements if li.text.strip()]
        else:
            print_error("No answers found with the expected format. The page structure might have changed.")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"Error fetching the webpage: {e}")
        return None


def find_solutions(url, answers):
    def fetch_solution_sections(soup):
        toc_sections = soup.find_all(class_="toclevel-1")
        result = []
        for content in toc_sections:
            text_el = content.find(class_="toctext")
            if text_el:
                result.append(text_el.text.strip())
        return result

    def extract_solution_content(soup, section_index):
        mw_content = soup.find("div", class_="mw-parser-output")
        if not mw_content:
            return []

        # Find all <h2> tags to identify sections (section index 0 - first section)
        h2_tags = mw_content.find_all("h2")
        h2_tags.pop(0)  # remove the "contents" h2
        if not (0 <= section_index < len(h2_tags)):
            return []

        selected_h2 = h2_tags[section_index]
        solution_content = []

        # find all siblings, then stop at next h2 (which is the end of the section)
        sibling = selected_h2.next_sibling
        while sibling:
            if getattr(sibling, "name", None) == "h2":
                break
            if getattr(sibling, "name", None) in ["p", "ul", "ol", "div"]:
                # Get all text, including lists and math images
                for elem in sibling.descendants:
                    if getattr(elem, "name", None) == "img":
                        latex = elem.get("alt", "")
                        solution_content.append(converter.latex_to_text(latex).strip("\n"))
                    elif isinstance(elem, str):
                        text = elem.strip()
                        if text:
                            solution_content.append(text.strip())
            solution_content.append("\n")
            sibling = sibling.next_sibling
        return solution_content

    max_question = len(answers)
    print_info(f"Ready to fetch solutions for questions 1 to {max_question}.")

    while True:
        try:
            question = get_valid_int("🔍 Enter the question number (or 0 to exit): ", 1, max_question)
            if question == 0:
                print_info("Exiting solution finder.")
                break

            print_info(f"Fetching solution page for question {question}...")
            problem_url = f"{url.replace('_Answer_Key', '_Problems')}/Problem_{question}"
            response = requests.get(problem_url, headers={"User-Agent": ua.random}, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            sections = fetch_solution_sections(soup)

            if not sections:
                print_error("No solution sections found for this question.")
                continue

            print_info("Available solution sections:")
            for i, section in enumerate(sections, start=1):
                print(f"{Fore.CYAN}{i}. {section}")

            section_choice = get_valid_int("📖 Enter section number to view (or 0 to go back): ", 1, len(sections))
            if section_choice == 0:
                continue

            print_info("Fetching and displaying solution...")
            content = extract_solution_content(soup, section_choice - 1)

            if content:
                print_success("📝 Solution:")
                print(" ".join(content))
            else:
                print_error("No readable solution content found in the selected section.")

        except requests.exceptions.RequestException as e:
            print_error(f"Network error while fetching the page: {e}")


def main():
    """Main function to run the AMC answer scraper."""
    print_header("🧮 AMC/AIME/AJHSME Answer Key Scraper 🧮")
    print(f"{Fore.MAGENTA}{'=' * 40}")

    while True:
        try:
            # Get valid inputs from user
            test_year = str(
                get_valid_int(
                    "📅 Enter the year of the AMC test: ",
                    1950,
                    datetime.now().year,
                    min_msg="Tests started in 1950, please enter a year after.",
                    max_msg="Do not enter a year in the future",
                    allow_zero=False,
                )
            )
            test_type = get_valid_test_type(test_year)

            # Construct URL and scrape answers
            url = construct_url(test_year, test_type)
            answers = scrape_answers(url)  #

            if answers:
                print(f"\n{Fore.BLUE}{Style.BRIGHT}🎯 Answers for {test_year} {test_type}:")
                print(f"{Fore.BLUE}{'-' * 50}")

                # Print answers with alternating colors
                for i, answer in enumerate(answers, 1):
                    print(Fore.WHITE, end="")
                    color = Style.BRIGHT if i % 2 == 1 else Style.NORMAL
                    print(f"{color}{i:2d}. {answer}")
            else:
                print_error("Failed to retrieve answers. Please check if the test exists on AoPS wiki.")

            solutions = prompt("\n📖 Do you want to see the solutions to the answers? (yes/no): ").strip().lower()
            if solutions and solutions[0] == "y":
                find_solutions(url, answers)

            choice = prompt("\n🔄 Do you want to scrape another test? (yes/no): ").strip().lower()
            if choice and choice[0] == "n":
                break

            print(f"\n{Fore.MAGENTA}{'=' * 40}")
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print_error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
