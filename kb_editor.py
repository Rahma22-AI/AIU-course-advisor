import streamlit as st
import pandas as pd
import os

FILENAME = 'courses.csv'

# Ensure CSV exists
if not os.path.exists(FILENAME):
    df = pd.DataFrame(columns=[
        "Course Code", "Course Name", "Description",
        "Prerequisites", "Co-requisites",
        "Credit Hours", "Semester Offered"
    ])
    df.to_csv(FILENAME, index=False)

def load_courses():
    return pd.read_csv(FILENAME)

def save_courses(df):
    df.to_csv(FILENAME, index=False)

def add_course():
    print("\n--- Add a New Course ---")
    code = input("Course Code: ")
    name = input("Course Name: ")
    desc = input("Description: ")
    prereq = input("Prerequisites (comma-separated): ")
    coreq = input("Co-requisites (comma-separated): ")
    credit = int(input("Credit Hours: "))
    semester = input("Semester Offered (Fall/Spring/Both): ")

    df = load_courses()
    if code in df["Course Code"].values:
        print("Course already exists!")
        return
    df.loc[len(df.index)] = [code, name, desc, prereq, coreq, credit, semester]
    save_courses(df)
    print(f"{code} added successfully.\n")

def view_courses():
    df = load_courses()
    print("\n--- Course List ---")
    print(df)

def delete_course():
    code = input("Enter course code to delete: ")
    df = load_courses()
    df = df[df["Course Code"] != code]
    save_courses(df)
    print(f"{code} deleted (if existed).\n")

def main():
    while True:
        print("\nKnowledge Base Editor")
        print("1. View Courses")
        print("2. Add Course")
        print("3. Delete Course")
        print("4. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            view_courses()
        elif choice == "2":
            add_course()
        elif choice == "3":
            delete_course()
        elif choice == "4":
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
