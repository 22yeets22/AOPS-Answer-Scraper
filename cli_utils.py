from colorama import Fore, Style


def get_valid_int(prompt_text, min_val, max_val, min_msg=None, max_msg=None, allow_zero=True):
    while True:
        try:
            user_input = prompt(prompt_text).strip()
            if allow_zero and user_input == "0":
                return 0

            value = int(user_input)
            if value < min_val:
                if min_msg:
                    print_error(min_msg)
                else:
                    print_error(f"Please enter a number greater than or equal to {min_val}.")
                continue
            if value > max_val:
                if max_msg:
                    print_error(max_msg)
                else:
                    print_error(f"Please enter a number less than or equal to {max_val}.")
                continue

            return value
        except ValueError:
            print_error("Invalid input. Please enter a valid number.")


def print_error(text):
    print(f"{Fore.RED}{Style.BRIGHT}❌ {text}")


def print_success(text):
    print(f"{Fore.GREEN}{Style.BRIGHT}✅ {text}")


def print_info(text):
    print(f"{Fore.BLUE}ℹ️  {text}")


def print_header(text):
    print(f"{Fore.MAGENTA}{Style.BRIGHT}{text}")


def prompt(text, end=""):
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}", end=end)
    return input()
