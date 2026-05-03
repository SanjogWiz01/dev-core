#!/usr/bin/env python3

"""Read a line of input from the user and print it in reverse order."""

def main():
    try:
        s = input("Enter text: ")
    except EOFError:
        # If no input is provided (e.g., piped/EOF), treat as empty string
        s = ""
    # Reverse the string and print
    print(s[::-1])

if __name__ == "__main__":
    main()
